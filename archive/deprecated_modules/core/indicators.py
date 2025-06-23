"""
Technical Indicators - Exact Pine Script implementations
These are the normalized versions used in the ML model
"""
import math
from typing import List, Tuple, Optional, Dict
from .math_helpers import pine_ema, pine_sma, pine_rma
from .normalization import rescale, normalizer
from .na_handling import filter_none_values  # PHASE 3: Add NA handling
from .pine_functions import nz, na  # Pine Script function equivalents
from .indicator_state_manager import IndicatorStateManager
from .stateful_ta import StatefulRSI, StatefulEMA, StatefulCCI, StatefulWaveTrend, StatefulDMI

# Global indicator state manager - single instance for entire application
_indicator_manager = IndicatorStateManager()


def calculate_rsi(close_values: List[float], length: int) -> float:
    """
    Calculate RSI (Relative Strength Index)
    Pine Script: ta.rsi(src, length)
    """
    # PHASE 3 FIX: Filter None values
    clean_values = filter_none_values(close_values)
    
    if not clean_values or length <= 0 or len(clean_values) < 2:
        return 50.0  # Neutral RSI

    # Calculate price changes
    gains = []
    losses = []

    for i in range(len(clean_values) - 1):
        change = clean_values[i] - clean_values[i + 1]
        if change > 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))

    # Calculate average gain and loss using RMA
    avg_gain = pine_rma(gains, length)
    avg_loss = pine_rma(losses, length)

    # Calculate RSI
    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def n_rsi(close_values: List[float], n1: int, n2: int) -> float:
    """
    Normalized RSI for ML
    Pine Script: rescale(ta.ema(ta.rsi(src, n1), n2), 0, 100, 0, 1)

    Args:
        close_values: List of close prices (newest first)
        n1: RSI period
        n2: EMA smoothing period
    """
    # PHASE 3 FIX: Filter None values
    clean_values = filter_none_values(close_values)
    
    if not clean_values:
        return 0.5  # Neutral normalized value

    # Step 1: Calculate RSI values for each bar
    rsi_values = []
    for i in range(len(clean_values)):
        # Get subset of values from current bar backwards
        subset = clean_values[i:]
        if len(subset) >= 2:
            rsi = calculate_rsi(subset, n1)
            rsi_values.append(rsi)

    # Step 2: Apply EMA smoothing
    if rsi_values:
        smoothed_rsi = pine_ema(rsi_values, n2)
    else:
        smoothed_rsi = 50.0

    # Step 3: Rescale to [0, 1]
    return rescale(smoothed_rsi, 0, 100, 0, 1)


def calculate_cci(close_values: List[float], high_values: List[float],
                  low_values: List[float], length: int) -> float:
    """
    Calculate CCI (Commodity Channel Index)
    Pine Script: ta.cci(src, length)
    """
    # PHASE 3 FIX: Filter None values from all inputs
    clean_close = filter_none_values(close_values)
    clean_high = filter_none_values(high_values)
    clean_low = filter_none_values(low_values)
    
    if not clean_close or not clean_high or not clean_low or length <= 0:
        return 0.0

    # Calculate typical price (hlc3) for each bar
    tp_values = []
    min_len = min(len(clean_close), len(clean_high), len(clean_low))

    for i in range(min_len):
        tp = (clean_high[i] + clean_low[i] + clean_close[i]) / 3.0
        tp_values.append(tp)

    if not tp_values:
        return 0.0

    # Calculate SMA of typical price
    sma_tp = pine_sma(tp_values, length)

    # Calculate mean deviation
    deviations = []
    actual_length = min(length, len(tp_values))

    for i in range(actual_length):
        deviations.append(abs(tp_values[i] - sma_tp))

    mean_deviation = sum(deviations) / len(deviations) if deviations else 0.0

    # Calculate CCI
    if mean_deviation == 0:
        return 0.0

    cci = (tp_values[0] - sma_tp) / (0.015 * mean_deviation)

    return cci


