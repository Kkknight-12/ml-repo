"""
Mode-Aware Bar Processor
=======================

Enhanced bar processor that integrates market mode detection
for improved signal quality.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from .enhanced_bar_processor import EnhancedBarProcessor, BarResult
from indicators.ehlers.market_mode_detector import MarketModeDetector
from config.settings import TradingConfig


@dataclass
class ModeAwareBarResult(BarResult):
    """Extended bar result with market mode information"""
    market_mode: str = 'unknown'
    mode_confidence: float = 0.5
    trend_strength: float = 0.0
    cycle_period: float = 20.0
    mode_filtered_signal: int = 0


class ModeAwareBarProcessor(EnhancedBarProcessor):
    """
    Enhanced bar processor with market mode awareness
    
    Key improvements:
    - Filters signals based on market mode
    - Adapts parameters for trend vs cycle conditions
    - Provides mode-specific confidence scores
    """
    
    def __init__(self, config: TradingConfig, symbol: str, 
                 timeframe: str = "5minute",
                 allow_trend_trades: bool = False,
                 min_mode_confidence: float = 0.3):
        """
        Initialize mode-aware processor
        
        Args:
            config: Trading configuration
            symbol: Symbol being processed
            timeframe: Timeframe for analysis
            allow_trend_trades: Whether to allow signals in trending markets
            min_mode_confidence: Minimum confidence for mode detection
        """
        super().__init__(config, symbol, timeframe)
        
        # Mode detection settings
        self.allow_trend_trades = allow_trend_trades
        self.min_mode_confidence = min_mode_confidence
        
        # Initialize market mode detector
        self.mode_detector = MarketModeDetector(
            mode_smoothing=10,
            trend_threshold=0.1,
            min_cycle_strength=min_mode_confidence
        )
        
        # Storage for mode analysis
        self.mode_history = []
        self.last_mode_analysis = None
        
    def process_bar(self, open_price: float, high: float, low: float, 
                   close: float, volume: float) -> Optional[ModeAwareBarResult]:
        """
        Process bar with market mode awareness
        
        Returns:
            ModeAwareBarResult with mode-filtered signals
        """
        # Get base processing result
        base_result = super().process_bar(open_price, high, low, close, volume)
        
        if base_result is None:
            return None
        
        # Calculate HL2 for mode detection
        hl2 = pd.Series([(high + low) / 2], index=[pd.Timestamp.now()])
        
        # Get recent price history for mode detection
        recent_closes = []
        for i in range(min(50, len(self.bars))):
            recent_closes.append(self.bars.get_close(i))
        
        recent_closes = pd.Series(
            list(reversed(recent_closes)),  # Reverse to get chronological order
            index=pd.date_range(end=pd.Timestamp.now(), periods=len(recent_closes), freq='5min')
        )
        
        # Need enough history for mode detection
        if len(recent_closes) < 30:
            # Return base result without mode filtering
            return ModeAwareBarResult(
                **base_result.__dict__,
                market_mode='unknown',
                mode_confidence=0.5,
                trend_strength=0.0,
                cycle_period=20.0,
                mode_filtered_signal=base_result.signal
            )
        
        # Perform market mode detection
        mode_analysis = self._detect_market_mode(recent_closes, hl2)
        
        # Filter signal based on mode
        filtered_signal = self._filter_signal_by_mode(
            base_result.signal,
            mode_analysis
        )
        
        # Create enhanced result
        result = ModeAwareBarResult(
            **base_result.__dict__,
            market_mode=mode_analysis['mode'].iloc[-1],
            mode_confidence=mode_analysis['confidence'].iloc[-1],
            trend_strength=mode_analysis['trend_strength'].iloc[-1],
            cycle_period=mode_analysis['cycle_period'].iloc[-1],
            mode_filtered_signal=filtered_signal
        )
        
        # Store mode history
        self.mode_history.append({
            'timestamp': pd.Timestamp.now(),
            'mode': result.market_mode,
            'confidence': result.mode_confidence,
            'original_signal': base_result.signal,
            'filtered_signal': filtered_signal
        })
        
        return result
    
    def _detect_market_mode(self, closes: pd.Series, 
                           current_hl2: pd.Series) -> Dict:
        """
        Detect current market mode
        
        Args:
            closes: Recent close prices
            current_hl2: Current bar's HL2
            
        Returns:
            Mode analysis dictionary
        """
        # Extend closes with current bar
        extended_closes = pd.concat([closes, pd.Series([closes.iloc[-1]], 
                                                      index=[current_hl2.index[0]])])
        
        # Calculate HL2 series (approximate from closes)
        hl2_series = extended_closes  # Simplified for now
        
        # Detect mode
        mode_analysis = self.mode_detector.detect_market_mode(
            extended_closes,
            hl2_series
        )
        
        self.last_mode_analysis = mode_analysis
        
        return mode_analysis
    
    def _filter_signal_by_mode(self, signal: int, 
                              mode_analysis: Dict) -> int:
        """
        Filter signal based on market mode
        
        Args:
            signal: Original signal
            mode_analysis: Market mode analysis
            
        Returns:
            Filtered signal (may be 0)
        """
        if signal == 0:
            return 0
        
        current_mode = mode_analysis['mode'].iloc[-1]
        confidence = mode_analysis['confidence'].iloc[-1]
        
        # Check if we should filter this signal
        if not self.allow_trend_trades and current_mode == 'trend':
            # Log filtered signal
            self._log_filtered_signal(signal, 'trend_mode')
            return 0
        
        # Filter low confidence signals
        if confidence < self.min_mode_confidence:
            self._log_filtered_signal(signal, 'low_confidence')
            return 0
        
        # Additional filtering based on trend strength
        if current_mode == 'trend':
            trend_strength = mode_analysis['trend_strength'].iloc[-1]
            if trend_strength > 0.8:  # Very strong trend
                self._log_filtered_signal(signal, 'strong_trend')
                return 0
        
        return signal
    
    def _log_filtered_signal(self, signal: int, reason: str):
        """Log when a signal is filtered"""
        if hasattr(self, 'logger'):
            self.logger.debug(
                f"Signal filtered: {signal} due to {reason}"
            )
    
    def get_mode_statistics(self) -> Dict:
        """Get statistics about market modes and filtering"""
        if not self.mode_history:
            return {}
        
        df = pd.DataFrame(self.mode_history)
        
        # Calculate statistics
        total_signals = (df['original_signal'] != 0).sum()
        filtered_signals = (df['filtered_signal'] != 0).sum()
        
        mode_dist = df['mode'].value_counts()
        
        # Signals by mode
        trend_signals = df[df['mode'] == 'trend']['original_signal'].ne(0).sum()
        cycle_signals = df[df['mode'] == 'cycle']['original_signal'].ne(0).sum()
        
        trend_filtered = df[df['mode'] == 'trend']['filtered_signal'].ne(0).sum()
        cycle_filtered = df[df['mode'] == 'cycle']['filtered_signal'].ne(0).sum()
        
        return {
            'total_bars': len(df),
            'mode_distribution': mode_dist.to_dict(),
            'avg_confidence': df['confidence'].mean(),
            'total_signals': total_signals,
            'filtered_signals': filtered_signals,
            'filter_rate': 1 - (filtered_signals / total_signals) if total_signals > 0 else 0,
            'trend_signals': f"{trend_filtered}/{trend_signals}" if trend_signals > 0 else "0/0",
            'cycle_signals': f"{cycle_filtered}/{cycle_signals}" if cycle_signals > 0 else "0/0"
        }
    
    def adapt_parameters_by_mode(self, current_mode: str):
        """
        Adapt processing parameters based on market mode
        
        Args:
            current_mode: Current market mode
        """
        if current_mode == 'trend':
            # In trends, be more selective
            # Could adjust ML threshold, filter settings, etc.
            pass
        else:  # cycle mode
            # In cycles, use normal parameters
            pass
        
        # This is a placeholder for future enhancements


def test_mode_aware_processor():
    """Test the mode-aware processor"""
    from config.settings import TradingConfig
    
    # Create test config
    config = TradingConfig()
    
    # Create processor
    processor = ModeAwareBarProcessor(
        config=config,
        symbol='TEST',
        allow_trend_trades=False
    )
    
    # Generate test data
    # Trending section
    for i in range(50):
        price = 100 + i * 0.2
        result = processor.process_bar(
            open_price=price - 0.1,
            high=price + 0.1,
            low=price - 0.1,
            close=price,
            volume=1000000
        )
    
    # Cycling section
    for i in range(50):
        price = 110 + 2 * np.sin(i * 0.3)
        result = processor.process_bar(
            open_price=price - 0.1,
            high=price + 0.1,
            low=price - 0.1,
            close=price,
            volume=1000000
        )
    
    # Get statistics
    stats = processor.get_mode_statistics()
    print("Mode-Aware Processor Test Results:")
    print(f"Total bars processed: {stats.get('total_bars', 0)}")
    print(f"Mode distribution: {stats.get('mode_distribution', {})}")
    print(f"Filter rate: {stats.get('filter_rate', 0):.1%}")
    
    return processor


if __name__ == "__main__":
    test_mode_aware_processor()