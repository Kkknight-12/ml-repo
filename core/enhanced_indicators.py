"""
Enhanced Stateful Indicators
===========================

These are the enhanced versions of technical indicators that maintain state
like Pine Script's ta.* functions. They update incrementally instead of
recalculating from full history.

CRITICAL: Always use these instead of the old functions for accurate results!
"""
from typing import Optional, Tuple
from .indicator_state_manager import IndicatorStateManager
from .normalization import rescale
from .stateful_ta import StatefulEMA


# Global indicator manager - shared across all indicators
_indicator_manager = IndicatorStateManager()


def get_indicator_manager() -> IndicatorStateManager:
    """Get the global indicator state manager"""
    return _indicator_manager


def enhanced_ema(value: float, period: int, symbol: str, timeframe: str) -> float:
    """
    Enhanced Exponential Moving Average with state management
    
    Args:
        value: Current value to process
        period: EMA period
        symbol: Trading symbol (e.g., 'RELIANCE')
        timeframe: Timeframe (e.g., '5min', 'daily')
        
    Returns:
        Current EMA value
    """
    ema = _indicator_manager.get_or_create_ema(symbol, timeframe, period)
    return ema.update(value)


def enhanced_sma(value: float, period: int, symbol: str, timeframe: str) -> float:
    """
    Enhanced Simple Moving Average with state management
    
    Args:
        value: Current value to process
        period: SMA period
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Current SMA value
    """
    sma = _indicator_manager.get_or_create_sma(symbol, timeframe, period)
    return sma.update(value)


def enhanced_rma(value: float, period: int, symbol: str, timeframe: str) -> float:
    """
    Enhanced Relative Moving Average (Wilder's) with state management
    
    Args:
        value: Current value to process
        period: RMA period
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Current RMA value
    """
    rma = _indicator_manager.get_or_create_rma(symbol, timeframe, period)
    return rma.update(value)


def enhanced_rsi(close: float, period: int, symbol: str, timeframe: str) -> float:
    """
    Enhanced RSI with state management
    
    Args:
        close: Current close price
        period: RSI period
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Current RSI value (0-100)
    """
    rsi = _indicator_manager.get_or_create_rsi(symbol, timeframe, period)
    return rsi.update(close)


def enhanced_n_rsi(close: float, n1: int, n2: int, symbol: str, timeframe: str) -> float:
    """
    Enhanced Normalized RSI for ML (maintains state)
    Pine Script: rescale(ta.ema(ta.rsi(src, n1), n2), 0, 100, 0, 1)
    
    Args:
        close: Current close price
        n1: RSI period
        n2: EMA smoothing period
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Normalized RSI value (0-1)
    """
    # Step 1: Get stateful RSI
    rsi_value = enhanced_rsi(close, n1, symbol, timeframe)
    
    # Step 2: Apply EMA smoothing to RSI
    smoothed_rsi = enhanced_ema(rsi_value, n2, symbol, f"{timeframe}_rsi_{n1}")
    
    # Step 3: Rescale to [0, 1]
    return rescale(smoothed_rsi, 0, 100, 0, 1)


def enhanced_atr(high: float, low: float, close: float, period: int, 
                symbol: str, timeframe: str) -> float:
    """
    Enhanced Average True Range with state management
    
    Args:
        high: Current high price
        low: Current low price
        close: Current close price
        period: ATR period
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Current ATR value
    """
    atr = _indicator_manager.get_or_create_atr(symbol, timeframe, period)
    return atr.update(high, low, close)


def enhanced_cci(high: float, low: float, close: float, period: int,
                symbol: str, timeframe: str) -> float:
    """
    Enhanced Commodity Channel Index with state management
    
    Args:
        high: Current high price
        low: Current low price
        close: Current close price
        period: CCI period
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Current CCI value
    """
    cci = _indicator_manager.get_or_create_cci(symbol, timeframe, period)
    return cci.update(high, low, close)


