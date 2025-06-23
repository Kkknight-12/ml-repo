#!/usr/bin/env python3
"""
Quick ML Test
=============
Purpose: Quickly verify if ML predictions are working
- Use existing data file
- Show ML prediction progression
- Identify any issues
"""

import pandas as pd
import os
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor

def quick_ml_test():
    """Quick test to see if ML is producing predictions"""
    
    print("=" * 60)
    print("🚀 Quick ML Prediction Test")
    print("=" * 60)
    print()
    
    # Check for data file
    data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        print("   Run fetch_pinescript_style_data.py first!")
        return
    
    # Load data
    print(f"📂 Loading: {data_file}")
    df = pd.read_csv(data_file)
    print(f"✅ Loaded {len(df)} bars\n")
    
    # Test with different max_bars_back values
    test_configs = [
        (50, "Very Small Window"),
        (100, "Small Window"),
        (500, "Medium Window"),
        (1000, "Large Window"),
    ]
    
    for max_bars_back, description in test_configs:
        print(f"\n{'='*50}")
        print(f"🔧 Testing with max_bars_back={max_bars_back} ({description})")
        print(f"{'='*50}")
        
        # Create config
        config = TradingConfig(
            max_bars_back=max_bars_back,
            neighbors_count=8,
            feature_count=5,
            # All filters OFF for pure ML test
            use_volatility_filter=False,
            use_regime_filter=False,
            use_adx_filter=False,
            use_kernel_filter=False,
            use_ema_filter=False,
            use_sma_filter=False
        )
        
        # Create processor
        processor = BarProcessor(config)
        
        # Process bars and track predictions
        predictions = []
        ml_started = False
        ml_start_bar = None
        
        # Key bars to monitor
        # Note: ML starts ~3-4 bars after max_bars_back due to training label lookback
        monitor_bars = [
            max_bars_back - 1,      # Just before ML should start
            max_bars_back,          # Traditional start point
            max_bars_back + 3,      # Actual ML start (with lookback delay)
            max_bars_back + 4,      # Just after ML starts
            max_bars_back + 10,     # A bit later
            max_bars_back + 50,     # Much later
            len(df) - 1             # Last bar
        ]
        
        print(f"\n📊 Processing {len(df)} bars...")
        
        for i in range(len(df)):
            bar = df.iloc[i]
            
            result = processor.process_bar(
                open_price=bar['open'],
                high=bar['high'],
                low=bar['low'],
                close=bar['close'],
                volume=bar['volume']
            )
            
            # Track when ML starts
            if result.prediction != 0.0 and not ml_started:
                ml_started = True
                ml_start_bar = i
            
            predictions.append(result.prediction)
            
            # Show debug for key bars
            if i in monitor_bars and i < len(df):
                status = "🟢 ML Active" if result.prediction != 0 else "⚪ Waiting"
                print(f"   Bar {i:4d}: Prediction = {result.prediction:6.2f} [{status}]")
        
        # Summary statistics
        non_zero = [p for p in predictions if p != 0.0]
        
        print(f"\n📈 Results:")
        print(f"   ML started at bar: {ml_start_bar}")
        print(f"   Expected start: ~{max_bars_back + 3} (max_bars_back + training lookback)")
        print(f"   Match: {'✅ YES' if ml_start_bar and abs(ml_start_bar - (max_bars_back + 3)) <= 1 else '❌ NO'}")
        
        if non_zero:
            print(f"\n   Prediction Statistics:")
            print(f"   - Count: {len(non_zero)}")
            print(f"   - Range: [{min(non_zero):.2f}, {max(non_zero):.2f}]")
            print(f"   - Average: {sum(non_zero)/len(non_zero):.2f}")
            
            # Check distribution
            positive = len([p for p in non_zero if p > 0])
            negative = len([p for p in non_zero if p < 0])
            print(f"   - Positive: {positive} ({positive/len(non_zero)*100:.1f}%)")
            print(f"   - Negative: {negative} ({negative/len(non_zero)*100:.1f}%)")
        else:
            print(f"\n   ⚠️ No predictions generated!")
    
    print("\n" + "="*60)
    print("✅ Quick ML Test Complete!")
    print("="*60)
    
    # Final recommendation
    print("\n💡 Recommendations:")
    print("1. If ML predictions are 0, check feature calculations")
    print("2. ML starts at max_bars_back + ~3-4 bars (this is EXPECTED)")
    print("3. If predictions are weak (close to 0), try different parameters")
    print("4. Best max_bars_back is usually 25-50% of total data")
    print("5. The 3-4 bar delay is due to training label lookback (src[4] vs src[0])")

if __name__ == "__main__":
    quick_ml_test()
