"""
Pine Script Function Equivalents
Essential Pine Script functions for Python conversion
"""
import math
from typing import Union, Optional, List
import numpy as np


def nz(value: Union[float, int, None, np.ndarray, List], replacement: Union[float, int] = 0) -> Union[float, int, np.ndarray, List]:
    """
    Pine Script nz() function - replaces NaN/None with a default value
    
    Pine Script: nz(x, y) returns x if it's a valid number, otherwise y
    
    Args:
        value: The value to check
        replacement: The replacement value if input is NaN/None (default: 0)
    
    Returns:
        Original value if valid, otherwise replacement
    """
    # Handle None
    if value is None:
        return replacement
    
    # Handle single float/int
    if isinstance(value, (float, int)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return replacement
        return value
    
    # Handle numpy arrays
    if isinstance(value, np.ndarray):
        result = np.where(np.isnan(value) | np.isinf(value), replacement, value)
        return result
    
    # Handle lists
    if isinstance(value, list):
        result = []
        for v in value:
            if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
                result.append(replacement)
            else:
                result.append(v)
        return result
    
    # For any other type, return as is
    return value


def na(value: Union[float, int, None]) -> bool:
    """
    Pine Script na() function - checks if value is NaN/None
    
    Args:
        value: The value to check
        
    Returns:
        True if value is NaN/None, False otherwise
    """
    if value is None:
        return True
    
    if isinstance(value, float):
        return math.isnan(value) or math.isinf(value)
    
    return False


def iff(condition: bool, true_value: any, false_value: any) -> any:
    """
    Pine Script iff() function - ternary operator
    
    Pine Script: iff(condition, valueIfTrue, valueIfFalse)
    
    Args:
        condition: Boolean condition
        true_value: Value to return if condition is True
        false_value: Value to return if condition is False
        
    Returns:
        true_value if condition is True, otherwise false_value
    """
    return true_value if condition else false_value


def change(series: List[Union[float, int, None]], lookback: int = 1) -> Optional[float]:
    """
    Pine Script change() function - calculates the difference between current and previous value
    
    Pine Script: change(source) returns source - source[1]
    
    Args:
        series: List of values (newest first)
        lookback: How many bars to look back (default: 1)
        
    Returns:
        The change value, or None if not enough data
    """
    if len(series) <= lookback:
        return None
        
    current = series[0]
    previous = series[lookback]
    
    # Handle None/NaN
    if na(current) or na(previous):
        return None
        
    return current - previous


def valuewhen(condition_series: List[bool], value_series: List[Union[float, int]], occurrence: int = 0) -> Optional[Union[float, int]]:
    """
    Pine Script valuewhen() function - returns value when condition was true
    
    Args:
        condition_series: List of boolean conditions (newest first)
        value_series: List of values (newest first)
        occurrence: Which occurrence to return (0 = most recent)
        
    Returns:
        Value at the nth occurrence where condition was true
    """
    if len(condition_series) != len(value_series):
        return None
    
    occurrences_found = 0
    for i in range(len(condition_series)):
        if condition_series[i]:
            if occurrences_found == occurrence:
                return value_series[i]
            occurrences_found += 1
    
    return None


def crossover_value(series1_current: Union[float, int], series1_previous: Union[float, int],
                    series2_current: Union[float, int], series2_previous: Union[float, int]) -> bool:
    """
    Pine Script ta.crossover() for single values - detects when series1 crosses above series2
    
    Pine Script logic:
    - Current bar: series1 > series2
    - Previous bar: series1 <= series2
    
    Args:
        series1_current: Current value of series1 (e.g., fast MA)
        series1_previous: Previous value of series1
        series2_current: Current value of series2 (e.g., slow MA)
        series2_previous: Previous value of series2
        
    Returns:
        True if series1 crossed above series2, False otherwise
    """
    # Handle None/NaN values
    if any(na(v) for v in [series1_current, series1_previous, series2_current, series2_previous]):
        return False
    
    # Pine Script crossover logic
    # Previous: series1 <= series2
    # Current: series1 > series2
    return (series1_previous <= series2_previous) and (series1_current > series2_current)


def crossunder_value(series1_current: Union[float, int], series1_previous: Union[float, int],
                     series2_current: Union[float, int], series2_previous: Union[float, int]) -> bool:
    """
    Pine Script ta.crossunder() for single values - detects when series1 crosses below series2
    
    Pine Script logic:
    - Current bar: series1 < series2
    - Previous bar: series1 >= series2
    
    Args:
        series1_current: Current value of series1 (e.g., fast MA)
        series1_previous: Previous value of series1
        series2_current: Current value of series2 (e.g., slow MA)
        series2_previous: Previous value of series2
        
    Returns:
        True if series1 crossed below series2, False otherwise
    """
    # Handle None/NaN values
    if any(na(v) for v in [series1_current, series1_previous, series2_current, series2_previous]):
        return False
    
    # Pine Script crossunder logic
    # Previous: series1 >= series2
    # Current: series1 < series2
    return (series1_previous >= series2_previous) and (series1_current < series2_current)


def barssince(condition_series: List[bool]) -> Optional[int]:
    """
    Pine Script ta.barssince() function - counts bars since condition was true
    
    Pine Script: ta.barssince(condition) returns the number of bars since condition was true
    
    Args:
        condition_series: List of boolean conditions (newest first)
        
    Returns:
        Number of bars since condition was true, or None if never true
        
    Example:
        conditions = [False, False, True, False, False]  # True was 2 bars ago
        barssince(conditions) -> 2
    """
    if not condition_series:
        return None
    
    # Search from newest to oldest (index 0 is current bar)
    for i in range(len(condition_series)):
        if condition_series[i]:
            return i
    
    # Condition was never true in the available history
    return None


def barssince_na(condition_series: List[bool], max_bars: int = 500) -> int:
    """
    Pine Script ta.barssince() with na handling - returns max_bars if never true
    
    This variant is useful when you need a numeric value instead of None
    
    Args:
        condition_series: List of boolean conditions (newest first)
        max_bars: Maximum value to return if condition never true
        
    Returns:
        Number of bars since condition was true, or max_bars if never true
    """
    result = barssince(condition_series)
    return result if result is not None else max_bars
