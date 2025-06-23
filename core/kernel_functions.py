"""
Kernel Functions for Nadaraya-Watson Estimator
Direct conversion from Pine Script's KernelFunctions library
"""
import math
from typing import List, Optional, Tuple
from .pine_functions import crossover_value, crossunder_value


def rational_quadratic(src_values: List[float], lookback: int,
                       relative_weight: float, start_at_bar: int) -> float:
    """
    Rational Quadratic Kernel - An infinite sum of Gaussian Kernels

    Pine Script:
    - As relative_weight → 0: longer timeframes dominate
    - As relative_weight → ∞: behaves like Gaussian kernel

    Args:
        src_values: Source price values (newest first)
        lookback: Number of bars for estimation
        relative_weight: Relative weighting of timeframes
        start_at_bar: Bar index to start regression

    Returns:
        Estimated value using RQ kernel
    """
    if not src_values or lookback <= 0:
        return src_values[0] if src_values else 0.0

    current_weight = 0.0
    cumulative_weight = 0.0

    # Pine Script uses array.size which gets all available data
    # We should limit to available data, not exceed it
    size = len(src_values)
    
    # Pine Script: for i = 0 to _size + startAtBar
    # But we need to ensure we don't exceed available data
    max_iterations = min(size, size + start_at_bar)
    
    # Important: Pine Script accesses src[i] where i can be large
    # We need to ensure we don't go out of bounds
    for i in range(max_iterations):
        # Make sure we have data at this index
        if i >= size:
            # If we're beyond data, we can't continue
            break
            
        y = src_values[i]

        # Rational Quadratic kernel formula
        # w = (1 + (i^2 / (lookback^2 * 2 * relative_weight)))^(-relative_weight)
        weight = math.pow(
            1 + (i * i) / (lookback * lookback * 2 * relative_weight),
            -relative_weight
        )

        current_weight += y * weight
        cumulative_weight += weight

    # Avoid division by zero
    if cumulative_weight == 0:
        return src_values[0] if src_values else 0.0

    return current_weight / cumulative_weight


def gaussian(src_values: List[float], lookback: int, start_at_bar: int) -> float:
    """
    Gaussian Kernel - Uses Radial Basis Function (RBF)

    Args:
        src_values: Source price values (newest first)
        lookback: Number of bars for estimation
        start_at_bar: Bar index to start regression

    Returns:
        Estimated value using Gaussian kernel
    """
    if not src_values or lookback <= 0:
        return src_values[0] if src_values else 0.0

    current_weight = 0.0
    cumulative_weight = 0.0

    size = len(src_values)
    max_iterations = min(size, size + start_at_bar)

    for i in range(max_iterations):
        if i >= size:
            break
            
        y = src_values[i]

        # Gaussian kernel formula
        # w = exp(-(i^2) / (2 * lookback^2))
        weight = math.exp(-(i * i) / (2 * lookback * lookback))

        current_weight += y * weight
        cumulative_weight += weight

    if cumulative_weight == 0:
        return src_values[0] if src_values else 0.0

    return current_weight / cumulative_weight


def get_kernel_estimate(src_values: List[float], kernel_type: str,
                        lookback: int, relative_weight: float,
                        regression_level: int) -> float:
    """
    Get kernel estimate using specified kernel type

    Args:
        src_values: Source values
        kernel_type: 'rational_quadratic' or 'gaussian'
        lookback: Lookback period
        relative_weight: For RQ kernel
        regression_level: Start bar for regression

    Returns:
        Kernel estimate
    """
    if kernel_type == 'rational_quadratic':
        return rational_quadratic(src_values, lookback, relative_weight, regression_level)
    elif kernel_type == 'gaussian':
        return gaussian(src_values, lookback, regression_level)
    else:
        return src_values[0] if src_values else 0.0


