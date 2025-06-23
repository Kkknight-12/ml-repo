"""
NA/None Handling Fixes - Phase 3
Adds robust validation and error handling for missing data
"""
from typing import List, Optional, Tuple
import math


def validate_ohlcv(open_price: Optional[float], high: Optional[float], 
                   low: Optional[float], close: Optional[float], 
                   volume: Optional[float]) -> Tuple[bool, str]:
    """
    Validate OHLCV data for None and NaN values
    
    Returns:
        (is_valid, error_message)
    """
    # Check for None values in critical fields
    if any(v is None for v in [open_price, high, low, close]):
        return False, "Missing price data (None values)"
    
    # Check for NaN values
    if any(math.isnan(v) for v in [open_price, high, low, close]):
        return False, "Invalid price data (NaN values)"
    
    # Check for infinity
    if any(math.isinf(v) for v in [open_price, high, low, close]):
        return False, "Invalid price data (Infinity)"
    
    # Check for negative prices
    if any(v < 0 for v in [open_price, high, low, close]):
        return False, "Negative price values"
    
    # Check logical consistency
    if high < low:
        return False, "High is less than low"
    
    if high < max(open_price, close) or low > min(open_price, close):
        return False, "High/Low outside of Open/Close range"
    
    # Volume can be None or 0
    if volume is not None and (math.isnan(volume) or volume < 0):
        return False, "Invalid volume"
    
    return True, ""


def filter_none_values(values: List[Optional[float]]) -> List[float]:
    """
    Filter out None and NaN values from a list
    
    Args:
        values: List that may contain None or NaN
        
    Returns:
        Filtered list with only valid float values
    """
    if not values:
        return []
    
    filtered = []
    for v in values:
        if v is not None and not math.isnan(v) and not math.isinf(v):
            filtered.append(v)
    
    return filtered


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safe division that handles zero denominator and None values
    """
    if denominator == 0 or denominator is None:
        return default
    
    if numerator is None:
        return default
        
    try:
        result = numerator / denominator
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except:
        return default


def safe_log(value: float, default: float = 0.0) -> float:
    """
    Safe logarithm that handles negative, zero, and None values
    """
    if value is None or value <= 0:
        return default
        
    try:
        result = math.log(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except:
        return default


def safe_sqrt(value: float, default: float = 0.0) -> float:
    """
    Safe square root that handles negative and None values
    """
    if value is None or value < 0:
        return default
        
    try:
        result = math.sqrt(value)
        if math.isnan(result):
            return default
        return result
    except:
        return default


def interpolate_missing_values(values: List[Optional[float]]) -> List[float]:
    """
    Interpolate missing values in a time series
    Uses linear interpolation for None values
    """
    if not values:
        return []
    
    result = []
    last_valid = None
    last_valid_idx = -1
    
    # First pass: identify valid values
    valid_indices = []
    for i, v in enumerate(values):
        if v is not None and not math.isnan(v):
            valid_indices.append(i)
    
    if not valid_indices:
        # No valid values, return zeros
        return [0.0] * len(values)
    
    # Second pass: interpolate
    for i, v in enumerate(values):
        if v is not None and not math.isnan(v):
            result.append(v)
            last_valid = v
            last_valid_idx = i
        else:
            # Find next valid value
            next_valid = None
            next_valid_idx = len(values)
            
            for j in range(i + 1, len(values)):
                if values[j] is not None and not math.isnan(values[j]):
                    next_valid = values[j]
                    next_valid_idx = j
                    break
            
            # Interpolate
            if last_valid is not None and next_valid is not None:
                # Linear interpolation
                progress = (i - last_valid_idx) / (next_valid_idx - last_valid_idx)
                interpolated = last_valid + progress * (next_valid - last_valid)
                result.append(interpolated)
            elif last_valid is not None:
                # Use last valid value
                result.append(last_valid)
            elif next_valid is not None:
                # Use next valid value
                result.append(next_valid)
            else:
                # No valid values, use 0
                result.append(0.0)
    
    return result


# Wrapper functions for safe calculations
def safe_max(*values) -> float:
    """Safe max that filters None values"""
    filtered = [v for v in values if v is not None and not math.isnan(v)]
    return max(filtered) if filtered else 0.0


def safe_min(*values) -> float:
    """Safe min that filters None values"""
    filtered = [v for v in values if v is not None and not math.isnan(v)]
    return min(filtered) if filtered else 0.0


def safe_abs(value: Optional[float]) -> float:
    """Safe absolute value"""
    if value is None:
        return 0.0
    
    try:
        result = abs(value)
        if math.isnan(result):
            return 0.0
        return result
    except:
        return 0.0


def validate_list_data(values: List[Optional[float]], min_length: int = 1) -> Tuple[bool, str]:
    """
    Validate a list of values for calculations
    
    Returns:
        (is_valid, error_message)
    """
    if not values:
        return False, "Empty list"
    
    # Filter valid values
    valid_values = filter_none_values(values)
    
    if len(valid_values) < min_length:
        return False, f"Insufficient valid data (need {min_length}, have {len(valid_values)})"
    
    return True, ""


# Example usage in indicators
def safe_calculate_rsi(close_values: List[Optional[float]], length: int) -> float:
    """
    RSI calculation with None handling
    """
    # Filter None values
    clean_values = filter_none_values(close_values)
    
    if len(clean_values) < 2:
        return 50.0  # Neutral RSI
    
    # Rest of RSI calculation...
    # (existing logic but with clean_values)
    
    return 50.0  # Placeholder