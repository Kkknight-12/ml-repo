"""
Lorentzian Classification - Core ML Algorithm WITH DEBUG
Direct implementation of Pine Script's KNN with Lorentzian Distance

Key Innovation: Uses Lorentzian distance instead of Euclidean to better
handle market volatility and "price-time" warping effects
"""
import math
from typing import List, Tuple, Optional
from data.data_types import (
    Settings, Label, FeatureArrays, FeatureSeries,
    MLModel, Filter, FilterSettings
)


class LorentzianKNN:
    """
    K-Nearest Neighbors classifier using Lorentzian Distance
    Exact implementation of Pine Script algorithm
    """

    def __init__(self, settings: Settings, label: Label):
        """
        Initialize the Lorentzian KNN model

        Args:
            settings: Configuration settings
            label: Direction labels (long=1, short=-1, neutral=0)
        """
        self.settings = settings
        self.label = label

        # Model state
        self.model = MLModel()

        # Training data
        self.y_train_array: List[int] = []

        # Predictions for current bar
        self.predictions: List[float] = []
        self.distances: List[float] = []
        self.prediction = 0.0
        self.signal = label.neutral
        
        # Debug flag
        self.debug_enabled = False
        self.debug_bar = None

    def get_lorentzian_distance(self, i: int, feature_count: int,
                                feature_series: FeatureSeries,
                                feature_arrays: FeatureArrays) -> float:
        """
        Calculate Lorentzian distance between current features and historical features

        Pine Script formula:
        math.log(1 + math.abs(feature_current - feature_historical))

        Args:
            i: Index in feature arrays (0 = most recent)
            feature_count: Number of features to use (2-5)
            feature_series: Current bar's features
            feature_arrays: Historical feature arrays

        Returns:
            Lorentzian distance (sum across all features)
        """
        distance = 0.0

        # Helper function to safely get array value
        def get_value(arr: List[float], idx: int) -> float:
            if idx < len(arr):
                val = arr[idx]
                # PHASE 3 FIX: Check for None/NaN
                if val is not None and not math.isnan(val):
                    return val
            return 0.0
        
        # Helper function to validate feature value
        def validate_feature(val: float) -> float:
            # PHASE 3 FIX: Handle None/NaN features
            if val is None or math.isnan(val):
                return 0.0
            return val

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
        y_train_series = src[4] < src[0] ? direction.short :
                        src[4] > src[0] ? direction.long : direction.neutral

        Args:
            src_current: Current bar's source price
            src_4bars_ago: Price from 4 bars ago
        """
        if src_4bars_ago < src_current:
            label = self.label.short
        elif src_4bars_ago > src_current:
            label = self.label.long
        else:
            label = self.label.neutral

        self.y_train_array.append(label)

    def predict(self, feature_series: FeatureSeries, feature_arrays: FeatureArrays,
                bar_index: int, max_bars_back_index: int) -> float:
        """
        Generate prediction using Approximate Nearest Neighbors

        This is the core ML logic from Pine Script:
        1. Iterate through historical data
        2. Calculate Lorentzian distances
        3. Maintain k-nearest neighbors with chronological spacing
        4. Sum predictions to get final prediction

        Args:
            feature_series: Current bar's features
            feature_arrays: Historical features
            bar_index: Current bar index
            max_bars_back_index: Minimum bar index to process

        Returns:
            Prediction value (sum of k-nearest neighbor labels)
        """
        # Enable debug for specific bar
        if self.debug_bar is not None and bar_index == self.debug_bar:
            self.debug_enabled = True
            print(f"\n{'='*60}")
            print(f"DEBUG: ML Prediction at bar {bar_index}")
            print(f"{'='*60}")
        else:
            self.debug_enabled = False
        
        # Reset for new prediction
        last_distance = -1.0
        self.predictions.clear()
        self.distances.clear()

        # Determine loop size
        size = min(self.settings.max_bars_back - 1, len(self.y_train_array) - 1)
        size_loop = min(self.settings.max_bars_back - 1, size)
        
        if self.debug_enabled:
            print(f"Loop size: {size_loop}")
            print(f"Training array length: {len(self.y_train_array)}")
            print(f"Feature array lengths: F1={len(feature_arrays.f1)}, F2={len(feature_arrays.f2)}")
            print(f"Current features: F1={feature_series.f1:.4f}, F2={feature_series.f2:.4f}")

        # Only process if we have enough data
        if bar_index < max_bars_back_index:
            if self.debug_enabled:
                print(f"SKIPPING: bar_index ({bar_index}) < max_bars_back_index ({max_bars_back_index})")
            return 0.0

        neighbor_count = 0
        # Approximate Nearest Neighbors Search
        for i in range(size_loop + 1):
            # Calculate distance to historical point
            d = self.get_lorentzian_distance(
                i, self.settings.feature_count, feature_series, feature_arrays
            )

            # Pine Script: if d >= lastDistance and i%4
            # Check chronological spacing (every 4th bar) and distance threshold
            modulo_check = i % 4 != 0
            distance_check = d >= last_distance
            
            if self.debug_enabled and i < 20:  # Show first 20
                print(f"i={i}: d={d:.4f}, last_d={last_distance:.4f}, "
                      f"mod_check={modulo_check} (i%4={i%4}), dist_check={distance_check}")
            
            if distance_check and modulo_check:
                neighbor_count += 1
                last_distance = d
                self.distances.append(d)

                # Get label for this historical point
                if i < len(self.y_train_array):
                    label_val = self.y_train_array[i]
                    self.predictions.append(float(label_val))
                    
                    if self.debug_enabled and neighbor_count <= 10:
                        print(f"  → Neighbor {neighbor_count}: i={i}, label={label_val}, d={d:.4f}")

                # Maintain k neighbors
                if len(self.predictions) > self.settings.neighbors_count:
                    # Update last_distance to 75th percentile
                    k_75 = int(self.settings.neighbors_count * 3 / 4)
                    if k_75 < len(self.distances):
                        old_last = last_distance
                        last_distance = self.distances[k_75]
                        if self.debug_enabled:
                            print(f"  → Updated last_distance: {old_last:.4f} -> {last_distance:.4f}")

                    # Remove oldest neighbor
                    self.distances.pop(0)
                    self.predictions.pop(0)

        if self.debug_enabled:
            print(f"\nFinal results:")
            print(f"Neighbors found: {len(self.predictions)}")
            print(f"Predictions: {self.predictions}")
            print(f"Sum: {sum(self.predictions) if self.predictions else 0}")

        # Sum predictions to get final prediction
        self.prediction = sum(self.predictions) if self.predictions else 0.0
        return self.prediction

    def update_signal(self, filter_all: bool) -> int:
        """
        Update signal based on prediction and filters

        Pine Script:
        signal := prediction > 0 and filter_all ? direction.long :
                 prediction < 0 and filter_all ? direction.short :
                 nz(signal[1])

        Args:
            filter_all: Combined filter result

        Returns:
            Current signal (long/short/neutral)
        """
        if self.prediction > 0 and filter_all:
            self.signal = self.label.long
        elif self.prediction < 0 and filter_all:
            self.signal = self.label.short
        # Otherwise keep previous signal (stateless - handled by caller)

        return self.signal

    def get_prediction_strength(self) -> float:
        """
        Get normalized prediction strength (0-1)
        Used for coloring and confidence

        Returns:
            Normalized prediction value
        """
        if self.settings.neighbors_count == 0:
            return 0.0

        # Normalize to [0, 1] range
        max_prediction = float(self.settings.neighbors_count)
        normalized = abs(self.prediction) / max_prediction

        return min(normalized, 1.0)