def enhanced_n_cci(high: float, low: float, close: float, n1: int, n2: int,
                  symbol: str, timeframe: str) -> float:
    """
    Enhanced Normalized CCI for ML (maintains state)
    Pine Script: normalize(ta.ema(ta.cci(src, n1), n2), 0, 1)
    
    Args:
        high: Current high price
        low: Current low price
        close: Current close price
        n1: CCI period
        n2: EMA smoothing period
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Normalized CCI value (0-1)
    """
    # Step 1: Get stateful CCI
    cci_value = enhanced_cci(high, low, close, n1, symbol, timeframe)
    
    # Step 2: Apply EMA smoothing to CCI
    smoothed_cci = enhanced_ema(cci_value, n2, symbol, f"{timeframe}_cci_{n1}")
    
    # Step 3: Normalize using dynamic range (like Pine Script)
    # For now, using a typical CCI range of -200 to +200
    # In production, this should use the normalizer with historical tracking
    normalized = (smoothed_cci + 200) / 400  # Maps [-200, 200] to [0, 1]
    return max(0, min(1, normalized))  # Clamp to [0, 1]


def enhanced_wavetrend(high: float, low: float, close: float, n1: int, n2: int,
                      symbol: str, timeframe: str) -> Tuple[float, float]:
    """
    Enhanced WaveTrend Oscillator with state management
    
    Args:
        high: Current high price
        low: Current low price
        close: Current close price
        n1: First period parameter
        n2: Second period parameter
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Tuple of (wt1, wt2)
    """
    wt = _indicator_manager.get_or_create_wavetrend(symbol, timeframe, n1, n2)
    return wt.update(high, low, close)


def enhanced_n_wt(high: float, low: float, close: float, n1: int, n2: int,
                 symbol: str, timeframe: str) -> float:
    """
    Enhanced Normalized WaveTrend for ML (maintains state)
    Pine Script: normalize(wt1 - wt2, 0, 1)
    
    Args:
        high: Current high price
        low: Current low price
        close: Current close price
        n1: First period parameter
        n2: Second period parameter
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Normalized WT value (0-1)
    """
    # Get stateful WaveTrend values
    wt1, wt2 = enhanced_wavetrend(high, low, close, n1, n2, symbol, timeframe)
    wt_diff = wt1 - wt2
    
    # Normalize using typical WT range of -100 to +100
    # In production, this should use the normalizer with historical tracking
    normalized = (wt_diff + 100) / 200  # Maps [-100, 100] to [0, 1]
    return max(0, min(1, normalized))  # Clamp to [0, 1]


def enhanced_dmi(high: float, low: float, close: float, di_length: int, adx_length: int,
                symbol: str, timeframe: str) -> Tuple[float, float, float]:
    """
    Enhanced Directional Movement Index with state management
    
    Args:
        high: Current high price
        low: Current low price
        close: Current close price
        di_length: DI calculation period
        adx_length: ADX calculation period
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Tuple of (DI+, DI-, ADX)
    """
    dmi = _indicator_manager.get_or_create_dmi(symbol, timeframe, di_length, adx_length)
    return dmi.update(high, low, close)


def enhanced_n_adx(high: float, low: float, close: float, period: int,
                  symbol: str, timeframe: str) -> float:
    """
    Enhanced Normalized ADX for ML (maintains state)
    Pine Script: rescale(adx, 0, 100, 0, 1)
    
    Args:
        high: Current high price
        low: Current low price
        close: Current close price
        period: ADX period
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Normalized ADX value (0-1)
    """
    # Get ADX from DMI calculation
    _, _, adx = enhanced_dmi(high, low, close, period, period, symbol, timeframe)
    
    # Rescale to [0, 1]
    return rescale(adx, 0, 100, 0, 1)


def enhanced_stdev(value: float, period: int, symbol: str, timeframe: str) -> float:
    """
    Enhanced Standard Deviation with state management
    
    Args:
        value: Current value to process
        period: Standard deviation period
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Current standard deviation
    """
    stdev = _indicator_manager.get_or_create_stdev(symbol, timeframe, period)
    return stdev.update(value)


