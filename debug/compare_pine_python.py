#!/usr/bin/env python3
"""
Deep Comparison with Pine Script
================================
This script carefully compares our implementation with Pine Script
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from ml.lorentzian_knn import LorentzianKNN
from data.data_types import Settings, Label, FeatureArrays, FeatureSeries

def analyze_pine_vs_python():
    """
    Compare Pine Script logic with our Python implementation
    """
    
    print("=" * 80)
    print("🔍 PINE SCRIPT vs PYTHON COMPARISON")
    print("=" * 80)
    
    # First, let's check array management
    print("\n1. ARRAY MANAGEMENT DIFFERENCES:")
    print("-" * 40)
    print("Pine Script arrays:")
    print("  - array.push(arr, val) → adds to END")
    print("  - array.get(arr, 0) → gets FIRST element")
    print("  - array.shift(arr) → removes FIRST element")
    print("\nOur Python arrays:")
    print("  - list.insert(0, val) → adds to BEGINNING")
    print("  - list[0] → gets FIRST element") 
    print("  - list.pop(0) → removes FIRST element")
    print("\n⚠️  ISSUE: We're adding to beginning, Pine adds to end!")
    
    # Check how we're accessing arrays in distance calculation
    print("\n2. ARRAY ACCESS IN DISTANCE CALCULATION:")
    print("-" * 40)
    print("Pine Script: array.get(featureArrays.f1, i)")
    print("  - i=0 gets OLDEST value (first added)")
    print("  - i=1 gets second oldest, etc.")
    print("\nOur Python: feature_arrays.f1[i]")
    print("  - i=0 gets NEWEST value (last added)")
    print("  - This is BACKWARDS!")
    
    # Check the ML loop
    print("\n3. ML LOOP ANALYSIS:")
    print("-" * 40)
    print("Pine Script loop:")
    print("  for i = 0 to sizeLoop")
    print("    - Starts from oldest data (i=0)")
    print("    - Works forward in time")
    print("\nOur loop should:")
    print("  - Access oldest data first")
    print("  - But we're accessing newest first!")
    
    # Test with actual data
    print("\n4. TESTING WITH ACTUAL DATA:")
    print("-" * 40)
    
    # Load data
    data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return
    
    df = pd.read_csv(data_file)
    
    # Create minimal config
    config = TradingConfig(
        max_bars_back=100,  # Small for testing
        neighbors_count=8,
        feature_count=2,    # Just 2 features for simplicity
        use_volatility_filter=False,
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=False
    )
    
    # Initialize processor
    processor = BarProcessor(config, total_bars=len(df))
    
    # Process some bars
    print("\nProcessing 110 bars to check array building...")
    for i in range(110):
        bar = df.iloc[i]
        processor.process_bar(
            bar['open'], bar['high'], bar['low'], 
            bar['close'], bar['volume']
        )
    
    # Check feature arrays
    print(f"\nFeature array lengths:")
    print(f"  F1: {len(processor.feature_arrays.f1)}")
    print(f"  F2: {len(processor.feature_arrays.f2)}")
    
    if len(processor.feature_arrays.f1) > 5:
        print(f"\nFirst 5 elements of F1:")
        print(f"  [0]: {processor.feature_arrays.f1[0]:.4f} (should be OLDEST)")
        print(f"  [1]: {processor.feature_arrays.f1[1]:.4f}")
        print(f"  [2]: {processor.feature_arrays.f1[2]:.4f}")
        print(f"  [3]: {processor.feature_arrays.f1[3]:.4f}")
        print(f"  [4]: {processor.feature_arrays.f1[4]:.4f}")
    
    # Check training labels
    print(f"\nTraining labels: {len(processor.ml_model.y_train_array)}")
    if len(processor.ml_model.y_train_array) > 5:
        print(f"Last 5 labels: {processor.ml_model.y_train_array[-5:]}")
    
    print("\n" + "=" * 80)
    print("🚨 CRITICAL FINDINGS:")
    print("=" * 80)
    print("\n1. ARRAY ORDER IS REVERSED!")
    print("   - Pine Script: oldest → newest")
    print("   - Our Python: newest → oldest")
    print("\n2. This means when ML algorithm looks for neighbors:")
    print("   - It's comparing with WRONG historical data")
    print("   - Distance calculations are incorrect")
    print("\n3. Solution:")
    print("   - Change insert(0, x) to append(x)")
    print("   - OR reverse array access in distance calculation")

if __name__ == "__main__":
    analyze_pine_vs_python()
