#!/usr/bin/env python3
"""
Test with Correct Understanding of Pine Script Logic
===================================================
ML predictions happen in the LAST max_bars_back bars, not AFTER first max_bars_back!
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor

def test_correct_pine_logic():
    """Test with correct Pine Script logic understanding"""
    
    print("=" * 80)
    print("🎯 Testing with Correct Pine Script Logic")
    print("=" * 80)
    
    # Load data
    data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return
    
    df = pd.read_csv(data_file)
    total_bars = len(df)
    print(f"\n✅ Loaded {total_bars} bars")
    
    # Config - using smaller max_bars_back for faster testing
    config = TradingConfig(
        max_bars_back=100,  # ML will run in last 100 bars
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
    
    # Initialize with total bars (Pine Script style)
    processor = BarProcessor(config, total_bars=total_bars)
    
    print(f"\n📊 Pine Script Logic:")
    print(f"   Total bars: {total_bars}")
    print(f"   max_bars_back: {config.max_bars_back}")
    print(f"   max_bars_back_index: {processor.max_bars_back_index}")
    print(f"   ML will start at bar: {processor.max_bars_back_index}")
    print(f"   That's the last {config.max_bars_back} bars of data!")
    
    # Process ALL bars (or at least up to where ML starts + some extra)
    process_up_to = min(processor.max_bars_back_index + 20, total_bars)
    print(f"\n🏃 Processing {process_up_to} bars...")
    
    non_zero_predictions = 0
    prediction_bars = []
    
    for i in range(process_up_to):
        bar = df.iloc[i]
        
        result = processor.process_bar(
            bar['open'], bar['high'], bar['low'], 
            bar['close'], bar['volume']
        )
        
        # Show progress
        if i % 500 == 0:
            print(f"   Progress: Bar {i}/{process_up_to}")
        
        # Track when ML starts
        if i == processor.max_bars_back_index - 1:
            print(f"\n📍 Bar {i}: Next bar should start ML predictions!")
        
        # Check predictions
        if result.prediction != 0:
            non_zero_predictions += 1
            prediction_bars.append(i)
            
            if non_zero_predictions <= 5:
                print(f"\n✅ Bar {i}: ML Prediction = {result.prediction}")
                
                # Show some debug info for first prediction
                if non_zero_predictions == 1:
                    ml = processor.ml_model
                    print(f"   Neighbors found: {len(ml.predictions)}")
                    print(f"   Neighbor labels: {ml.predictions}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 RESULTS:")
    print("=" * 80)
    
    if non_zero_predictions > 0:
        print(f"✅ SUCCESS! Found {non_zero_predictions} non-zero predictions")
        print(f"   First at bar: {prediction_bars[0]}")
        print(f"   Prediction bars: {prediction_bars[:10]}...")
    else:
        print("❌ No predictions found")
        print(f"   Processed up to bar {process_up_to}")
        print(f"   ML should have started at bar {processor.max_bars_back_index}")
    
    # Additional check
    if process_up_to < processor.max_bars_back_index + 10:
        print(f"\n⚠️  Need to process more bars!")
        print(f"   We stopped at bar {process_up_to}")
        print(f"   But ML starts at bar {processor.max_bars_back_index}")
    
    return non_zero_predictions > 0

if __name__ == "__main__":
    success = test_correct_pine_logic()
    exit(0 if success else 1)
