"""
Market Mode Detector
===================

High-level interface for detecting market mode (trend vs cycle)
and filtering signals accordingly.

This integrates Ehlers' techniques with our Lorentzian system.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from .sinewave_indicator import SinewaveIndicator


class MarketModeDetector:
    """
    Detects market mode and provides signal filtering
    
    Key features:
    - Identifies trending vs cycling markets
    - Filters signals based on market mode
    - Provides mode confidence scores
    - Adapts parameters based on market conditions
    """
    
    def __init__(self, mode_smoothing: int = 10, 
                 trend_threshold: float = 0.1,
                 min_cycle_strength: float = 0.3):
        """
        Initialize Market Mode Detector
        
        Args:
            mode_smoothing: Bars to smooth mode detection
            trend_threshold: Threshold for trend detection
            min_cycle_strength: Minimum strength for cycle mode
        """
        self.mode_smoothing = mode_smoothing
        self.trend_threshold = trend_threshold
        self.min_cycle_strength = min_cycle_strength
        
        # Initialize Sinewave indicator
        self.sinewave = SinewaveIndicator()
        
        # Storage for mode history
        self.mode_history = []
        self.confidence_history = []
        
    def calculate_mode_confidence(self, sine: pd.Series, 
                                 leadsine: pd.Series) -> pd.Series:
        """
        Calculate confidence in mode detection
        
        Args:
            sine: Sine wave values
            leadsine: Lead sine values
            
        Returns:
            Confidence scores (0-1)
        """
        # Calculate separation between lines
        separation = (sine - leadsine).abs()
        
        # Normalize to 0-1 range
        rolling_max = separation.rolling(window=50).max()
        rolling_min = separation.rolling(window=50).min()
        
        # Avoid division by zero
        range_val = rolling_max - rolling_min
        range_val[range_val == 0] = 1
        
        # Confidence is high when separation is clear
        confidence = (separation - rolling_min) / range_val
        
        # Smooth the confidence
        confidence = confidence.rolling(window=5).mean()
        
        return confidence.fillna(0.5)
    
    def detect_trend_strength(self, prices: pd.Series, 
                            period: int = 20) -> pd.Series:
        """
        Calculate trend strength using linear regression
        
        Args:
            prices: Price series
            period: Lookback period
            
        Returns:
            Trend strength (0-1)
        """
        def calculate_r_squared(y):
            """Calculate R-squared of linear regression"""
            if len(y) < 3:
                return 0
            
            x = np.arange(len(y))
            
            # Handle NaN values
            mask = ~np.isnan(y)
            if mask.sum() < 3:
                return 0
            
            x = x[mask]
            y = y[mask]
            
            # Linear regression
            A = np.vstack([x, np.ones(len(x))]).T
            try:
                m, c = np.linalg.lstsq(A, y, rcond=None)[0]
                
                # Calculate R-squared
                y_pred = m * x + c
                ss_res = np.sum((y - y_pred) ** 2)
                ss_tot = np.sum((y - y.mean()) ** 2)
                
                if ss_tot == 0:
                    return 0
                    
                r_squared = 1 - (ss_res / ss_tot)
                return max(0, min(1, r_squared))
                
            except:
                return 0
        
        # Calculate rolling R-squared
        trend_strength = prices.rolling(window=period).apply(calculate_r_squared)
        
        return trend_strength.fillna(0)
    
    def detect_market_mode(self, prices: pd.Series, 
                          hl2: Optional[pd.Series] = None) -> Dict:
        """
        Comprehensive market mode detection
        
        Args:
            prices: Close prices
            hl2: (High + Low) / 2, if None will use close
            
        Returns:
            Dictionary with mode analysis
        """
        # Use HL2 if provided, otherwise use close
        analysis_prices = hl2 if hl2 is not None else prices
        
        # Get Sinewave analysis
        sinewave_result = self.sinewave.calculate(analysis_prices)
        
        # Calculate additional metrics
        mode_confidence = self.calculate_mode_confidence(
            sinewave_result['sine'], 
            sinewave_result['leadsine']
        )
        
        trend_strength = self.detect_trend_strength(prices)
        
        # Refine mode detection with multiple criteria
        refined_mode = self._refine_mode_detection(
            sinewave_result['mode'],
            mode_confidence,
            trend_strength,
            sinewave_result['period']
        )
        
        # Store history
        self.mode_history.append(refined_mode)
        self.confidence_history.append(mode_confidence)
        
        return {
            'mode': refined_mode,
            'confidence': mode_confidence,
            'trend_strength': trend_strength,
            'cycle_period': sinewave_result['period'],
            'sine': sinewave_result['sine'],
            'leadsine': sinewave_result['leadsine'],
            'sinewave_signals': sinewave_result['signals']
        }
    
    def _refine_mode_detection(self, base_mode: pd.Series,
                              confidence: pd.Series,
                              trend_strength: pd.Series,
                              period: pd.Series) -> pd.Series:
        """
        Refine mode detection using multiple criteria
        """
        refined_mode = base_mode.copy()
        
        # Strong trend overrides cycle detection
        strong_trend = trend_strength > 0.7
        refined_mode[strong_trend] = 'trend'
        
        # Low confidence defaults to trend (safer)
        low_confidence = confidence < 0.3
        refined_mode[low_confidence] = 'trend'
        
        # Very short or long periods indicate trend
        abnormal_period = (period < 10) | (period > 50)
        refined_mode[abnormal_period] = 'trend'
        
        # Smooth mode transitions
        # Convert to numeric for smoothing
        mode_numeric = (refined_mode == 'cycle').astype(int)
        smoothed = mode_numeric.rolling(
            window=self.mode_smoothing, 
            min_periods=1
        ).mean()
        
        # Convert back to labels
        refined_mode[smoothed > 0.5] = 'cycle'
        refined_mode[smoothed <= 0.5] = 'trend'
        
        return refined_mode
    
    def filter_signals(self, ml_signals: pd.Series, 
                      market_mode: pd.Series,
                      confidence: pd.Series,
                      allow_trend_trades: bool = False) -> pd.Series:
        """
        Filter ML signals based on market mode
        
        Args:
            ml_signals: Original ML signals
            market_mode: Detected market mode
            confidence: Mode confidence scores
            allow_trend_trades: Whether to allow trades in trends
            
        Returns:
            Filtered signal series
        """
        filtered_signals = ml_signals.copy()
        
        if not allow_trend_trades:
            # Only allow signals in cycle mode
            trend_mask = market_mode == 'trend'
            filtered_signals[trend_mask] = 0
        else:
            # Reduce position size in trends
            trend_mask = market_mode == 'trend'
            # This would be handled by position sizing
            
        # Filter low confidence signals
        low_conf_mask = confidence < self.min_cycle_strength
        filtered_signals[low_conf_mask] = 0
        
        return filtered_signals
    
    def get_mode_stats(self) -> Dict:
        """Get statistics about market modes"""
        if not self.mode_history:
            return {}
        
        # Concatenate history
        all_modes = pd.concat(self.mode_history)
        all_confidence = pd.concat(self.confidence_history)
        
        # Calculate statistics
        mode_counts = all_modes.value_counts()
        mode_pct = mode_counts / len(all_modes) * 100
        
        return {
            'mode_distribution': mode_pct.to_dict(),
            'avg_confidence': all_confidence.mean(),
            'current_mode': all_modes.iloc[-1] if len(all_modes) > 0 else None,
            'mode_changes': (all_modes != all_modes.shift()).sum()
        }


def test_market_mode_detector():
    """Test the market mode detector"""
    
    # Create mixed market data
    bars = 300
    
    # Trending section
    trend1 = np.linspace(100, 110, 100) + np.random.normal(0, 0.2, 100)
    
    # Cycling section
    t = np.linspace(0, 6 * np.pi, 100)
    cycle = 110 + 3 * np.sin(t) + np.random.normal(0, 0.1, 100)
    
    # Another trend
    trend2 = np.linspace(110, 105, 100) + np.random.normal(0, 0.2, 100)
    
    # Combine
    prices = np.concatenate([trend1, cycle, trend2])
    price_series = pd.Series(prices, index=pd.date_range('2024-01-01', periods=bars))
    
    # Create some fake ML signals
    ml_signals = pd.Series(0, index=price_series.index)
    # Add signals throughout
    signal_indices = np.random.choice(bars, size=30, replace=False)
    ml_signals.iloc[signal_indices] = np.random.choice([-1, 1], size=30)
    
    # Test detector
    detector = MarketModeDetector()
    mode_result = detector.detect_market_mode(price_series)
    
    # Filter signals
    filtered_signals = detector.filter_signals(
        ml_signals,
        mode_result['mode'],
        mode_result['confidence']
    )
    
    print("Market Mode Detector Test Results:")
    print(f"Mode distribution:")
    print(mode_result['mode'].value_counts())
    print(f"\nOriginal signals: {(ml_signals != 0).sum()}")
    print(f"Filtered signals: {(filtered_signals != 0).sum()}")
    print(f"\nMode statistics:")
    print(detector.get_mode_stats())
    
    return mode_result, filtered_signals


if __name__ == "__main__":
    test_market_mode_detector()