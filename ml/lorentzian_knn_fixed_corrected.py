"""
Lorentzian Classification - Fixed ML Algorithm WITH CORRECTED INDEXING
=====================================================================

This fixes the array indexing issue where Pine Script expects i=0 to be
the most recent historical bar, but Python was accessing the oldest.
"""
import math
from typing import List, Tuple, Optional
from data.data_types import (
    Settings, Label, FeatureArrays, FeatureSeries,
    MLModel, Filter, FilterSettings
)
from core.pine_functions import nz, na


class LorentzianKNNFixedCorrected:
    """
    Fixed K-Nearest Neighbors classifier using Lorentzian Distance
    WITH CORRECTED ARRAY INDEXING
    """

    def __init__(self, settings: Settings, label: Label):
        """
        Initialize the Lorentzian KNN model with persistent arrays
        
        Args:
            settings: Configuration settings
            label: Direction labels (long=1, short=-1, neutral=0)
        """
        self.settings = settings
        self.label = label

        # Model state
        self.model = MLModel()

        # Training data (var in Pine Script)
        self.y_train_array: List[int] = []  # var y_train_array

        # CRITICAL FIX: These arrays must NEVER be cleared!
        # In Pine Script, 'var' arrays persist for the entire chart lifetime
        self.predictions: List[float] = []  # var predictions - NEVER RESET!
        self.distances: List[float] = []    # var distances - NEVER RESET!
        
        # Track if we've ever had neighbors (for debugging)
        self.max_neighbors_seen = 0
        
        # Current bar values (not var in Pine Script)
        self.prediction = 0.0
        self.signal = label.neutral
        self.last_valid_prediction = 0.0

    def get_lorentzian_distance(self, i: int, feature_count: int,
                                feature_series: FeatureSeries,
                                feature_arrays: FeatureArrays) -> float:
        """
        Calculate Lorentzian distance between current features and historical features
        
        FIXED: Now correctly accesses arrays from newest to oldest
        
        Pine Script formula:
        math.log(1 + math.abs(feature_current - feature_historical))
        """
        distance = 0.0

        # CRITICAL FIX: Helper function to get array value with CORRECT indexing
        def get_value(arr: List[float], idx: int) -> float:
            """
            Get value from array with Pine Script indexing
            i=0 should access the most recent historical value (end of array)
            """
            if idx >= len(arr):
                return 0.0
            # Access from end of array: i=0 → arr[-1], i=1 → arr[-2], etc.
            return nz(arr[-(idx + 1)], 0.0)
        
        # Helper function to validate feature value
        def validate_feature(val: float) -> float:
            return nz(val, 0.0)

        # Calculate distance based on feature count
        if feature_count >= 2:
            f1 = validate_feature(feature_series.f1)
            distance += math.log(1 + abs(f1 - get_value(feature_arrays.f1, i)))
            
            f2 = validate_feature(feature_series.f2)
            distance += math.log(1 + abs(f2 - get_value(feature_arrays.f2, i)))

        if feature_count >= 3:
            f3 = validate_feature(feature_series.f3)
            distance += math.log(1 + abs(f3 - get_value(feature_arrays.f3, i)))

        if feature_count >= 4:
            f4 = validate_feature(feature_series.f4)
            distance += math.log(1 + abs(f4 - get_value(feature_arrays.f4, i)))

        if feature_count >= 5:
            f5 = validate_feature(feature_series.f5)
            distance += math.log(1 + abs(f5 - get_value(feature_arrays.f5, i)))

        return distance

    def update_training_data(self, src_current: float, src_4bars_ago: float) -> None:
        """
        Update training labels based on price movement
        
        Pine Script:
        y_train_series := src[4] < src[0] ? label.short : 
                         src[4] > src[0] ? label.long : label.neutral
        array.push(y_train_array, y_train_series)
        """
        # Determine label based on price movement
        if src_4bars_ago < src_current:
            # Price went up, so 4 bars ago was a good short
            y_train_series = self.label.short
        elif src_4bars_ago > src_current:
            # Price went down, so 4 bars ago was a good long
            y_train_series = self.label.long
        else:
            y_train_series = self.label.neutral

        # Add to training array
        self.y_train_array.append(y_train_series)

    def predict(self, feature_series: FeatureSeries,
                feature_arrays: FeatureArrays, bar_index: int) -> float:
        """
        Make prediction using k-nearest neighbors
        
        FIXED: Now correctly iterates from newest to oldest historical data
        """
        # Check if we have enough training data
        if len(self.y_train_array) == 0:
            self.prediction = 0.0
            return self.prediction

        # Pine Script: size = math.min(maxBarsBackIndex >= 0 ? maxBarsBackIndex : 0, y_train_array.size() - 1)
        size = len(self.y_train_array) - 1
        size_loop = min(self.settings.max_bars_back - 1, size) if size > 0 else 0

        if size_loop < 0:
            self.prediction = 0.0
            return self.prediction

        # Reset last_distance for this bar (not var in Pine Script)
        last_distance = -1.0
        neighbors_added_this_bar = 0

        # Approximate Nearest Neighbors Search
        for i in range(size_loop + 1):
            # Calculate distance to historical point
            d = self.get_lorentzian_distance(
                i, self.settings.feature_count, feature_series, feature_arrays
            )

            # Pine Script: if d >= lastDistance and i%4
            # CRITICAL: i%4 is truthy when i%4 != 0
            if d >= last_distance and i % 4 != 0:
                last_distance = d
                self.distances.append(d)

                # FIXED: Get label with correct indexing
                # i=0 should get the most recent training label
                if i < len(self.y_train_array):
                    # Access from end: i=0 → y_train_array[-1]
                    label_idx = -(i + 1)
                    self.predictions.append(float(self.y_train_array[label_idx]))
                    neighbors_added_this_bar += 1

                # Maintain k neighbors (sliding window)
                if len(self.predictions) > self.settings.neighbors_count:
                    # CRITICAL: Update threshold BEFORE removing
                    # Pine Script: lastDistance := array.get(distances, math.round(settings.neighborsCount*3/4))
                    k_75 = round(self.settings.neighbors_count * 3 / 4)
                    if k_75 < len(self.distances):
                        last_distance = self.distances[k_75]

                    # Remove oldest neighbor (FIFO)
                    self.distances.pop(0)
                    self.predictions.pop(0)

        # Track maximum neighbors seen
        current_neighbor_count = len(self.predictions)
        self.max_neighbors_seen = max(self.max_neighbors_seen, current_neighbor_count)

        # Sum predictions to get final prediction
        self.prediction = sum(self.predictions) if self.predictions else 0.0
        
        # Store last valid prediction
        if self.prediction != 0.0:
            self.last_valid_prediction = self.prediction
        
        return self.prediction

    def update_signal(self, filter_all: bool) -> int:
        """
        Update signal based on prediction and filters
        
        Pine Script:
        signal := prediction > 0 and filter_all ? direction.long :
                 prediction < 0 and filter_all ? direction.short :
                 nz(signal[1])
        """
        if self.prediction > 0 and filter_all:
            self.signal = self.label.long
        elif self.prediction < 0 and filter_all:
            self.signal = self.label.short
        # Otherwise keep previous signal (handled by caller)

        return self.signal

    def get_prediction_strength(self) -> float:
        """
        Get normalized prediction strength (0-1)
        """
        if self.settings.neighbors_count == 0:
            return 0.0

        # Normalize to [0, 1] range
        max_prediction = float(self.settings.neighbors_count)
        normalized = abs(self.prediction) / max_prediction

        return min(normalized, 1.0)
    
    def get_neighbor_count(self) -> int:
        """Get current number of neighbors in sliding window"""
        return len(self.predictions)
    
    def get_max_neighbors_seen(self) -> int:
        """Get maximum number of neighbors ever seen"""
        return self.max_neighbors_seen