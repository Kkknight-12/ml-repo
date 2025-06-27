"""
Flexible Bar Processor with Phase 3 Integration
==============================================

Bar processor that supports both original and flexible ML systems
with easy rollback capability.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from dataclasses import dataclass
import logging

from scanner.enhanced_bar_processor import EnhancedBarProcessor, BarResult
from ml.flexible_lorentzian_knn import FlexibleLorentzianKNN, FlexibleFeatureSet
from indicators.advanced.fisher_transform import FisherTransform
from indicators.advanced.volume_weighted_momentum import VolumeWeightedMomentum
from indicators.advanced.market_internals import MarketInternals
from config.settings import TradingConfig
from config.constants import PREDICTION_LENGTH

logger = logging.getLogger(__name__)


@dataclass
class FlexibleBarResult(BarResult):
    """Extended result with flexible ML data"""
    flexible_prediction: float = 0.0
    feature_values: Dict[str, float] = None
    feature_importance: Dict[str, float] = None
    ml_system_used: str = "original"  # "original" or "flexible"


class FlexibleBarProcessor(EnhancedBarProcessor):
    """
    Bar processor with flexible ML support and Phase 3 features
    """
    
    def __init__(self, config: TradingConfig, symbol: str, timeframe: str,
                 use_flexible_ml: bool = False,
                 feature_config: Dict = None):
        """
        Initialize flexible processor
        
        Args:
            config: Trading configuration
            symbol: Symbol to process
            timeframe: Timeframe
            use_flexible_ml: Whether to use flexible ML system
            feature_config: Configuration for features
        """
        super().__init__(config, symbol, timeframe)
        
        self.use_flexible_ml = use_flexible_ml
        self.feature_config = feature_config or self._get_default_feature_config()
        
        # Phase 3 indicators
        self.fisher = FisherTransform(period=10)
        self.vwm = VolumeWeightedMomentum(momentum_period=14)
        self.internals = MarketInternals(profile_period=20)
        
        # Initialize flexible ML if enabled
        if self.use_flexible_ml:
            self._init_flexible_ml()
        
        # Performance comparison
        self.prediction_comparison = []
        
        logger.info(f"Initialized FlexibleBarProcessor with flexible_ml={use_flexible_ml}")
    
    def _get_default_feature_config(self) -> Dict:
        """Get default feature configuration"""
        return {
            'original_features': ['rsi', 'wt', 'cci', 'adx', 'features_4'],
            'phase3_features': ['fisher', 'vwm', 'order_flow', 'volume_trend', 'buying_pressure'],
            'use_phase3': True,
            'feature_weights': None  # Will be learned
        }
    
    def _init_flexible_ml(self):
        """Initialize flexible ML system"""
        # Determine which features to use
        features = self.feature_config['original_features'].copy()
        
        if self.feature_config.get('use_phase3', False):
            # Add Phase 3 features
            features.extend(self.feature_config['phase3_features'])
        
        # Create flexible ML
        self.flexible_ml = FlexibleLorentzianKNN(
            feature_names=features,
            n_neighbors=self.config.neighbors_count,
            max_bars_back=self.config.max_bars_back,
            prediction_length=PREDICTION_LENGTH  # From constants.py (4 bars)
        )
        
        logger.info(f"Initialized flexible ML with {len(features)} features: {features}")
    
    def process_bar(self, open_price: float, high: float, low: float, 
                   close: float, volume: float) -> Optional[FlexibleBarResult]:
        """
        Process bar with flexible ML support
        
        Args:
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Volume
            
        Returns:
            FlexibleBarResult if signal generated
        """
        # Get base result from parent
        base_result = super().process_bar(open_price, high, low, close, volume)
        
        # Update Phase 3 indicators
        fisher_val, fisher_trigger = self.fisher.update(high, low)
        vwm_data = self.vwm.update(close, volume)
        internal_data = self.internals.update(open_price, high, low, close, volume)
        
        # Collect all features
        # Get the current values from feature arrays (most recent values)
        all_features = {
            # Original features from feature arrays
            'rsi': self.feature_arrays.f1[-1] if self.feature_arrays.f1 else 50.0,
            'wt': self.feature_arrays.f2[-1] if self.feature_arrays.f2 else 0.0,
            'cci': self.feature_arrays.f3[-1] if self.feature_arrays.f3 else 0.0,
            'adx': self.feature_arrays.f4[-1] if self.feature_arrays.f4 else 0.0,
            'features_4': self.feature_arrays.f5[-1] if self.feature_arrays.f5 else 0.0,  # f5 is the 5th feature
            # Phase 3 features
            'fisher': fisher_val,
            'vwm': vwm_data['vwm'],
            'order_flow': internal_data['order_flow_imbalance'],
            'volume_trend': internal_data['volume_trend'],
            'buying_pressure': internal_data['buying_pressure']
        }
        
        # Make predictions
        if self.use_flexible_ml and hasattr(self, 'flexible_ml'):
            # Use flexible ML
            flexible_prediction = self.flexible_ml.predict(all_features)
            feature_importance = self.flexible_ml.get_feature_importance()
            ml_system = "flexible"
            
            # Update flexible ML training data if we have a signal
            if base_result and abs(base_result.prediction) > 0:
                feature_set = self.flexible_ml.update_features(all_features)
                # Add to training after prediction_length bars
                # (This would be done properly with future price data)
        else:
            # Use original prediction
            flexible_prediction = base_result.prediction if base_result else 0.0
            feature_importance = {}
            ml_system = "original"
        
        # Compare predictions if both available
        if base_result and self.use_flexible_ml:
            self.prediction_comparison.append({
                'bar': self.bars_processed,
                'original': base_result.prediction,
                'flexible': flexible_prediction,
                'difference': abs(base_result.prediction - flexible_prediction)
            })
            
            # Log significant differences
            if abs(base_result.prediction - flexible_prediction) > 2.0:
                logger.info(f"Prediction divergence: Original={base_result.prediction:.2f}, "
                          f"Flexible={flexible_prediction:.2f}")
        
        # Create result
        if base_result or (self.use_flexible_ml and abs(flexible_prediction) >= self.config.neighbors_count):
            # Determine which prediction to use for signal
            final_prediction = flexible_prediction if self.use_flexible_ml else (
                base_result.prediction if base_result else 0.0
            )
            
            # Determine signal
            if abs(final_prediction) >= self.config.neighbors_count:
                signal = 1 if final_prediction > 0 else -1
            else:
                signal = base_result.signal if base_result else 0
            
            return FlexibleBarResult(
                # Required BarResult fields
                bar_index=self.bars_processed,
                open=open_price,
                high=high,
                low=low,
                close=close,
                prediction=final_prediction,
                signal=signal,
                start_long_trade=base_result.start_long_trade if base_result else False,
                start_short_trade=base_result.start_short_trade if base_result else False,
                end_long_trade=base_result.end_long_trade if base_result else False,
                end_short_trade=base_result.end_short_trade if base_result else False,
                filter_states=base_result.filter_states if base_result else {},
                is_early_signal_flip=base_result.is_early_signal_flip if base_result else False,
                prediction_strength=abs(final_prediction) / self.config.neighbors_count,
                stop_loss=base_result.stop_loss if base_result else None,
                take_profit=base_result.take_profit if base_result else None,
                # Extended fields
                flexible_prediction=flexible_prediction,
                feature_values=all_features.copy(),
                feature_importance=feature_importance,
                ml_system_used=ml_system
            )
        
        return None
    
    def get_comparison_stats(self) -> Dict:
        """Get statistics comparing original vs flexible predictions"""
        if not self.prediction_comparison:
            return {}
        
        differences = [p['difference'] for p in self.prediction_comparison]
        
        return {
            'comparisons': len(self.prediction_comparison),
            'avg_difference': np.mean(differences),
            'max_difference': np.max(differences),
            'correlation': np.corrcoef(
                [p['original'] for p in self.prediction_comparison],
                [p['flexible'] for p in self.prediction_comparison]
            )[0, 1] if len(self.prediction_comparison) > 1 else 0.0
        }
    
    def switch_ml_system(self, use_flexible: bool):
        """Switch between original and flexible ML systems"""
        self.use_flexible_ml = use_flexible
        
        if use_flexible and not hasattr(self, 'flexible_ml'):
            self._init_flexible_ml()
        
        logger.info(f"Switched to {'flexible' if use_flexible else 'original'} ML system")
    
    def get_state(self) -> Dict:
        """Get processor state including flexible ML info"""
        state = super().get_state()
        
        state.update({
            'ml_system': 'flexible' if self.use_flexible_ml else 'original',
            'flexible_ml_state': self.flexible_ml.get_state() if hasattr(self, 'flexible_ml') else None,
            'comparison_stats': self.get_comparison_stats(),
            'phase3_features': {
                'fisher': self.fisher.fisher,
                'vwm': self.vwm.vwm,
                'order_flow': self.internals.order_flow_imbalance if hasattr(self.internals, 'order_flow_imbalance') else 0
            }
        })
        
        return state