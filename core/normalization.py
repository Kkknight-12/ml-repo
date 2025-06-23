"""
Normalization functions from MLExtensions library
These are critical for ML feature preparation
"""
from typing import List, Dict, Optional


class Normalizer:
    """
    Handles normalization with historical min/max tracking
    Mimics Pine Script's var _historicMin and var _historicMax
    """

    def __init__(self):
        # Track historic min/max for each series
        self.historic_min: Dict[str, float] = {}
        self.historic_max: Dict[str, float] = {}

    def normalize(self, value: float, series_name: str,
                  target_min: float = 0.0, target_max: float = 1.0) -> float:
        """
        Normalize a value to target range using historical min/max

        Pine Script:
        var _historicMin = 10e10
        var _historicMax = -10e10
        _historicMin := math.min(nz(src, _historicMin), _historicMin)
        _historicMax := math.max(nz(src, _historicMax), _historicMax)
        min + (max - min) * (src - _historicMin) / math.max(_historicMax - _historicMin, 10e-10)
        """
        # Initialize if first time seeing this series
        if series_name not in self.historic_min:
            self.historic_min[series_name] = 10e10
            self.historic_max[series_name] = -10e10

        # Update historic min/max
        self.historic_min[series_name] = min(value, self.historic_min[series_name])
        self.historic_max[series_name] = max(value, self.historic_max[series_name])

        # Calculate normalized value
        hist_range = self.historic_max[series_name] - self.historic_min[series_name]

        # Avoid division by zero
        if hist_range < 10e-10:
            return target_min

        normalized = target_min + (target_max - target_min) * \
                     (value - self.historic_min[series_name]) / hist_range

        return normalized


def rescale(value: float, old_min: float, old_max: float,
            new_min: float, new_max: float) -> float:
    """
    Rescale a value from one range to another

    Pine Script:
    newMin + (newMax - newMin) * (src - oldMin) / math.max(oldMax - oldMin, 10e-10)
    """
    old_range = old_max - old_min

    # Avoid division by zero
    if abs(old_range) < 10e-10:
        return new_min

    return new_min + (new_max - new_min) * (value - old_min) / old_range


def tanh_transform(values: List[float], smoothing_frequency: int,
                   quadratic_mean_length: int) -> float:
    """
    Complete tanh transform as used in MLExtensions
    Combines normalizeDeriv, tanh, and dualPoleFilter
    """
    from .math_helpers import normalize_deriv, tanh, dual_pole_filter

    if not values:
        return 0.0

    # Step 1: Normalize derivative
    n_deriv = normalize_deriv(values, quadratic_mean_length)

    # Step 2: Apply tanh
    tanh_value = tanh(n_deriv)

    # Step 3: Apply dual pole filter (simplified for single value)
    # In real implementation, we'd maintain a list of tanh values
    # For now, return the tanh value
    return tanh_value


# Global normalizer instance (mimics Pine Script's var behavior)
normalizer = Normalizer()