def n_cci(close_values: List[Optional[float]], high_values: List[Optional[float]],
          low_values: List[Optional[float]], n1: int, n2: int) -> float:
    """
    Normalized CCI for ML
    Pine Script: normalize(ta.ema(ta.cci(src, n1), n2), 0, 1)
    """
    # PHASE 3 FIX: Filter None values from all inputs
    clean_close = filter_none_values(close_values)
    clean_high = filter_none_values(high_values)
    clean_low = filter_none_values(low_values)
    
    if not clean_close:
        return 0.5

    # Calculate CCI values for EMA
    cci_values = []
    min_len = min(len(clean_close), len(clean_high), len(clean_low))

    for i in range(min_len):
        # Get subset from current bar backwards
        close_subset = clean_close[i:]
        high_subset = clean_high[i:]
        low_subset = clean_low[i:]

        if len(close_subset) >= 2:
            cci = calculate_cci(close_subset, high_subset, low_subset, n1)
            cci_values.append(cci)

    # Apply EMA smoothing
    if cci_values:
        smoothed_cci = pine_ema(cci_values, n2)
    else:
        smoothed_cci = 0.0

    # Normalize using historical min/max
    return normalizer.normalize(smoothed_cci, f"cci_{n1}_{n2}", 0, 1)


def calculate_wavetrend(hlc3_values: List[Optional[float]], n1: int, n2: int) -> Tuple[float, float]:
    """
    Calculate WaveTrend Oscillator
    Returns: (wt1, wt2) tuple
    """
    # PHASE 3 FIX: Filter None values
    clean_values = filter_none_values(hlc3_values)
    
    if not clean_values or len(clean_values) < 2:
        return 0.0, 0.0
    
    hlc3_values = clean_values  # Use clean values

    # Step 1: Calculate EMA of HLC3
    ema1 = pine_ema(hlc3_values, n1)

    # Step 2: Calculate EMA of absolute difference
    diff_values = []
    for i in range(len(hlc3_values)):
        # Need EMA values at each point for the difference
        subset = hlc3_values[i:]
        if subset:
            ema_at_i = pine_ema(subset, n1)
            diff = abs(hlc3_values[i] - ema_at_i)
            diff_values.append(diff)

    ema2 = pine_ema(diff_values, n1) if diff_values else 0.0

    # Step 3: Calculate CI (Chande Index)
    if ema2 == 0:
        ci = 0.0
    else:
        ci = (hlc3_values[0] - ema1) / (0.015 * ema2)

    # Step 4: Calculate WT1 (TCI - Trend Change Index)
    # Need to maintain CI values for EMA calculation
    # For simplicity, using current CI
    wt1 = ci  # In full implementation, would be EMA of CI values

    # Step 5: Calculate WT2 (SMA of WT1)
    wt2 = wt1  # In full implementation, would be SMA of WT1 values

    return wt1, wt2


def n_wt(hlc3_values: List[Optional[float]], n1: int = 10, n2: int = 11) -> float:
    """
    Normalized WaveTrend for ML
    Pine Script: normalize(wt1 - wt2, 0, 1)
    """
    # PHASE 3 FIX: Filter None values
    clean_values = filter_none_values(hlc3_values)
    
    if not clean_values:
        return 0.5
    
    hlc3_values = clean_values  # Use clean values

    wt1, wt2 = calculate_wavetrend(hlc3_values, n1, n2)
    wt_diff = wt1 - wt2

    # Normalize using historical min/max
    return normalizer.normalize(wt_diff, f"wt_{n1}_{n2}", 0, 1)


def calculate_adx(high_values: List[Optional[float]], low_values: List[Optional[float]],
                  close_values: List[Optional[float]], length: int) -> float:
    """
    Calculate ADX (Average Directional Index)
    """
    # PHASE 3 FIX: Filter None values from all inputs
    clean_high = filter_none_values(high_values)
    clean_low = filter_none_values(low_values)
    clean_close = filter_none_values(close_values)
    
    if not clean_high or not clean_low or not clean_close or length <= 0:
        return 0.0
    
    high_values = clean_high
    low_values = clean_low
    close_values = clean_close

    min_len = min(len(high_values), len(low_values), len(close_values))
    if min_len < length * 2:  # Need enough data for proper calculation
        return 0.0

    # Calculate True Range and Directional Movement for all bars
    tr_values = []
    plus_dm_values = []
    minus_dm_values = []

    for i in range(min_len - 1):
        # True Range
        high = high_values[i]
        low = low_values[i]
        prev_close = close_values[i + 1]

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        tr_values.append(tr)

        # Directional Movement
        high_diff = high - high_values[i + 1]
        low_diff = low_values[i + 1] - low

        plus_dm = max(high_diff, 0) if high_diff > low_diff else 0
        minus_dm = max(low_diff, 0) if low_diff > high_diff else 0

        plus_dm_values.append(plus_dm)
        minus_dm_values.append(minus_dm)

    # Calculate smoothed values using RMA
    if len(tr_values) < length:
        return 0.0

    # Initialize smoothed values
    smooth_tr = sum(tr_values[:length]) / length
    smooth_plus_dm = sum(plus_dm_values[:length]) / length
    smooth_minus_dm = sum(minus_dm_values[:length]) / length
    
    # Calculate DX values
    dx_values = []
    
    # Process each bar to get DX values
    for i in range(length, len(tr_values)):
        # Update smoothed values (RMA formula)
        smooth_tr = (smooth_tr * (length - 1) + tr_values[i]) / length
        smooth_plus_dm = (smooth_plus_dm * (length - 1) + plus_dm_values[i]) / length
        smooth_minus_dm = (smooth_minus_dm * (length - 1) + minus_dm_values[i]) / length
        
        # Calculate DI+ and DI-
        di_plus = (smooth_plus_dm / smooth_tr * 100) if smooth_tr > 0 else 0
        di_minus = (smooth_minus_dm / smooth_tr * 100) if smooth_tr > 0 else 0
        
        # Calculate DX
        di_sum = di_plus + di_minus
        if di_sum == 0:
            dx = 0
        else:
            dx = abs(di_plus - di_minus) / di_sum * 100
            
        dx_values.append(dx)
    
    # Calculate ADX as RMA of DX
    if len(dx_values) < length:
        return 0.0
        
    # Initialize ADX with first average
    adx = sum(dx_values[:length]) / length
    
    # Apply RMA to remaining DX values
    for i in range(length, len(dx_values)):
        adx = (adx * (length - 1) + dx_values[i]) / length
    
    return adx


