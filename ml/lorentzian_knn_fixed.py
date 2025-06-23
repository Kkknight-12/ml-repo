"""
Lorentzian Classification - Fixed ML Algorithm
==============================================

This fixes the neighbor selection issue by ensuring arrays persist like Pine Script's 'var' arrays.
Pine Script's var arrays NEVER clear - they persist for the entire chart lifetime.
"""
import math
from typing import List, Tuple, Optional
from data.data_types import (
    Settings, Label, FeatureArrays, FeatureSeries,
    MLModel, Filter, FilterSettings
)
from core.pine_functions import nz, na


class LorentzianKNNFixed:
    """
    Fixed K-Nearest Neighbors classifier using Lorentzian Distance
    Ensures Pine Script 'var' array behavior is maintained
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
        
        Pine Script formula:
        math.log(1 + math.abs(feature_current - feature_historical))
        """
        distance = 0.0

        # Helper function to safely get array value
        def get_value(arr: List[float], idx: int) -> float:
            if idx < len(arr):
                return nz(arr[idx], 0.0)
            return 0.0
        
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
        y_train_series = src[4] < src[0] ? direction.short :
                        src[4] > src[0] ? direction.long : direction.neutral
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
        
        CRITICAL: Maintains persistent arrays like Pine Script 'var' behavior
        """
        # IMPORTANT: We DO NOT clear persistent arrays!
        # Pine Script's 'var' arrays persist across ALL bars
        
        # last_distance resets each bar (not var in Pine Script)
        last_distance = -1.0

        # Process whatever data we have
        if len(self.y_train_array) == 0:
            return 0.0
            
        # Determine loop size
        size = len(self.y_train_array) - 1
        size_loop = min(self.settings.max_bars_back - 1, size) if size > 0 else 0
        
        if size_loop < 0:
            return 0.0

        # Count neighbors added this bar
        neighbors_added_this_bar = 0
        initial_neighbor_count = len(self.predictions)

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

                # Get label for this historical point
                if i < len(self.y_train_array):
                    self.predictions.append(float(self.y_train_array[i]))
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

        # Log neighbor accumulation (for debugging)
        if neighbors_added_this_bar > 0 and current_neighbor_count < self.settings.neighbors_count:
            # Still accumulating neighbors
            pass
        
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
    
    def predict_with_debug(self, feature_series: FeatureSeries, feature_arrays: FeatureArrays, bar_index: int) -> None:
        """
        Predict with enhanced debug logging to track neighbor accumulation
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Log current state
        logger.info(f"Bar {bar_index} | PERSISTENT ARRAY STATE:")
        logger.info(f"  - Current neighbors in window: {len(self.predictions)}")
        logger.info(f"  - Max neighbors ever seen: {self.max_neighbors_seen}")
        logger.info(f"  - Training data size: {len(self.y_train_array)}")
        
        # Log initial state
        initial_neighbors = len(self.predictions)
        logger.info(f"Initial neighbors before processing: {initial_neighbors}")
        
        # Check if we have training data
        if len(self.y_train_array) == 0:
            logger.error("No training data available!")
            self.prediction = 0.0
            return
        
        # Calculate size and size_loop
        size = len(self.y_train_array) - 1
        size_loop = min(self.settings.max_bars_back - 1, size) if size > 0 else 0
        
        logger.info(f"Processing loop size: {size_loop + 1} bars")
        
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
            
            # Check modulo condition
            modulo_passes = i % 4 != 0
            distance_passes = d >= last_distance
            
            # Log every 100th bar to track progress
            if i % 100 == 0:
                logger.debug(f"  Bar {i}: distance={d:.3f}, modulo_passes={modulo_passes}, distance_passes={distance_passes}")
            
            # Pine Script: if d >= lastDistance and i%4
            if distance_passes and modulo_passes:
                last_distance = d
                self.distances.append(d)
                
                # Get label
                if i < len(self.y_train_array):
                    label = self.y_train_array[i]
                    self.predictions.append(float(label))
                    neighbors_added += 1
                    
                    # Log neighbor addition
                    if neighbors_added <= 10 or len(self.predictions) == self.settings.neighbors_count:
                        logger.warning(f"NEIGHBOR #{len(self.predictions)} ADDED: i={i}, distance={d:.3f}, label={label}")
                    
                    # Maintain k neighbors
                    if len(self.predictions) > self.settings.neighbors_count:
                        # Update threshold
                        k_75 = round(self.settings.neighbors_count * 3 / 4)
                        if k_75 < len(self.distances):
                            old_threshold = last_distance
                            last_distance = self.distances[k_75]
                            logger.debug(f"Threshold updated: {old_threshold:.3f} -> {last_distance:.3f}")
                        
                        # Remove oldest
                        self.distances.pop(0)
                        removed_pred = self.predictions.pop(0)
                        logger.debug(f"Removed oldest neighbor (prediction={removed_pred})")
        
        # Update max neighbors seen
        current_neighbors = len(self.predictions)
        self.max_neighbors_seen = max(self.max_neighbors_seen, current_neighbors)
        
        # Log results
        logger.warning(f"Bar {bar_index} | NEIGHBOR ACCUMULATION:")
        logger.warning(f"  - Neighbors at start: {initial_neighbors}")
        logger.warning(f"  - Neighbors added this bar: {neighbors_added}")
        logger.warning(f"  - Neighbors at end: {current_neighbors}")
        logger.warning(f"  - Max neighbors ever: {self.max_neighbors_seen}")
        
        # Log if we reached target
        if current_neighbors == self.settings.neighbors_count:
            logger.error(f"✅ REACHED TARGET: {self.settings.neighbors_count} neighbors!")
        else:
            logger.error(f"❌ STILL ACCUMULATING: {current_neighbors}/{self.settings.neighbors_count} neighbors")
        
        # Log prediction array contents
        if self.predictions:
            pred_str = " ".join(str(int(p)) for p in self.predictions[:10])
            if len(self.predictions) > 10:
                pred_str += f" ... ({len(self.predictions) - 10} more)"
            logger.info(f"Prediction Array: [{pred_str}]")
        
        # Calculate final prediction
        self.prediction = sum(self.predictions) if self.predictions else 0.0
        
        logger.error(f"FINAL PREDICTION: {self.prediction} (sum of {len(self.predictions)} neighbors)")