def calculate_kernel_values(src_values: List[float], kernel_lookback: int,
                           kernel_relative_weight: float, kernel_regression_level: int,
                           kernel_lag: int) -> Tuple[float, float, float, float]:
    """
    Calculate current and previous kernel values for both RQ and Gaussian
    
    Returns:
        (yhat1_current, yhat1_prev, yhat2_current, yhat2_prev)
    """
    if len(src_values) < kernel_lookback:
        return 0.0, 0.0, 0.0, 0.0
    
    # Current values
    yhat1 = rational_quadratic(
        src_values, kernel_lookback, kernel_relative_weight, kernel_regression_level
    )
    yhat2 = gaussian(src_values, kernel_lookback - kernel_lag, kernel_regression_level)
    
    # Previous values (using data from 1 bar ago)
    yhat1_prev = 0.0
    yhat2_prev = 0.0
    
    if len(src_values) > 1:
        src_prev = src_values[1:]
        yhat1_prev = rational_quadratic(
            src_prev, kernel_lookback, kernel_relative_weight, kernel_regression_level
        )
        yhat2_prev = gaussian(src_prev, kernel_lookback - kernel_lag, kernel_regression_level)
    
    return yhat1, yhat1_prev, yhat2, yhat2_prev


def is_kernel_bullish(src_values: List[float], kernel_lookback: int,
                      kernel_relative_weight: float, kernel_regression_level: int,
                      use_kernel_smoothing: bool, kernel_lag: int) -> bool:
    """
    Determine if kernel regression is bullish

    Returns True if kernel indicates bullish conditions
    """
    if len(src_values) < kernel_lookback:
        return True  # Not enough data, default to bullish

    # Get kernel values
    yhat1, yhat1_prev, yhat2, yhat2_prev = calculate_kernel_values(
        src_values, kernel_lookback, kernel_relative_weight, 
        kernel_regression_level, kernel_lag
    )

    if use_kernel_smoothing:
        # Bullish if smoothed line is above main line
        return yhat2 >= yhat1
    else:
        # Bullish if kernel is rising (rate of change positive)
        return yhat1 > yhat1_prev


def is_kernel_bearish(src_values: List[float], kernel_lookback: int,
                      kernel_relative_weight: float, kernel_regression_level: int,
                      use_kernel_smoothing: bool, kernel_lag: int) -> bool:
    """
    Determine if kernel regression is bearish

    Returns True if kernel indicates bearish conditions
    """
    if len(src_values) < kernel_lookback:
        return True  # Not enough data, default to bearish allowed

    # Get kernel values
    yhat1, yhat1_prev, yhat2, yhat2_prev = calculate_kernel_values(
        src_values, kernel_lookback, kernel_relative_weight, 
        kernel_regression_level, kernel_lag
    )

    if use_kernel_smoothing:
        # Bearish if smoothed line is below main line
        return yhat2 <= yhat1
    else:
        # Bearish if kernel is falling (rate of change negative)
        return yhat1 < yhat1_prev


def get_kernel_crossovers(src_values: List[float], kernel_lookback: int,
                         kernel_relative_weight: float, kernel_regression_level: int,
                         kernel_lag: int) -> Tuple[bool, bool]:
    """
    Detect kernel crossovers (for alerts and dynamic exits)
    
    Pine Script:
    bool isBullishCrossAlert = ta.crossover(yhat2, yhat1)
    bool isBearishCrossAlert = ta.crossunder(yhat2, yhat1)
    
    Returns:
        (bullish_cross, bearish_cross)
    """
    if len(src_values) < kernel_lookback + 1:
        return False, False
    
    # Get kernel values
    yhat1, yhat1_prev, yhat2, yhat2_prev = calculate_kernel_values(
        src_values, kernel_lookback, kernel_relative_weight, 
        kernel_regression_level, kernel_lag
    )
    
    # Check for crossovers
    bullish_cross = crossover_value(yhat2, yhat2_prev, yhat1, yhat1_prev)
    bearish_cross = crossunder_value(yhat2, yhat2_prev, yhat1, yhat1_prev)
    
    return bullish_cross, bearish_cross
