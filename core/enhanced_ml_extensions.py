"""
Enhanced ML Extensions - Filters with stateful indicators
========================================================

Enhanced versions of ML extension functions that use stateful indicators
where appropriate. These maintain state across bars like Pine Script.
"""
import math
from typing import List, Tuple, Optional
from .enhanced_indicators import (
    enhanced_atr, enhanced_ema, enhanced_change,
    get_indicator_manager
)
from .enhanced_indicators import enhanced_dmi  # Using enhanced version
from .na_handling import filter_none_values, safe_divide


def enhanced_regime_filter(ohlc4: float, high: float, low: float,
                          threshold: float, use_regime_filter: bool,
                          symbol: str, timeframe: str) -> bool:
    """
    Enhanced Regime Filter using EXACT Pine Script logic
    
    Args:
        ohlc4: Current OHLC4 value
        high: Current high
        low: Current low
        threshold: Threshold for trend detection
        use_regime_filter: Whether to use the filter
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        True if market is trending (above threshold)
    """
    # Import the fixed implementation V2
    from .regime_filter_fix_v2 import fixed_regime_filter_v2
    return fixed_regime_filter_v2(ohlc4, high, low, threshold, use_regime_filter, symbol, timeframe)


def enhanced_filter_adx(high: float, low: float, close: float,
                       length: int, adx_threshold: int,
                       use_adx_filter: bool, symbol: str, timeframe: str) -> bool:
    """
    Enhanced ADX Filter using stateful ADX calculation
    
    Args:
        high: Current high
        low: Current low
        close: Current close
        length: ADX period
        adx_threshold: Threshold value
        use_adx_filter: Whether to use the filter
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        True if ADX > threshold (trending market)
    """
    if not use_adx_filter:
        return True

    # Get ADX from stateful DMI
    from .enhanced_indicators import enhanced_dmi
    _, _, adx = enhanced_dmi(high, low, close, length, length, symbol, timeframe)

    return adx > adx_threshold


def enhanced_filter_volatility(high: float, low: float, close: float,
                              min_length: int = 1, max_length: int = 10,
                              use_volatility_filter: bool = True,
                              symbol: str = "", timeframe: str = "") -> bool:
    """
    Enhanced Volatility Filter using stateful ATR
    
    Args:
        high: Current high
        low: Current low
        close: Current close
        min_length: Period for recent ATR
        max_length: Period for historical ATR
        use_volatility_filter: Whether to use the filter
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        True if recent ATR > historical ATR
    """
    if not use_volatility_filter:
        return True

    # Calculate recent and historical ATR using stateful indicators
    recent_atr = enhanced_atr(high, low, close, min_length, symbol, f"{timeframe}_vol_recent")
    historical_atr = enhanced_atr(high, low, close, max_length, symbol, f"{timeframe}_vol_hist")

    return recent_atr > historical_atr


def enhanced_backtest(high_values: List[Optional[float]], low_values: List[Optional[float]], 
                     open_values: List[Optional[float]], start_long_trades: List[bool], 
                     end_long_trades: List[bool], start_short_trades: List[bool], 
                     end_short_trades: List[bool], early_signal_flips: List[bool], 
                     max_bars_back_index: int, current_bar_index: int, 
                     src_values: List[Optional[float]], use_worst_case: bool) -> Tuple:
    """
    Enhanced backtest function (same as original for now)
    Returns: (totalWins, totalLosses, totalEarlySignalFlips, totalTrades,
              tradeStatsHeader, winLossRatio, winRate)
    """
    # This implementation remains the same as it doesn't use indicators
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


# Wrapper functions for backward compatibility
def enhanced_regime_filter_batch(ohlc4_values: List[Optional[float]], threshold: float,
                                use_regime_filter: bool, high_values: List[Optional[float]] = None,
                                low_values: List[Optional[float]] = None,
                                symbol: str = "", timeframe: str = "") -> bool:
    """
    Batch version that processes the latest value from arrays
    For compatibility with existing code
    """
    if not use_regime_filter:
        return True
        
    # Clean values
    clean_ohlc4 = filter_none_values(ohlc4_values)
    clean_high = filter_none_values(high_values) if high_values else None
    clean_low = filter_none_values(low_values) if low_values else None
    
    if not clean_ohlc4 or (high_values and not clean_high) or (low_values and not clean_low):
        return True
        
    # Process only the most recent value
    ohlc4 = clean_ohlc4[0]  # Most recent
    high = clean_high[0] if clean_high else ohlc4
    low = clean_low[0] if clean_low else ohlc4
    
    return enhanced_regime_filter(ohlc4, high, low, threshold, use_regime_filter, symbol, timeframe)


def enhanced_filter_adx_batch(high_values: List[Optional[float]], low_values: List[Optional[float]],
                             close_values: List[Optional[float]], length: int, adx_threshold: int,
                             use_adx_filter: bool, symbol: str = "", timeframe: str = "") -> bool:
    """
    Batch version for compatibility
    """
    if not use_adx_filter:
        return True
        
    # Clean values
    clean_high = filter_none_values(high_values)
    clean_low = filter_none_values(low_values)
    clean_close = filter_none_values(close_values)
    
    if not clean_high or not clean_low or not clean_close:
        return True
        
    # Process only the most recent value
    high = clean_high[0]
    low = clean_low[0]
    close = clean_close[0]
    
    return enhanced_filter_adx(high, low, close, length, adx_threshold, use_adx_filter, symbol, timeframe)


def enhanced_filter_volatility_batch(high_values: List[Optional[float]], low_values: List[Optional[float]],
                                   close_values: List[Optional[float]], min_length: int = 1,
                                   max_length: int = 10, use_volatility_filter: bool = True,
                                   symbol: str = "", timeframe: str = "") -> bool:
    """
    Batch version for compatibility
    """
    if not use_volatility_filter:
        return True
        
    # Clean values
    clean_high = filter_none_values(high_values)
    clean_low = filter_none_values(low_values)
    clean_close = filter_none_values(close_values)
    
    if not clean_high or not clean_low or not clean_close:
        return True
        
    # Process only the most recent value
    high = clean_high[0]
    low = clean_low[0]
    close = clean_close[0]
    
    return enhanced_filter_volatility(high, low, close, min_length, max_length, 
                                    use_volatility_filter, symbol, timeframe)
