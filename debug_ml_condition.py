#!/usr/bin/env python3
"""
Debug ML Condition
==================

Check why predictions aren't being added
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import json

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.fivemin_optimized_settings import FIVEMIN_BALANCED
from data.cache_manager import MarketDataCache
from ml.lorentzian_knn_fixed_corrected import LorentzianKNNFixedCorrected

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def debug_ml_condition():
    """Debug why ML predictions aren't being added"""
    
    print("🔍 DEBUGGING ML CONDITION")
    print("="*80)
    
    # Get data
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return
    
    # Create processor
    processor = EnhancedBarProcessor(FIVEMIN_BALANCED, symbol, "5minute")
    
    # Replace the predict method with a debug version
    ml_model = processor.ml_model
    original_predict = ml_model.predict
    
    def debug_predict(feature_series, feature_arrays, bar_index):
        """Debug version of predict"""
        # Run original first
        result = original_predict(feature_series, feature_arrays, bar_index)
        
        # If this is bar 2000, add extra debugging
        if bar_index == 2000:
            print(f"\n🔍 DETAILED DEBUG FOR BAR 2000:")
            print(f"   Training array size: {len(ml_model.y_train_array)}")
            print(f"   First 10 training labels: {ml_model.y_train_array[:10]}")
            print(f"   Last 10 training labels: {ml_model.y_train_array[-10:]}")
            
            # Manually check the condition for first few iterations
            last_distance = -1.0
            for i in range(10):
                # Get distance
                d = ml_model.get_lorentzian_distance(
                    i, ml_model.settings.feature_count, 
                    feature_series, feature_arrays
                )
                
                print(f"\n   i={i}:")
                print(f"     distance={d:.4f}")
                print(f"     last_distance={last_distance:.4f}")
                print(f"     i%4={i%4}")
                print(f"     d >= last_distance: {d >= last_distance}")
                print(f"     i%4 != 0: {i%4 != 0}")
                print(f"     Condition met: {d >= last_distance and i%4 != 0}")
                
                if d >= last_distance and i % 4 != 0:
                    print(f"     ✅ SHOULD ADD PREDICTION")
                    if i < len(ml_model.y_train_array):
                        label_idx = -(i + 1)
                        label = ml_model.y_train_array[label_idx]
                        print(f"     Training label at index {label_idx}: {label}")
                    else:
                        print(f"     ❌ i ({i}) >= training array size ({len(ml_model.y_train_array)})")
                    last_distance = d
                else:
                    print(f"     ❌ Condition not met")
        
        return result
    
    ml_model.predict = debug_predict
    
    # Process bars up to 2001
    print("\n🔄 Processing bars...")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if i > 2001:
            break
            
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        if i == 2001:
            print(f"\n📍 After bar 2001:")
            print(f"   ML predictions array: {ml_model.predictions}")
            print(f"   ML distances array: {ml_model.distances}")


if __name__ == "__main__":
    debug_ml_condition()