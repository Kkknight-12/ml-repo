"""
Enhanced Lorentzian k-NN with Phase 3 Features
==============================================

Extends the original Lorentzian k-NN with:
1. Additional technical indicators (Fisher, VWM, Market Internals)
2. Feature weighting optimization
3. Larger training window
4. Better validation
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import deque
from dataclasses import dataclass
import pandas as pd

# Import original k-NN
from ml.lorentzian_knn_fixed_corrected import LorentzianKNN, FeatureSet

# Import new indicators
from indicators.advanced.fisher_transform import FisherTransform
from indicators.advanced.volume_weighted_momentum import VolumeWeightedMomentum
from indicators.advanced.market_internals import MarketInternals


@dataclass
class EnhancedFeatureSet(FeatureSet):
    """Extended feature set with Phase 3 indicators"""
    # Original features
    rsi: float = 0.0
    wt: float = 0.0
    cci: float = 0.0
    adx: float = 0.0
    # New Phase 3 features
    fisher: float = 0.0
    vwm: float = 0.0
    order_flow: float = 0.0
    volume_trend: float = 0.0
    buying_pressure: float = 0.0
    
    def to_array(self, feature_indices: List[int] = None) -> np.ndarray:
        """Convert to numpy array with selected features"""
        all_features = [
            self.rsi, self.wt, self.cci, self.adx,  # Original
            self.fisher, self.vwm, self.order_flow,  # New
            self.volume_trend, self.buying_pressure
        ]
        
        if feature_indices:
            return np.array([all_features[i] for i in feature_indices])
        return np.array(all_features)


class EnhancedLorentzianKNN(LorentzianKNN):
    """
    Enhanced k-NN classifier with Phase 3 improvements
    """
    
    def __init__(self, 
                 n_neighbors: int = 8,
                 max_bars_back: int = 3000,  # Increased from 2000
                 feature_count: int = 8,      # Increased from 5
                 prediction_length: int = 5,
                 use_dynamic_weights: bool = True):
        """
        Initialize enhanced k-NN
        
        Args:
            n_neighbors: Number of neighbors
            max_bars_back: Maximum lookback (increased for more data)
            feature_count: Number of features to use
            prediction_length: Bars ahead to predict
            use_dynamic_weights: Whether to use dynamic feature weights
        """
        # Initialize base class with original settings
        super().__init__(n_neighbors, max_bars_back, 5, prediction_length)
        
        # Override with enhanced settings
        self.feature_count = feature_count
        self.use_dynamic_weights = use_dynamic_weights
        
        # Phase 3 indicators
        self.fisher = FisherTransform(period=10)
        self.vwm = VolumeWeightedMomentum(momentum_period=14)
        self.internals = MarketInternals(profile_period=20)
        
        # Feature selection and weights
        self.selected_features = self._select_best_features()
        self.feature_weights = np.ones(self.feature_count)
        
        # Enhanced training data
        self.feature_history = deque(maxlen=max_bars_back)
        self.label_history = deque(maxlen=max_bars_back)
        
        # Performance tracking for weight optimization
        self.prediction_accuracy = deque(maxlen=100)
        
    def _select_best_features(self) -> List[int]:
        """Select best features based on feature count"""
        # Feature indices:
        # 0: RSI, 1: WT, 2: CCI, 3: ADX (original)
        # 4: Fisher, 5: VWM, 6: Order Flow (new)
        # 7: Volume Trend, 8: Buying Pressure
        
        if self.feature_count <= 5:
            # Use original features
            return list(range(5))
        elif self.feature_count == 6:
            # Add Fisher
            return [0, 1, 2, 3, 4, 5]
        elif self.feature_count == 7:
            # Add Order Flow
            return [0, 1, 2, 3, 4, 5, 6]
        else:
            # Use all features
            return list(range(min(self.feature_count, 9)))
    
    def update_features(self, open_price: float, high: float, low: float, 
                       close: float, volume: float) -> EnhancedFeatureSet:
        """
        Update all features including Phase 3 indicators
        
        Args:
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Volume
            
        Returns:
            Enhanced feature set
        """
        # Update base features
        base_features = super().update_features(open_price, high, low, close, volume)
        
        # Update Phase 3 indicators
        fisher_val, _ = self.fisher.update(high, low)
        vwm_data = self.vwm.update(close, volume)
        internal_data = self.internals.update(open_price, high, low, close, volume)
        
        # Create enhanced feature set
        enhanced = EnhancedFeatureSet(
            rsi=base_features.rsi,
            wt=base_features.wt,
            cci=base_features.cci,
            adx=base_features.adx,
            fisher=fisher_val,
            vwm=vwm_data['vwm'],
            order_flow=internal_data['order_flow_imbalance'],
            volume_trend=internal_data['volume_trend'],
            buying_pressure=internal_data['buying_pressure']
        )
        
        return enhanced
    
    def predict(self, features: EnhancedFeatureSet) -> float:
        """
        Make prediction with enhanced features
        
        Args:
            features: Enhanced feature set
            
        Returns:
            Prediction value
        """
        if len(self.feature_history) < self.n_neighbors:
            return 0.0
        
        # Convert to selected features only
        current_features = features.to_array(self.selected_features)
        
        # Apply dynamic weights if enabled
        if self.use_dynamic_weights:
            current_features *= self.feature_weights
        
        # Calculate distances to all historical points
        distances = []
        for i, hist_features in enumerate(self.feature_history):
            hist_array = hist_features.to_array(self.selected_features)
            if self.use_dynamic_weights:
                hist_array *= self.feature_weights
            
            # Lorentzian distance
            dist = np.sum(np.log(1 + np.abs(current_features - hist_array)))
            distances.append((dist, self.label_history[i]))
        
        # Sort by distance and get k nearest
        distances.sort(key=lambda x: x[0])
        k_nearest = distances[:self.n_neighbors]
        
        # Weighted average of neighbor labels
        if k_nearest:
            weights = [1 / (1 + d[0]) for d in k_nearest]
            labels = [d[1] for d in k_nearest]
            prediction = np.average(labels, weights=weights)
        else:
            prediction = 0.0
        
        return prediction
    
    def update_weights(self, prediction_error: float):
        """
        Update feature weights based on prediction error
        
        Args:
            prediction_error: Error from last prediction
        """
        if not self.use_dynamic_weights:
            return
        
        # Simple gradient-based weight update
        learning_rate = 0.01
        
        # Increase weights for features that correlate with correct predictions
        if abs(prediction_error) < 0.5:  # Good prediction
            self.feature_weights *= (1 + learning_rate)
        else:  # Poor prediction
            self.feature_weights *= (1 - learning_rate * 0.5)
        
        # Normalize weights
        self.feature_weights = np.clip(self.feature_weights, 0.5, 2.0)
        self.feature_weights /= np.mean(self.feature_weights)
    
    def train_batch(self, data: pd.DataFrame, 
                   validation_split: float = 0.2) -> Dict[str, float]:
        """
        Enhanced batch training with validation
        
        Args:
            data: DataFrame with OHLCV data
            validation_split: Fraction for validation
            
        Returns:
            Training metrics
        """
        # Split data
        split_idx = int(len(data) * (1 - validation_split))
        train_data = data.iloc[:split_idx]
        val_data = data.iloc[split_idx:]
        
        # Reset model
        self.reset()
        
        # Training phase
        train_predictions = []
        train_actuals = []
        
        for idx, row in train_data.iterrows():
            # Update features
            features = self.update_features(
                row['open'], row['high'], row['low'], 
                row['close'], row['volume']
            )
            
            # Make prediction
            prediction = self.predict(features)
            train_predictions.append(prediction)
            
            # Calculate actual direction (for next prediction_length bars)
            if idx + self.prediction_length < len(train_data):
                future_idx = idx + self.prediction_length
                actual = 1 if train_data.iloc[future_idx]['close'] > row['close'] else -1
                train_actuals.append(actual)
                
                # Update training data
                self.feature_history.append(features)
                self.label_history.append(actual)
                
                # Update weights if using dynamic weights
                if len(train_predictions) > self.prediction_length:
                    error = abs(prediction - train_actuals[-self.prediction_length-1])
                    self.update_weights(error)
        
        # Validation phase
        val_predictions = []
        val_actuals = []
        
        for idx, row in val_data.iterrows():
            features = self.update_features(
                row['open'], row['high'], row['low'], 
                row['close'], row['volume']
            )
            
            prediction = self.predict(features)
            val_predictions.append(prediction)
            
            if idx + self.prediction_length < len(data):
                future_idx = idx + self.prediction_length
                actual = 1 if data.iloc[future_idx]['close'] > row['close'] else -1
                val_actuals.append(actual)
        
        # Calculate metrics
        train_accuracy = self._calculate_accuracy(train_predictions, train_actuals)
        val_accuracy = self._calculate_accuracy(val_predictions, val_actuals)
        
        return {
            'train_accuracy': train_accuracy,
            'val_accuracy': val_accuracy,
            'train_size': len(train_actuals),
            'val_size': len(val_actuals),
            'feature_weights': self.feature_weights.tolist()
        }
    
    def _calculate_accuracy(self, predictions: List[float], 
                           actuals: List[float]) -> float:
        """Calculate prediction accuracy"""
        if not predictions or not actuals:
            return 0.0
        
        correct = sum(
            1 for p, a in zip(predictions, actuals) 
            if (p > 0 and a > 0) or (p < 0 and a < 0)
        )
        
        return correct / len(actuals)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        feature_names = [
            'RSI', 'WT', 'CCI', 'ADX',
            'Fisher', 'VWM', 'OrderFlow',
            'VolumeTrend', 'BuyingPressure'
        ]
        
        importance = {}
        for i, idx in enumerate(self.selected_features):
            if idx < len(feature_names):
                weight = self.feature_weights[i] if i < len(self.feature_weights) else 1.0
                importance[feature_names[idx]] = weight
        
        return importance
    
    def reset(self):
        """Reset model state"""
        super().reset()
        self.feature_history.clear()
        self.label_history.clear()
        self.prediction_accuracy.clear()
        self.feature_weights = np.ones(self.feature_count)
        
        # Reset indicators
        self.fisher.reset()
        self.vwm.reset()
        self.internals.reset()