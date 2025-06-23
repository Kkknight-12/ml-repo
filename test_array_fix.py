#!/usr/bin/env python3
"""
Test After Array Order Fix
==========================
Tests if ML predictions work after fixing array order to match Pine Script
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor

def test_array_order_fix():
    """Test ML predictions after fixing array order"""
    
    print("=" * 80)
    print("🔧 Testing After Array Order Fix")
    print("=" * 80)
    
    # Load data
    data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return
    
    df = pd.read_csv(data_file)
    print(f"\n✅ Loaded {len(df)} bars")
    
    # Minimal config
    config = TradingConfig(
        max_bars_back=500,
        neighbors_count=8,
        feature_count=5,
        
        # Disable all filters for pure ML test
        use_volatility_filter=False,
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=False,
        use_ema_filter=False,
        use_sma_filter=False
    )
    
    # Initialize processor
    processor = BarProcessor(config, total_bars=len(df))
    
    # Debug arrays at specific points
    print("\n🏃 Processing bars...")
    
    # Process initial bars
    for i in range(100):
        bar = df.iloc[i]
        processor.process_bar(
            bar['open'], bar['high'], bar['low'], 
            bar['close'], bar['volume']
        )
    
    # Check array ordering after 100 bars
    print(f"\n📊 After 100 bars:")
    print(f"Feature array F1 length: {len(processor.feature_arrays.f1)}")
    if len(processor.feature_arrays.f1) >= 5:
        print(f"First 5 elements (oldest to newest):")
        for j in range(5):
            print(f"  [{j}]: {processor.feature_arrays.f1[j]:.4f}")
    
    print(f"\nTraining labels: {len(processor.ml_model.y_train_array)}")
    if len(processor.ml_model.y_train_array) >= 5:
        print(f"First 5 labels: {processor.ml_model.y_train_array[:5]}")
    
    # Continue processing to ML start
    non_zero_predictions = 0
    predictions_list = []
    
    for i in range(100, min(600, len(df))):
        bar = df.iloc[i]
        
        result = processor.process_bar(
            bar['open'], bar['high'], bar['low'], 
            bar['close'], bar['volume']
        )
        
        # Track predictions after ML starts
        if i >= 500:
            if result.prediction != 0:
                non_zero_predictions += 1
                predictions_list.append(result.prediction)
                
                # Show first few non-zero predictions
                if non_zero_predictions <= 5:
                    print(f"\n✅ Bar {i}: ML Prediction = {result.prediction}")
                    
                    # Debug info
                    if non_zero_predictions == 1:
                        ml = processor.ml_model
                        print(f"   Neighbors found: {len(ml.predictions)}")
                        print(f"   Neighbor values: {ml.predictions}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 RESULTS:")
    print("=" * 80)
    
    if non_zero_predictions > 0:
        print(f"✅ SUCCESS! Found {non_zero_predictions} non-zero predictions")
        print(f"📈 Prediction range: {min(predictions_list):.1f} to {max(predictions_list):.1f}")
        print(f"📊 Average prediction: {sum(predictions_list)/len(predictions_list):.1f}")
        print("\n🎉 Array order fix seems to be working!")
    else:
        print("❌ STILL GETTING ZERO PREDICTIONS!")
        print("\nPossible remaining issues:")
        print("1. Signal history array access needs updating")
        print("2. Distance calculation might need adjustment")
        print("3. Feature normalization issue")
    
    return non_zero_predictions > 0

if __name__ == "__main__":
    success = test_array_order_fix()
    exit(0 if success else 1)
