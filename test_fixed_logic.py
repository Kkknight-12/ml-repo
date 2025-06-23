#!/usr/bin/env python3
"""
Test with Fixed max_bars_back_index Logic
=========================================
Fixes the issue where ML was waiting for bar 1899 to start
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor

def test_with_fixed_logic():
    """Test with corrected max_bars_back_index logic"""
    
    print("=" * 80)
    print("🔧 Testing with Fixed max_bars_back_index")
    print("=" * 80)
    
    # Load data
    data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return
    
    df = pd.read_csv(data_file)
    print(f"\n✅ Loaded {len(df)} bars")
    
    # Config with small max_bars_back
    config = TradingConfig(
        max_bars_back=50,  # Small value
        neighbors_count=8,
        feature_count=5,
        
        # Disable all filters
        use_volatility_filter=False,
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=False,
        use_ema_filter=False,
        use_sma_filter=False
    )
    
    # Initialize processor WITHOUT total_bars
    # This will make max_bars_back_index = 0
    processor = BarProcessor(config)  # No total_bars argument!
    
    print(f"\n📊 Initial state:")
    print(f"   max_bars_back: {config.max_bars_back}")
    print(f"   max_bars_back_index: {processor.max_bars_back_index}")
    print(f"   ML should start at bar: {config.max_bars_back}")
    
    # Process bars
    print("\n🏃 Processing bars...")
    non_zero_predictions = 0
    first_prediction_bar = None
    
    for i in range(min(100, len(df))):
        bar = df.iloc[i]
        
        result = processor.process_bar(
            bar['open'], bar['high'], bar['low'], 
            bar['close'], bar['volume']
        )
        
        # Check for ML predictions
        if i >= config.max_bars_back:
            if result.prediction != 0 and first_prediction_bar is None:
                first_prediction_bar = i
                print(f"\n✅ First non-zero prediction at bar {i}: {result.prediction}")
                non_zero_predictions += 1
            elif result.prediction != 0:
                non_zero_predictions += 1
                if non_zero_predictions <= 5:
                    print(f"   Bar {i}: Prediction = {result.prediction}")
        
        # Progress update
        if i == config.max_bars_back - 1:
            print(f"\nBar {i}: Next bar should start ML predictions...")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 RESULTS:")
    print("=" * 80)
    
    if non_zero_predictions > 0:
        print(f"✅ SUCCESS! Found {non_zero_predictions} non-zero predictions")
        print(f"   First prediction at bar: {first_prediction_bar}")
    else:
        print("❌ Still getting zero predictions")
        print("   But at least ML should be running now!")
    
    return non_zero_predictions > 0

if __name__ == "__main__":
    success = test_with_fixed_logic()
    exit(0 if success else 1)
