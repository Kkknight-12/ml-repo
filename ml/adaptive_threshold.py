"""
Adaptive ML Threshold System
============================

Dynamically adjusts ML thresholds based on market conditions, time of day,
and recent performance to optimize signal quality.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from collections import deque
from datetime import datetime, time
import json
import os


@dataclass
class MarketCondition:
    """Current market conditions"""
    volatility: float  # 0-1 scale
    trend_strength: float  # -1 to 1
    volume_ratio: float  # Current vs average
    time_of_day: str  # 'open', 'mid', 'close'
    recent_performance: float  # Recent win rate


@dataclass
class ThresholdAdjustment:
    """Threshold adjustment based on conditions"""
    base_threshold: float
    volatility_adj: float
    trend_adj: float
    volume_adj: float
    time_adj: float
    performance_adj: float
    final_threshold: float
    confidence: float


class AdaptiveMLThreshold:
    """
    Dynamically adjusts ML thresholds based on market conditions
    """
    
    def __init__(self, 
                 base_threshold: float = 3.0,
                 lookback_periods: int = 100,
                 min_threshold: float = 2.0,
                 max_threshold: float = 4.5):
        """
        Initialize adaptive threshold system
        
        Args:
            base_threshold: Default ML threshold
            lookback_periods: Periods to analyze for conditions
            min_threshold: Minimum allowed threshold
            max_threshold: Maximum allowed threshold
        """
        self.base_threshold = base_threshold
        self.lookback_periods = lookback_periods
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        
        # Adjustment parameters
        self.adjustments = {
            'volatility': {
                'low': 0.3,      # Lower threshold in low volatility
                'normal': 0.0,   # No adjustment
                'high': -0.3     # Higher threshold in high volatility
            },
            'trend': {
                'strong_up': -0.2,    # Lower threshold in strong trends
                'strong_down': -0.2,
                'sideways': 0.2       # Higher threshold in ranging markets
            },
            'volume': {
                'low': 0.2,      # Higher threshold on low volume
                'normal': 0.0,
                'high': -0.1     # Slightly lower on high volume
            },
            'time': {
                'open': 0.3,     # Higher threshold at open
                'mid': 0.0,      # Normal during mid-day
                'close': 0.2     # Higher threshold near close
            },
            'performance': {
                'poor': 0.3,     # Increase threshold if losing
                'normal': 0.0,
                'good': -0.2     # Decrease threshold if winning
            }
        }
        
        # State tracking
        self.price_buffer = deque(maxlen=lookback_periods)
        self.volume_buffer = deque(maxlen=lookback_periods)
        self.signal_buffer = deque(maxlen=50)  # Recent signals for performance
        self.threshold_history = deque(maxlen=100)
        
        # Performance tracking
        self.recent_trades = deque(maxlen=20)
        
    def update(self, high: float, low: float, close: float, 
               volume: float, timestamp: pd.Timestamp) -> ThresholdAdjustment:
        """
        Update threshold based on current conditions
        
        Args:
            high: High price
            low: Low price
            close: Close price
            volume: Volume
            timestamp: Current timestamp
            
        Returns:
            ThresholdAdjustment with details
        """
        # Update buffers
        self.price_buffer.append({
            'high': high,
            'low': low,
            'close': close,
            'timestamp': timestamp
        })
        self.volume_buffer.append(volume)
        
        # Analyze current conditions
        conditions = self._analyze_conditions(timestamp)
        
        # Calculate adjustments
        adjustment = self._calculate_adjustment(conditions)
        
        # Store history
        self.threshold_history.append({
            'timestamp': timestamp,
            'threshold': adjustment.final_threshold,
            'conditions': conditions
        })
        
        return adjustment
    
    def _analyze_conditions(self, timestamp: pd.Timestamp) -> MarketCondition:
        """Analyze current market conditions"""
        # Default conditions
        if len(self.price_buffer) < 20:
            return MarketCondition(
                volatility=0.5,
                trend_strength=0.0,
                volume_ratio=1.0,
                time_of_day='mid',
                recent_performance=0.5
            )
        
        # Calculate volatility (using ATR concept)
        ranges = []
        for bar in list(self.price_buffer)[-20:]:
            ranges.append(bar['high'] - bar['low'])
        
        avg_range = np.mean(ranges)
        recent_range = ranges[-1]
        volatility = min(1.0, recent_range / (avg_range * 2))
        
        # Calculate trend strength
        closes = [bar['close'] for bar in self.price_buffer]
        if len(closes) >= 20:
            sma_20 = np.mean(closes[-20:])
            sma_5 = np.mean(closes[-5:])
            trend_strength = (sma_5 - sma_20) / sma_20
            trend_strength = max(-1, min(1, trend_strength * 10))
        else:
            trend_strength = 0.0
        
        # Volume ratio
        if len(self.volume_buffer) >= 20:
            avg_volume = np.mean(list(self.volume_buffer)[:-1])
            volume_ratio = self.volume_buffer[-1] / avg_volume if avg_volume > 0 else 1.0
        else:
            volume_ratio = 1.0
        
        # Time of day
        hour = timestamp.hour
        if 9 <= hour < 10:
            time_of_day = 'open'
        elif 10 <= hour < 14:
            time_of_day = 'mid'
        else:
            time_of_day = 'close'
        
        # Recent performance
        if self.recent_trades:
            wins = sum(1 for trade in self.recent_trades if trade['pnl'] > 0)
            recent_performance = wins / len(self.recent_trades)
        else:
            recent_performance = 0.5
        
        return MarketCondition(
            volatility=volatility,
            trend_strength=trend_strength,
            volume_ratio=volume_ratio,
            time_of_day=time_of_day,
            recent_performance=recent_performance
        )
    
    def _calculate_adjustment(self, conditions: MarketCondition) -> ThresholdAdjustment:
        """Calculate threshold adjustment based on conditions"""
        
        # Volatility adjustment
        if conditions.volatility < 0.3:
            vol_adj = self.adjustments['volatility']['low']
        elif conditions.volatility > 0.7:
            vol_adj = self.adjustments['volatility']['high']
        else:
            vol_adj = self.adjustments['volatility']['normal']
        
        # Trend adjustment
        if abs(conditions.trend_strength) > 0.5:
            trend_adj = self.adjustments['trend']['strong_up']
        else:
            trend_adj = self.adjustments['trend']['sideways']
        
        # Volume adjustment
        if conditions.volume_ratio < 0.7:
            volume_adj = self.adjustments['volume']['low']
        elif conditions.volume_ratio > 1.5:
            volume_adj = self.adjustments['volume']['high']
        else:
            volume_adj = self.adjustments['volume']['normal']
        
        # Time adjustment
        time_adj = self.adjustments['time'][conditions.time_of_day]
        
        # Performance adjustment
        if conditions.recent_performance < 0.4:
            perf_adj = self.adjustments['performance']['poor']
        elif conditions.recent_performance > 0.6:
            perf_adj = self.adjustments['performance']['good']
        else:
            perf_adj = self.adjustments['performance']['normal']
        
        # Calculate final threshold
        total_adjustment = vol_adj + trend_adj + volume_adj + time_adj + perf_adj
        final_threshold = self.base_threshold + total_adjustment
        
        # Constrain to limits
        final_threshold = max(self.min_threshold, min(self.max_threshold, final_threshold))
        
        # Calculate confidence in adjustment
        confidence = self._calculate_confidence(conditions)
        
        return ThresholdAdjustment(
            base_threshold=self.base_threshold,
            volatility_adj=vol_adj,
            trend_adj=trend_adj,
            volume_adj=volume_adj,
            time_adj=time_adj,
            performance_adj=perf_adj,
            final_threshold=final_threshold,
            confidence=confidence
        )
    
    def _calculate_confidence(self, conditions: MarketCondition) -> float:
        """Calculate confidence in threshold adjustment"""
        confidence = 1.0
        
        # Reduce confidence in extreme conditions
        if conditions.volatility > 0.8 or conditions.volatility < 0.2:
            confidence *= 0.8
            
        # Reduce confidence with limited performance data
        if len(self.recent_trades) < 10:
            confidence *= 0.7
            
        # Reduce confidence in choppy markets
        if abs(conditions.trend_strength) < 0.2:
            confidence *= 0.9
            
        return confidence
    
    def record_trade(self, entry_price: float, exit_price: float, 
                    direction: int, ml_score: float):
        """Record trade result for performance tracking"""
        pnl = (exit_price - entry_price) / entry_price * direction
        
        self.recent_trades.append({
            'pnl': pnl,
            'ml_score': ml_score,
            'timestamp': pd.Timestamp.now()
        })
    
    def get_threshold_stats(self) -> Dict:
        """Get statistics on threshold adjustments"""
        if not self.threshold_history:
            return {}
            
        thresholds = [h['threshold'] for h in self.threshold_history]
        
        return {
            'current': thresholds[-1] if thresholds else self.base_threshold,
            'mean': np.mean(thresholds),
            'std': np.std(thresholds),
            'min': min(thresholds),
            'max': max(thresholds),
            'changes': len([i for i in range(1, len(thresholds)) 
                          if abs(thresholds[i] - thresholds[i-1]) > 0.1])
        }
    
    def suggest_base_adjustment(self) -> float:
        """Suggest new base threshold based on performance"""
        if len(self.recent_trades) < 20:
            return self.base_threshold
            
        # Analyze performance by ML score ranges
        score_ranges = [(2.0, 2.5), (2.5, 3.0), (3.0, 3.5), (3.5, 4.0), (4.0, 4.5)]
        best_range = None
        best_performance = 0
        
        for low, high in score_ranges:
            trades_in_range = [t for t in self.recent_trades 
                             if low <= t['ml_score'] < high]
            
            if len(trades_in_range) >= 5:
                win_rate = sum(1 for t in trades_in_range if t['pnl'] > 0) / len(trades_in_range)
                
                if win_rate > best_performance:
                    best_performance = win_rate
                    best_range = (low, high)
        
        if best_range:
            suggested_threshold = (best_range[0] + best_range[1]) / 2
            return suggested_threshold
        
        return self.base_threshold
    
    def save_state(self, filepath: str):
        """Save adaptive threshold state"""
        state = {
            'base_threshold': self.base_threshold,
            'threshold_history': list(self.threshold_history)[-50:],
            'recent_trades': list(self.recent_trades),
            'adjustments': self.adjustments
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(state, f, default=str)
    
    def load_state(self, filepath: str):
        """Load adaptive threshold state"""
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                state = json.load(f)
                
            self.base_threshold = state.get('base_threshold', self.base_threshold)
            self.recent_trades = deque(state.get('recent_trades', []), maxlen=20)
            self.adjustments = state.get('adjustments', self.adjustments)