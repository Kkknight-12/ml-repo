"""
Phase 3 Enhanced Bar Processor
==============================

Integrates all Phase 3 enhancements:
- Enhanced ML model with new features
- Adaptive thresholds
- Mode-aware processing
- Confirmation filters
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from dataclasses import dataclass

from scanner.confirmation_processor import ConfirmationProcessor, ConfirmationResult
from ml.enhanced_lorentzian_wrapper import EnhancedLorentzianWrapper, EnhancedFeatures
from ml.adaptive_threshold import AdaptiveMLThreshold
from config.settings import TradingConfig


@dataclass
class Phase3Result(ConfirmationResult):
    """Extended result with Phase 3 data"""
    adaptive_threshold: float = 3.0
    feature_importance: Dict[str, float] = None
    enhanced_features: EnhancedFeatures = None
    ml_confidence: float = 0.0


class Phase3EnhancedProcessor(ConfirmationProcessor):
    """
    Phase 3 enhanced processor with all improvements
    """
    
    def __init__(self, config: TradingConfig, symbol: str, timeframe: str,
                 use_adaptive_threshold: bool = True,
                 use_enhanced_ml: bool = True,
                 feature_count: int = 8):
        """
        Initialize Phase 3 processor
        
        Args:
            config: Trading configuration
            symbol: Symbol to process
            timeframe: Timeframe
            use_adaptive_threshold: Use adaptive ML thresholds
            use_enhanced_ml: Use enhanced ML model
            feature_count: Number of features for ML
        """
        super().__init__(config, symbol, timeframe)
        
        self.use_adaptive_threshold = use_adaptive_threshold
        self.use_enhanced_ml = use_enhanced_ml
        
        # Replace standard ML with enhanced version
        if use_enhanced_ml:
            self.ml_model = EnhancedLorentzianKNN(
                n_neighbors=config.neighbors_count,
                max_bars_back=3000,  # Larger training window
                feature_count=feature_count,
                prediction_length=config.prediction_length,
                use_dynamic_weights=True
            )
        
        # Add adaptive threshold
        if use_adaptive_threshold:
            self.adaptive_threshold = AdaptiveMLThreshold(
                base_threshold=3.0,
                lookback_periods=100
            )
        else:
            self.adaptive_threshold = None
        
        # Track performance for adaptation
        self.recent_signals = []
        self.performance_buffer = []
        
    def process_bar(self, open_price: float, high: float, low: float, 
                   close: float, volume: float) -> Optional[Phase3Result]:
        """
        Process bar with Phase 3 enhancements
        
        Args:
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Volume
            
        Returns:
            Phase3Result if signal confirmed, None otherwise
        """
        # Update indicators and get base result
        base_result = super().process_bar(open_price, high, low, close, volume)
        
        # Get current timestamp
        timestamp = pd.Timestamp.now()
        
        # If no base signal, still update adaptive threshold
        if self.adaptive_threshold:
            threshold_adj = self.adaptive_threshold.update(
                high, low, close, volume, timestamp
            )
            current_threshold = threshold_adj.final_threshold
        else:
            current_threshold = 3.0
        
        if not base_result:
            return None
        
        # Enhanced ML processing
        if self.use_enhanced_ml and hasattr(self.ml_model, 'update_features'):
            # Get enhanced features
            enhanced_features = self.ml_model.update_features(
                open_price, high, low, close, volume
            )
            
            # Make enhanced prediction
            enhanced_prediction = self.ml_model.predict(enhanced_features)
            
            # Get feature importance
            feature_importance = self.ml_model.get_feature_importance()
            
            # Calculate ML confidence
            ml_confidence = abs(enhanced_prediction) / 5.0  # Normalize to 0-1
        else:
            enhanced_features = None
            enhanced_prediction = base_result.prediction
            feature_importance = {}
            ml_confidence = abs(base_result.prediction) / 5.0
        
        # Apply adaptive threshold
        if abs(enhanced_prediction) < current_threshold:
            return None
        
        # Create Phase 3 result
        result = Phase3Result(
            signal=base_result.signal,
            market_mode=base_result.market_mode,
            prediction=enhanced_prediction,
            confirmed_signal=base_result.confirmed_signal,
            filter_states=base_result.filter_states,
            confirmation_score=base_result.confirmation_score,
            volume_ratio=base_result.volume_ratio,
            momentum_alignment=base_result.momentum_alignment,
            sr_proximity=base_result.sr_proximity,
            # Phase 3 additions
            adaptive_threshold=current_threshold,
            feature_importance=feature_importance,
            enhanced_features=enhanced_features,
            ml_confidence=ml_confidence
        )
        
        # Track signal for performance feedback
        self.recent_signals.append({
            'timestamp': timestamp,
            'result': result,
            'entry_price': close
        })
        
        return result
    
    def update_performance(self, symbol: str, entry_price: float, 
                          exit_price: float, direction: int):
        """
        Update model with trade performance
        
        Args:
            symbol: Symbol traded
            entry_price: Entry price
            exit_price: Exit price  
            direction: Trade direction (1 or -1)
        """
        # Calculate P&L
        pnl = (exit_price - entry_price) / entry_price * direction
        
        # Find corresponding signal
        for signal in self.recent_signals:
            if abs(signal['entry_price'] - entry_price) < 0.01:
                ml_score = signal['result'].prediction
                
                # Update adaptive threshold
                if self.adaptive_threshold:
                    self.adaptive_threshold.record_trade(
                        entry_price, exit_price, direction, ml_score
                    )
                
                # Update ML weights if using enhanced model
                if self.use_enhanced_ml and hasattr(self.ml_model, 'update_weights'):
                    prediction_error = 1.0 if pnl < 0 else 0.0
                    self.ml_model.update_weights(prediction_error)
                
                break
        
        # Store performance
        self.performance_buffer.append({
            'symbol': symbol,
            'pnl': pnl,
            'timestamp': pd.Timestamp.now()
        })
    
    def train_on_historical(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Train enhanced model on historical data
        
        Args:
            data: Historical OHLCV data
            
        Returns:
            Training metrics
        """
        if not self.use_enhanced_ml:
            return {}
        
        print(f"Training enhanced model on {len(data)} bars...")
        
        # Reset model
        self.ml_model.reset()
        
        # Train with validation
        metrics = self.ml_model.train_batch(data, validation_split=0.2)
        
        print(f"Training complete:")
        print(f"  Train accuracy: {metrics['train_accuracy']:.1%}")
        print(f"  Validation accuracy: {metrics['val_accuracy']:.1%}")
        
        return metrics
    
    def get_current_state(self) -> Dict:
        """Get current processor state"""
        state = super().get_current_state()
        
        # Add Phase 3 state
        state.update({
            'adaptive_threshold': self.adaptive_threshold.get_threshold_stats() 
                                if self.adaptive_threshold else {},
            'feature_importance': self.ml_model.get_feature_importance()
                                if self.use_enhanced_ml else {},
            'recent_performance': len(self.performance_buffer),
            'ml_confidence_avg': np.mean([s['result'].ml_confidence 
                                         for s in self.recent_signals[-10:]])
                               if self.recent_signals else 0.0
        })
        
        return state
    
    def optimize_parameters(self, data: pd.DataFrame, 
                          metric: str = 'sharpe') -> Dict:
        """
        Optimize processor parameters on historical data
        
        Args:
            data: Historical data
            metric: Optimization metric
            
        Returns:
            Optimal parameters
        """
        print(f"Optimizing parameters on {len(data)} bars...")
        
        best_params = {}
        best_score = -float('inf')
        
        # Parameter grid
        param_grid = {
            'ml_threshold_base': [2.5, 3.0, 3.5],
            'feature_count': [5, 6, 7, 8],
            'neighbors': [5, 8, 10],
            'use_momentum': [True, False],
            'volume_ratio': [1.1, 1.2, 1.3]
        }
        
        # Grid search (simplified)
        for ml_thresh in param_grid['ml_threshold_base']:
            for features in param_grid['feature_count']:
                for neighbors in param_grid['neighbors']:
                    
                    # Create test processor
                    test_config = TradingConfig(
                        neighbors_count=neighbors,
                        max_bars_back=3000
                    )
                    
                    test_processor = Phase3EnhancedProcessor(
                        test_config, self.symbol, self.timeframe,
                        use_adaptive_threshold=True,
                        use_enhanced_ml=True,
                        feature_count=features
                    )
                    
                    # Set base threshold
                    if test_processor.adaptive_threshold:
                        test_processor.adaptive_threshold.base_threshold = ml_thresh
                    
                    # Run backtest
                    signals = []
                    for _, row in data.iterrows():
                        result = test_processor.process_bar(
                            row['open'], row['high'], row['low'],
                            row['close'], row['volume']
                        )
                        if result:
                            signals.append(result)
                    
                    # Calculate score
                    if len(signals) > 10:
                        # Simple score based on signal count and ML confidence
                        score = len(signals) * np.mean([s.ml_confidence for s in signals])
                        
                        if score > best_score:
                            best_score = score
                            best_params = {
                                'ml_threshold_base': ml_thresh,
                                'feature_count': features,
                                'neighbors': neighbors,
                                'signal_count': len(signals)
                            }
        
        print(f"Optimization complete. Best params: {best_params}")
        return best_params