#!/usr/bin/env python3
"""
Debug ML Configuration Issues
=============================

Simple test to see why ML-optimized config isn't working
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import json

from backtest_framework_enhanced import EnhancedBacktestEngine
from config.settings import TradingConfig
from config.ml_optimized_settings import MLOptimizedTradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from scanner.enhanced_bar_processor_ml_optimized import MLOptimizedBarProcessor
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def test_ml_threshold_impact():
    """Test the impact of ML threshold on trade generation"""
    
    print("="*80)
    print("🔍 DEBUGGING ML THRESHOLD IMPACT")
    print("="*80)
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)  # Shorter period for debugging
    
    # Get data
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return
    
    print(f"\nData: {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    
    # Test different thresholds
    thresholds = [0, 1, 2, 3, 4, 5]
    
    for threshold in thresholds:
        print(f"\n{'='*60}")
        print(f"Testing ML Threshold = {threshold}")
        print('='*60)
        
        # Create config with specific threshold
        config = TradingConfig()
        config.ml_prediction_threshold = threshold
        config.use_dynamic_exits = True
        
        # Track statistics
        ml_predictions = []
        signals_generated = 0
        entries_generated = 0
        ml_blocked = 0
        
        # Create processor
        if threshold > 0:
            processor = MLOptimizedBarProcessor(config, symbol, "5minute")
        else:
            processor = EnhancedBarProcessor(config, symbol, "5minute")
        
        # Process bars
        for i, (idx, row) in enumerate(df.iterrows()):
            result = processor.process_bar(
                row['open'], row['high'], row['low'], 
                row['close'], row['volume']
            )
            
            # After warmup
            if i >= config.max_bars_back:
                ml_predictions.append(result.prediction)
                
                if result.signal != 0:
                    signals_generated += 1
                    
                    # Check if ML threshold would block
                    if threshold > 0 and abs(result.prediction) < threshold:
                        ml_blocked += 1
                
                if result.start_long_trade or result.start_short_trade:
                    entries_generated += 1
        
        # Analyze ML predictions
        if ml_predictions:
            import numpy as np
            pred_array = np.array(ml_predictions)
            non_zero = sum(1 for p in ml_predictions if abs(p) >= 0.1)
            above_threshold = sum(1 for p in ml_predictions if abs(p) >= threshold)
            
            print(f"\nML Prediction Analysis:")
            print(f"  Total predictions: {len(ml_predictions)}")
            print(f"  Non-zero predictions: {non_zero} ({non_zero/len(ml_predictions)*100:.1f}%)")
            print(f"  Above threshold ({threshold}): {above_threshold} ({above_threshold/len(ml_predictions)*100:.1f}%)")
            print(f"  Prediction range: [{pred_array.min():.1f}, {pred_array.max():.1f}]")
            print(f"  Average |prediction|: {np.abs(pred_array).mean():.2f}")
            
            print(f"\nSignal/Entry Analysis:")
            print(f"  ML signals generated: {signals_generated}")
            print(f"  Entries generated: {entries_generated}")
            if threshold > 0:
                print(f"  Blocked by threshold: {ml_blocked}")
                print(f"  Expected entries: ~{signals_generated - ml_blocked}")


def test_config_differences():
    """Test why configs generate different trade counts"""
    
    print("\n" + "="*80)
    print("🔍 TESTING CONFIG DIFFERENCES")
    print("="*80)
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    engine = EnhancedBacktestEngine()
    
    configs = [
        ("Baseline", TradingConfig()),
        ("ML-Optimized (No Threshold)", create_ml_config_no_threshold()),
        ("ML-Optimized (Threshold=3)", MLOptimizedTradingConfig())
    ]
    
    for name, config in configs:
        print(f"\n{name}:")
        print(f"  ML Threshold: {getattr(config, 'ml_prediction_threshold', 0)}")
        print(f"  Volatility Filter: {config.use_volatility_filter}")
        print(f"  Regime Filter: {config.use_regime_filter}")
        print(f"  Kernel Filter: {config.use_kernel_filter}")
        
        try:
            metrics = engine.run_backtest(
                symbol, start_date, end_date, config
            )
            print(f"  Result: {metrics.total_trades} trades, {metrics.win_rate:.1f}% win rate")
        except Exception as e:
            print(f"  Error: {e}")


def create_ml_config_no_threshold():
    """Create ML config without threshold for comparison"""
    config = MLOptimizedTradingConfig()
    config.ml_prediction_threshold = 0  # Disable threshold
    return config


if __name__ == "__main__":
    test_ml_threshold_impact()
    test_config_differences()