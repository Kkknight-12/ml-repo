#!/usr/bin/env python3
"""
Implement early signal flip detection to match Pine Script
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_enhanced_signal_generator():
    """Create enhanced signal generator with early flip detection"""
    
    code = '''"""
Signal Generator - Enhanced with Early Flip Detection
Implements Pine Script's signal stability logic
"""
from typing import List, Tuple, Optional, Dict
from data.data_types import Label, Filter
from ml.lorentzian_knn_fixed_corrected import LorentzianKNNFixedCorrected as LorentzianKNN


class SignalGenerator:
    """
    Generates trading signals based on ML predictions and filters
    Now includes early signal flip detection to match Pine Script
    """

    def __init__(self, label: Label):
        """Initialize with direction labels"""
        self.label = label

    def is_early_signal_flip(self, signal_history: List[int]) -> bool:
        """
        Check if current signal change is an early flip
        
        Pine Script logic:
        isEarlySignalFlip = ta.change(signal) and 
            (ta.change(signal[1]) or ta.change(signal[2]) or ta.change(signal[3]))
        
        This means a flip is "early" if:
        - The signal just changed AND
        - Any of the previous 3 bars also had a signal change
        
        Args:
            signal_history: List where [0] is current, [1] is previous, etc.
            
        Returns:
            True if this is an early flip
        """
        if len(signal_history) < 5:
            return False
            
        # Check if signal changed now
        current_change = signal_history[0] != signal_history[1]
        
        if not current_change:
            return False
            
        # Check if any of the previous 3 bars had changes
        change_1_bar_ago = signal_history[1] != signal_history[2]
        change_2_bars_ago = signal_history[2] != signal_history[3]
        change_3_bars_ago = signal_history[3] != signal_history[4]
        
        # Early flip if current change AND any recent change
        return current_change and (change_1_bar_ago or change_2_bars_ago or change_3_bars_ago)

    def check_entry_conditions(
            self,
            signal: int,
            signal_history: List[int],
            is_bullish_kernel: bool,
            is_bearish_kernel: bool,
            is_ema_uptrend: bool,
            is_ema_downtrend: bool,
            is_sma_uptrend: bool,
            is_sma_downtrend: bool
    ) -> Tuple[bool, bool]:
        """
        Check for entry conditions with early flip prevention
        
        Args:
            signal: Current ML signal
            signal_history: List of previous signals (0=current, 1=prev, etc)
            is_bullish_kernel: Kernel filter bullish state
            is_bearish_kernel: Kernel filter bearish state
            is_ema_uptrend: EMA filter state
            is_ema_downtrend: EMA filter state
            is_sma_uptrend: SMA filter state
            is_sma_downtrend: SMA filter state
            
        Returns:
            (start_long_trade, start_short_trade)
        """
        # Check if signal type changed
        is_different_signal = False
        if len(signal_history) > 0:
            is_different_signal = signal != signal_history[0]
        else:
            is_different_signal = True  # First signal
            
        # Check for early flip
        is_early_flip = self.is_early_signal_flip([signal] + signal_history)
        
        # Block signals if it's an early flip
        if is_early_flip:
            return False, False

        # Buy signal conditions
        is_buy_signal = (signal == self.label.long and
                         is_ema_uptrend and is_sma_uptrend)
        is_new_buy_signal = is_buy_signal and is_different_signal

        # Sell signal conditions
        is_sell_signal = (signal == self.label.short and
                          is_ema_downtrend and is_sma_downtrend)
        is_new_sell_signal = is_sell_signal and is_different_signal

        # Final entry conditions
        start_long_trade = (is_new_buy_signal and is_bullish_kernel and
                            is_ema_uptrend and is_sma_uptrend)

        start_short_trade = (is_new_sell_signal and is_bearish_kernel and
                             is_ema_downtrend and is_sma_downtrend)

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
        """
        Check for exit conditions
        
        Pine Script uses:
        - 4-bar fixed exit rule
        - Optional dynamic exits based on kernel
        
        Args:
            bars_held: Number of bars since entry
            signal_history: Historical signals
            entry_history: History of (start_long, start_short) tuples
            use_dynamic_exits: Whether to use dynamic exits
            kernel_cross_signals: (bullish_cross, bearish_cross) from kernel
            last_signal_was_bullish: For dynamic exits (from Pine Script)
            last_signal_was_bearish: For dynamic exits (from Pine Script)
            
        Returns:
            (end_long_trade, end_short_trade)
        """
        # Default exits
        end_long_trade = False
        end_short_trade = False

        # Need at least 4 bars of history for exit logic
        if len(entry_history) < 4:
            return False, False

        # Get entry from 4 bars ago
        start_long_4_bars_ago = entry_history[4][0] if len(entry_history) >= 5 else False
        start_short_4_bars_ago = entry_history[4][1] if len(entry_history) >= 5 else False

        # Fixed exit conditions (4-bar rule)
        is_held_four_bars = bars_held == 4
        is_held_less_than_four = 0 < bars_held < 4

        # Determine last signal type
        if len(signal_history) >= 5:
            last_signal_buy = signal_history[4] == self.label.long
            last_signal_sell = signal_history[4] == self.label.short
        else:
            last_signal_buy = False
            last_signal_sell = False

        # Current new signals
        current_signal = signal_history[0] if signal_history else self.label.neutral
        is_new_sell_signal = (len(signal_history) > 1 and
                              current_signal == self.label.short and
                              current_signal != signal_history[1])
        is_new_buy_signal = (len(signal_history) > 1 and
                             current_signal == self.label.long and
                             current_signal != signal_history[1])

        # Fixed exits
        end_long_trade_strict = (
                ((is_held_four_bars and last_signal_buy) or
                 (is_held_less_than_four and is_new_sell_signal and last_signal_buy))
                and start_long_4_bars_ago
        )

        end_short_trade_strict = (
                ((is_held_four_bars and last_signal_sell) or
                 (is_held_less_than_four and is_new_buy_signal and last_signal_sell))
                and start_short_4_bars_ago
        )

        # Dynamic exits
        if use_dynamic_exits:
            # Pine Script: Dynamic Exit Conditions: Booleans for dynamically closing trades based on kernel crosses
            end_long_trade_dynamic = kernel_cross_signals[0] and last_signal_was_bullish
            end_short_trade_dynamic = kernel_cross_signals[1] and last_signal_was_bearish

            end_long_trade = end_long_trade_strict or end_long_trade_dynamic
            end_short_trade = end_short_trade_strict or end_short_trade_dynamic
        else:
            end_long_trade = end_long_trade_strict
            end_short_trade = end_short_trade_strict

        return end_long_trade, end_short_trade

    def calculate_bars_held(self, entry_history: List[Tuple[bool, bool]]) -> int:
        """
        Calculate how many bars a position has been held
        
        Args:
            entry_history: List of (start_long, start_short) tuples
            
        Returns:
            Number of bars held (0 if no position)
        """
        bars_held = 0
        
        for i, (start_long, start_short) in enumerate(entry_history):
            if start_long or start_short:
                bars_held = i
                break
                
        return bars_held
'''
    
    # Write the enhanced signal generator
    output_path = "scanner/signal_generator_enhanced.py"
    with open(output_path, 'w') as f:
        f.write(code)
    
    print(f"✅ Created enhanced signal generator: {output_path}")
    print("\nKey enhancements:")
    print("1. Added is_early_signal_flip() method")
    print("2. Blocks entry signals if they're early flips")
    print("3. Matches Pine Script's signal stability logic")
    
    return output_path


if __name__ == "__main__":
    create_enhanced_signal_generator()