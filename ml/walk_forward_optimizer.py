"""
Walk-Forward Optimizer for ML Model
===================================

Implements rolling window optimization to adapt ML parameters to changing market conditions.
This helps prevent overfitting and ensures the model stays relevant as markets evolve.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import pickle
import os

# Import needed config classes
from config.phase2_optimized_settings import Phase2OptimizedConfig
from config.settings import TradingConfig
from config.adaptive_config import create_adaptive_config

logger = logging.getLogger(__name__)


@dataclass
class OptimizationWindow:
    """Represents a single optimization window"""
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    window_id: int
    
    @property
    def train_size(self) -> int:
        """Number of days in training period"""
        return (self.train_end - self.train_start).days
    
    @property
    def test_size(self) -> int:
        """Number of days in test period"""
        return (self.test_end - self.test_start).days


@dataclass
class OptimizationResult:
    """Results from optimizing a single window"""
    window_id: int
    best_params: Dict
    train_score: float
    test_score: float
    train_trades: int
    test_trades: int
    parameter_stability: float  # How similar to previous window


class WalkForwardOptimizer:
    """
    Implements walk-forward analysis for ML parameter optimization
    """
    
    def __init__(self, 
                 train_days: int = 60,
                 test_days: int = 20,
                 step_days: int = 10,
                 min_trades: int = 20):
        """
        Initialize walk-forward optimizer
        
        Args:
            train_days: Days for training window
            test_days: Days for testing window
            step_days: Days to step forward each iteration
            min_trades: Minimum trades required in window
        """
        self.train_days = train_days
        self.test_days = test_days
        self.step_days = step_days
        self.min_trades = min_trades
        
        # Parameter search space
        self.param_space = {
            'ml_threshold': [2.5, 3.0, 3.5, 4.0],
            'neighbors_count': [3, 5, 8, 10],
            'max_bars_back': [2000, 2500, 3000],
            'use_volume_weight': [True, False],
            'feature_weights': [
                [1.0, 1.0, 1.0, 1.0, 1.0],  # Equal weights
                [2.0, 1.0, 1.0, 1.0, 1.0],  # RSI emphasis
                [1.0, 2.0, 1.0, 1.0, 1.0],  # WT emphasis
                [1.0, 1.0, 2.0, 1.0, 1.0],  # CCI emphasis
            ]
        }
        
        # Cache for optimization results
        self.cache_dir = "optimization_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def create_windows(self, data: pd.DataFrame) -> List[OptimizationWindow]:
        """
        Create rolling optimization windows
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            List of optimization windows
        """
        windows = []
        
        # Ensure data is sorted by date
        data = data.sort_index()
        
        # Get date range
        start_date = data.index[0]
        end_date = data.index[-1]
        
        # Create windows
        window_id = 0
        current_date = start_date + timedelta(days=self.train_days)
        
        while current_date + timedelta(days=self.test_days) <= end_date:
            window = OptimizationWindow(
                train_start=current_date - timedelta(days=self.train_days),
                train_end=current_date,
                test_start=current_date,
                test_end=current_date + timedelta(days=self.test_days),
                window_id=window_id
            )
            windows.append(window)
            
            # Step forward
            current_date += timedelta(days=self.step_days)
            window_id += 1
            
        logger.info(f"Created {len(windows)} optimization windows")
        return windows
    
    def optimize_window(self, 
                       data: pd.DataFrame,
                       window: OptimizationWindow,
                       processor_class,
                       symbol: str,
                       data_manager) -> OptimizationResult:
        """
        Optimize parameters for a single window
        
        Args:
            data: Full dataset
            window: Optimization window
            processor_class: Bar processor class to use
            symbol: Symbol being optimized
            data_manager: Data manager for adaptive config
            
        Returns:
            Optimization result
        """
        # Split data
        train_data = data[window.train_start:window.train_end]
        test_data = data[window.test_start:window.test_end]
        
        # Track results
        best_score = -float('inf')
        best_params = {}
        
        # Grid search over parameter space
        for ml_threshold in self.param_space['ml_threshold']:
            for neighbors in self.param_space['neighbors_count']:
                for max_bars in self.param_space['max_bars_back']:
                    for use_volume in self.param_space['use_volume_weight']:
                        for weights in self.param_space['feature_weights']:
                            
                            # Create Phase2OptimizedConfig
                            phase2_config = Phase2OptimizedConfig(ml_threshold=ml_threshold)
                            
                            # Get adaptive config
                            stats = data_manager.analyze_price_movement(train_data)
                            adaptive_config = create_adaptive_config(symbol, '5minute', stats)
                            
                            # Create TradingConfig with optimized parameters
                            trading_config = TradingConfig(
                                source=adaptive_config.source,
                                neighbors_count=neighbors,
                                max_bars_back=max_bars,
                                feature_count=adaptive_config.feature_count,
                                features=adaptive_config.features
                            )
                            
                            # Run backtest on training data
                            train_score, train_trades = self._run_backtest(
                                train_data, processor_class, trading_config, 
                                phase2_config, symbol
                            )
                            
                            # Skip if not enough trades
                            if train_trades < self.min_trades:
                                continue
                                
                            # Update best if improved
                            if train_score > best_score:
                                best_score = train_score
                                best_params = {
                                    'ml_threshold': ml_threshold,
                                    'neighbors_count': neighbors,
                                    'max_bars_back': max_bars,
                                    'use_volume_weight': use_volume,
                                    'feature_weights': weights
                                }
        
        # Test best parameters on out-of-sample data
        if best_params:
            # Re-create configs with best params
            phase2_config = Phase2OptimizedConfig(ml_threshold=best_params['ml_threshold'])
            stats = data_manager.analyze_price_movement(test_data)
            adaptive_config = create_adaptive_config(symbol, '5minute', stats)
            
            trading_config = TradingConfig(
                source=adaptive_config.source,
                neighbors_count=best_params['neighbors_count'],
                max_bars_back=best_params['max_bars_back'],
                feature_count=adaptive_config.feature_count,
                features=adaptive_config.features
            )
            
            test_score, test_trades = self._run_backtest(
                test_data, processor_class, trading_config, 
                phase2_config, symbol
            )
        else:
            test_score, test_trades = 0.0, 0
            
        # Calculate parameter stability (simplified for now)
        stability = 1.0  # Will implement comparison with previous window
        
        return OptimizationResult(
            window_id=window.window_id,
            best_params=best_params,
            train_score=best_score,
            test_score=test_score,
            train_trades=train_trades,
            test_trades=test_trades,
            parameter_stability=stability
        )
    
    def _run_backtest(self, 
                     data: pd.DataFrame,
                     processor_class,
                     trading_config: TradingConfig,
                     phase2_config: Phase2OptimizedConfig,
                     symbol: str) -> Tuple[float, int]:
        """
        Run backtest and return score and trade count
        
        Args:
            data: Data to backtest on
            processor_class: Processor class
            trading_config: Trading configuration
            phase2_config: Phase 2 configuration
            symbol: Symbol being tested
            
        Returns:
            (score, trade_count)
        """
        # This is a simplified version - would integrate with existing backtest
        processor = processor_class(trading_config, symbol=symbol, timeframe="5minute")
        
        signals = []
        trades = []
        
        # Process bars
        for idx, row in data.iterrows():
            result = processor.process_bar(
                open_price=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume']
            )
            
            if result and hasattr(result, 'confirmed_signal') and result.confirmed_signal != 0:
                # Check ML threshold
                if abs(result.prediction) >= phase2_config.ml_threshold:
                    signals.append({
                        'timestamp': idx,
                        'signal': result.confirmed_signal,
                        'price': row['close']
                    })
        
        # Simple P&L calculation (would use SmartExitManager in real version)
        for i, signal in enumerate(signals):
            if i < len(signals) - 1:
                entry_price = signal['price']
                exit_price = signals[i + 1]['price']
                
                if signal['signal'] > 0:  # Long
                    pnl = (exit_price - entry_price) / entry_price
                else:  # Short
                    pnl = (entry_price - exit_price) / entry_price
                    
                trades.append(pnl)
        
        # Calculate score (Sharpe ratio approximation)
        if trades:
            avg_return = np.mean(trades)
            std_return = np.std(trades)
            score = avg_return / std_return if std_return > 0 else avg_return
        else:
            score = 0.0
            
        return score, len(trades)
    
    def run_optimization(self,
                        data: pd.DataFrame,
                        processor_class,
                        symbol: str,
                        data_manager,
                        parallel: bool = True) -> List[OptimizationResult]:
        """
        Run full walk-forward optimization
        
        Args:
            data: Full dataset
            processor_class: Processor class to optimize
            symbol: Symbol being optimized
            data_manager: Data manager for adaptive config
            parallel: Whether to run windows in parallel
            
        Returns:
            List of optimization results
        """
        # Create windows
        windows = self.create_windows(data)
        
        if not windows:
            logger.warning("No optimization windows created")
            return []
            
        results = []
        
        if parallel:
            # Run windows in parallel
            with ProcessPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(
                        self.optimize_window, 
                        data, 
                        window, 
                        processor_class,
                        symbol,
                        data_manager
                    ): window 
                    for window in windows
                }
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                        logger.info(f"Completed window {result.window_id}: "
                                  f"Train={result.train_score:.3f}, "
                                  f"Test={result.test_score:.3f}")
                    except Exception as e:
                        logger.error(f"Error in window optimization: {e}")
        else:
            # Run sequentially
            for window in windows:
                result = self.optimize_window(
                    data, window, processor_class, symbol, data_manager
                )
                results.append(result)
                logger.info(f"Completed window {result.window_id}: "
                          f"Train={result.train_score:.3f}, "
                          f"Test={result.test_score:.3f}")
        
        # Sort by window ID
        results.sort(key=lambda x: x.window_id)
        
        # Save results
        self._save_results(results)
        
        return results
    
    def analyze_results(self, results: List[OptimizationResult]) -> Dict:
        """
        Analyze optimization results
        
        Args:
            results: List of optimization results
            
        Returns:
            Analysis dictionary
        """
        if not results:
            return {}
            
        # Extract scores
        train_scores = [r.train_score for r in results]
        test_scores = [r.test_score for r in results]
        
        # Calculate statistics
        analysis = {
            'num_windows': len(results),
            'avg_train_score': np.mean(train_scores),
            'avg_test_score': np.mean(test_scores),
            'train_test_correlation': np.corrcoef(train_scores, test_scores)[0, 1],
            'parameter_stability': np.mean([r.parameter_stability for r in results]),
            'best_window': max(results, key=lambda x: x.test_score).window_id,
            'worst_window': min(results, key=lambda x: x.test_score).window_id,
            
            # Parameter frequency analysis
            'most_common_params': self._get_most_common_params(results),
            
            # Performance over time
            'performance_trend': self._calculate_trend(test_scores),
            
            # Overfitting analysis
            'overfitting_ratio': np.mean([
                (r.train_score - r.test_score) / r.train_score 
                for r in results if r.train_score > 0
            ])
        }
        
        return analysis
    
    def _get_most_common_params(self, 
                               results: List[OptimizationResult]) -> Dict:
        """Get most commonly selected parameters"""
        param_counts = {}
        
        for result in results:
            for param, value in result.best_params.items():
                if param not in param_counts:
                    param_counts[param] = {}
                    
                value_str = str(value)
                param_counts[param][value_str] = param_counts[param].get(value_str, 0) + 1
        
        # Get most common value for each parameter
        most_common = {}
        for param, counts in param_counts.items():
            if counts:
                most_common[param] = max(counts, key=counts.get)
                
        return most_common
    
    def _calculate_trend(self, scores: List[float]) -> str:
        """Calculate performance trend"""
        if len(scores) < 2:
            return "insufficient_data"
            
        # Simple linear regression
        x = np.arange(len(scores))
        slope = np.polyfit(x, scores, 1)[0]
        
        if slope > 0.01:
            return "improving"
        elif slope < -0.01:
            return "deteriorating"
        else:
            return "stable"
    
    def _save_results(self, results: List[OptimizationResult]):
        """Save optimization results to cache"""
        filepath = os.path.join(
            self.cache_dir, 
            f"walk_forward_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        )
        
        with open(filepath, 'wb') as f:
            pickle.dump(results, f)
            
        logger.info(f"Saved optimization results to {filepath}")
    
    def get_adaptive_params(self, 
                           results: List[OptimizationResult],
                           current_date: pd.Timestamp) -> Dict:
        """
        Get adaptive parameters for current date based on optimization results
        
        Args:
            results: Historical optimization results
            current_date: Current date
            
        Returns:
            Recommended parameters
        """
        # Find most recent window
        recent_results = [
            r for r in results 
            if r.test_score > 0  # Only successful windows
        ]
        
        if not recent_results:
            # Return defaults
            return {
                'ml_threshold': 3.0,
                'neighbors_count': 8,
                'max_bars_back': 2000
            }
            
        # Weight recent windows more heavily
        weights = np.exp(-0.1 * np.arange(len(recent_results)))[::-1]
        weights /= weights.sum()
        
        # Weighted average of parameters (simplified)
        weighted_params = {}
        
        for param in ['ml_threshold', 'neighbors_count', 'max_bars_back']:
            values = []
            for i, result in enumerate(recent_results):
                if param in result.best_params:
                    values.append((result.best_params[param], weights[i]))
                    
            if values:
                # Weighted average
                weighted_sum = sum(v * w for v, w in values)
                weight_sum = sum(w for _, w in values)
                weighted_params[param] = weighted_sum / weight_sum
                
        return weighted_params