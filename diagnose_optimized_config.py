#!/usr/bin/env python3
"""
Diagnose OptimizedTradingConfig Issues
======================================

Find out why OptimizedTradingConfig only generates 2 trades.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import json

from scanner.enhanced_bar_processor import EnhancedBarProcessor, BarResult
from config.settings import TradingConfig
from config.fixed_optimized_settings import FixedOptimizedTradingConfig
from data.cache_manager import MarketDataCache
import pandas as pd

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def diagnose_optimized_config():
    """Step through processing to find where signals are blocked"""
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print("="*80)
    print("🔍 OPTIMIZEDTRADINGCONFIG DIAGNOSTIC")
    print("="*80)
    
    # Get data
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No cached data available")
        return
    
    print(f"Data points: {len(df)}")
    
    # Test configurations
    standard_config = TradingConfig()
    standard_config.use_dynamic_exits = True
    
    optimized_config = FixedOptimizedTradingConfig()
    # Apply the same filter disabling as in test_multi_target_exits.py
    optimized_config.use_ema_filter = False
    optimized_config.use_sma_filter = False
    optimized_config.use_adx_filter = False
    optimized_config.regime_threshold = -0.1
    
    # Initialize processors
    standard_processor = EnhancedBarProcessor(standard_config, symbol, "5minute")
    optimized_processor = EnhancedBarProcessor(optimized_config, symbol, "5minute")
    
    # Track signals
    standard_entries = []
    optimized_entries = []
    
    # Process bars
    bars_processed = 0
    for idx, row in df.iterrows():
        bars_processed += 1
        
        # Process with both configs
        std_result = standard_processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        opt_result = optimized_processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # Skip warmup
        if bars_processed < 2000:
            continue
        
        # Track entry signals
        if std_result and (std_result.start_long_trade or std_result.start_short_trade):
            standard_entries.append({
                'bar': bars_processed,
                'date': idx,
                'signal': 'LONG' if std_result.start_long_trade else 'SHORT',
                'ml_pred': std_result.prediction,
                'filters': std_result.filter_states
            })
        
        if opt_result and (opt_result.start_long_trade or opt_result.start_short_trade):
            optimized_entries.append({
                'bar': bars_processed,
                'date': idx,
                'signal': 'LONG' if opt_result.start_long_trade else 'SHORT',
                'ml_pred': opt_result.prediction,
                'filters': opt_result.filter_states
            })
        
        # Log first divergence
        if len(standard_entries) > len(optimized_entries) and len(optimized_entries) == 0:
            print(f"\n⚠️ FIRST DIVERGENCE at bar {bars_processed}:")
            print(f"Standard generated entry signal but Optimized didn't")
            print(f"\nStandard config:")
            print(f"  ML Prediction: {std_result.prediction:.2f}")
            print(f"  Signal: {std_result.signal}")
            print(f"  Filters: {std_result.filter_states}")
            print(f"  Entry signal: {'LONG' if std_result.start_long_trade else 'SHORT' if std_result.start_short_trade else 'NONE'}")
            
            print(f"\nOptimized config:")
            print(f"  ML Prediction: {opt_result.prediction:.2f}")
            print(f"  Signal: {opt_result.signal}")
            print(f"  Filters: {opt_result.filter_states}")
            print(f"  Entry signal: {'LONG' if opt_result.start_long_trade else 'SHORT' if opt_result.start_short_trade else 'NONE'}")
            
            # Check what's different
            print(f"\n🔍 DIFFERENCES:")
            if std_result.prediction != opt_result.prediction:
                print(f"  ML Prediction differs: {std_result.prediction:.2f} vs {opt_result.prediction:.2f}")
            
            if std_result.signal != opt_result.signal:
                print(f"  Signal differs: {std_result.signal} vs {opt_result.signal}")
            
            # Check filter differences
            for filter_name in std_result.filter_states:
                if std_result.filter_states.get(filter_name) != opt_result.filter_states.get(filter_name):
                    print(f"  Filter '{filter_name}' differs: {std_result.filter_states.get(filter_name)} vs {opt_result.filter_states.get(filter_name)}")
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"Standard config: {len(standard_entries)} entry signals")
    print(f"Optimized config: {len(optimized_entries)} entry signals")
    print(f"Difference: {len(standard_entries) - len(optimized_entries)} signals")
    
    # Show all optimized entries
    if optimized_entries:
        print(f"\n🎯 OPTIMIZED CONFIG ENTRIES:")
        for i, entry in enumerate(optimized_entries):
            print(f"{i+1}. Bar {entry['bar']} ({entry['date']}): {entry['signal']} (ML pred: {entry['ml_pred']:.2f})")
    
    # Analyze ML predictions
    print(f"\n🧠 ML PREDICTION ANALYSIS:")
    
    # Check if ML model is generating different predictions
    ml_differences = 0
    signal_differences = 0
    filter_differences = 0
    
    sample_bars = 0
    for idx, row in df.iterrows():
        sample_bars += 1
        if sample_bars < 2000 or sample_bars > 2100:  # Sample 100 bars after warmup
            continue
        
        std_result = standard_processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        opt_result = optimized_processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        if std_result.prediction != opt_result.prediction:
            ml_differences += 1
        
        if std_result.signal != opt_result.signal:
            signal_differences += 1
        
        if std_result.filter_all != opt_result.filter_all:
            filter_differences += 1
    
    print(f"In 100 sample bars after warmup:")
    print(f"  ML predictions differ: {ml_differences} times")
    print(f"  Signals differ: {signal_differences} times")
    print(f"  Filter results differ: {filter_differences} times")
    
    # Check feature differences
    print(f"\n📈 FEATURE COMPARISON:")
    print(f"Standard features:")
    for k, v in standard_config.features.items():
        print(f"  {k}: {v}")
    
    print(f"\nOptimized features:")
    for k, v in optimized_config.features.items():
        std_feat = standard_config.features[k]
        if v != std_feat:
            print(f"  {k}: {v} ⚠️ (was {std_feat})")
        else:
            print(f"  {k}: {v}")
    
    # Check other key differences
    print(f"\n⚙️ KEY PARAMETER DIFFERENCES:")
    print(f"Neighbors count: {standard_config.neighbors_count} → {optimized_config.neighbors_count}")
    print(f"Kernel smoothing: {standard_config.use_kernel_smoothing} → {optimized_config.use_kernel_smoothing}")
    print(f"Kernel lookback: {standard_config.kernel_lookback} → {optimized_config.kernel_lookback}")


if __name__ == "__main__":
    diagnose_optimized_config()