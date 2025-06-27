"""
Volume Confirmation Filter
=========================

Filters signals based on volume analysis.
Only allows signals when volume confirms the move.
"""

import numpy as np
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class VolumeStats:
    """Volume analysis statistics"""
    current_volume: float
    avg_volume: float
    volume_ratio: float
    volume_trend: str  # 'increasing', 'decreasing', 'stable'
    is_confirmed: bool
    confidence: float


class VolumeConfirmationFilter:
    """
    Filters signals based on volume confirmation.
    
    Key concepts:
    1. Volume should be above average for valid signals
    2. Volume trend should align with price direction
    3. Spike detection for breakout confirmation
    """
    
    def __init__(self, 
                 lookback_period: int = 20,
                 min_volume_ratio: float = 1.5,
                 spike_threshold: float = 2.0,
                 trend_period: int = 5):
        """
        Initialize volume filter.
        
        Args:
            lookback_period: Period for average volume calculation
            min_volume_ratio: Minimum volume/average ratio for confirmation
            spike_threshold: Threshold for volume spike detection
            trend_period: Period for volume trend analysis
        """
        self.lookback_period = lookback_period
        self.min_volume_ratio = min_volume_ratio
        self.spike_threshold = spike_threshold
        self.trend_period = trend_period
        
        # Buffers
        self.volume_buffer: List[float] = []
        self.price_buffer: List[float] = []
        
    def update(self, volume: float, close: float) -> VolumeStats:
        """
        Update volume analysis with new bar.
        
        Args:
            volume: Current bar volume
            close: Current close price
            
        Returns:
            VolumeStats with analysis results
        """
        # Update buffers
        self.volume_buffer.append(volume)
        self.price_buffer.append(close)
        
        # Keep buffer size limited
        if len(self.volume_buffer) > self.lookback_period * 2:
            self.volume_buffer.pop(0)
            self.price_buffer.pop(0)
        
        # Need minimum data
        if len(self.volume_buffer) < self.lookback_period:
            return VolumeStats(
                current_volume=volume,
                avg_volume=volume,
                volume_ratio=1.0,
                volume_trend='stable',
                is_confirmed=False,
                confidence=0.0
            )
        
        # Calculate average volume
        recent_volumes = self.volume_buffer[-self.lookback_period:]
        avg_volume = np.mean(recent_volumes)
        
        # Volume ratio
        volume_ratio = volume / avg_volume if avg_volume > 0 else 0
        
        # Volume trend
        volume_trend = self._analyze_volume_trend()
        
        # Confirmation logic
        is_confirmed, confidence = self._check_confirmation(
            volume_ratio, volume_trend, close
        )
        
        return VolumeStats(
            current_volume=volume,
            avg_volume=avg_volume,
            volume_ratio=volume_ratio,
            volume_trend=volume_trend,
            is_confirmed=is_confirmed,
            confidence=confidence
        )
    
    def _analyze_volume_trend(self) -> str:
        """Analyze recent volume trend"""
        if len(self.volume_buffer) < self.trend_period:
            return 'stable'
        
        recent_volumes = self.volume_buffer[-self.trend_period:]
        
        # Simple linear regression slope
        x = np.arange(len(recent_volumes))
        slope = np.polyfit(x, recent_volumes, 1)[0]
        
        # Normalize by average
        avg_volume = np.mean(recent_volumes)
        normalized_slope = slope / avg_volume if avg_volume > 0 else 0
        
        # Classify trend
        if normalized_slope > 0.1:
            return 'increasing'
        elif normalized_slope < -0.1:
            return 'decreasing'
        else:
            return 'stable'
    
    def _check_confirmation(self, volume_ratio: float, 
                          volume_trend: str, close: float) -> tuple:
        """
        Check if volume confirms the signal.
        
        Returns:
            (is_confirmed, confidence)
        """
        # Base confirmation on volume ratio
        if volume_ratio < self.min_volume_ratio:
            return False, 0.0
        
        # Calculate confidence based on multiple factors
        confidence = 0.0
        
        # 1. Volume ratio contribution (40%)
        if volume_ratio >= self.spike_threshold:
            confidence += 0.4
        elif volume_ratio >= self.min_volume_ratio:
            confidence += 0.4 * (volume_ratio - self.min_volume_ratio) / \
                         (self.spike_threshold - self.min_volume_ratio)
        
        # 2. Volume trend contribution (30%)
        if volume_trend == 'increasing':
            confidence += 0.3
        elif volume_trend == 'stable':
            confidence += 0.15
        
        # 3. Price-volume correlation (30%)
        if len(self.price_buffer) >= self.trend_period:
            price_change = (close - self.price_buffer[-self.trend_period]) / \
                          self.price_buffer[-self.trend_period]
            
            # Volume should increase with price movement
            if abs(price_change) > 0.01:  # Significant price move
                if volume_ratio > 1.5:
                    confidence += 0.3
                elif volume_ratio > 1.2:
                    confidence += 0.15
        
        # Confirmed if confidence > 50%
        is_confirmed = confidence >= 0.5
        
        return is_confirmed, confidence
    
    def check_breakout_volume(self, volume: float, 
                            price_breakout: bool) -> bool:
        """
        Special check for breakout confirmation.
        Breakouts need stronger volume confirmation.
        """
        if not price_breakout:
            return True  # Not a breakout, regular rules apply
        
        if len(self.volume_buffer) < self.lookback_period:
            return False
        
        avg_volume = np.mean(self.volume_buffer[-self.lookback_period:])
        volume_ratio = volume / avg_volume if avg_volume > 0 else 0
        
        # Breakouts need spike-level volume
        return volume_ratio >= self.spike_threshold
    
    def get_volume_profile(self) -> Dict:
        """Get detailed volume profile statistics"""
        if len(self.volume_buffer) < self.lookback_period:
            return {}
        
        recent_volumes = self.volume_buffer[-self.lookback_period:]
        
        return {
            'avg_volume': np.mean(recent_volumes),
            'volume_std': np.std(recent_volumes),
            'volume_median': np.median(recent_volumes),
            'volume_trend': self._analyze_volume_trend(),
            'high_volume_bars': sum(1 for v in recent_volumes 
                                  if v > np.mean(recent_volumes) * 1.5),
            'low_volume_bars': sum(1 for v in recent_volumes 
                                 if v < np.mean(recent_volumes) * 0.5)
        }