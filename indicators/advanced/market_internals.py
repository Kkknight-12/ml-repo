"""
Market Internals Indicators
===========================

Advanced indicators that look at market microstructure and internals
to provide additional context for trading decisions.
"""

import numpy as np
from typing import Dict, Optional, List
from collections import deque
from dataclasses import dataclass


@dataclass
class MarketProfile:
    """Market profile data"""
    poc: float  # Point of Control (most traded price)
    value_area_high: float
    value_area_low: float
    volume_distribution: Dict[float, float]
    skew: float  # Positive = buying pressure, Negative = selling pressure


class MarketInternals:
    """
    Collection of market internal indicators
    """
    
    def __init__(self, 
                 profile_period: int = 20,
                 flow_period: int = 10,
                 breadth_period: int = 14):
        """
        Initialize market internals
        
        Args:
            profile_period: Period for market profile
            flow_period: Period for order flow
            breadth_period: Period for market breadth
        """
        self.profile_period = profile_period
        self.flow_period = flow_period
        self.breadth_period = breadth_period
        
        # Buffers
        self.price_volume_buffer = deque(maxlen=profile_period)
        self.flow_buffer = deque(maxlen=flow_period)
        self.spread_buffer = deque(maxlen=breadth_period)
        
        # State
        self.current_profile = None
        self.order_flow_imbalance = 0.0
        self.spread_ratio = 1.0
        
    def update(self, open_price: float, high: float, low: float, 
               close: float, volume: float) -> Dict[str, float]:
        """
        Update all market internal indicators
        
        Args:
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Volume
            
        Returns:
            Dictionary with all indicator values
        """
        # Store price-volume data
        self.price_volume_buffer.append({
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'typical': (high + low + close) / 3
        })
        
        # Calculate order flow imbalance
        self._update_order_flow(open_price, high, low, close, volume)
        
        # Calculate spread/range metrics
        self._update_spread_metrics(high, low, close)
        
        # Update market profile
        if len(self.price_volume_buffer) >= self.profile_period:
            self.current_profile = self._calculate_market_profile()
        
        # Compile results
        results = {
            'order_flow_imbalance': self.order_flow_imbalance,
            'spread_ratio': self.spread_ratio,
            'buying_pressure': self._calculate_buying_pressure(),
            'volume_trend': self._calculate_volume_trend(),
        }
        
        # Add market profile data if available
        if self.current_profile:
            results.update({
                'poc': self.current_profile.poc,
                'value_area_high': self.current_profile.value_area_high,
                'value_area_low': self.current_profile.value_area_low,
                'profile_skew': self.current_profile.skew
            })
            
        return results
    
    def _update_order_flow(self, open_price: float, high: float, 
                          low: float, close: float, volume: float):
        """Calculate order flow imbalance"""
        # Estimate buying vs selling volume
        # Using the Tick Rule approximation
        range_size = high - low
        
        if range_size > 0:
            # Volume attributed to buying
            buy_volume = volume * ((close - low) / range_size)
            # Volume attributed to selling  
            sell_volume = volume * ((high - close) / range_size)
            
            # Calculate imbalance
            total = buy_volume + sell_volume
            if total > 0:
                self.order_flow_imbalance = (buy_volume - sell_volume) / total
            else:
                self.order_flow_imbalance = 0.0
                
            # Store in buffer
            self.flow_buffer.append({
                'buy_volume': buy_volume,
                'sell_volume': sell_volume,
                'imbalance': self.order_flow_imbalance
            })
    
    def _update_spread_metrics(self, high: float, low: float, close: float):
        """Calculate spread and range metrics"""
        # Current spread
        spread = high - low
        
        # Average spread
        if self.spread_buffer:
            avg_spread = np.mean([s['spread'] for s in self.spread_buffer])
            self.spread_ratio = spread / avg_spread if avg_spread > 0 else 1.0
        
        self.spread_buffer.append({
            'spread': spread,
            'close_location': (close - low) / spread if spread > 0 else 0.5
        })
    
    def _calculate_market_profile(self) -> MarketProfile:
        """Calculate market profile from recent data"""
        # Collect all prices and volumes
        prices = []
        volumes = []
        
        for bar in self.price_volume_buffer:
            # Approximate volume distribution across the bar
            price_levels = np.linspace(bar['low'], bar['high'], 10)
            vol_per_level = bar['volume'] / 10
            
            prices.extend(price_levels)
            volumes.extend([vol_per_level] * 10)
        
        # Create volume distribution
        price_bins = np.linspace(min(prices), max(prices), 30)
        volume_dist = {}
        
        for i in range(len(price_bins) - 1):
            mask = (np.array(prices) >= price_bins[i]) & (np.array(prices) < price_bins[i+1])
            volume_dist[price_bins[i]] = sum(np.array(volumes)[mask])
        
        # Find POC (Point of Control)
        poc = max(volume_dist, key=volume_dist.get)
        
        # Calculate value area (70% of volume)
        sorted_prices = sorted(volume_dist.items(), key=lambda x: x[1], reverse=True)
        total_volume = sum(volume_dist.values())
        target_volume = total_volume * 0.7
        
        accumulated_volume = 0
        value_prices = []
        
        for price, vol in sorted_prices:
            accumulated_volume += vol
            value_prices.append(price)
            if accumulated_volume >= target_volume:
                break
        
        value_area_high = max(value_prices) if value_prices else poc
        value_area_low = min(value_prices) if value_prices else poc
        
        # Calculate skew
        weighted_sum = sum(price * vol for price, vol in volume_dist.items())
        vwap = weighted_sum / total_volume if total_volume > 0 else poc
        skew = (vwap - poc) / poc * 100
        
        return MarketProfile(
            poc=poc,
            value_area_high=value_area_high,
            value_area_low=value_area_low,
            volume_distribution=volume_dist,
            skew=skew
        )
    
    def _calculate_buying_pressure(self) -> float:
        """Calculate overall buying pressure"""
        if not self.flow_buffer:
            return 0.5
            
        # Average order flow imbalance
        avg_imbalance = np.mean([f['imbalance'] for f in self.flow_buffer])
        
        # Convert to 0-1 scale
        buying_pressure = (avg_imbalance + 1) / 2
        
        return buying_pressure
    
    def _calculate_volume_trend(self) -> float:
        """Calculate volume trend strength"""
        if len(self.price_volume_buffer) < 3:
            return 0.0
            
        volumes = [bar['volume'] for bar in self.price_volume_buffer]
        recent_avg = np.mean(volumes[-3:])
        overall_avg = np.mean(volumes)
        
        if overall_avg > 0:
            volume_trend = (recent_avg - overall_avg) / overall_avg
        else:
            volume_trend = 0.0
            
        return volume_trend
    
    def get_support_resistance_levels(self) -> Dict[str, List[float]]:
        """Get support and resistance levels from market profile"""
        if not self.current_profile:
            return {'support': [], 'resistance': []}
            
        # Value area boundaries are natural S/R levels
        current_close = self.price_volume_buffer[-1]['close'] if self.price_volume_buffer else 0
        
        support = []
        resistance = []
        
        # POC is a major level
        if current_close > self.current_profile.poc:
            support.append(self.current_profile.poc)
        else:
            resistance.append(self.current_profile.poc)
            
        # Value area boundaries
        if current_close > self.current_profile.value_area_high:
            support.append(self.current_profile.value_area_high)
        else:
            resistance.append(self.current_profile.value_area_high)
            
        if current_close > self.current_profile.value_area_low:
            support.append(self.current_profile.value_area_low)
        else:
            resistance.append(self.current_profile.value_area_low)
            
        return {
            'support': sorted(support, reverse=True),
            'resistance': sorted(resistance)
        }
    
    def reset(self):
        """Reset all indicators"""
        self.price_volume_buffer.clear()
        self.flow_buffer.clear()
        self.spread_buffer.clear()
        self.current_profile = None
        self.order_flow_imbalance = 0.0
        self.spread_ratio = 1.0