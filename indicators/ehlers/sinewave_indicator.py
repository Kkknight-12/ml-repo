"""
Sinewave Indicator
==================

Implements Ehlers' Sinewave Indicator for detecting market mode
(trending vs cycling) and anticipating cycle turns.

Key Features:
- Detects trend vs cycle mode
- Provides leading signals (45-degree phase lead)
- Lines run parallel in trends (no signals)
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, Optional
from .hilbert_transform import HilbertTransform


class SinewaveIndicator:
    """
    Ehlers Sinewave Indicator
    
    This indicator consists of two lines:
    1. Sine: The sine of the phase angle
    2. LeadSine: The sine of (phase + 45 degrees)
    
    When lines cross, it signals a cycle turn.
    When lines run parallel, market is trending.
    """
    
    def __init__(self, dc_period: int = 30):
        """
        Initialize Sinewave Indicator
        
        Args:
            dc_period: Dominant cycle period for initialization
        """
        self.dc_period = dc_period
        self.hilbert = HilbertTransform()
        
        # Smoothing factors
        self.smooth_factor = 0.33  # For phase smoothing
        
    def calculate_dc_phase(self, smooth_prices: pd.Series, 
                          period: pd.Series) -> pd.Series:
        """
        Calculate dominant cycle phase with smoothing
        
        Args:
            smooth_prices: Smoothed price series
            period: Dominant cycle period
            
        Returns:
            Smoothed dominant cycle phase
        """
        # Get Hilbert components
        ht_result = self.hilbert.transform(smooth_prices)
        
        # Initialize DC phase
        dc_phase = pd.Series(index=smooth_prices.index, dtype=float)
        dc_phase[:] = 0.0
        
        # Calculate instantaneous phase
        inst_phase = ht_result['phase']
        
        # Smooth the phase using EMA-like approach
        alpha = self.smooth_factor
        
        for i in range(1, len(dc_phase)):
            if pd.notna(inst_phase.iloc[i]):
                # Smooth the phase
                dc_phase.iloc[i] = alpha * inst_phase.iloc[i] + (1 - alpha) * dc_phase.iloc[i-1]
                
                # Handle phase wrapping
                if dc_phase.iloc[i] - dc_phase.iloc[i-1] > 180:
                    dc_phase.iloc[i] -= 360
                elif dc_phase.iloc[i] - dc_phase.iloc[i-1] < -180:
                    dc_phase.iloc[i] += 360
        
        return dc_phase
    
    def calculate_sine_wave(self, dc_phase: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Sine and LeadSine from phase
        
        Args:
            dc_phase: Dominant cycle phase
            
        Returns:
            Tuple of (sine, leadsine) series
        """
        # Convert to radians
        phase_rad = np.radians(dc_phase)
        
        # Calculate Sine
        sine = np.sin(phase_rad)
        
        # Calculate LeadSine (45-degree lead)
        lead_phase_rad = np.radians(dc_phase + 45)
        leadsine = np.sin(lead_phase_rad)
        
        # Convert to Series
        sine = pd.Series(sine, index=dc_phase.index)
        leadsine = pd.Series(leadsine, index=dc_phase.index)
        
        return sine, leadsine
    
    def detect_market_mode(self, sine: pd.Series, leadsine: pd.Series,
                          threshold: float = 0.1) -> pd.Series:
        """
        Detect market mode (trending vs cycling)
        
        Args:
            sine: Sine wave series
            leadsine: Lead sine wave series
            threshold: Threshold for parallel detection
            
        Returns:
            Series with 'trend' or 'cycle' labels
        """
        # Calculate the difference between lines
        diff = (sine - leadsine).abs()
        
        # Smooth the difference
        smooth_diff = diff.rolling(window=10).mean()
        
        # Initialize mode series
        mode = pd.Series(index=sine.index, dtype=str)
        mode[:] = 'cycle'  # Default to cycle mode
        
        # When lines are parallel (small difference), market is trending
        mode[smooth_diff < threshold] = 'trend'
        
        # Additional check: if sine values are stuck near extremes
        sine_smooth = sine.rolling(window=5).mean()
        stuck_high = (sine_smooth > 0.9) | (sine_smooth < -0.9)
        mode[stuck_high] = 'trend'
        
        return mode
    
    def generate_signals(self, sine: pd.Series, leadsine: pd.Series,
                        mode: pd.Series) -> pd.Series:
        """
        Generate trading signals from sinewave crossovers
        
        Args:
            sine: Sine wave series
            leadsine: Lead sine wave series
            mode: Market mode series
            
        Returns:
            Signal series (1 for buy, -1 for sell, 0 for no signal)
        """
        # Initialize signals
        signals = pd.Series(0, index=sine.index)
        
        # Only generate signals in cycle mode
        cycle_mask = mode == 'cycle'
        
        # Detect crossovers
        for i in range(1, len(signals)):
            if not cycle_mask.iloc[i]:
                continue
                
            # Buy signal: LeadSine crosses above Sine (cycle bottom)
            if (leadsine.iloc[i] > sine.iloc[i] and 
                leadsine.iloc[i-1] <= sine.iloc[i-1]):
                signals.iloc[i] = 1
                
            # Sell signal: LeadSine crosses below Sine (cycle top)
            elif (leadsine.iloc[i] < sine.iloc[i] and 
                  leadsine.iloc[i-1] >= sine.iloc[i-1]):
                signals.iloc[i] = -1
        
        return signals
    
    def calculate(self, prices: pd.Series) -> Dict:
        """
        Complete Sinewave indicator calculation
        
        Args:
            prices: Input price series (typically HL2)
            
        Returns:
            Dictionary containing:
            - sine: Sine wave values
            - leadsine: Leading sine wave
            - mode: Market mode (trend/cycle)
            - signals: Trading signals
            - period: Dominant cycle period
        """
        # Get Hilbert Transform results
        ht_result = self.hilbert.transform(prices)
        
        # Calculate DC Phase
        dc_phase = self.calculate_dc_phase(prices, ht_result['period'])
        
        # Calculate Sine waves
        sine, leadsine = self.calculate_sine_wave(dc_phase)
        
        # Detect market mode
        mode = self.detect_market_mode(sine, leadsine)
        
        # Generate signals
        signals = self.generate_signals(sine, leadsine, mode)
        
        return {
            'sine': sine,
            'leadsine': leadsine,
            'mode': mode,
            'signals': signals,
            'period': ht_result['period'],
            'phase': dc_phase
        }


def test_sinewave_indicator():
    """Test the Sinewave indicator with trending and cycling data"""
    
    # Create test data with both trending and cycling sections
    bars = 200
    
    # First 100 bars: Cycling market
    t1 = np.linspace(0, 4 * np.pi, 100)
    cycle_data = 100 + 5 * np.sin(t1)
    
    # Second 100 bars: Trending market
    trend_data = np.linspace(105, 120, 100) + np.random.normal(0, 0.5, 100)
    
    # Combine
    prices = np.concatenate([cycle_data, trend_data])
    
    # Create series
    price_series = pd.Series(prices, index=pd.date_range('2024-01-01', periods=bars))
    
    # Apply Sinewave indicator
    indicator = SinewaveIndicator()
    result = indicator.calculate(price_series)
    
    print("Sinewave Indicator Test Results:")
    print(f"Mode distribution:")
    print(result['mode'].value_counts())
    print(f"\nSignals generated: {(result['signals'] != 0).sum()}")
    print(f"Signals in cycle section: {(result['signals'][:100] != 0).sum()}")
    print(f"Signals in trend section: {(result['signals'][100:] != 0).sum()}")
    
    return result


if __name__ == "__main__":
    test_sinewave_indicator()