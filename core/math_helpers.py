"""
Mathematical helper functions - Exact Pine Script conversions
No numpy yet - keeping it simple with pure Python
"""
import math
from typing import List, Optional
from .na_handling import filter_none_values, safe_divide, safe_sqrt  # PHASE 3: Add NA handling


def tanh(src: Optional[float]) -> float:
    """
    Hyperbolic tangent - compresses input to [-1, 1]
    Pine Script: tanh = -1 + 2/(1 + math.exp(-2*src))
    """
    # PHASE 3 FIX: Handle None/NaN values
    if src is None or math.isnan(src):
        return 0.0
    
    try:
        return -1 + 2 / (1 + math.exp(-2 * src))
    except:
        return 0.0


def normalize_deriv(values: List[Optional[float]], quadratic_mean_length: int) -> float:
    """
    Normalizes derivative using RMS (Root Mean Square)
    Used in tanh transform calculations

    Pine Script equivalent:
    deriv = src - src[2]
    quadraticMean = math.sqrt(nz(math.sum(math.pow(deriv, 2), quadraticMeanLength) / quadraticMeanLength))
    nDeriv = deriv / quadraticMean
    """
    # PHASE 3 FIX: Filter None values
    clean_values = filter_none_values(values)
    
    if len(clean_values) < 3:
        return 0.0
    
    values = clean_values  # Use clean values from here

    # Calculate derivative (current - 2 bars ago)
    deriv = values[0] - values[2] if len(values) > 2 else 0.0

    # Calculate quadratic mean (RMS) over the specified length
    sum_squared = 0.0
    count = 0

    for i in range(min(quadratic_mean_length, len(values) - 2)):
        if i + 2 < len(values):
            d = values[i] - values[i + 2]
            sum_squared += d * d
            count += 1

    quadratic_mean = math.sqrt(sum_squared / count) if count > 0 else 1.0

    # Avoid division by zero
    if quadratic_mean == 0:
        quadratic_mean = 1.0

    return deriv / quadratic_mean


def dual_pole_filter(values: List[Optional[float]], lookback: int) -> float:
    """
    Smoothing filter implementation
    Pine Script's complex smoothing algorithm
    """
    # PHASE 3 FIX: Filter None values
    clean_values = filter_none_values(values)
    
    if not clean_values or lookback <= 0:
        return 0.0
    
    values = clean_values  # Use clean values from here

    omega = -99 * math.pi / (70 * lookback)
    alpha = math.exp(omega)
    beta = -alpha * alpha
    gamma = math.cos(omega) * 2 * alpha
    delta = 1 - gamma - beta

    # Initialize filter values
    filter_values = []

    for i in range(len(values)):
        src = values[i]

        # Sliding average: 0.5 * (src + nz(src[1], src))
        prev_src = values[i + 1] if i + 1 < len(values) else src
        sliding_avg = 0.5 * (src + prev_src)

        if i == 0:
            # First value
            filter_val = delta * sliding_avg
        elif i == 1:
            # Second value
            filter_val = delta * sliding_avg + gamma * filter_values[0]
        else:
            # Subsequent values
            filter_val = delta * sliding_avg + gamma * filter_values[-1] + beta * filter_values[-2]

        filter_values.append(filter_val)

    return filter_values[-1] if filter_values else 0.0


def pine_ema(values: List[Optional[float]], length: int) -> float:
    """
    Exponential Moving Average - Pine Script style
    Returns the current EMA value
    """
    # PHASE 3 FIX: Filter None values
    clean_values = filter_none_values(values)
    
    if not clean_values or length <= 0:
        return 0.0
    
    values = clean_values  # Use clean values from here

    alpha = 2.0 / (length + 1)

    # Start with SMA for initial value
    if len(values) >= length:
        ema = sum(values[-length:]) / length

        # Apply EMA formula from oldest to newest
        for i in range(len(values) - length, -1, -1):
            ema = alpha * values[i] + (1 - alpha) * ema
    else:
        # Not enough data, use simple average
        ema = sum(values) / len(values)

    return ema


def pine_sma(values: List[Optional[float]], length: int) -> float:
    """
    Simple Moving Average - Pine Script style
    Returns the current SMA value
    """
    # PHASE 3 FIX: Filter None values
    clean_values = filter_none_values(values)
    
    if not clean_values or length <= 0:
        return 0.0
    
    values = clean_values  # Use clean values from here

    # Use available values if less than length
    actual_length = min(length, len(values))
    if actual_length == 0:
        return 0.0

    return sum(values[:actual_length]) / actual_length


def pine_rma(values: List[Optional[float]], length: int) -> float:
    """
    Relative Moving Average (Running Moving Average) - Pine Script style
    Also known as Wilder's Smoothing
    """
    # PHASE 3 FIX: Filter None values
    clean_values = filter_none_values(values)
    
    if not clean_values or length <= 0:
        return 0.0
    
    values = clean_values  # Use clean values from here

    alpha = 1.0 / length

    # Initialize with SMA
    if len(values) >= length:
        rma = sum(values[-length:]) / length

        # Apply RMA formula from oldest to newest
        for i in range(len(values) - length, -1, -1):
            rma = alpha * values[i] + (1 - alpha) * rma
    else:
        # Not enough data, use simple average
        rma = sum(values) / len(values)

    return rma


def pine_stdev(values: List[Optional[float]], length: int) -> float:
    """
    Standard Deviation - Pine Script style
    """
    # PHASE 3 FIX: Filter None values
    clean_values = filter_none_values(values)
    
    if not clean_values or length <= 0:
        return 0.0
    
    values = clean_values  # Use clean values from here

    actual_length = min(length, len(values))
    if actual_length < 2:
        return 0.0

    subset = values[:actual_length]
    mean = sum(subset) / actual_length

    variance = sum((x - mean) ** 2 for x in subset) / actual_length
    return math.sqrt(variance)


def pine_atr(high_values: List[Optional[float]], low_values: List[Optional[float]],
             close_values: List[Optional[float]], length: int) -> float:
    """
    Average True Range - Pine Script style
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

    # Calculate True Range values
    tr_values = []

    for i in range(len(high_values)):
        if i < len(low_values) and i < len(close_values):
            high = high_values[i]
            low = low_values[i]

            # Previous close (if available)
            prev_close = close_values[i + 1] if i + 1 < len(close_values) else close_values[i]

            # True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
            # PHASE 3 FIX: Use safe operations
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            ) if high > 0 and low > 0 else 0.0
            tr_values.append(tr)

    # Apply RMA to TR values
    return pine_rma(tr_values, length)
