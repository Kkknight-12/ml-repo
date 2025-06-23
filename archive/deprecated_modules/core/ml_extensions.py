"""
ML Extensions - Filters and helper functions
Direct conversion from Pine Script's MLExtensions library
"""
import math
from typing import List, Tuple, Optional
from .math_helpers import pine_ema, pine_atr, pine_rma
from .na_handling import filter_none_values, safe_divide  # PHASE 3: Add NA handling
from .indicator_state_manager import IndicatorStateManager
from .stateful_ta import StatefulEMA, StatefulATR, StatefulChange

# Use the same global instance from indicators module
from .indicators import _indicator_manager


def regime_filter(ohlc4_values: List[Optional[float]], threshold: float,
                  use_regime_filter: bool, high_values: List[Optional[float]] = None,
                  low_values: List[Optional[float]] = None) -> bool:
    """
    Regime Filter - detects trending vs ranging markets
    Based on KLMF (Kalman-Like Moving Filter) slope

    Pine Script:
    - Calculates normalized slope decline
    - Returns true if market is trending (above threshold)
    """
    if not use_regime_filter:
        return True

    # PHASE 3 FIX: Filter None values
    clean_ohlc4 = filter_none_values(ohlc4_values)
    
    if not clean_ohlc4 or len(clean_ohlc4) < 200:
        return True
    
    ohlc4_values = clean_ohlc4  # Use clean values

    # Need to process bars in chronological order (oldest to newest)
    # Since our list is newest first, we need to reverse for calculations
    src_chronological = list(reversed(ohlc4_values[-200:]))  # Last 200 bars
    
    # Also reverse high/low if provided
    high_chronological = None
    low_chronological = None
    if high_values and low_values:
        # PHASE 3 FIX: Clean high/low values too
        clean_high = filter_none_values(high_values)
        clean_low = filter_none_values(low_values)
        high_chronological = list(reversed(clean_high[-200:])) if clean_high else None
        low_chronological = list(reversed(clean_low[-200:])) if clean_low else None
    
    # Initialize persistent variables
    value1 = 0.0
    value2 = 0.0
    klmf = 0.0
    klmf_values = []
    abs_curve_slopes = []
    
    # Process each bar
    for i in range(1, len(src_chronological)):
        # Update value1 and value2
        value1 = 0.2 * (src_chronological[i] - src_chronological[i-1]) + 0.8 * value1
        
        # For value2, use actual high-low if available, otherwise approximate
        if high_chronological and low_chronological and i < len(high_chronological) and i < len(low_chronological):
            # Use actual high-low range
            high_low_range = high_chronological[i] - low_chronological[i]
            value2 = 0.1 * high_low_range + 0.8 * value2
        else:
            # Approximate using price movement
            price_change = abs(src_chronological[i] - src_chronological[i-1])
            value2 = 0.1 * price_change + 0.8 * value2
        
        # Calculate omega and alpha
        if value2 != 0:
            omega = abs(value1 / value2)
        else:
            omega = 0
            
        alpha = (-omega * omega + math.sqrt(omega ** 4 + 16 * omega ** 2)) / 8
        
        # Update KLMF
        klmf = alpha * src_chronological[i] + (1 - alpha) * klmf
        klmf_values.append(klmf)
        
        # Calculate absolute curve slope
        if i > 0 and len(klmf_values) > 1:
            abs_curve_slope = abs(klmf - klmf_values[-2])
            abs_curve_slopes.append(abs_curve_slope)
    
    # Calculate exponential average of absolute curve slope
    # Changed condition: require at least 50 slopes instead of 200
    if len(abs_curve_slopes) >= 50:
        # Use EMA for the average with available length
        ema_length = min(200, len(abs_curve_slopes))
        multiplier = 2.0 / (ema_length + 1)
        exp_avg_slope = abs_curve_slopes[0]
        
        for i in range(1, len(abs_curve_slopes)):
            exp_avg_slope = abs_curve_slopes[i] * multiplier + exp_avg_slope * (1 - multiplier)
        
        # Get current slope (most recent)
        current_slope = abs_curve_slopes[-1] if abs_curve_slopes else 0
        
        # Calculate normalized slope decline
        if exp_avg_slope > 0:
            normalized_slope_decline = (current_slope - exp_avg_slope) / exp_avg_slope
        else:
            normalized_slope_decline = 0
        
        # Return true if slope decline is above threshold (trending market)
        return normalized_slope_decline >= threshold
    
    # If not enough data, return True (assume trending)
    return True


