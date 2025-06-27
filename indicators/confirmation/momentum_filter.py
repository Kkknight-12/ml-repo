"""
Momentum Confirmation Filter
===========================

Filters signals based on momentum alignment.
Uses RSI, MACD, and rate of change for confirmation.
"""

import numpy as np
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class MomentumStats:
    """Momentum analysis statistics"""
    rsi: float
    macd_value: float
    macd_signal: float
    macd_histogram: float
    roc: float  # Rate of change
    momentum_score: float
    is_aligned: bool
    signal_strength: str  # 'strong', 'moderate', 'weak'


class MomentumConfirmationFilter:
    """
    Filters signals based on momentum indicators alignment.
    
    Key concepts:
    1. RSI should confirm direction (not overbought/oversold)
    2. MACD should show momentum in signal direction
    3. Rate of change should be positive for longs, negative for shorts
    """
    
    def __init__(self,
                 rsi_period: int = 14,
                 rsi_overbought: float = 70,
                 rsi_oversold: float = 30,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_signal: int = 9,
                 roc_period: int = 10):
        """
        Initialize momentum filter.
        
        Args:
            rsi_period: Period for RSI calculation
            rsi_overbought: RSI overbought threshold
            rsi_oversold: RSI oversold threshold
            macd_fast: Fast EMA period for MACD
            macd_slow: Slow EMA period for MACD
            macd_signal: Signal line EMA period
            roc_period: Period for rate of change
        """
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal_period = macd_signal
        self.roc_period = roc_period
        
        # Buffers
        self.price_buffer: List[float] = []
        self.rsi_buffer: List[float] = []
        self.gains_buffer: List[float] = []
        self.losses_buffer: List[float] = []
        
        # MACD state
        self.ema_fast: Optional[float] = None
        self.ema_slow: Optional[float] = None
        self.macd_signal_ema: Optional[float] = None
        self.macd_values: List[float] = []
        
    def update(self, close: float) -> MomentumStats:
        """
        Update momentum analysis with new price.
        
        Args:
            close: Current close price
            
        Returns:
            MomentumStats with analysis results
        """
        self.price_buffer.append(close)
        
        # Calculate RSI
        rsi = self._calculate_rsi()
        
        # Calculate MACD
        macd_value, macd_signal, macd_histogram = self._calculate_macd(close)
        
        # Calculate Rate of Change
        roc = self._calculate_roc()
        
        # Calculate momentum score
        momentum_score = self._calculate_momentum_score(
            rsi, macd_histogram, roc
        )
        
        # Check alignment
        is_aligned, signal_strength = self._check_alignment(
            rsi, macd_histogram, roc, momentum_score
        )
        
        return MomentumStats(
            rsi=rsi,
            macd_value=macd_value,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            roc=roc,
            momentum_score=momentum_score,
            is_aligned=is_aligned,
            signal_strength=signal_strength
        )
    
    def _calculate_rsi(self) -> float:
        """Calculate RSI (Relative Strength Index)"""
        if len(self.price_buffer) < 2:
            return 50.0  # Neutral
        
        # Calculate price changes
        if len(self.price_buffer) >= 2:
            change = self.price_buffer[-1] - self.price_buffer[-2]
            gain = max(0, change)
            loss = max(0, -change)
            
            self.gains_buffer.append(gain)
            self.losses_buffer.append(loss)
            
            # Limit buffer size
            if len(self.gains_buffer) > self.rsi_period * 2:
                self.gains_buffer.pop(0)
                self.losses_buffer.pop(0)
        
        if len(self.gains_buffer) < self.rsi_period:
            return 50.0  # Not enough data
        
        # Calculate average gains and losses
        avg_gain = np.mean(self.gains_buffer[-self.rsi_period:])
        avg_loss = np.mean(self.losses_buffer[-self.rsi_period:])
        
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, close: float) -> Tuple[float, float, float]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        # Update EMAs
        if self.ema_fast is None:
            self.ema_fast = close
            self.ema_slow = close
        else:
            alpha_fast = 2.0 / (self.macd_fast + 1)
            alpha_slow = 2.0 / (self.macd_slow + 1)
            
            self.ema_fast = alpha_fast * close + (1 - alpha_fast) * self.ema_fast
            self.ema_slow = alpha_slow * close + (1 - alpha_slow) * self.ema_slow
        
        # Calculate MACD line
        macd_value = self.ema_fast - self.ema_slow
        self.macd_values.append(macd_value)
        
        # Limit buffer
        if len(self.macd_values) > self.macd_signal_period * 2:
            self.macd_values.pop(0)
        
        # Calculate signal line
        if self.macd_signal_ema is None:
            self.macd_signal_ema = macd_value
        else:
            alpha_signal = 2.0 / (self.macd_signal_period + 1)
            self.macd_signal_ema = alpha_signal * macd_value + \
                                  (1 - alpha_signal) * self.macd_signal_ema
        
        # Calculate histogram
        macd_histogram = macd_value - self.macd_signal_ema
        
        return macd_value, self.macd_signal_ema, macd_histogram
    
    def _calculate_roc(self) -> float:
        """Calculate Rate of Change"""
        if len(self.price_buffer) <= self.roc_period:
            return 0.0
        
        current_price = self.price_buffer[-1]
        past_price = self.price_buffer[-self.roc_period - 1]
        
        if past_price == 0:
            return 0.0
        
        roc = ((current_price - past_price) / past_price) * 100
        return roc
    
    def _calculate_momentum_score(self, rsi: float, 
                                macd_histogram: float, roc: float) -> float:
        """
        Calculate overall momentum score (0-1).
        Higher score indicates stronger momentum.
        """
        score = 0.0
        
        # RSI contribution (33%)
        if rsi > 50 and rsi < self.rsi_overbought:
            # Bullish momentum
            score += 0.33 * ((rsi - 50) / (self.rsi_overbought - 50))
        elif rsi < 50 and rsi > self.rsi_oversold:
            # Bearish momentum
            score += 0.33 * ((50 - rsi) / (50 - self.rsi_oversold))
        
        # MACD contribution (33%)
        if len(self.macd_values) > 0:
            # Normalize MACD histogram
            recent_values = self.macd_values[-20:] if len(self.macd_values) > 20 else self.macd_values
            max_hist = max(abs(v) for v in recent_values) if recent_values else 1
            
            if max_hist > 0:
                normalized_hist = macd_histogram / max_hist
                score += 0.33 * min(1.0, abs(normalized_hist))
        
        # ROC contribution (34%)
        # Normalize ROC (typical range -5% to +5%)
        normalized_roc = min(1.0, abs(roc) / 5.0)
        score += 0.34 * normalized_roc
        
        return min(1.0, score)
    
    def _check_alignment(self, rsi: float, macd_histogram: float,
                       roc: float, momentum_score: float) -> Tuple[bool, str]:
        """
        Check if momentum indicators are aligned.
        
        Returns:
            (is_aligned, signal_strength)
        """
        # Count aligned indicators
        aligned_count = 0
        
        # Check RSI
        if (rsi > 50 and rsi < self.rsi_overbought) or \
           (rsi < 50 and rsi > self.rsi_oversold):
            aligned_count += 1
        
        # Check MACD
        if abs(macd_histogram) > 0:
            aligned_count += 1
        
        # Check ROC
        if abs(roc) > 0.5:  # Meaningful movement
            aligned_count += 1
        
        # Determine alignment and strength
        is_aligned = aligned_count >= 2  # At least 2 of 3 indicators
        
        if momentum_score >= 0.7:
            signal_strength = 'strong'
        elif momentum_score >= 0.4:
            signal_strength = 'moderate'
        else:
            signal_strength = 'weak'
        
        return is_aligned, signal_strength
    
    def check_signal_momentum(self, signal_direction: int) -> Tuple[bool, float]:
        """
        Check if momentum supports the signal direction.
        
        Args:
            signal_direction: 1 for long, -1 for short
            
        Returns:
            (is_confirmed, confidence)
        """
        if len(self.price_buffer) < max(self.rsi_period, self.roc_period):
            return False, 0.0
        
        stats = self.update(self.price_buffer[-1])
        
        # Check direction alignment
        confidence = 0.0
        
        # RSI alignment (40%)
        if signal_direction > 0:  # Long signal
            if stats.rsi > 50 and stats.rsi < self.rsi_overbought:
                confidence += 0.4 * ((stats.rsi - 50) / (self.rsi_overbought - 50))
        else:  # Short signal
            if stats.rsi < 50 and stats.rsi > self.rsi_oversold:
                confidence += 0.4 * ((50 - stats.rsi) / (50 - self.rsi_oversold))
        
        # MACD alignment (30%)
        if (signal_direction > 0 and stats.macd_histogram > 0) or \
           (signal_direction < 0 and stats.macd_histogram < 0):
            confidence += 0.3
        
        # ROC alignment (30%)
        if (signal_direction > 0 and stats.roc > 0) or \
           (signal_direction < 0 and stats.roc < 0):
            confidence += 0.3 * min(1.0, abs(stats.roc) / 3.0)
        
        is_confirmed = confidence >= 0.5 and stats.is_aligned
        
        return is_confirmed, confidence