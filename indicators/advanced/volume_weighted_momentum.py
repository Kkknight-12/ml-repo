"""
Volume-Weighted Momentum Indicator
==================================

Combines price momentum with volume to identify strong moves backed by volume.
This helps filter out weak price movements that lack conviction.
"""

import numpy as np
from typing import Dict, Optional
from collections import deque


class VolumeWeightedMomentum:
    """
    Volume-weighted momentum oscillator
    """
    
    def __init__(self, momentum_period: int = 14, volume_period: int = 20):
        """
        Initialize volume-weighted momentum
        
        Args:
            momentum_period: Period for momentum calculation
            volume_period: Period for volume average
        """
        self.momentum_period = momentum_period
        self.volume_period = volume_period
        
        # Buffers
        self.price_buffer = deque(maxlen=momentum_period + 1)
        self.volume_buffer = deque(maxlen=volume_period)
        self.vwm_buffer = deque(maxlen=momentum_period)
        
        # State
        self.momentum = 0.0
        self.volume_ratio = 1.0
        self.vwm = 0.0
        self.signal_line = 0.0
        
    def update(self, close: float, volume: float) -> Dict[str, float]:
        """
        Update indicator with new price and volume
        
        Args:
            close: Close price
            volume: Volume
            
        Returns:
            Dictionary with indicator values
        """
        self.price_buffer.append(close)
        self.volume_buffer.append(volume)
        
        result = {
            'momentum': 0.0,
            'volume_ratio': 1.0,
            'vwm': 0.0,
            'signal': 0.0,
            'divergence': 0.0
        }
        
        # Need enough data
        if len(self.price_buffer) < self.momentum_period + 1:
            return result
            
        # Calculate raw momentum
        self.momentum = (close - self.price_buffer[0]) / self.price_buffer[0] * 100
        
        # Calculate volume ratio
        if len(self.volume_buffer) >= 2:
            avg_volume = np.mean(list(self.volume_buffer)[:-1])
            self.volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        
        # Calculate volume-weighted momentum
        self.vwm = self.momentum * np.sqrt(self.volume_ratio)
        
        # Update buffer
        self.vwm_buffer.append(self.vwm)
        
        # Calculate signal line (EMA of VWM)
        if len(self.vwm_buffer) >= 3:
            self.signal_line = np.mean(list(self.vwm_buffer)[-3:])
        
        # Calculate divergence strength
        divergence = self.vwm - self.signal_line
        
        result.update({
            'momentum': self.momentum,
            'volume_ratio': self.volume_ratio,
            'vwm': self.vwm,
            'signal': self.signal_line,
            'divergence': divergence
        })
        
        return result
    
    def get_signal_strength(self) -> float:
        """
        Get normalized signal strength (0-1)
        
        Returns:
            Signal strength between 0 and 1
        """
        if not self.vwm_buffer:
            return 0.0
            
        # Normalize VWM to 0-1 range
        abs_vwm = abs(self.vwm)
        
        # Map to 0-1 using sigmoid-like function
        strength = 1 - np.exp(-abs_vwm / 10)
        
        # Boost if volume is high
        if self.volume_ratio > 2.0:
            strength = min(1.0, strength * 1.2)
            
        return strength
    
    def check_divergence(self, prices: list) -> Optional[str]:
        """
        Check for price/VWM divergence
        
        Args:
            prices: Recent prices
            
        Returns:
            'bullish', 'bearish', or None
        """
        if len(prices) < 5 or len(self.vwm_buffer) < 5:
            return None
            
        # Get recent peaks/troughs
        price_change = prices[-1] - prices[-5]
        vwm_change = self.vwm_buffer[-1] - self.vwm_buffer[-5]
        
        # Bullish divergence: price down, VWM up
        if price_change < 0 and vwm_change > 0:
            return 'bullish'
            
        # Bearish divergence: price up, VWM down  
        if price_change > 0 and vwm_change < 0:
            return 'bearish'
            
        return None
    
    def get_trend_strength(self) -> Dict[str, float]:
        """
        Analyze trend strength using VWM
        
        Returns:
            Dictionary with trend metrics
        """
        if len(self.vwm_buffer) < 3:
            return {'trend': 0.0, 'consistency': 0.0, 'acceleration': 0.0}
            
        # Recent VWM values
        recent_vwm = list(self.vwm_buffer)[-5:]
        
        # Trend direction and strength
        trend = np.mean(recent_vwm)
        
        # Consistency (lower std = more consistent)
        consistency = 1 - min(1, np.std(recent_vwm) / (abs(trend) + 1))
        
        # Acceleration
        if len(recent_vwm) >= 3:
            acceleration = recent_vwm[-1] - recent_vwm[-3]
        else:
            acceleration = 0.0
            
        return {
            'trend': trend,
            'consistency': consistency,
            'acceleration': acceleration
        }
    
    def reset(self):
        """Reset indicator state"""
        self.price_buffer.clear()
        self.volume_buffer.clear()
        self.vwm_buffer.clear()
        self.momentum = 0.0
        self.volume_ratio = 1.0
        self.vwm = 0.0
        self.signal_line = 0.0