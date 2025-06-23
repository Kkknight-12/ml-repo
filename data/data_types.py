"""
Pine Script Type Definitions - Direct 1:1 Mapping
No modifications, no improvements - exact conversion
"""
from dataclasses import dataclass
from typing import List, Optional
import numpy as np


@dataclass
class Settings:
    """Settings object - matches Pine Script exactly"""
    source: str = 'close'
    neighbors_count: int = 8
    max_bars_back: int = 2000
    feature_count: int = 5
    color_compression: int = 1
    show_exits: bool = False
    use_dynamic_exits: bool = False


@dataclass
class Label:
    """Direction labels - no changes from Pine Script"""
    long: int = 1
    short: int = -1
    neutral: int = 0


@dataclass
class FeatureArrays:
    """Storage for feature arrays - using lists like Pine arrays"""
    f1: List[float]
    f2: List[float]
    f3: List[float]
    f4: List[float]
    f5: List[float]

    def __init__(self):
        # Initialize empty arrays
        self.f1 = []
        self.f2 = []
        self.f3 = []
        self.f4 = []
        self.f5 = []


@dataclass
class FeatureSeries:
    """Current bar feature values"""
    f1: float
    f2: float
    f3: float
    f4: float
    f5: float


@dataclass
class MLModel:
    """ML model state - exact Pine Script fields"""
    first_bar_index: int
    training_labels: List[int]
    loop_size: int
    last_distance: float
    distances_array: List[float]
    predictions_array: List[int]
    prediction: int

    def __init__(self):
        self.first_bar_index = 0
        self.training_labels = []
        self.loop_size = 0
        self.last_distance = -1.0
        self.distances_array = []
        self.predictions_array = []
        self.prediction = 0


@dataclass
class FilterSettings:
    """Filter configuration"""
    use_volatility_filter: bool = True
    use_regime_filter: bool = True
    use_adx_filter: bool = False
    regime_threshold: float = -0.1
    adx_threshold: int = 20


@dataclass
class Filter:
    """Current filter states"""
    volatility: bool
    regime: bool
    adx: bool