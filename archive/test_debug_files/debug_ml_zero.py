#!/usr/bin/env python3
"""
Quick Debug Script for ML Predictions = 0 Issue
===============================================
This script helps identify why ML predictions are returning 0
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from collections import Counter

def analyze_price_movements(df):
    """Check if data has enough price movement for signals"""
    print("\n=== Price Movement Analysis ===")
    
    movements = []
    for i in range(4, len(df)):
        current = df.iloc[i]['close']
        past = df.iloc[i-4]['close']
        
        if past < current:
            movements.append('SHORT')  # Price went up, so short
        elif past > current:
            movements.append('LONG')   # Price went down, so long
        else:
            movements.append('NEUTRAL')
    
    counts = Counter(movements)
    print(f"Price movements (4-bar):")
    print(f"  LONG: {counts['LONG']} ({counts['LONG']/len(movements)*100:.1f}%)")
    print(f"  SHORT: {counts['SHORT']} ({counts['SHORT']/len(movements)*100:.1f}%)")
    print(f"  NEUTRAL: {counts['NEUTRAL']} ({counts['NEUTRAL']/len(movements)*100:.1f}%)")
    
    return counts

def debug_ml_predictions():
    """Debug why ML predictions are 0"""
    
    print("=" * 60)
    print("🔍 ML Prediction Debug Script")
    print("=" * 60)
    
    # Load data
    data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return
    
    df = pd.read_csv(data_file)
    print(f"\n✅ Loaded {len(df)} bars")
    
    # Analyze price movements first
    movement_counts = analyze_price_movements(df)
    
    if movement_counts['NEUTRAL'] > len(df) * 0.9:
        print("\n⚠️  WARNING: Over 90% of price movements are NEUTRAL!")
        print("   This would cause ML predictions to be 0")
    
    # Create minimal config (no filters)
    print("\n=== Testing with Minimal Config ===")
    config = TradingConfig(
        max_bars_back=500,  # Smaller for faster debug
        neighbors_count=8,
        feature_count=5,
        
        # Disable ALL filters
        use_volatility_filter=False,
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=False,
        use_ema_filter=False,
        use_sma_filter=False
    )
    
    # Initialize processor
    processor = BarProcessor(config, total_bars=len(df))
    print(f"Max bars back index: {processor.max_bars_back_index}")
    
    # Process bars and track ML behavior
    first_prediction_bar = None
    prediction_values = []
    
    print("\n=== Processing Bars ===")
    for i in range(min(600, len(df))):  # Process up to 600 bars
        bar = df.iloc[i]
        
        # Add debug at key points
        if i == 499:
            print(f"\n📍 Bar {i}: ML should start next bar...")
            # Check training labels so far
            ml = processor.ml_model
            if ml.y_train_array:
                label_counts = Counter(ml.y_train_array)
                print(f"   Training labels so far: {dict(label_counts)}")
        
        result = processor.process_bar(
            bar['open'], bar['high'], bar['low'], 
            bar['close'], bar['volume']
        )
        
        # Track predictions after ML starts
        if i >= 500:
            prediction_values.append(result.prediction)
            
            if result.prediction != 0 and first_prediction_bar is None:
                first_prediction_bar = i
                print(f"\n✅ First non-zero prediction at bar {i}: {result.prediction}")
                
                # Show ML state
                ml = processor.ml_model
                print(f"   Neighbors used: {len(ml.predictions)}")
                print(f"   Neighbor labels: {ml.predictions}")
            
            elif i % 50 == 0:  # Progress update
                print(f"📊 Bar {i}: Prediction = {result.prediction}")
    
    # Final analysis
    print("\n=== Final Analysis ===")
    ml = processor.ml_model
    
    print(f"\n1. Training Data:")
    label_counts = Counter(ml.y_train_array)
    print(f"   Total labels: {len(ml.y_train_array)}")
    print(f"   Distribution: {dict(label_counts)}")
    
    print(f"\n2. Predictions:")
    print(f"   Total predictions made: {len(prediction_values)}")
    print(f"   Unique values: {set(prediction_values)}")
    print(f"   All zeros: {all(p == 0 for p in prediction_values)}")
    
    if first_prediction_bar:
        print(f"   First non-zero at bar: {first_prediction_bar}")
    else:
        print(f"   ❌ No non-zero predictions found!")
    
    print(f"\n3. Feature Check (last bar):")
    features = processor._calculate_features()
    print(f"   F1 (RSI): {features.f1:.4f}")
    print(f"   F2 (WT): {features.f2:.4f}")
    print(f"   F3 (CCI): {features.f3:.4f}")
    print(f"   F4 (ADX): {features.f4:.4f}")
    print(f"   F5 (RSI): {features.f5:.4f}")
    
    # Recommendations
    print("\n=== Recommendations ===")
    
    if movement_counts['NEUTRAL'] > len(df) * 0.5:
        print("⚠️  High number of NEUTRAL labels - check if prices are too stable")
    
    if all(p == 0 for p in prediction_values):
        print("❌ All predictions are 0. Possible causes:")
        print("   1. All training labels are neutral")
        print("   2. No neighbors passing distance threshold")
        print("   3. Feature normalization issues")
        print("   4. Distance calculation problems")
        
        print("\nNext steps:")
        print("   - Add debug logging to lorentzian_knn.py")
        print("   - Check distance calculations")
        print("   - Verify neighbor selection logic")

if __name__ == "__main__":
    debug_ml_predictions()
