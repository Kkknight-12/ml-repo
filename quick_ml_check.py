#!/usr/bin/env python3
"""
Quick ML Check for 5-minute data
=================================
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import json

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.fivemin_optimized_settings import FIVEMIN_BALANCED
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def quick_check():
    """Quick check of ML predictions"""
    
    print("🔍 QUICK ML CHECK")
    print("="*60)
    
    # Get MORE data to ensure we have enough for warmup
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months of data
    
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return
    
    print(f"\n📊 Total bars available: {len(df)}")
    print(f"   Warmup period: {FIVEMIN_BALANCED.max_bars_back} bars")
    print(f"   Bars after warmup: {len(df) - FIVEMIN_BALANCED.max_bars_back}")
    
    if len(df) < FIVEMIN_BALANCED.max_bars_back + 100:
        print("\n❌ NOT ENOUGH DATA FOR ML WARMUP!")
        print(f"   Need at least {FIVEMIN_BALANCED.max_bars_back + 100} bars")
        print(f"   Have only {len(df)} bars")
        return
    
    # Create processor
    processor = EnhancedBarProcessor(FIVEMIN_BALANCED, symbol, "5minute")
    
    # Process bars and check when ML starts
    ml_started = False
    first_ml_bar = None
    non_zero_count = 0
    
    print(f"\n🔄 Processing {len(df)} bars...")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # Check when ML predictions start
        if not ml_started and result.prediction != 0:
            ml_started = True
            first_ml_bar = i
            print(f"\n✅ ML predictions started at bar {i}")
            print(f"   First prediction: {result.prediction:.2f}")
        
        # Count non-zero predictions after warmup
        if i >= FIVEMIN_BALANCED.max_bars_back:
            if abs(result.prediction) > 0.01:
                non_zero_count += 1
                if non_zero_count <= 5:  # Show first 5
                    print(f"   Bar {i}: ML = {result.prediction:.2f}, Signal = {result.signal}")
    
    # Summary
    total_predictions = len(df) - FIVEMIN_BALANCED.max_bars_back
    if total_predictions > 0:
        print(f"\n📊 SUMMARY:")
        print(f"   Total bars processed: {len(df)}")
        print(f"   Bars after warmup: {total_predictions}")
        print(f"   Non-zero predictions: {non_zero_count} ({non_zero_count/total_predictions*100:.1f}%)")
        
        if non_zero_count == 0:
            print("\n❌ ALL PREDICTIONS ARE ZERO!")
            print("   This is the ML 0.00 bug we've seen before")
            print("   Check feature array update timing in EnhancedBarProcessor")
    
    # Check ML model state
    print(f"\n🔍 ML Model State:")
    print(f"   Training labels: {len(processor.ml_model.y_train_array)}")
    print(f"   Max neighbors seen: {processor.ml_model.max_neighbors_seen}")
    
    # Check if feature arrays are being populated
    if hasattr(processor, 'feature_arrays'):
        print(f"   Feature array f1 size: {len(processor.feature_arrays.f1)}")
        print(f"   Feature array f2 size: {len(processor.feature_arrays.f2)}")


if __name__ == "__main__":
    quick_check()