#!/usr/bin/env python3
"""
Trace ML 0.00 Bug in EnhancedBarProcessor
=========================================

Deep dive into why ML predictions are returning 0.00
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


def trace_ml_bug():
    """Trace through ML prediction process"""
    
    print("🔍 TRACING ML 0.00 BUG")
    print("="*80)
    
    # Get minimal data
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return
    
    print(f"\n📊 Processing {len(df)} bars")
    
    # Create processor with debug mode
    processor = EnhancedBarProcessor(FIVEMIN_BALANCED, symbol, "5minute", debug_mode=True)
    
    # Add debug hook to ML model
    ml_model = processor.ml_model
    original_predict = ml_model.predict
    
    def debug_predict(feature_series, feature_arrays, bar_index):
        """Debug wrapper for predict"""
        print(f"\n🔍 ML PREDICT CALLED - Bar {bar_index}")
        print(f"   Current features: f1={feature_series.f1:.2f}, f2={feature_series.f2:.2f}")
        
        # Check feature arrays BEFORE prediction
        if len(feature_arrays.f1) > 0:
            print(f"   Feature arrays size: {len(feature_arrays.f1)}")
            print(f"   Last f1 in array: {feature_arrays.f1[-1]:.2f}")
            print(f"   Comparing current f1 ({feature_series.f1:.2f}) with last f1 ({feature_arrays.f1[-1]:.2f})")
            
            if abs(feature_series.f1 - feature_arrays.f1[-1]) < 0.0001:
                print("   ⚠️ WARNING: Current f1 matches last f1 in array!")
                print("   This means we're comparing features with themselves!")
        
        # Call original predict
        result = original_predict(feature_series, feature_arrays, bar_index)
        
        print(f"   Prediction result: {ml_model.prediction:.2f}")
        print(f"   Training labels: {len(ml_model.y_train_array)}")
        
        return result
    
    # Replace predict method
    ml_model.predict = debug_predict
    
    # Process first 2010 bars to get past warmup
    print("\n🔄 Processing bars...")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if i > 2010:  # Just after warmup
            break
            
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # Extra logging around warmup transition
        if i == 1999:
            print("\n📍 APPROACHING WARMUP END (bar 1999)")
        elif i == 2000:
            print("\n📍 AT WARMUP BOUNDARY (bar 2000) - ML SHOULD START")
        elif i == 2001:
            print("\n📍 AFTER WARMUP (bar 2001) - ML SHOULD BE ACTIVE")
    
    # Check final state
    print("\n📊 FINAL STATE:")
    print(f"   Feature arrays f1 size: {len(processor.feature_arrays.f1)}")
    print(f"   Feature arrays f2 size: {len(processor.feature_arrays.f2)}")
    print(f"   Training labels: {len(processor.ml_model.y_train_array)}")
    print(f"   Last prediction: {processor.ml_model.prediction:.2f}")
    
    # Check the order in process_bar
    print("\n📋 CHECKING PROCESS_BAR ORDER:")
    with open('scanner/enhanced_bar_processor.py', 'r') as f:
        lines = f.readlines()
        
    in_process_bar = False
    line_num = 0
    
    for i, line in enumerate(lines):
        if 'def process_bar' in line:
            in_process_bar = True
            line_num = i + 1
        elif in_process_bar and 'def ' in line:
            break
        elif in_process_bar:
            if 'ml_model.predict' in line:
                print(f"   Line {i+1}: ML prediction call")
            elif '_update_feature_arrays' in line:
                print(f"   Line {i+1}: Feature array update")
            elif 'feature_series = self._calculate_features' in line:
                print(f"   Line {i+1}: Feature calculation")
    
    print("\n💡 ANALYSIS:")
    print("The issue is that ML predictions happen AFTER warmup (bar 2000+)")
    print("But we need to check if features are being compared correctly")


if __name__ == "__main__":
    trace_ml_bug()