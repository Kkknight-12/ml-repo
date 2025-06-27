#!/usr/bin/env python3
"""
Relaxed Signal Generator
========================

Less restrictive entry conditions for more reasonable trade frequency
"""

from typing import List, Tuple
from data.data_types import Label


class RelaxedSignalGenerator:
    """
    Signal generator with relaxed entry conditions
    
    Key changes:
    1. Remove "different from previous" requirement
    2. Use EMA OR SMA trend (not both)
    3. Optional ML threshold
    """
    
    def __init__(self, label: Label, ml_threshold: float = 0):
        self.label = label
        self.ml_threshold = ml_threshold
        self.entry_cooldown = 10  # Minimum bars between entries
        self.last_entry_bar = -100
    
    def check_entry_conditions(
        self,
        signal: int,
        signal_history: List[int],
        ml_prediction: float,
        is_bullish_kernel: bool,
        is_bearish_kernel: bool,
        is_ema_uptrend: bool,
        is_ema_downtrend: bool,
        is_sma_uptrend: bool,
        is_sma_downtrend: bool,
        current_bar: int = 0
    ) -> Tuple[bool, bool]:
        """
        Check relaxed entry conditions
        
        Changes:
        1. No "different signal" requirement
        2. EMA OR SMA trend (not both required)
        3. Cooldown period between entries
        4. Optional ML threshold
        """
        # Check ML threshold if set
        if self.ml_threshold > 0 and abs(ml_prediction) < self.ml_threshold:
            return False, False
        
        # Check cooldown
        if current_bar - self.last_entry_bar < self.entry_cooldown:
            return False, False
        
        # Long entry: signal + kernel + (EMA OR SMA uptrend)
        start_long_trade = (
            signal == self.label.long and
            is_bullish_kernel and
            (is_ema_uptrend or is_sma_uptrend)  # Relaxed: OR instead of AND
        )
        
        # Short entry: signal + kernel + (EMA OR SMA downtrend)
        start_short_trade = (
            signal == self.label.short and
            is_bearish_kernel and
            (is_ema_downtrend or is_sma_downtrend)  # Relaxed: OR instead of AND
        )
        
        # Update last entry bar if entry triggered
        if start_long_trade or start_short_trade:
            self.last_entry_bar = current_bar
        
        return start_long_trade, start_short_trade
    
    def check_entry_conditions_simple(
        self,
        signal: int,
        ml_prediction: float,
        is_bullish_kernel: bool,
        is_bearish_kernel: bool,
        current_bar: int = 0
    ) -> Tuple[bool, bool]:
        """
        Very simple entry conditions (for testing)
        
        Only requires:
        1. ML signal direction
        2. Kernel confirmation
        3. Optional ML threshold
        """
        # Check ML threshold if set
        if self.ml_threshold > 0 and abs(ml_prediction) < self.ml_threshold:
            return False, False
        
        # Check cooldown
        if current_bar - self.last_entry_bar < self.entry_cooldown:
            return False, False
        
        # Simple entries: just signal + kernel
        start_long_trade = signal == self.label.long and is_bullish_kernel
        start_short_trade = signal == self.label.short and is_bearish_kernel
        
        # Update last entry bar
        if start_long_trade or start_short_trade:
            self.last_entry_bar = current_bar
        
        return start_long_trade, start_short_trade
    
    def check_exit_conditions(
        self,
        bars_held: int,
        signal_history: List[int],
        entry_history: List[Tuple[bool, bool]],
        use_dynamic_exits: bool,
        kernel_cross_signals: Tuple[bool, bool],
        last_signal_was_bullish: bool = None,
        last_signal_was_bearish: bool = None
    ) -> Tuple[bool, bool]:
        """Standard exit conditions"""
        # Default exits
        end_long_trade = False
        end_short_trade = False
        
        # Fixed bar exit (5 bars)
        if bars_held >= 5:
            if len(entry_history) > 5:
                if entry_history[5][0]:  # Was long entry 5 bars ago
                    end_long_trade = True
                if entry_history[5][1]:  # Was short entry 5 bars ago
                    end_short_trade = True
        
        # Dynamic exits based on kernel
        if use_dynamic_exits and bars_held > 0:
            if kernel_cross_signals[1] and last_signal_was_bullish:  # Bearish cross
                end_long_trade = True
            if kernel_cross_signals[0] and last_signal_was_bearish:  # Bullish cross
                end_short_trade = True
        
        return end_long_trade, end_short_trade
    
    def calculate_bars_held(self, entry_history: List[Tuple[bool, bool]]) -> int:
        """Calculate bars held in position"""
        if not entry_history:
            return 0
        
        bars_held = 0
        for i, (long_entry, short_entry) in enumerate(entry_history):
            if long_entry or short_entry:
                bars_held = i
                break
        
        return bars_held
    
    def is_early_signal_flip(self, signal_history: List[int]) -> bool:
        """Not used in relaxed version"""
        return False


# Test the impact
if __name__ == "__main__":
    from data.data_types import Label
    
    label = Label()
    
    # Compare generators
    print("Signal Generator Comparison:")
    print("1. Original: Requires different signal + kernel + EMA + SMA")
    print("2. Relaxed: No different signal + kernel + (EMA OR SMA)")
    print("3. Simple: Just signal + kernel")
    
    # Example scenario
    print("\nExample: ML says LONG for 10 bars in a row")
    print("Original: Only 1 entry (first bar)")
    print("Relaxed: Multiple entries (with cooldown)")
    print("Simple: Multiple entries (with cooldown)")