def filter_adx(high_values: List[Optional[float]], low_values: List[Optional[float]],
               close_values: List[Optional[float]], length: int, adx_threshold: int,
               use_adx_filter: bool) -> bool:
    """
    ADX Filter - filters based on trend strength
    Returns True if ADX > threshold (trending market)
    """
    if not use_adx_filter:
        return True

    if not high_values or not low_values or not close_values:
        return True

    from .indicators import calculate_adx

    adx = calculate_adx(high_values, low_values, close_values, length)

    return adx > adx_threshold


def filter_volatility(high_values: List[Optional[float]], low_values: List[Optional[float]],
                      close_values: List[Optional[float]], min_length: int = 1,
                      max_length: int = 10, use_volatility_filter: bool = True) -> bool:
    """
    Volatility Filter - compares recent vs historical volatility
    Returns True if recent ATR > historical ATR
    """
    if not use_volatility_filter:
        return True

    if not high_values or not low_values or not close_values:
        return True

    # Calculate recent and historical ATR
    recent_atr = pine_atr(high_values, low_values, close_values, min_length)
    historical_atr = pine_atr(high_values, low_values, close_values, max_length)

    return recent_atr > historical_atr


def backtest(high_values: List[Optional[float]], low_values: List[Optional[float]], open_values: List[Optional[float]],
             start_long_trades: List[bool], end_long_trades: List[bool],
             start_short_trades: List[bool], end_short_trades: List[bool],
             early_signal_flips: List[bool], max_bars_back_index: int,
             current_bar_index: int, src_values: List[Optional[float]], use_worst_case: bool) -> Tuple:
    """
    Simplified backtest function for statistics
    Returns: (totalWins, totalLosses, totalEarlySignalFlips, totalTrades,
              tradeStatsHeader, winLossRatio, winRate)
    """
    # This is a placeholder - actual implementation would track trades properly
    # For now, return dummy values to test the structure

    total_trades = 0
    total_wins = 0
    total_losses = 0
    total_early_flips = 0

    # Count trades based on signals
    for i in range(len(start_long_trades)):
        if i < len(start_long_trades) and start_long_trades[i]:
            total_trades += 1
            # Simplified win/loss logic
            if i < len(end_long_trades) - 4:
                # Check if profitable after 4 bars
                entry_price = src_values[i] if i < len(src_values) else 0
                exit_price = src_values[i + 4] if i + 4 < len(src_values) else entry_price
                if exit_price > entry_price:
                    total_wins += 1
                else:
                    total_losses += 1

    # Count short trades
    for i in range(len(start_short_trades)):
        if i < len(start_short_trades) and start_short_trades[i]:
            total_trades += 1
            # Simplified win/loss logic
            if i < len(end_short_trades) - 4:
                entry_price = src_values[i] if i < len(src_values) else 0
                exit_price = src_values[i + 4] if i + 4 < len(src_values) else entry_price
                if exit_price < entry_price:
                    total_wins += 1
                else:
                    total_losses += 1

    # Count early signal flips
    for flip in early_signal_flips:
        if flip:
            total_early_flips += 1

    # Calculate ratios
    win_loss_ratio = total_wins / total_losses if total_losses > 0 else total_wins
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

    trade_stats_header = "📈 Trade Stats"

    return (total_wins, total_losses, total_early_flips, total_trades,
            trade_stats_header, win_loss_ratio, win_rate)


# =============================================================================
# ENHANCED STATEFUL VERSIONS - Use these for production!
# =============================================================================