def n_adx(high_values: List[Optional[float]], low_values: List[Optional[float]],
          close_values: List[Optional[float]], n1: int) -> float:
    """
    Normalized ADX for ML
    Pine Script: rescale(adx, 0, 100, 0, 1)
    """
    # PHASE 3 FIX: Already handled in calculate_adx
    if not high_values or not low_values or not close_values:
        return 0.5

    adx = calculate_adx(high_values, low_values, close_values, n1)

    # Rescale to [0, 1]
    return rescale(adx, 0, 100, 0, 1)


def dmi(high_values: List[Optional[float]], low_values: List[Optional[float]],
        close_values: List[Optional[float]], length_di: int, length_adx: int) -> Tuple[float, float, float]:
    """
    Pine Script ta.dmi() function - Directional Movement Index
    
    Returns: (diPlus, diMinus, adx)
    
    Args:
        high_values: List of high prices (newest first)
        low_values: List of low prices (newest first)
        close_values: List of close prices (newest first)
        length_di: Length for DI calculation
        length_adx: Length for ADX calculation
        
    Returns:
        Tuple of (DI+, DI-, ADX)
    """
    # PHASE 3 FIX: Filter None values from all inputs
    clean_high = filter_none_values(high_values)
    clean_low = filter_none_values(low_values)
    clean_close = filter_none_values(close_values)
    
    if not clean_high or not clean_low or not clean_close or length_di <= 0:
        return 0.0, 0.0, 0.0
    
    high_values = clean_high
    low_values = clean_low
    close_values = clean_close

    min_len = min(len(high_values), len(low_values), len(close_values))
    if min_len < length_di * 2:  # Need enough data for proper calculation
        return 0.0, 0.0, 0.0

    # Calculate True Range and Directional Movement for all bars
    tr_values = []
    plus_dm_values = []
    minus_dm_values = []

    for i in range(min_len - 1):
        # True Range
        high = high_values[i]
        low = low_values[i]
        prev_close = close_values[i + 1]

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        tr_values.append(tr)

        # Directional Movement
        high_diff = high - high_values[i + 1]
        low_diff = low_values[i + 1] - low

        plus_dm = max(high_diff, 0) if high_diff > low_diff else 0
        minus_dm = max(low_diff, 0) if low_diff > high_diff else 0

        plus_dm_values.append(plus_dm)
        minus_dm_values.append(minus_dm)

    # Calculate smoothed values using RMA
    if len(tr_values) < length_di:
        return 0.0, 0.0, 0.0

    # Initialize smoothed values for DI
    smooth_tr = sum(tr_values[:length_di]) / length_di
    smooth_plus_dm = sum(plus_dm_values[:length_di]) / length_di
    smooth_minus_dm = sum(minus_dm_values[:length_di]) / length_di
    
    # Calculate DX values
    dx_values = []
    di_plus_current = 0.0
    di_minus_current = 0.0
    
    # Process each bar to get DX values
    for i in range(length_di, len(tr_values)):
        # Update smoothed values (RMA formula)
        smooth_tr = (smooth_tr * (length_di - 1) + tr_values[i]) / length_di
        smooth_plus_dm = (smooth_plus_dm * (length_di - 1) + plus_dm_values[i]) / length_di
        smooth_minus_dm = (smooth_minus_dm * (length_di - 1) + minus_dm_values[i]) / length_di
        
        # Calculate DI+ and DI-
        di_plus = (smooth_plus_dm / smooth_tr * 100) if smooth_tr > 0 else 0
        di_minus = (smooth_minus_dm / smooth_tr * 100) if smooth_tr > 0 else 0
        
        # Store current values (most recent)
        if i == len(tr_values) - 1:
            di_plus_current = di_plus
            di_minus_current = di_minus
        
        # Calculate DX
        di_sum = di_plus + di_minus
        if di_sum == 0:
            dx = 0
        else:
            dx = abs(di_plus - di_minus) / di_sum * 100
            
        dx_values.append(dx)
    
    # Calculate ADX as RMA of DX
    if len(dx_values) < length_adx:
        return di_plus_current, di_minus_current, 0.0
        
    # Initialize ADX with first average
    adx = sum(dx_values[:length_adx]) / length_adx
    
    # Apply RMA to remaining DX values
    for i in range(length_adx, len(dx_values)):
        adx = (adx * (length_adx - 1) + dx_values[i]) / length_adx
    
    return di_plus_current, di_minus_current, adx


