#!/usr/bin/env python3
"""
Focused trace of ML bug at warmup boundary
==========================================
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


def trace_ml_at_boundary():
    """Trace ML behavior right at warmup boundary"""
    
    print("🔍 FOCUSED ML BUG TRACE")
    print("="*80)
    
    # Get data
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # More data
    
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return
    
    print(f"\n📊 Total bars: {len(df)}")
    print(f"   Warmup period: {FIVEMIN_BALANCED.max_bars_back} bars")
    
    # Create processor
    processor = EnhancedBarProcessor(FIVEMIN_BALANCED, symbol, "5minute")
    
    # Hook into ML model's predict method
    ml_model = processor.ml_model
    
    # Track calls
    predict_calls = []
    
    original_predict = ml_model.predict
    
    def trace_predict(feature_series, feature_arrays, bar_index):
        """Trace predict calls"""
        call_info = {
            'bar_index': bar_index,
            'current_f1': feature_series.f1,
            'array_size': len(feature_arrays.f1),
            'last_f1': feature_arrays.f1[-1] if feature_arrays.f1 else None
        }
        predict_calls.append(call_info)
        
        # Call original
        return original_predict(feature_series, feature_arrays, bar_index)
    
    ml_model.predict = trace_predict
    
    # Process bars focusing on warmup boundary
    print("\n🔄 Processing bars around warmup boundary...")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        # Focus on bars around 2000
        if i < 1995:
            # Fast forward
            processor.process_bar(row['open'], row['high'], row['low'], row['close'], row['volume'])
            continue
        
        if i > 2010:
            break
        
        print(f"\n📍 Bar {i}:")
        
        # Check feature arrays BEFORE processing
        print(f"   Feature arrays before: f1 size = {len(processor.feature_arrays.f1)}")
        
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # Check after
        print(f"   Feature arrays after: f1 size = {len(processor.feature_arrays.f1)}")
        print(f"   ML Prediction: {result.prediction:.2f}")
        print(f"   Training labels: {len(processor.ml_model.y_train_array)}")
        
        if i >= 2000 and abs(result.prediction) < 0.01:
            print("   ⚠️ ML PREDICTION IS ZERO AFTER WARMUP!")
    
    # Analyze predict calls
    print("\n📊 ML PREDICT CALLS:")
    for call in predict_calls[-10:]:  # Last 10 calls
        print(f"\nBar {call['bar_index']}:")
        print(f"   Current f1: {call['current_f1']:.4f}")
        print(f"   Array size: {call['array_size']}")
        print(f"   Last f1 in array: {call['last_f1']:.4f if call['last_f1'] else 'None'}")
        if call['last_f1'] and abs(call['current_f1'] - call['last_f1']) < 0.0001:
            print("   ⚠️ CURRENT F1 MATCHES LAST F1 - COMPARING WITH SELF!")
    
    # Check k-NN logic
    print("\n🔍 CHECKING K-NN LOGIC:")
    if len(processor.feature_arrays.f1) > 2000:
        # Simulate a prediction
        from data.data_types import FeatureSeries
        test_features = FeatureSeries(
            f1=50.0, f2=0.0, f3=100.0, f4=25.0, f5=60.0
        )
        
        # Check what happens
        print("\n   Testing with dummy features...")
        print(f"   Test features: f1={test_features.f1}")
        
        # Get some distances
        for i in range(min(5, len(processor.feature_arrays.f1))):
            dist = abs(test_features.f1 - processor.feature_arrays.f1[-(i+1)])
            print(f"   Distance to f1[{-(i+1)}]: {dist:.4f}")


if __name__ == "__main__":
    trace_ml_at_boundary()