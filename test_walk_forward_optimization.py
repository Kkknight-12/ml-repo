"""
Test Walk-Forward Optimization
==============================

Tests the walk-forward optimizer with Phase 2 complete system.
This will help us find adaptive parameters that improve performance.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from ml.walk_forward_optimizer import WalkForwardOptimizer
from data.smart_data_manager import SmartDataManager
from scanner.confirmation_processor import ConfirmationProcessor
from config.phase2_optimized_settings import Phase2OptimizedConfig


def test_walk_forward_single_symbol(symbol: str = 'RELIANCE', days: int = 180):
    """Test walk-forward optimization on single symbol"""
    
    print(f"\n{'='*60}")
    print(f"WALK-FORWARD OPTIMIZATION TEST - {symbol}")
    print(f"{'='*60}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=days)
    
    if df is None or len(df) < 5000:
        print(f"⚠️  Insufficient data: {len(df) if df is not None else 0} bars")
        return None
    
    print(f"\nData loaded: {len(df)} bars ({days} days)")
    
    # Create optimizer
    optimizer = WalkForwardOptimizer(
        train_days=60,
        test_days=20,
        step_days=10,
        min_trades=10
    )
    
    # Show parameter search space
    print("\nParameter Search Space:")
    for param, values in optimizer.param_space.items():
        if param != 'feature_weights':
            print(f"  {param}: {values}")
        else:
            print(f"  {param}: {len(values)} variations")
    
    # Create windows
    windows = optimizer.create_windows(df)
    print(f"\nCreated {len(windows)} optimization windows")
    
    if windows:
        print("\nWindow Examples:")
        for i in [0, len(windows)//2, -1]:
            if 0 <= i < len(windows):
                w = windows[i]
                print(f"  Window {w.window_id}: Train {w.train_size}d, Test {w.test_size}d")
    
    # Run optimization (sequential for testing)
    print("\nRunning optimization (this may take a while)...")
    results = optimizer.run_optimization(
        df, 
        ConfirmationProcessor,
        Phase2OptimizedConfig,
        parallel=False  # Sequential for debugging
    )
    
    # Analyze results
    if results:
        analysis = optimizer.analyze_results(results)
        
        print(f"\n{'='*50}")
        print("OPTIMIZATION RESULTS")
        print(f"{'='*50}")
        
        print(f"\nPerformance Summary:")
        print(f"  Windows analyzed: {analysis['num_windows']}")
        print(f"  Avg train score: {analysis['avg_train_score']:.3f}")
        print(f"  Avg test score: {analysis['avg_test_score']:.3f}")
        print(f"  Train/test correlation: {analysis['train_test_correlation']:.3f}")
        print(f"  Overfitting ratio: {analysis['overfitting_ratio']:.1%}")
        print(f"  Performance trend: {analysis['performance_trend']}")
        
        print(f"\nMost Common Parameters:")
        for param, value in analysis['most_common_params'].items():
            print(f"  {param}: {value}")
        
        # Get adaptive params for today
        current_params = optimizer.get_adaptive_params(results, pd.Timestamp.now())
        print(f"\nRecommended Parameters (current):")
        for param, value in current_params.items():
            print(f"  {param}: {value}")
    
    return results


def test_parameter_stability(results):
    """Analyze parameter stability across windows"""
    
    if not results:
        return
    
    print(f"\n{'='*50}")
    print("PARAMETER STABILITY ANALYSIS")
    print(f"{'='*50}")
    
    # Track parameter changes
    param_history = {
        'ml_threshold': [],
        'neighbors_count': [],
        'max_bars_back': []
    }
    
    for result in results:
        for param in param_history:
            if param in result.best_params:
                param_history[param].append(result.best_params[param])
    
    # Calculate stability metrics
    for param, values in param_history.items():
        if len(values) > 1:
            changes = [abs(values[i] - values[i-1]) for i in range(1, len(values))]
            avg_change = np.mean(changes) if changes else 0
            stability = 1 - (avg_change / (max(values) - min(values) + 0.001))
            
            print(f"\n{param}:")
            print(f"  Range: {min(values)} - {max(values)}")
            print(f"  Avg change: {avg_change:.3f}")
            print(f"  Stability: {stability:.1%}")


def create_optimization_config():
    """Create configuration for walk-forward optimization"""
    
    config = {
        'optimization_params': {
            'train_days': 60,
            'test_days': 20,
            'step_days': 10,
            'min_trades': 10
        },
        'search_space': {
            'ml_threshold': [2.0, 2.5, 3.0, 3.5, 4.0],
            'neighbors_count': [3, 5, 8, 10, 12],
            'max_bars_back': [1500, 2000, 2500, 3000],
            'volume_ratio': [1.1, 1.2, 1.3, 1.5],
            'mode_confidence': [0.2, 0.3, 0.4, 0.5]
        },
        'scoring_metric': 'sharpe_ratio',  # or 'win_rate', 'expectancy', 'profit_factor'
        'min_sample_size': 20
    }
    
    return config


def main():
    """Run walk-forward optimization tests"""
    
    print("\n" + "="*60)
    print("WALK-FORWARD OPTIMIZATION TEST")
    print("="*60)
    print("\nThis test will:")
    print("1. Create rolling train/test windows")
    print("2. Optimize parameters on each window")
    print("3. Test on out-of-sample data")
    print("4. Recommend adaptive parameters")
    
    # Test on single symbol
    results = test_walk_forward_single_symbol('RELIANCE', days=180)
    
    # Analyze stability
    if results:
        test_parameter_stability(results)
    
    # Show optimization config
    config = create_optimization_config()
    print(f"\n{'='*50}")
    print("RECOMMENDED OPTIMIZATION CONFIG")
    print(f"{'='*50}")
    print("\nFor production use, expand search space:")
    for category, params in config.items():
        print(f"\n{category}:")
        for key, value in params.items():
            print(f"  {key}: {value}")
    
    print(f"\n{'='*60}")
    print("WALK-FORWARD OPTIMIZATION COMPLETE")
    print(f"{'='*60}")
    print("\nNext Steps:")
    print("1. Implement parallel processing for faster optimization")
    print("2. Add more sophisticated scoring metrics")
    print("3. Test on multiple symbols")
    print("4. Integrate with live trading for adaptive parameters")


if __name__ == "__main__":
    main()