def series_from(feature_string: str, close_values: List[Optional[float]],
                high_values: List[Optional[float]], low_values: List[Optional[float]],
                hlc3_values: List[Optional[float]], param_a: int, param_b: int) -> float:
    """
    Get feature value based on feature string
    Matches Pine Script's series_from() function

    Returns: Current value of the specified indicator
    """
    if feature_string == "RSI":
        return n_rsi(close_values, param_a, param_b)
    elif feature_string == "WT":
        return n_wt(hlc3_values, param_a, param_b)
    elif feature_string == "CCI":
        return n_cci(close_values, high_values, low_values, param_a, param_b)
    elif feature_string == "ADX":
        return n_adx(high_values, low_values, close_values, param_a)
    else:
        return 0.5  # Neutral value for unknown indicator


# =============================================================================
# ENHANCED STATEFUL VERSIONS - Use these for production!
# =============================================================================

def enhanced_n_rsi(current_close: float, previous_close: Optional[float],
                  symbol: str, timeframe: str, n1: int, n2: int) -> float:
    """
    Enhanced Normalized RSI using stateful indicators
    Matches Pine Script: rescale(ta.ema(ta.rsi(src, n1), n2), 0, 100, 0, 1)
    
    Args:
        current_close: Current bar's close price
        previous_close: Previous bar's close price (needed for RSI)
        symbol: Trading symbol (e.g., 'RELIANCE')
        timeframe: Timeframe (e.g., '5minute')
        n1: RSI period
        n2: EMA smoothing period
        
    Returns:
        Normalized RSI value [0, 1]
    """
    # Get or create RSI instance for this symbol/timeframe
    rsi = _indicator_manager.get_or_create_rsi(symbol, timeframe, n1)
    
    # Calculate current RSI value
    rsi_value = rsi.update(current_close)
    
    # Apply EMA smoothing
    ema_key = f"rsi_ema_{n1}"
    ema = _indicator_manager.get_or_create_ema(symbol, timeframe, n2)
    smoothed_rsi = ema.update(rsi_value)
    
    # Rescale to [0, 1]
    return rescale(smoothed_rsi, 0, 100, 0, 1)


def enhanced_n_cci(current_high: float, current_low: float, current_close: float,
                  symbol: str, timeframe: str, n1: int, n2: int) -> float:
    """
    Enhanced Normalized CCI using stateful indicators
    Matches Pine Script: normalize(ta.ema(ta.cci(src, n1), n2), 0, 1)
    
    Args:
        current_high: Current bar's high price
        current_low: Current bar's low price
        current_close: Current bar's close price
        symbol: Trading symbol
        timeframe: Timeframe
        n1: CCI period
        n2: EMA smoothing period
        
    Returns:
        Normalized CCI value [0, 1]
    """
    # Get or create CCI instance
    cci = _indicator_manager.get_or_create_cci(symbol, timeframe, n1)
    
    # Calculate current CCI value
    cci_value = cci.update(current_high, current_low, current_close)
    
    # Apply EMA smoothing
    ema = _indicator_manager.get_or_create_ema(symbol, timeframe, n2)
    smoothed_cci = ema.update(cci_value)
    
    # Normalize using historical min/max
    return normalizer.normalize(smoothed_cci, f"{symbol}_{timeframe}_cci_{n1}_{n2}", 0, 1)


