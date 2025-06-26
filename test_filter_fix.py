#!/usr/bin/env python3
"""
Test Filter Fix
===============

Quick test to see if disabling ADX filter improves results.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.fixed_optimized_settings import FixedOptimizedTradingConfig
from data.cache_manager import MarketDataCache


def test_filter_fix():
    """Test if filter fix improves ML predictions"""
    
    symbol = "RELIANCE"
    config = FixedOptimizedTradingConfig()
    
    # Get recent data
    cache = MarketDataCache()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    if df is None or df.empty:
        print("❌ No cached data available")
        return
    
    # Ensure date index
    if 'date' in df.columns:
        df.set_index('date', inplace=True)
    
    print("="*60)
    print("🔍 FILTER FIX TEST")
    print("="*60)
    print(f"Symbol: {symbol}")
    print(f"Total bars: {len(df)}")
    print(f"ADX filter: {config.use_adx_filter} (should be False)")
    print()
    
    # Initialize processor
    processor = EnhancedBarProcessor(config, symbol, "5minute")
    
    # Track results
    ml_predictions = []
    filter_all_count = 0
    entry_signals = 0
    
    # Process last 500 bars after warmup
    start_idx = max(0, len(df) - 2500)  # Ensure we have warmup
    
    print(f"Processing {len(df) - start_idx} bars...")
    
    for i, (idx, row) in enumerate(df.iloc[start_idx:].iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        if result and i >= config.max_bars_back:
            # Track ML predictions
            if result.prediction != 0.0:
                ml_predictions.append(result.prediction)
            
            # Track filter effectiveness
            if result.filter_all:
                filter_all_count += 1
            
            # Track entry signals
            if result.start_long_trade or result.start_short_trade:
                entry_signals += 1
                print(f"  Entry signal at bar {i}: {'LONG' if result.start_long_trade else 'SHORT'}")
    
    # Results
    total_bars_analyzed = len(df) - start_idx - config.max_bars_back
    
    print(f"\n📊 RESULTS:")
    print(f"Bars analyzed (after warmup): {total_bars_analyzed}")
    print(f"Non-zero ML predictions: {len(ml_predictions)} "
          f"({len(ml_predictions)/max(total_bars_analyzed, 1)*100:.1f}%)")
    print(f"All filters passed: {filter_all_count} times "
          f"({filter_all_count/max(total_bars_analyzed, 1)*100:.1f}%)")
    print(f"Entry signals generated: {entry_signals}")
    
    if ml_predictions:
        print(f"\nML Prediction range: [{min(ml_predictions):.0f}, {max(ml_predictions):.0f}]")
        print(f"Average ML prediction: {sum(ml_predictions)/len(ml_predictions):.2f}")
    
    # Diagnosis
    print(f"\n💡 DIAGNOSIS:")
    if len(ml_predictions) == 0:
        print("❌ Still no ML predictions - feature array fix may not be working")
    elif len(ml_predictions) < 10:
        print("⚠️ Very few ML predictions - k-NN may be too restrictive")
    else:
        print("✅ ML predictions are being generated!")
    
    if entry_signals == 0:
        print("❌ No entry signals - filters may still be too restrictive")
    else:
        print(f"✅ {entry_signals} entry signals generated")


if __name__ == "__main__":
    test_filter_fix()