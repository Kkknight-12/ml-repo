"""
Hilbert Transform Component
===========================

Implements the Hilbert Transform for extracting instantaneous phase
and amplitude from price data. This is a core component for the
Sinewave indicator.

Based on John Ehlers' "Rocket Science for Traders"
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional


class HilbertTransform:
    """
    Hilbert Transform implementation for cycle analysis
    
    The Hilbert Transform extracts the imaginary component of a signal,
    which when combined with the real component, gives us phase information.
    """
    
    def __init__(self, smooth_period: int = 7):
        """
        Initialize Hilbert Transform
        
        Args:
            smooth_period: Period for initial smoothing (default 7)
        """
        self.smooth_period = smooth_period
        
        # Hilbert Transform coefficients (90-degree phase shift)
        # These create a 6-bar FIR filter
        self.coefficients = [
            0.0962,
            0.5769,
            0.5769,
            0.0962
        ]
        
    def compute_quadrature(self, prices: pd.Series) -> pd.Series:
        """
        Compute quadrature (imaginary) component using Hilbert Transform
        
        Args:
            prices: Price series (typically smoothed)
            
        Returns:
            Quadrature component series
        """
        # Initialize output
        quadrature = pd.Series(index=prices.index, dtype=float)
        quadrature[:] = 0.0
        
        # Apply Hilbert Transform (4-bar weighted difference)
        for i in range(6, len(prices)):
            quadrature.iloc[i] = (
                self.coefficients[0] * (prices.iloc[i] - prices.iloc[i-6]) +
                self.coefficients[1] * (prices.iloc[i-2] - prices.iloc[i-4]) +
                self.coefficients[2] * (prices.iloc[i-3] - prices.iloc[i-3]) +  # This is 0
                self.coefficients[3] * (prices.iloc[i-4] - prices.iloc[i-2])
            )
            
        return quadrature
    
    def compute_in_phase(self, prices: pd.Series) -> pd.Series:
        """
        Compute in-phase (real) component with 3-bar delay
        
        Args:
            prices: Price series
            
        Returns:
            In-phase component series
        """
        # In-phase is simply the price delayed by 3 bars
        in_phase = prices.shift(3)
        return in_phase
    
    def smooth_price(self, prices: pd.Series) -> pd.Series:
        """
        Apply 4-bar WMA smoothing to reduce noise
        
        Args:
            prices: Raw price series
            
        Returns:
            Smoothed price series
        """
        # 4-bar weighted moving average
        weights = np.array([1, 2, 2, 1])
        weights = weights / weights.sum()
        
        smoothed = prices.rolling(window=4).apply(
            lambda x: np.sum(x * weights) if len(x) == 4 else np.nan
        )
        
        return smoothed
    
    def compute_phase(self, in_phase: pd.Series, quadrature: pd.Series) -> pd.Series:
        """
        Compute instantaneous phase from components
        
        Args:
            in_phase: Real component
            quadrature: Imaginary component
            
        Returns:
            Phase in degrees (-180 to 180)
        """
        # Use atan2 for full quadrant resolution
        phase = np.degrees(np.arctan2(quadrature, in_phase))
        
        # Handle NaN values
        phase = pd.Series(phase, index=in_phase.index)
        
        return phase
    
    def compute_period(self, phase: pd.Series) -> pd.Series:
        """
        Compute dominant cycle period from phase
        
        Args:
            phase: Phase series in degrees
            
        Returns:
            Period in bars
        """
        # Calculate phase change
        phase_change = phase.diff()
        
        # Handle phase wrapping
        phase_change = phase_change.apply(
            lambda x: x + 360 if x < -180 else (x - 360 if x > 180 else x)
        )
        
        # Smooth the phase change
        smooth_phase_change = phase_change.rolling(window=5).mean()
        
        # Calculate period (360 degrees / phase change per bar)
        period = 360 / smooth_phase_change.abs()
        
        # Limit period to reasonable range (10-50 bars)
        period = period.clip(lower=10, upper=50)
        
        return period
    
    def transform(self, prices: pd.Series) -> dict:
        """
        Complete Hilbert Transform process
        
        Args:
            prices: Input price series (close, hl2, etc.)
            
        Returns:
            Dictionary containing:
            - smooth: Smoothed prices
            - in_phase: Real component
            - quadrature: Imaginary component
            - phase: Instantaneous phase
            - period: Dominant cycle period
        """
        # Step 1: Smooth the input prices
        smooth = self.smooth_price(prices)
        
        # Step 2: Compute components
        in_phase = self.compute_in_phase(smooth)
        quadrature = self.compute_quadrature(smooth)
        
        # Step 3: Compute phase
        phase = self.compute_phase(in_phase, quadrature)
        
        # Step 4: Compute period
        period = self.compute_period(phase)
        
        return {
            'smooth': smooth,
            'in_phase': in_phase,
            'quadrature': quadrature,
            'phase': phase,
            'period': period
        }


def test_hilbert_transform():
    """Test the Hilbert Transform with sample data"""
    
    # Create sample sine wave data
    bars = 100
    period = 20
    t = np.linspace(0, 4 * np.pi, bars)
    prices = 100 + 5 * np.sin(t * 2 * np.pi / period)
    
    # Add some noise
    prices += np.random.normal(0, 0.5, bars)
    
    # Create series
    price_series = pd.Series(prices, index=pd.date_range('2024-01-01', periods=bars))
    
    # Apply Hilbert Transform
    ht = HilbertTransform()
    result = ht.transform(price_series)
    
    print("Hilbert Transform Test Results:")
    print(f"Average detected period: {result['period'].iloc[20:].mean():.1f} bars")
    print(f"Expected period: {period} bars")
    print(f"Phase range: {result['phase'].min():.1f} to {result['phase'].max():.1f} degrees")
    
    return result


if __name__ == "__main__":
    test_hilbert_transform()