"""
Fisher Transform Indicator
==========================

The Fisher Transform converts prices into a Gaussian normal distribution,
making turning points clearer and more identifiable.
"""

import numpy as np
from typing import Optional, Tuple
from collections import deque


class FisherTransform:
    """
    Fisher Transform indicator for identifying turning points
    """
    
    def __init__(self, period: int = 10):
        """
        Initialize Fisher Transform
        
        Args:
            period: Lookback period for calculations
        """
        self.period = period
        self.price_buffer = deque(maxlen=period)
        self.fisher_buffer = deque(maxlen=3)
        self.trigger_buffer = deque(maxlen=3)
        
        # State tracking
        self.fisher = 0.0
        self.trigger = 0.0
        self.raw_value = 0.0
        
    def update(self, high: float, low: float) -> Tuple[float, float]:
        """
        Update Fisher Transform with new price
        
        Args:
            high: High price
            low: Low price
            
        Returns:
            (fisher_value, trigger_value)
        """
        # Calculate midpoint
        midpoint = (high + low) / 2
        self.price_buffer.append(midpoint)
        
        if len(self.price_buffer) < self.period:
            return 0.0, 0.0
            
        # Find highest and lowest over period
        max_high = max(self.price_buffer)
        min_low = min(self.price_buffer)
        
        # Normalize price to -1 to 1
        if max_high != min_low:
            self.raw_value = 2 * ((midpoint - min_low) / (max_high - min_low)) - 1
        else:
            self.raw_value = 0
            
        # Constrain to prevent infinity
        self.raw_value = max(-0.999, min(0.999, self.raw_value))
        
        # Fisher transform formula
        self.fisher = 0.5 * np.log((1 + self.raw_value) / (1 - self.raw_value))
        
        # Smooth with previous value
        if self.fisher_buffer:
            self.fisher = 0.5 * self.fisher + 0.5 * self.fisher_buffer[-1]
            
        # Trigger is previous Fisher value
        self.trigger = self.fisher_buffer[-1] if self.fisher_buffer else 0
        
        # Update buffers
        self.fisher_buffer.append(self.fisher)
        self.trigger_buffer.append(self.trigger)
        
        return self.fisher, self.trigger
    
    def get_signal(self) -> int:
        """
        Generate trading signal based on Fisher Transform
        
        Returns:
            1 for buy, -1 for sell, 0 for no signal
        """
        if len(self.fisher_buffer) < 2:
            return 0
            
        # Check for crossovers
        if self.fisher > self.trigger and self.fisher_buffer[-2] <= self.trigger_buffer[-2]:
            return 1  # Buy signal
        elif self.fisher < self.trigger and self.fisher_buffer[-2] >= self.trigger_buffer[-2]:
            return -1  # Sell signal
            
        return 0
    
    def get_divergence(self, prices: list) -> Optional[str]:
        """
        Check for divergence between price and Fisher Transform
        
        Args:
            prices: Recent price values
            
        Returns:
            'bullish', 'bearish', or None
        """
        if len(self.fisher_buffer) < 3 or len(prices) < 3:
            return None
            
        # Check for bullish divergence (price lower low, Fisher higher low)
        if prices[-1] < prices[-3] and self.fisher > self.fisher_buffer[-3]:
            return 'bullish'
            
        # Check for bearish divergence (price higher high, Fisher lower high)
        if prices[-1] > prices[-3] and self.fisher < self.fisher_buffer[-3]:
            return 'bearish'
            
        return None
    
    def get_extreme_reading(self) -> Optional[str]:
        """
        Check if Fisher Transform is at extreme levels
        
        Returns:
            'overbought', 'oversold', or None
        """
        if abs(self.fisher) > 2.5:
            return 'overbought' if self.fisher > 0 else 'oversold'
        elif abs(self.fisher) > 2.0:
            return 'approaching_overbought' if self.fisher > 0 else 'approaching_oversold'
            
        return None
    
    def reset(self):
        """Reset indicator state"""
        self.price_buffer.clear()
        self.fisher_buffer.clear()
        self.trigger_buffer.clear()
        self.fisher = 0.0
        self.trigger = 0.0
        self.raw_value = 0.0