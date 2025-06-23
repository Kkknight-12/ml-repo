"""
Lorentzian Classification - Core ML Algorithm
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
from core.pine_functions import nz, na


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

        # Training data (var in Pine Script)
        self.y_train_array: List[int] = []  # var y_train_array

        # PERSISTENT ARRAYS (var in Pine Script) - DO NOT CLEAR BETWEEN BARS!
        self.predictions: List[float] = []  # var predictions - persists across bars
        self.distances: List[float] = []    # var distances - persists across bars
        
        # Current bar values (not var in Pine Script)
        self.prediction = 0.0
        self.signal = label.neutral
        self.last_valid_prediction = 0.0  # Track last valid prediction
        
        # Track last distance for adaptive threshold
        self.last_distance = -1.0  # Resets each bar in Pine Script

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
                return nz(arr[idx], 0.0)  # Use Pine Script nz() function
            return 0.0
        
        # Helper function to validate feature value
        def validate_feature(val: float) -> float:
            # Use Pine Script nz() for NaN/None handling
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
                bar_index: int, max_bars_back_index: int = None) -> float:
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
            bar_index: Current bar index (for compatibility)
            max_bars_back_index: DEPRECATED - not used

        Returns:
            Prediction value (sum of k-nearest neighbor labels)
        """
        # IMPORTANT: DO NOT CLEAR PERSISTENT ARRAYS!
        # In Pine Script, 'var predictions' and 'var distances' persist across bars
        # They only shift/update, never fully clear
        
        # Reset last_distance for this bar (not var in Pine Script)
        last_distance = -1.0

        # FIX: Process whatever data we have, don't wait for max_bars_back
        # Pine Script starts ML as soon as we have ANY training data
        if len(self.y_train_array) == 0:
            return 0.0  # No data yet
            
        # Determine loop size - use whatever data we have
        size = len(self.y_train_array) - 1
        size_loop = min(self.settings.max_bars_back - 1, size) if size > 0 else 0
        
        # Ensure we have something to process
        if size_loop < 0:
            return 0.0

        # Approximate Nearest Neighbors Search
        for i in range(size_loop + 1):
            # Calculate distance to historical point
            d = self.get_lorentzian_distance(
                i, self.settings.feature_count, feature_series, feature_arrays
            )

            # Pine Script: if d >= lastDistance and i%4
            # In Pine Script, i%4 is truthy when i%4 != 0 (1,2,3 but not 0)
            # FIX: Changed to match Pine Script behavior
            if d >= last_distance and i % 4 != 0:
                last_distance = d
                self.distances.append(d)

                # Get label for this historical point
                if i < len(self.y_train_array):
                    self.predictions.append(float(self.y_train_array[i]))

                # Maintain k neighbors (circular buffer pattern)
                if len(self.predictions) > self.settings.neighbors_count:
                    # Update last_distance to 75th percentile
                    k_75 = int(self.settings.neighbors_count * 3 / 4)
                    if k_75 < len(self.distances):
                        last_distance = self.distances[k_75]

                    # Remove oldest neighbor (shift operation)
                    self.distances.pop(0)
                    self.predictions.pop(0)

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
    
    def predict_with_debug(self, feature_series: FeatureSeries, feature_arrays: FeatureArrays, bar_index: int) -> None:
        """
        Predict with Pine Script style debug logging
        This matches the exact debug output from Pine Script
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Log ML debug start
        logger.info(f"Initial lastDistance: -1")
        
        # Check if we have training data
        if len(self.y_train_array) == 0:
            logger.error("No training data available!")
            self.prediction = 0.0
            return
        
        # Calculate size and size_loop
        size = len(self.y_train_array) - 1
        size_loop = min(self.settings.max_bars_back - 1, size) if size > 0 else 0
        
        logger.info(f"Size: {size}, SizeLoop: {size_loop}")
        
        if size_loop < 0:
            logger.error("size_loop < 0, no prediction possible")
            self.prediction = 0.0
            return
        
        # Reset last_distance for this bar
        last_distance = -1.0
        neighbors_added = 0
        
        # Loop through historical bars
        for i in range(size_loop + 1):
            # Calculate distance
            d = self.get_lorentzian_distance(
                i, self.settings.feature_count,
                feature_series, feature_arrays
            )
            
            # Pine Script: if d >= lastDistance and i%4
            if d >= last_distance and i % 4 != 0:
                last_distance = d
                self.distances.append(d)
                
                # Get label
                if i < len(self.y_train_array):
                    label = self.y_train_array[i]
                    self.predictions.append(float(label))
                    neighbors_added += 1
                    
                    # Log neighbor addition
                    logger.warning(f"NEIGHBOR ADDED #{neighbors_added}: i={i}, distance={d:.3f}, label={label}")
                    
                    # Maintain k neighbors
                    if len(self.predictions) > self.settings.neighbors_count:
                        # Log before shift
                        logger.info(f"Before shift - Predictions size: {len(self.predictions)}, First prediction: {self.predictions[0]}")
                        
                        # Update last_distance to 75th percentile
                        k_75 = int(self.settings.neighbors_count * 3 / 4)
                        if k_75 < len(self.distances):
                            last_distance = self.distances[k_75]
                            logger.info(f"75th percentile update: New lastDistance = {last_distance:.3f}")
                        
                        # Remove oldest
                        self.distances.pop(0)
                        self.predictions.pop(0)
                        
                        logger.info(f"After shift - Predictions size: {len(self.predictions)}")
        
        # Log total neighbors found
        logger.error(f"TOTAL NEIGHBORS FOUND: {neighbors_added} (Expected: {self.settings.neighbors_count})")
        
        # Log prediction array contents
        if self.predictions:
            pred_str = " ".join(str(int(p)) for p in self.predictions)
            logger.error(f"Prediction Array Contents: [{pred_str} ]")
        
        # Calculate final prediction
        self.prediction = sum(self.predictions) if self.predictions else 0.0
        
        logger.error(f"FINAL PREDICTION VALUE: {self.prediction} (Sum of {len(self.predictions)} neighbors)")