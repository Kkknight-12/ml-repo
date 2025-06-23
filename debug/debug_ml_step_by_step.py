#!/usr/bin/env python3
"""
Deep ML Debug - Why Still Zero Predictions?
==========================================
This script debugs the ML algorithm step by step
"""

import pandas as pd
import sys
import os
import math
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import TradingConfig
from data.data_types import Settings, Label, FeatureArrays, FeatureSeries
from ml.lorentzian_knn import LorentzianKNN

def manual_ml_debug():
    """Manually step through ML algorithm to find issue"""
    
    print("=" * 80)
    print("🔬 DEEP ML ALGORITHM DEBUG")
    print("=" * 80)
    
    # Load data
    data_file = "../pinescript_style_ICICIBANK_2000bars.csv"
    if not os.path.exists(data_file):
        data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    
    df = pd.read_csv(data_file)
    print(f"\n✅ Loaded {len(df)} bars")
    
    # Create minimal settings
    settings = Settings(
        source='close',
        neighbors_count=8,
        max_bars_back=100,  # Small for testing
        feature_count=2,    # Just 2 features
        color_compression=1,
        show_exits=False,
        use_dynamic_exits=False
    )
    
    label = Label()
    
    # Initialize ML model
    ml = LorentzianKNN(settings, label)
    
    # Build some training data manually
    print("\n1. BUILDING TRAINING DATA:")
    for i in range(50):
        if i >= 4:
            current = df.iloc[i]['close']
            past = df.iloc[i-4]['close']
            
            if past < current:
                ml.y_train_array.append(label.short)  # -1
            elif past > current:
                ml.y_train_array.append(label.long)   # 1
            else:
                ml.y_train_array.append(label.neutral) # 0
    
    print(f"   Training labels: {len(ml.y_train_array)}")
    print(f"   Label distribution: {ml.y_train_array[:10]}")
    
    # Build feature arrays (simple test values)
    print("\n2. BUILDING FEATURE ARRAYS:")
    feature_arrays = FeatureArrays()
    
    # Add 50 feature values (normalized 0-1)
    for i in range(50):
        # Simple normalized values
        f1_val = 0.5 + 0.3 * math.sin(i * 0.1)  # Oscillating
        f2_val = 0.5 + 0.2 * math.cos(i * 0.1)  # Oscillating
        
        feature_arrays.f1.append(f1_val)
        feature_arrays.f2.append(f2_val)
    
    print(f"   Feature array lengths: F1={len(feature_arrays.f1)}, F2={len(feature_arrays.f2)}")
    print(f"   F1 first 5: {[f'{x:.3f}' for x in feature_arrays.f1[:5]]}")
    print(f"   F2 first 5: {[f'{x:.3f}' for x in feature_arrays.f2[:5]]}")
    
    # Current features
    current_f1 = 0.6
    current_f2 = 0.7
    feature_series = FeatureSeries(f1=current_f1, f2=current_f2, f3=0, f4=0, f5=0)
    
    print(f"\n3. CURRENT FEATURES:")
    print(f"   F1: {current_f1}")
    print(f"   F2: {current_f2}")
    
    # Now manually run the ML prediction algorithm
    print("\n4. RUNNING ML PREDICTION ALGORITHM:")
    
    # Reset
    last_distance = -1.0
    predictions = []
    distances = []
    
    # Calculate loop size
    size = min(settings.max_bars_back - 1, len(ml.y_train_array) - 1)
    size_loop = min(settings.max_bars_back - 1, size)
    
    print(f"   Loop size: {size_loop}")
    
    # Bar index check (simulate bar 100)
    bar_index = 100
    max_bars_back_index = 0  # For this test
    
    print(f"   Bar index: {bar_index}")
    print(f"   Max bars back index: {max_bars_back_index}")
    print(f"   Will process: {bar_index >= max_bars_back_index}")
    
    print("\n5. NEIGHBOR SEARCH:")
    neighbors_found = 0
    
    for i in range(size_loop + 1):
        # Calculate distance manually
        d = 0.0
        
        # Feature 1 distance
        if i < len(feature_arrays.f1):
            hist_f1 = feature_arrays.f1[i]
            d += math.log(1 + abs(current_f1 - hist_f1))
        
        # Feature 2 distance
        if i < len(feature_arrays.f2):
            hist_f2 = feature_arrays.f2[i]
            d += math.log(1 + abs(current_f2 - hist_f2))
        
        # Check conditions
        passes_distance = d >= last_distance
        passes_modulo = i % 4 != 0  # Pine Script: i%4 (non-zero)
        
        if i < 10:  # Show first 10
            print(f"   i={i}: d={d:.4f}, last_d={last_distance:.4f}, "
                  f"pass_dist={passes_distance}, pass_mod={passes_modulo}, "
                  f"i%4={i%4}")
        
        # Pine Script logic
        if passes_distance and passes_modulo:
            neighbors_found += 1
            last_distance = d
            distances.append(d)
            
            # Get label
            if i < len(ml.y_train_array):
                label_val = ml.y_train_array[i]
                predictions.append(float(label_val))
                
                if neighbors_found <= 5:
                    print(f"   ✓ Neighbor {neighbors_found}: i={i}, d={d:.4f}, label={label_val}")
            
            # Maintain k neighbors
            if len(predictions) > settings.neighbors_count:
                # Update last_distance to 75th percentile
                k_75 = int(settings.neighbors_count * 3 / 4)
                if k_75 < len(distances):
                    last_distance = distances[k_75]
                    print(f"   📊 Updated last_distance to 75th percentile: {last_distance:.4f}")
                
                distances.pop(0)
                predictions.pop(0)
    
    print(f"\n6. RESULTS:")
    print(f"   Total neighbors found: {neighbors_found}")
    print(f"   Final predictions list: {predictions}")
    print(f"   Sum of predictions: {sum(predictions) if predictions else 0}")
    
    # Analysis
    print("\n7. ANALYSIS:")
    if len(predictions) == 0:
        print("   ❌ NO NEIGHBORS FOUND!")
        print("   Possible issues:")
        print("   - Initial last_distance = -1.0 should always be exceeded")
        print("   - Check if modulo condition is filtering too much")
    else:
        print(f"   ✅ Found {len(predictions)} neighbors")
        print(f"   Prediction = {sum(predictions)}")
    
    # Check modulo pattern
    print("\n8. MODULO PATTERN CHECK:")
    print("   Indices that PASS i%4 != 0:")
    passing = [i for i in range(20) if i % 4 != 0]
    print(f"   {passing}")
    print("   Indices that FAIL i%4 != 0:")
    failing = [i for i in range(20) if i % 4 == 0]
    print(f"   {failing}")

if __name__ == "__main__":
    manual_ml_debug()
