"""
Flexible Lorentzian k-NN Implementation
======================================

A flexible version of Lorentzian k-NN that supports any number of features.
Designed to be a drop-in replacement for the fixed 5-feature version.
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Set
from collections import deque
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class FlexibleFeatureSet:
    """Container for flexible feature set"""
    features: Dict[str, float]
    timestamp: Optional[int] = None
    
    def get_array(self, feature_names: List[str]) -> np.ndarray:
        """Get features as array in specified order"""
        return np.array([self.features.get(name, 0.0) for name in feature_names])


class FlexibleLorentzianKNN:
    """
    Flexible k-NN classifier using Lorentzian Distance
    Supports any number and combination of features
    """
    
    def __init__(self, 
                 feature_names: List[str],
                 n_neighbors: int = 8,
                 max_bars_back: int = 2000,
                 prediction_length: int = 5):
        """
        Initialize flexible k-NN
        
        Args:
            feature_names: List of feature names to use
            n_neighbors: Number of neighbors for k-NN
            max_bars_back: Maximum training history
            prediction_length: Bars ahead to predict
        """
        self.feature_names = feature_names
        self.n_features = len(feature_names)
        self.n_neighbors = n_neighbors
        self.max_bars_back = max_bars_back
        self.prediction_length = prediction_length
        
        # Training data
        self.feature_history = deque(maxlen=max_bars_back)
        self.label_history = deque(maxlen=max_bars_back)
        
        # Performance tracking
        self.prediction_count = 0
        self.bar_index = 0
        
        # Feature statistics for normalization
        self.feature_stats = {name: {'min': 0, 'max': 100, 'mean': 50} 
                             for name in feature_names}
        
        logger.info(f"Initialized FlexibleLorentzianKNN with {self.n_features} features: {feature_names}")
    
    def update_features(self, features: Dict[str, float]) -> FlexibleFeatureSet:
        """
        Update with new feature values
        
        Args:
            features: Dictionary of feature name -> value
            
        Returns:
            FlexibleFeatureSet
        """
        # Create feature set
        feature_set = FlexibleFeatureSet(features=features, timestamp=self.bar_index)
        
        # Update statistics
        self._update_feature_stats(features)
        
        self.bar_index += 1
        
        return feature_set
    
    def _update_feature_stats(self, features: Dict[str, float]):
        """Update feature statistics for normalization"""
        for name, value in features.items():
            if name in self.feature_stats:
                stats = self.feature_stats[name]
                if self.bar_index == 0:
                    stats['min'] = stats['max'] = stats['mean'] = value
                else:
                    stats['min'] = min(stats['min'], value)
                    stats['max'] = max(stats['max'], value)
                    # Simple moving average
                    stats['mean'] = stats['mean'] * 0.99 + value * 0.01
    
    def add_training_data(self, feature_set: FlexibleFeatureSet, label: int):
        """
        Add training data point
        
        Args:
            feature_set: Features for this bar
            label: Direction label (1 or -1)
        """
        self.feature_history.append(feature_set)
        self.label_history.append(label)
    
    def predict(self, current_features: Dict[str, float]) -> float:
        """
        Make prediction using k-NN with Lorentzian distance
        
        Args:
            current_features: Current feature values
            
        Returns:
            Prediction value (-5 to 5)
        """
        # Need enough training data
        if len(self.feature_history) < self.n_neighbors:
            return 0.0
        
        # Get current feature array
        current_array = np.array([current_features.get(name, 0.0) 
                                 for name in self.feature_names])
        
        # Normalize features
        current_normalized = self._normalize_features(current_array)
        
        # Calculate distances to all training points
        distances = []
        
        for i, historical_features in enumerate(self.feature_history):
            # Get historical feature array
            hist_array = historical_features.get_array(self.feature_names)
            hist_normalized = self._normalize_features(hist_array)
            
            # Lorentzian distance
            distance = self._lorentzian_distance(current_normalized, hist_normalized)
            distances.append((distance, self.label_history[i], i))
        
        # Sort by distance and get k nearest
        distances.sort(key=lambda x: x[0])
        k_nearest = distances[:self.n_neighbors]
        
        # Calculate weighted prediction
        if k_nearest:
            # Use inverse distance weighting
            weights = []
            labels = []
            
            for dist, label, idx in k_nearest:
                # Weight = 1 / (1 + distance)
                weight = 1.0 / (1.0 + dist)
                weights.append(weight)
                labels.append(label)
            
            # Normalize weights
            total_weight = sum(weights)
            if total_weight > 0:
                weights = [w / total_weight for w in weights]
            
            # Weighted average of labels
            prediction = sum(w * l for w, l in zip(weights, labels))
            
            # Scale to -5 to 5 range (matching Pine Script)
            prediction = max(-5, min(5, prediction * 5))
        else:
            prediction = 0.0
        
        self.prediction_count += 1
        
        return prediction
    
    def _normalize_features(self, features: np.ndarray) -> np.ndarray:
        """Normalize features to 0-1 range"""
        normalized = np.zeros_like(features)
        
        for i, name in enumerate(self.feature_names):
            if i < len(features):
                stats = self.feature_stats[name]
                range_val = stats['max'] - stats['min']
                if range_val > 0:
                    normalized[i] = (features[i] - stats['min']) / range_val
                else:
                    normalized[i] = 0.5
        
        return normalized
    
    def _lorentzian_distance(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Calculate Lorentzian distance between two feature vectors
        
        Args:
            a: First feature vector
            b: Second feature vector
            
        Returns:
            Lorentzian distance
        """
        # Lorentzian distance formula: sum(log(1 + |a_i - b_i|))
        distance = 0.0
        
        for i in range(min(len(a), len(b))):
            diff = abs(a[i] - b[i])
            distance += math.log(1 + diff)
        
        return distance
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Estimate feature importance based on prediction variance
        
        Returns:
            Dictionary of feature -> importance score
        """
        if len(self.feature_history) < 10:
            return {name: 1.0 for name in self.feature_names}
        
        importance = {}
        
        # For each feature, measure how much predictions change when it varies
        for i, feature_name in enumerate(self.feature_names):
            # Get feature values from history
            values = [fs.features.get(feature_name, 0.0) 
                     for fs in self.feature_history]
            
            # Calculate variance
            if values:
                variance = np.var(values)
                importance[feature_name] = variance
            else:
                importance[feature_name] = 0.0
        
        # Normalize to sum to 1
        total = sum(importance.values())
        if total > 0:
            importance = {k: v/total for k, v in importance.items()}
        
        return importance
    
    def get_state(self) -> Dict:
        """Get current state for monitoring"""
        return {
            'features': self.feature_names,
            'n_features': self.n_features,
            'n_neighbors': self.n_neighbors,
            'training_size': len(self.feature_history),
            'predictions_made': self.prediction_count,
            'bar_index': self.bar_index,
            'feature_stats': self.feature_stats
        }
    
    def reset(self):
        """Reset the model"""
        self.feature_history.clear()
        self.label_history.clear()
        self.prediction_count = 0
        self.bar_index = 0
        self.feature_stats = {name: {'min': 0, 'max': 100, 'mean': 50} 
                             for name in self.feature_names}
    
    def is_compatible_with_fixed(self) -> bool:
        """Check if this instance can replace the fixed 5-feature version"""
        expected_features = ['rsi', 'wt', 'cci', 'adx', 'features_4']
        return (self.n_features == 5 and 
                all(f in self.feature_names for f in expected_features[:4]))
    
    def predict_fixed_compatible(self, feature_arrays) -> float:
        """
        Prediction method compatible with fixed k-NN interface
        
        Args:
            feature_arrays: FeatureArrays object from fixed implementation
            
        Returns:
            Prediction value
        """
        # Extract features from fixed arrays
        features = {
            'rsi': feature_arrays.f_array_0[-1] if feature_arrays.f_array_0 else 0,
            'wt': feature_arrays.f_array_1[-1] if feature_arrays.f_array_1 else 0,
            'cci': feature_arrays.f_array_2[-1] if feature_arrays.f_array_2 else 0,
            'adx': feature_arrays.f_array_3[-1] if feature_arrays.f_array_3 else 0,
            'features_4': feature_arrays.f_array_4[-1] if feature_arrays.f_array_4 else 0
        }
        
        return self.predict(features)