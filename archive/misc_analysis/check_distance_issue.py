#!/usr/bin/env python3
"""
Check Distance Calculation Issue
================================
Debug why distances might not be working correctly
"""

import pandas as pd
import sys
import os
import math
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor

def check_distance_issue():
    """Check if distance calculation is the problem"""
    
    print("=" * 80)
    print("🔍 DISTANCE CALCULATION DEBUG")
    print("=" * 80)
    
    # Test Lorentzian distance formula
    print("\n1. TESTING LORENTZIAN DISTANCE FORMULA:")
    print("   Formula: log(1 + |current - historical|)")
    
    # Test cases
    test_cases = [
        (0.5, 0.5),   # Same values
        (0.5, 0.6),   # Small difference
        (0.5, 1.0),   # Large difference
        (0.0, 1.0),   # Max difference
    ]
    
    for current, historical in test_cases:
        distance = math.log(1 + abs(current - historical))
        print(f"   current={current}, hist={historical} → distance={distance:.4f}")
    
    # Load real data
    data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    if not os.path.exists(data_file):
        print(f"\n❌ Data file not found: {data_file}")
        return
    
    df = pd.read_csv(data_file)
    
    # Simple config
    config = TradingConfig(
        max_bars_back=100,
        neighbors_count=8,
        feature_count=2,  # Just 2 features for simplicity
        use_volatility_filter=False,
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=False
    )
    
    # Process bars
    processor = BarProcessor(config, total_bars=len(df))
    
    print(f"\n2. PROCESSING BARS TO BUILD FEATURES:")
    
    # Process enough bars
    for i in range(110):
        bar = df.iloc[i]
        result = processor.process_bar(
            bar['open'], bar['high'], bar['low'], 
            bar['close'], bar['volume']
        )
        
        # At bar 100, check ML state
        if i == 100:
            print(f"\n3. AT BAR 100 - ML STATE:")
            ml = processor.ml_model
            
            print(f"   Training labels: {len(ml.y_train_array)}")
            print(f"   Feature arrays length: {len(processor.feature_arrays.f1)}")
            
            # Get current features
            features = processor._calculate_features()
            print(f"\n   Current features:")
            print(f"   F1: {features.f1:.4f}")
            print(f"   F2: {features.f2:.4f}")
            
            # Check some historical features
            print(f"\n   Historical features (first 5):")
            for j in range(min(5, len(processor.feature_arrays.f1))):
                print(f"   [{j}]: F1={processor.feature_arrays.f1[j]:.4f}, "
                      f"F2={processor.feature_arrays.f2[j]:.4f}")
            
            # Manually calculate some distances
            print(f"\n4. MANUAL DISTANCE CALCULATIONS:")
            for j in range(min(10, len(processor.feature_arrays.f1))):
                d_f1 = math.log(1 + abs(features.f1 - processor.feature_arrays.f1[j]))
                d_f2 = math.log(1 + abs(features.f2 - processor.feature_arrays.f2[j]))
                total_d = d_f1 + d_f2
                
                passes_modulo = j % 4 != 0
                
                print(f"   [{j}]: d_f1={d_f1:.4f}, d_f2={d_f2:.4f}, "
                      f"total={total_d:.4f}, modulo_pass={passes_modulo}")
            
            # Check if prediction was made
            print(f"\n5. ML PREDICTION RESULT:")
            print(f"   Prediction: {result.prediction}")
            print(f"   Neighbors used: {len(ml.predictions)}")
            if ml.predictions:
                print(f"   Neighbor labels: {ml.predictions}")
    
    # Additional check - feature value distribution
    print(f"\n6. FEATURE VALUE DISTRIBUTION CHECK:")
    if len(processor.feature_arrays.f1) > 0:
        f1_min = min(processor.feature_arrays.f1)
        f1_max = max(processor.feature_arrays.f1)
        f1_avg = sum(processor.feature_arrays.f1) / len(processor.feature_arrays.f1)
        
        print(f"   F1: min={f1_min:.4f}, max={f1_max:.4f}, avg={f1_avg:.4f}")
        
        # Check for suspicious values
        if f1_max == 1.0:
            print("   ⚠️  F1 has max value of exactly 1.0 - check normalization!")
        if f1_min == 0.0:
            print("   ⚠️  F1 has min value of exactly 0.0 - check normalization!")
    
    # Check Wave Trend specifically
    print(f"\n7. WAVE TREND (F2) CHECK:")
    if len(processor.feature_arrays.f2) > 0:
        f2_values = processor.feature_arrays.f2[:10]
        print(f"   First 10 F2 values: {[f'{x:.4f}' for x in f2_values]}")
        
        # Count zeros
        zero_count = sum(1 for x in processor.feature_arrays.f2 if x == 0.0)
        if zero_count > 0:
            print(f"   ⚠️  Found {zero_count} zero values in F2 (Wave Trend)!")

if __name__ == "__main__":
    check_distance_issue()