def enhanced_change(value: float, symbol: str, timeframe: str, series_name: str = "default") -> float:
    """
    Enhanced price change tracker with state management
    
    Args:
        value: Current value
        symbol: Trading symbol
        timeframe: Timeframe
        series_name: Name for the series being tracked
        
    Returns:
        Change from previous value
    """
    change = _indicator_manager.get_or_create_change(symbol, timeframe, series_name)
    return change.update(value)


def enhanced_crossover(series1: float, series2: float, symbol: str, timeframe: str,
                      series1_name: str = "s1", series2_name: str = "s2") -> bool:
    """
    Enhanced crossover detection with state management
    
    Args:
        series1: First series current value
        series2: Second series current value
        symbol: Trading symbol
        timeframe: Timeframe
        series1_name: Name of first series
        series2_name: Name of second series
        
    Returns:
        True if series1 crossed over series2
    """
    crossover = _indicator_manager.get_or_create_crossover(symbol, timeframe, series1_name, series2_name)
    return crossover.update(series1, series2)


def enhanced_crossunder(series1: float, series2: float, symbol: str, timeframe: str,
                       series1_name: str = "s1", series2_name: str = "s2") -> bool:
    """
    Enhanced crossunder detection with state management
    
    Args:
        series1: First series current value
        series2: Second series current value
        symbol: Trading symbol
        timeframe: Timeframe
        series1_name: Name of first series
        series2_name: Name of second series
        
    Returns:
        True if series1 crossed under series2
    """
    crossunder = _indicator_manager.get_or_create_crossunder(symbol, timeframe, series1_name, series2_name)
    return crossunder.update(series1, series2)


def enhanced_barssince(condition: bool, symbol: str, timeframe: str,
                      condition_name: str = "default") -> int:
    """
    Enhanced bars since condition tracker with state management
    
    Args:
        condition: Current condition state
        symbol: Trading symbol
        timeframe: Timeframe
        condition_name: Name of the condition being tracked
        
    Returns:
        Number of bars since condition was true
    """
    barssince = _indicator_manager.get_or_create_barssince(symbol, timeframe, condition_name)
    return barssince.update(condition)


def enhanced_series_from(feature_string: str, close: float, high: float, low: float,
                        param_a: int, param_b: int, symbol: str, timeframe: str) -> float:
    """
    Enhanced version of series_from that uses stateful indicators
    
    Args:
        feature_string: Indicator type ("RSI", "WT", "CCI", "ADX")
        close: Current close price
        high: Current high price
        low: Current low price
        param_a: First parameter
        param_b: Second parameter (unused for ADX)
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Current value of the specified indicator
    """
    if feature_string == "RSI":
        return enhanced_n_rsi(close, param_a, param_b, symbol, timeframe)
    elif feature_string == "WT":
        return enhanced_n_wt(high, low, close, param_a, param_b, symbol, timeframe)
    elif feature_string == "CCI":
        return enhanced_n_cci(high, low, close, param_a, param_b, symbol, timeframe)
    elif feature_string == "ADX":
        return enhanced_n_adx(high, low, close, param_a, symbol, timeframe)
    else:
        return 0.5  # Neutral value for unknown indicator


# Manager utility functions
def reset_symbol_indicators(symbol: str):
    """Reset all indicators for a specific symbol"""
    _indicator_manager.reset_symbol(symbol)


def reset_all_indicators():
    """Reset all indicators for all symbols"""
    _indicator_manager.reset_all()


def clear_symbol_indicators(symbol: str):
    """Clear all indicators for a specific symbol (free memory)"""
    _indicator_manager.clear_symbol(symbol)


def clear_all_indicators():
    """Clear all indicators (free all memory)"""
    _indicator_manager.clear_all()


def get_indicator_stats() -> dict:
    """Get statistics about managed indicators"""
    return _indicator_manager.get_stats()
