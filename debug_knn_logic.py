#!/usr/bin/env python3
"""
Debug k-NN Logic Specifically
=============================

Focus on why neighbors aren't being added to predictions array.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def debug_knn_step_by_step():
    """Step through k-NN logic in detail"""
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=200)
    
    print("="*80)
    print("🔍 k-NN LOGIC DEBUG")
    print("="*80)
    
    # Get data
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("❌ No cached data available")
        return
    
    # Ensure date index
    if 'date' in df.columns:
        df.set_index('date', inplace=True)
    
    # Initialize processor
    config = TradingConfig()
    processor = EnhancedBarProcessor(config, symbol, "5minute")
    
    # Process bars until just after warmup
    target_bar = 2005  # Just after warmup
    
    print(f"Processing {target_bar} bars...")
    
    for i, (idx, row) in enumerate(df.head(target_bar).iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # Log progress every 500 bars
        if i > 0 and i % 500 == 0:
            print(f"   Processed {i} bars...")
    
    # Now do ONE MORE bar with detailed debugging
    print(f"\n🎯 DETAILED DEBUG at bar {target_bar}:")
    
    # Get the next row
    next_row = df.iloc[target_bar]
    
    # Manually check feature calculations
    print("\n📊 FEATURE CHECK:")
    ml = processor.ml_model
    
    # Get current feature values
    from data.data_types import FeatureSeries
    # Get current feature values from the last calculation
    if hasattr(processor, '_last_feature_series'):
        feature_series = processor._last_feature_series
    else:
        # Create a dummy feature series for testing
        feature_series = FeatureSeries(
            f1=50.0,  # RSI typically ranges 0-100
            f2=0.0,   # WT can be negative or positive
            f3=0.0,   # CCI can be negative or positive
            f4=25.0,  # ADX typically ranges 0-100
            f5=50.0   # RSI typically ranges 0-100
        )
    
    print(f"   f1 (RSI_14): {feature_series.f1}")
    print(f"   f2 (WT_10_11): {feature_series.f2}")
    print(f"   f3 (CCI_20_1): {feature_series.f3}")
    print(f"   f4 (ADX_20_2): {feature_series.f4}")
    print(f"   f5 (RSI_9_1): {feature_series.f5}")
    
    # Check for NaN
    features = [feature_series.f1, feature_series.f2, feature_series.f3, 
                feature_series.f4, feature_series.f5]
    nan_count = sum(1 for f in features if pd.isna(f))
    print(f"\n   NaN features: {nan_count}")
    
    # Check feature arrays
    print("\n📈 FEATURE ARRAYS CHECK:")
    fa = processor.feature_arrays
    print(f"   f1 array length: {len(fa.f1)}")
    print(f"   Last 5 f1 values: {fa.f1[-5:] if len(fa.f1) >= 5 else fa.f1}")
    
    # Now manually run the prediction logic
    print("\n🔄 MANUAL k-NN PREDICTION:")
    
    # Check training data
    print(f"   Training data size: {len(ml.y_train_array)}")
    print(f"   Max bars back: {ml.settings.max_bars_back}")
    
    # Calculate size_loop
    size = len(ml.y_train_array) - 1
    size_loop = min(ml.settings.max_bars_back - 1, size) if size > 0 else 0
    print(f"   size: {size}")
    print(f"   size_loop: {size_loop}")
    
    # Test first few distance calculations
    print("\n   Testing first 20 iterations:")
    last_distance = -1.0
    
    for i in range(min(20, size_loop + 1)):
        # Calculate distance
        d = ml.get_lorentzian_distance(
            i, ml.settings.feature_count, feature_series, fa
        )
        
        # Check the condition
        condition1 = d >= last_distance
        condition2 = i % 4 != 0
        both = condition1 and condition2
        
        print(f"   i={i}: d={d:.4f}, last_d={last_distance:.4f}, "
              f"d>=last_d={condition1}, i%4={i%4}, i%4!=0={condition2}, "
              f"PASS={both}")
        
        if both:
            last_distance = d
            print(f"      → Would add neighbor! New last_distance={last_distance:.4f}")
    
    # Process the bar normally to compare
    result = processor.process_bar(
        next_row['open'], next_row['high'], next_row['low'], 
        next_row['close'], next_row['volume']
    )
    
    print(f"\n📊 ACTUAL RESULT:")
    print(f"   ML prediction: {ml.prediction}")
    print(f"   Predictions array size: {len(ml.predictions)}")
    print(f"   Distances array size: {len(ml.distances)}")


if __name__ == "__main__":
    debug_knn_step_by_step()