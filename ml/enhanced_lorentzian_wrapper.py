"""
Enhanced Lorentzian Wrapper
===========================

Wraps the existing Lorentzian k-NN with Phase 3 enhancements
without modifying the core implementation.
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass

# Import original components
from ml.lorentzian_knn_fixed_corrected import LorentzianKNNFixedCorrected
from data.data_types import Settings, Label, FeatureArrays
from config.constants import FeatureCount

# Import new indicators
from indicators.advanced.fisher_transform import FisherTransform
from indicators.advanced.volume_weighted_momentum import VolumeWeightedMomentum
from indicators.advanced.market_internals import MarketInternals
from ml.adaptive_threshold import AdaptiveMLThreshold


@dataclass
class EnhancedFeatures:
    """Container for enhanced features"""
    # Original features (will be filled by base model)
    rsi: float = 0.0
    wt: float = 0.0
    cci: float = 0.0
    adx: float = 0.0
    # Phase 3 features
    fisher: float = 0.0
    vwm: float = 0.0
    order_flow: float = 0.0
    volume_trend: float = 0.0
    buying_pressure: float = 0.0


class EnhancedLorentzianWrapper:
    """
    Wrapper that adds Phase 3 features to existing Lorentzian k-NN
    """
    
    def __init__(self, settings: Settings, label: Label):
        """Initialize wrapper with base model and enhancements"""
        # Create base model
        self.base_model = LorentzianKNNFixedCorrected(settings, label)
        self.settings = settings
        self.label = label
        
        # Phase 3 indicators
        self.fisher = FisherTransform(period=10)
        self.vwm = VolumeWeightedMomentum(momentum_period=14)
        self.internals = MarketInternals(profile_period=20)
        
        # Adaptive threshold
        self.adaptive_threshold = AdaptiveMLThreshold(base_threshold=3.0)
        
        # Enhanced features storage
        self.enhanced_features = EnhancedFeatures()
        
        # Feature weights for enhanced prediction
        self.feature_weights = {
            'base': 1.0,      # Weight for base prediction
            'fisher': 0.3,    # Additional weight for Fisher
            'vwm': 0.2,       # Additional weight for VWM
            'internals': 0.1  # Additional weight for internals
        }
        
    def process_features(self, feature_arrays: FeatureArrays, 
                        open_price: float, high: float, low: float,
                        close: float, volume: float) -> float:
        """
        Process features and return enhanced prediction
        
        Args:
            feature_arrays: Feature arrays from base processor
            open_price: Open price
            high: High price  
            low: Low price
            close: Close price
            volume: Volume
            
        Returns:
            Enhanced prediction value
        """
        # Get base prediction
        base_prediction = self.base_model.get_lorentzian_prediction(
            feature_arrays, self.settings, self.label
        )
        
        # Update Phase 3 indicators
        fisher_val, fisher_trigger = self.fisher.update(high, low)
        vwm_data = self.vwm.update(close, volume)
        internal_data = self.internals.update(open_price, high, low, close, volume)
        
        # Store enhanced features
        self.enhanced_features.fisher = fisher_val
        self.enhanced_features.vwm = vwm_data['vwm']
        self.enhanced_features.order_flow = internal_data['order_flow_imbalance']
        self.enhanced_features.volume_trend = internal_data['volume_trend']
        self.enhanced_features.buying_pressure = internal_data['buying_pressure']
        
        # Calculate enhanced prediction
        enhanced_prediction = self._calculate_enhanced_prediction(
            base_prediction, fisher_val, vwm_data, internal_data
        )
        
        # Update adaptive threshold
        threshold_adj = self.adaptive_threshold.update(
            high, low, close, volume, pd.Timestamp.now()
        )
        
        # Apply adaptive threshold
        if abs(enhanced_prediction) < threshold_adj.final_threshold:
            return 0.0
            
        return enhanced_prediction
    
    def _calculate_enhanced_prediction(self, base_prediction: float,
                                     fisher: float, vwm_data: Dict,
                                     internal_data: Dict) -> float:
        """
        Combine base prediction with Phase 3 features
        
        Args:
            base_prediction: Prediction from base model
            fisher: Fisher Transform value
            vwm_data: Volume-weighted momentum data
            internal_data: Market internals data
            
        Returns:
            Enhanced prediction
        """
        # Start with base prediction
        enhanced = base_prediction * self.feature_weights['base']
        
        # Add Fisher contribution
        if abs(fisher) > 1.5:  # Strong Fisher signal
            fisher_contrib = np.sign(fisher) * min(abs(fisher), 3.0)
            enhanced += fisher_contrib * self.feature_weights['fisher']
        
        # Add VWM contribution
        if abs(vwm_data['vwm']) > 0.5:  # Strong momentum
            vwm_contrib = np.sign(vwm_data['vwm']) * vwm_data['divergence']
            enhanced += vwm_contrib * self.feature_weights['vwm']
        
        # Add market internals contribution
        order_flow = internal_data['order_flow_imbalance']
        if abs(order_flow) > 0.5:  # Strong order flow
            enhanced += order_flow * self.feature_weights['internals']
        
        return enhanced
    
    def get_enhanced_features(self) -> EnhancedFeatures:
        """Get current enhanced features"""
        return self.enhanced_features
    
    def get_adaptive_threshold(self) -> float:
        """Get current adaptive threshold"""
        stats = self.adaptive_threshold.get_threshold_stats()
        return stats.get('current', 3.0)
    
    def update_feature_weights(self, performance_feedback: float):
        """
        Update feature weights based on performance
        
        Args:
            performance_feedback: Recent performance metric (-1 to 1)
        """
        # Simple adaptive weight update
        if performance_feedback > 0:
            # Good performance - increase Phase 3 weights slightly
            self.feature_weights['fisher'] = min(0.5, self.feature_weights['fisher'] * 1.02)
            self.feature_weights['vwm'] = min(0.4, self.feature_weights['vwm'] * 1.02)
        else:
            # Poor performance - decrease Phase 3 weights slightly
            self.feature_weights['fisher'] = max(0.1, self.feature_weights['fisher'] * 0.98)
            self.feature_weights['vwm'] = max(0.1, self.feature_weights['vwm'] * 0.98)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        return {
            'Base Model': self.feature_weights['base'],
            'Fisher Transform': self.feature_weights['fisher'],
            'Volume Momentum': self.feature_weights['vwm'],
            'Market Internals': self.feature_weights['internals'],
            'Current Threshold': self.get_adaptive_threshold()
        }
    
    def reset(self):
        """Reset all components"""
        self.base_model = LorentzianKNNFixedCorrected(self.settings, self.label)
        self.fisher.reset()
        self.vwm.reset()
        self.internals.reset()
        self.enhanced_features = EnhancedFeatures()


# Import for adaptive threshold
import pandas as pd