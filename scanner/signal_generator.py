"""
Signal Generator - Converts ML predictions to trading signals
Implements all Pine Script entry/exit logic WITHOUT state management
"""
from typing import List, Tuple, Optional, Dict
from data.data_types import Label, Filter
from ml.lorentzian_knn_fixed import LorentzianKNNFixed as LorentzianKNN


class SignalGenerator:
    """
    Generates trading signals based on ML predictions and filters
    Maintains NO state - each bar evaluated independently
    """

    def __init__(self, label: Label):
        """Initialize with direction labels"""
        self.label = label

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
        Check for entry conditions (buy/sell signals)

        Pine Script logic:
        - isNewBuySignal = isBuySignal and isDifferentSignalType
        - isNewSellSignal = isSellSignal and isDifferentSignalType
        - startLongTrade = isNewBuySignal and isBullish and isEmaUptrend and isSmaUptrend

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
        # NOTE: signal_history[0] is the most recent signal (before current)
        # signal_history[1] is the one before that
        is_different_signal = False
        if len(signal_history) > 0:
            # Compare with the most recent historical signal
            is_different_signal = signal != signal_history[0]
        else:
            is_different_signal = True  # First signal

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
        # Pine Script: isHeldFourBars = barsHeld == 4
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

        # Dynamic exits (if enabled)
        if use_dynamic_exits:
            # Pine Script dynamic exit logic:
            # endLongTradeDynamic = (isBearishChange and isValidLongExit[1])
            # endShortTradeDynamic = (isBullishChange and isValidShortExit[1])
            #
            # Where:
            # - isBearishChange is when kernel turns bearish
            # - isBullishChange is when kernel turns bullish
            # - isValidLongExit means exit bar came after entry bar
            # - isValidShortExit means exit bar came after entry bar
            
            # We use kernel crossovers as proxy for direction changes
            bullish_cross, bearish_cross = kernel_cross_signals
            
            # For validity check, we need to know if we're in a position
            # This is determined by checking if last signal was bullish/bearish
            if last_signal_was_bullish is None:
                # Infer from entry history
                last_signal_was_bullish = any(entry[0] for entry in entry_history[:10])
            if last_signal_was_bearish is None:
                last_signal_was_bearish = any(entry[1] for entry in entry_history[:10])
            
            # Dynamic exits based on kernel crossovers
            end_long_trade_dynamic = bearish_cross and last_signal_was_bullish
            end_short_trade_dynamic = bullish_cross and last_signal_was_bearish

            end_long_trade = end_long_trade_dynamic
            end_short_trade = end_short_trade_dynamic
        else:
            end_long_trade = end_long_trade_strict
            end_short_trade = end_short_trade_strict

        return end_long_trade, end_short_trade

    def calculate_bars_held(self, entry_history: List[Tuple[bool, bool]]) -> int:
        """
        Calculate bars held in position (no state, inferred from history)

        Args:
            entry_history: List of (start_long, start_short) tuples

        Returns:
            Number of bars held (0 if not in position)
        """
        bars_held = 0

        # Count bars since last entry
        for i, (long_entry, short_entry) in enumerate(entry_history):
            if long_entry or short_entry:
                bars_held = i
                break
            elif i < len(entry_history) - 1:
                # Check if still in position
                bars_held = i + 1
            else:
                bars_held = 0

        return min(bars_held, 4)  # Cap at 4 bars

    def is_early_signal_flip(self, signal_history: List[int]) -> bool:
        """
        Check if signal flipped too early (within 4 bars)

        Pine Script:
        isEarlySignalFlip = ta.change(signal) and (ta.change(signal[1]) or
                           ta.change(signal[2]) or ta.change(signal[3]))
        """
        if len(signal_history) < 4:
            return False

        # Current signal changed
        signal_changed = (len(signal_history) > 1 and
                          signal_history[0] != signal_history[1])

        if not signal_changed:
            return False

        # Check if any of previous 3 signals also changed
        early_flip = False
        for i in range(1, min(4, len(signal_history) - 1)):
            if signal_history[i] != signal_history[i + 1]:
                early_flip = True
                break

        return early_flip