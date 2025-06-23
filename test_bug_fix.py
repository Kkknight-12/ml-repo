#!/usr/bin/env python3
"""
Quick Test After Bug Fix
=======================
Tests if ML predictions are now working after fixing i%4 condition
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor

def test_bug_fix():
    """Quick test to verify ML predictions are now non-zero"""
    
    print("=" * 60)
    print("🔧 Testing ML Bug Fix")
    print("=" * 60)
    
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
    
    # Process bars and check predictions
    print("\n🏃 Processing bars...")
    non_zero_predictions = 0
    predictions_list = []
    
    for i in range(min(600, len(df))):
        bar = df.iloc[i]
        
        result = processor.process_bar(
            bar['open'], bar['high'], bar['low'], 
            bar['close'], bar['volume']
        )
        
        # Check predictions after ML starts
        if i >= 500:
            if result.prediction != 0:
                non_zero_predictions += 1
                predictions_list.append(result.prediction)
                
                # Show first few non-zero predictions
                if non_zero_predictions <= 5:
                    print(f"\n✅ Bar {i}: ML Prediction = {result.prediction}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 RESULTS:")
    print("=" * 60)
    
    if non_zero_predictions > 0:
        print(f"✅ SUCCESS! Found {non_zero_predictions} non-zero predictions")
        print(f"📈 Prediction range: {min(predictions_list):.1f} to {max(predictions_list):.1f}")
        print(f"📊 Average prediction: {sum(predictions_list)/len(predictions_list):.1f}")
    else:
        print("❌ STILL GETTING ZERO PREDICTIONS!")
        print("   Need to debug further...")
    
    return non_zero_predictions > 0

if __name__ == "__main__":
    success = test_bug_fix()
    exit(0 if success else 1)