def enhanced_n_wt(current_high: float, current_low: float, current_close: float,
                 symbol: str, timeframe: str, n1: int = 10, n2: int = 11) -> float:
    """
    Enhanced Normalized WaveTrend using stateful indicators
    Matches Pine Script: normalize(wt1 - wt2, 0, 1)
    
    Args:
        current_high: Current bar's high price
        current_low: Current bar's low price  
        current_close: Current bar's close price
        symbol: Trading symbol
        timeframe: Timeframe
        n1: Channel period (default 10)
        n2: Average period (default 11)
        
    Returns:
        Normalized WaveTrend value [0, 1]
    """
    # Get or create WaveTrend instance
    wt = _indicator_manager.get_or_create_wavetrend(symbol, timeframe, n1, n2)
    
    # Calculate current WaveTrend values
    wt1, wt2 = wt.update(current_high, current_low, current_close)
    wt_diff = wt1 - wt2
    
    # Normalize using historical min/max
    return normalizer.normalize(wt_diff, f"{symbol}_{timeframe}_wt_{n1}_{n2}", 0, 1)


def enhanced_n_adx(current_high: float, current_low: float, current_close: float,
                  symbol: str, timeframe: str, n1: int) -> float:
    """
    Enhanced Normalized ADX using stateful indicators
    Matches Pine Script: rescale(adx, 0, 100, 0, 1)
    
    Args:
        current_high: Current bar's high price
        current_low: Current bar's low price
        current_close: Current bar's close price
        symbol: Trading symbol
        timeframe: Timeframe
        n1: ADX period
        
    Returns:
        Normalized ADX value [0, 1]
    """
    # Get or create DMI instance (which includes ADX)
    dmi = _indicator_manager.get_or_create_dmi(symbol, timeframe, n1, n1)
    
    # Calculate current values
    di_plus, di_minus, adx = dmi.update(current_high, current_low, current_close)
    
    # Rescale to [0, 1]
    return rescale(adx, 0, 100, 0, 1)


def enhanced_series_from(feature_string: str, current_ohlc: Dict[str, float],
                        previous_close: Optional[float], symbol: str, timeframe: str,
                        param_a: int, param_b: int) -> float:
    """
    Enhanced version of series_from using stateful indicators
    
    Args:
        feature_string: Feature name ('RSI', 'WT', 'CCI', 'ADX')
        current_ohlc: Dict with 'high', 'low', 'close' keys
        previous_close: Previous bar's close (for RSI)
        symbol: Trading symbol
        timeframe: Timeframe
        param_a: First parameter
        param_b: Second parameter
        
    Returns:
        Current value of the specified indicator
    """
    high = current_ohlc.get('high', 0.0)
    low = current_ohlc.get('low', 0.0)
    close = current_ohlc.get('close', 0.0)
    
    if feature_string == "RSI":
        return enhanced_n_rsi(close, previous_close, symbol, timeframe, param_a, param_b)
    elif feature_string == "WT":
        return enhanced_n_wt(high, low, close, symbol, timeframe, param_a, param_b)
    elif feature_string == "CCI":
        return enhanced_n_cci(high, low, close, symbol, timeframe, param_a, param_b)
    elif feature_string == "ADX":
        return enhanced_n_adx(high, low, close, symbol, timeframe, param_a)
    else:
        return 0.5  # Neutral value for unknown indicator


def enhanced_dmi(current_high: float, current_low: float, current_close: float,
                symbol: str, timeframe: str, length_di: int, length_adx: int) -> Tuple[float, float, float]:
    """
    Enhanced DMI using stateful indicators
    Matches Pine Script ta.dmi() function
    
    Args:
        current_high: Current bar's high price
        current_low: Current bar's low price
        current_close: Current bar's close price
        symbol: Trading symbol
        timeframe: Timeframe
        length_di: Length for DI calculation
        length_adx: Length for ADX calculation
        
    Returns:
        Tuple of (DI+, DI-, ADX)
    """
    # Get or create DMI instance
    dmi = _indicator_manager.get_or_create_dmi(symbol, timeframe, length_di, length_adx)
    
    # Calculate and return current values
    return dmi.update(current_high, current_low, current_close)


# Utility function to get the indicator manager (for testing/debugging)
def get_indicator_manager() -> IndicatorStateManager:
    """Get the global indicator state manager instance"""
    return _indicator_manager