class EnhancedRegimeFilter:
    """
    Stateful implementation of the regime filter
    Maintains KLMF state across bars
    """
    def __init__(self, symbol: str, timeframe: str, threshold: float = -0.1):
        self.symbol = symbol
        self.timeframe = timeframe
        self.threshold = threshold
        self.value1 = 0.0
        self.value2 = 0.0
        self.klmf = 0.0
        
        # Use EMA for slope average
        self.slope_ema = _indicator_manager.get_or_create_ema(symbol, timeframe, 200)
        self.bars_processed = 0
        self.last_klmf = 0.0
        
    def update(self, current_ohlc4: float, current_high: float, current_low: float,
               previous_ohlc4: float, use_filter: bool = True) -> bool:
        """
        Update filter with new bar data
        Returns True if market is trending (passes filter)
        """
        if not use_filter:
            return True
            
        self.bars_processed += 1
        
        if self.bars_processed < 2:
            return True  # Not enough data
            
        # Update value1 and value2
        price_change = current_ohlc4 - previous_ohlc4
        self.value1 = 0.2 * price_change + 0.8 * self.value1
        
        # Use actual high-low range
        high_low_range = current_high - current_low
        self.value2 = 0.1 * high_low_range + 0.8 * self.value2
        
        # Calculate omega and alpha
        if self.value2 != 0:
            omega = abs(self.value1 / self.value2)
        else:
            omega = 0
            
        alpha = (-omega * omega + math.sqrt(omega ** 4 + 16 * omega ** 2)) / 8
        
        # Update KLMF
        self.klmf = alpha * current_ohlc4 + (1 - alpha) * self.klmf
        
        # Calculate absolute curve slope
        abs_curve_slope = abs(self.klmf - self.last_klmf)
        self.last_klmf = self.klmf
        
        # Update exponential average of slope
        exp_avg_slope = self.slope_ema.update(abs_curve_slope)
        
        # Calculate normalized slope decline
        if exp_avg_slope > 0 and self.bars_processed >= 50:
            normalized_slope_decline = (abs_curve_slope - exp_avg_slope) / exp_avg_slope
            # Return true if slope decline is above threshold (trending market)
            return normalized_slope_decline >= self.threshold
        
        # Default to trending if not enough data
        return True


def enhanced_regime_filter(current_ohlc4: float, current_high: float, current_low: float,
                          previous_ohlc4: float, symbol: str, timeframe: str,
                          threshold: float, use_regime_filter: bool) -> bool:
    """
    Enhanced stateful version of regime filter
    
    Args:
        current_ohlc4: Current bar's OHLC4 value
        current_high: Current bar's high
        current_low: Current bar's low
        previous_ohlc4: Previous bar's OHLC4 value
        symbol: Trading symbol
        timeframe: Timeframe
        threshold: Threshold for trend detection
        use_regime_filter: Whether to use the filter
        
    Returns:
        True if market is trending (passes filter)
    """
    if not use_regime_filter:
        return True
        
    # Get or create filter instance
    key = f"regime_filter_{threshold}"
    if not hasattr(_indicator_manager, '_custom_filters'):
        _indicator_manager._custom_filters = {}
        
    filter_key = f"{symbol}_{timeframe}_{key}"
    if filter_key not in _indicator_manager._custom_filters:
        _indicator_manager._custom_filters[filter_key] = EnhancedRegimeFilter(
            symbol, timeframe, threshold
        )
        
    filter_instance = _indicator_manager._custom_filters[filter_key]
    return filter_instance.update(current_ohlc4, current_high, current_low,
                                 previous_ohlc4, use_regime_filter)


def enhanced_filter_adx(current_high: float, current_low: float, current_close: float,
                       symbol: str, timeframe: str, length: int, adx_threshold: int,
                       use_adx_filter: bool) -> bool:
    """
    Enhanced stateful version of ADX filter
    
    Args:
        current_high: Current bar's high
        current_low: Current bar's low
        current_close: Current bar's close
        symbol: Trading symbol
        timeframe: Timeframe
        length: ADX period
        adx_threshold: Threshold for trend strength
        use_adx_filter: Whether to use the filter
        
    Returns:
        True if ADX > threshold (trending market)
    """
    if not use_adx_filter:
        return True
        
    # Get DMI instance (includes ADX)
    dmi = _indicator_manager.get_or_create_dmi(symbol, timeframe, length, length)
    
    # Update and get current ADX
    _, _, adx = dmi.update(current_high, current_low, current_close)
    
    return adx > adx_threshold


def enhanced_filter_volatility(current_high: float, current_low: float, current_close: float,
                              symbol: str, timeframe: str, min_length: int = 1,
                              max_length: int = 10, use_volatility_filter: bool = True) -> bool:
    """
    Enhanced stateful version of volatility filter
    
    Args:
        current_high: Current bar's high
        current_low: Current bar's low
        current_close: Current bar's close
        symbol: Trading symbol
        timeframe: Timeframe
        min_length: Period for recent ATR
        max_length: Period for historical ATR
        use_volatility_filter: Whether to use the filter
        
    Returns:
        True if recent ATR > historical ATR
    """
    if not use_volatility_filter:
        return True
        
    # Get or create ATR instances
    recent_atr = _indicator_manager.get_or_create_atr(symbol, timeframe, min_length)
    historical_atr = _indicator_manager.get_or_create_atr(symbol, timeframe, max_length)
    
    # Update both ATRs
    recent_val = recent_atr.update(current_high, current_low, current_close)
    historical_val = historical_atr.update(current_high, current_low, current_close)
    
    # Return true if recent volatility is higher
    return recent_val > historical_val