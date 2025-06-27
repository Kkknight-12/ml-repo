"""
Support/Resistance Confirmation Filter
====================================

Validates signals based on proximity to support/resistance levels.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import deque


@dataclass
class SRLevel:
    """Support/Resistance level"""
    price: float
    strength: int  # Number of touches
    level_type: str  # 'support' or 'resistance'
    last_touch: int  # Bars since last touch


@dataclass
class SRValidation:
    """Support/Resistance validation result"""
    nearest_support: Optional[float]
    nearest_resistance: Optional[float]
    distance_to_support: float
    distance_to_resistance: float
    is_valid: bool
    validation_score: float
    level_strength: str  # 'strong', 'moderate', 'weak'


class SupportResistanceFilter:
    """
    Validates signals based on support/resistance levels.
    
    Key concepts:
    1. Long signals should be near support
    2. Short signals should be near resistance
    3. Avoid signals in the middle of nowhere
    4. Stronger levels provide better confirmation
    """
    
    def __init__(self,
                 lookback_period: int = 100,
                 min_touches: int = 2,
                 tolerance_percent: float = 0.3,
                 max_distance_percent: float = 1.0):
        """
        Initialize S/R filter.
        
        Args:
            lookback_period: Bars to look back for S/R levels
            min_touches: Minimum touches to confirm a level
            tolerance_percent: Price tolerance for level touches (%)
            max_distance_percent: Max distance from S/R for valid signal (%)
        """
        self.lookback_period = lookback_period
        self.min_touches = min_touches
        self.tolerance_percent = tolerance_percent / 100
        self.max_distance_percent = max_distance_percent / 100
        
        # Price history
        self.high_buffer = deque(maxlen=lookback_period)
        self.low_buffer = deque(maxlen=lookback_period)
        self.close_buffer = deque(maxlen=lookback_period)
        
        # Identified levels
        self.support_levels: List[SRLevel] = []
        self.resistance_levels: List[SRLevel] = []
        
        # Bar counter
        self.bar_count = 0
        
    def update(self, high: float, low: float, close: float):
        """Update with new price bar"""
        self.bar_count += 1
        
        # Update buffers
        self.high_buffer.append(high)
        self.low_buffer.append(low)
        self.close_buffer.append(close)
        
        # Identify levels periodically
        if self.bar_count % 10 == 0:  # Every 10 bars
            self._identify_levels()
            
    def _identify_levels(self):
        """Identify support and resistance levels"""
        if len(self.high_buffer) < 20:
            return
            
        # Find local highs and lows
        highs = list(self.high_buffer)
        lows = list(self.low_buffer)
        
        # Find swing points
        swing_highs = []
        swing_lows = []
        
        for i in range(2, len(highs) - 2):
            # Swing high: higher than 2 bars before and after
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                swing_highs.append((i, highs[i]))
                
            # Swing low: lower than 2 bars before and after
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                swing_lows.append((i, lows[i]))
        
        # Cluster nearby levels
        self.resistance_levels = self._cluster_levels(swing_highs, 'resistance')
        self.support_levels = self._cluster_levels(swing_lows, 'support')
        
    def _cluster_levels(self, swings: List[Tuple[int, float]], 
                       level_type: str) -> List[SRLevel]:
        """Cluster nearby swing points into levels"""
        if not swings:
            return []
            
        # Sort by price
        swings.sort(key=lambda x: x[1])
        
        levels = []
        current_cluster = [swings[0]]
        
        for i in range(1, len(swings)):
            # Check if within tolerance of current cluster
            cluster_avg = np.mean([s[1] for s in current_cluster])
            if abs(swings[i][1] - cluster_avg) / cluster_avg <= self.tolerance_percent:
                current_cluster.append(swings[i])
            else:
                # Create level from cluster
                if len(current_cluster) >= self.min_touches:
                    avg_price = np.mean([s[1] for s in current_cluster])
                    last_touch = self.bar_count - current_cluster[-1][0]
                    
                    levels.append(SRLevel(
                        price=avg_price,
                        strength=len(current_cluster),
                        level_type=level_type,
                        last_touch=last_touch
                    ))
                
                # Start new cluster
                current_cluster = [swings[i]]
        
        # Handle last cluster
        if len(current_cluster) >= self.min_touches:
            avg_price = np.mean([s[1] for s in current_cluster])
            last_touch = self.bar_count - current_cluster[-1][0]
            
            levels.append(SRLevel(
                price=avg_price,
                strength=len(current_cluster),
                level_type=level_type,
                last_touch=last_touch
            ))
        
        return levels
    
    def validate_signal(self, price: float, signal_direction: int) -> SRValidation:
        """
        Validate signal based on S/R levels.
        
        Args:
            price: Current price
            signal_direction: 1 for long, -1 for short
            
        Returns:
            SRValidation result
        """
        # Find nearest levels
        nearest_support = self._find_nearest_level(price, self.support_levels, below=True)
        nearest_resistance = self._find_nearest_level(price, self.resistance_levels, below=False)
        
        # Calculate distances
        dist_to_support = abs(price - nearest_support) / price if nearest_support else float('inf')
        dist_to_resistance = abs(nearest_resistance - price) / price if nearest_resistance else float('inf')
        
        # Validation logic
        is_valid = False
        validation_score = 0.0
        
        if signal_direction > 0:  # Long signal
            # Should be near support
            if dist_to_support <= self.max_distance_percent:
                is_valid = True
                # Closer to support = higher score
                validation_score = 1.0 - (dist_to_support / self.max_distance_percent)
                
                # Bonus for strong support levels
                support_level = self._get_level(nearest_support, self.support_levels)
                if support_level and support_level.strength >= 3:
                    validation_score = min(1.0, validation_score * 1.2)
                    
        else:  # Short signal
            # Should be near resistance
            if dist_to_resistance <= self.max_distance_percent:
                is_valid = True
                # Closer to resistance = higher score
                validation_score = 1.0 - (dist_to_resistance / self.max_distance_percent)
                
                # Bonus for strong resistance levels
                resistance_level = self._get_level(nearest_resistance, self.resistance_levels)
                if resistance_level and resistance_level.strength >= 3:
                    validation_score = min(1.0, validation_score * 1.2)
        
        # Determine level strength
        if validation_score >= 0.7:
            level_strength = 'strong'
        elif validation_score >= 0.4:
            level_strength = 'moderate'
        else:
            level_strength = 'weak'
        
        return SRValidation(
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
            distance_to_support=dist_to_support,
            distance_to_resistance=dist_to_resistance,
            is_valid=is_valid,
            validation_score=validation_score,
            level_strength=level_strength
        )
    
    def _find_nearest_level(self, price: float, levels: List[SRLevel], 
                          below: bool) -> Optional[float]:
        """Find nearest level above or below price"""
        if not levels:
            return None
            
        if below:
            # Find highest level below price
            below_levels = [l.price for l in levels if l.price < price]
            return max(below_levels) if below_levels else None
        else:
            # Find lowest level above price
            above_levels = [l.price for l in levels if l.price > price]
            return min(above_levels) if above_levels else None
    
    def _get_level(self, price: float, levels: List[SRLevel]) -> Optional[SRLevel]:
        """Get level object by price"""
        for level in levels:
            if abs(level.price - price) < 0.001:
                return level
        return None
    
    def get_levels_summary(self) -> Dict:
        """Get summary of current S/R levels"""
        return {
            'support_count': len(self.support_levels),
            'resistance_count': len(self.resistance_levels),
            'strongest_support': max(self.support_levels, key=lambda x: x.strength).price 
                               if self.support_levels else None,
            'strongest_resistance': max(self.resistance_levels, key=lambda x: x.strength).price 
                                  if self.resistance_levels else None,
            'support_levels': [(l.price, l.strength) for l in self.support_levels],
            'resistance_levels': [(l.price, l.strength) for l in self.resistance_levels]
        }