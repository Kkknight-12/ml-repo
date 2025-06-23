#!/usr/bin/env python3
"""
Test Sliding Window Fix
=======================
Verify that ML predictions now start correctly with sliding window approach
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor

def test_sliding_window():
    """Test the sliding window fix"""
    
    print("=" * 80)
    print("🚀 TESTING SLIDING WINDOW FIX")
    print("=" * 80)
    
    # Load data
    data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return
    
    df = pd.read_csv(data_file)
    print(f"\n✅ Loaded {len(df)} bars")
    
    # Test with different max_bars_back values
    for max_bars_back in [50, 100, 200]:
        print(f"\n{'='*60}")
        print(f"Testing with max_bars_back = {max_bars_back}")
        print(f"{'='*60}")
        
        # Create config
        config = TradingConfig(
            max_bars_back=max_bars_back,
            neighbors_count=8,
            feature_count=5,
            # Disable all filters for clear ML testing
            use_volatility_filter=False,
            use_regime_filter=False,
            use_adx_filter=False,
            use_kernel_filter=False,
            use_ema_filter=False,
            use_sma_filter=False
        )
        
        # Initialize processor (no total_bars needed!)
        processor = BarProcessor(config)
        
        # Track when ML predictions start
        ml_start_bar = None
        signal_count = 0
        
        # Process bars
        print(f"\nProcessing bars...")
        for i in range(min(500, len(df))):  # Process up to 500 bars
            bar = df.iloc[i]
            
            result = processor.process_bar(
                bar['open'], bar['high'], bar['low'], 
                bar['close'], bar['volume']
            )
            
            if result and result.prediction != 0 and ml_start_bar is None:
                ml_start_bar = i
                print(f"✅ ML predictions started at bar {i}")
                print(f"   First prediction: {result.prediction}")
                print(f"   Training labels collected: {len(processor.ml_model.y_train_array)}")
            
            if result and (result.start_long_trade or result.start_short_trade):
                signal_count += 1
                signal_type = "BUY" if result.start_long_trade else "SELL"
                print(f"   Signal at bar {i}: {signal_type} (prediction={result.prediction:.2f})")
        
        # Summary
        print(f"\n📊 Summary:")
        print(f"   Expected ML start: After {max_bars_back} bars")
        print(f"   Actual ML start: Bar {ml_start_bar}")
        print(f"   Total signals: {signal_count}")
        
        # Verify correctness
        if ml_start_bar and ml_start_bar >= max_bars_back:
            print(f"   ✅ ML started correctly!")
        else:
            print(f"   ❌ ML start issue detected")

def test_real_time_simulation():
    """Simulate real-time bar processing"""
    print("\n" + "=" * 80)
    print("🔴 SIMULATING REAL-TIME PROCESSING")
    print("=" * 80)
    
    # Configuration
    config = TradingConfig(
        max_bars_back=100,
        neighbors_count=8,
        feature_count=2,  # Just 2 features for simplicity
        use_volatility_filter=False,
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=False
    )
    
    # Initialize processor
    processor = BarProcessor(config)
    
    # Simulate real-time bars
    print("\nSimulating 150 bars one by one...")
    
    # Create some synthetic data for demo
    import random
    random.seed(42)
    
    base_price = 1450.0
    for i in range(150):
        # Generate realistic OHLC
        change = random.uniform(-10, 10)
        open_price = base_price + change
        high = open_price + random.uniform(0, 5)
        low = open_price - random.uniform(0, 5)
        close = random.uniform(low, high)
        volume = random.randint(10000, 100000)
        
        # Process bar
        result = processor.process_bar(open_price, high, low, close, volume)
        
        # Show progress at key points
        if i == 50:
            print(f"\nBar 50: Training labels = {len(processor.ml_model.y_train_array)}")
        elif i == 99:
            print(f"Bar 99: About to start ML predictions...")
        elif i == 100:
            print(f"Bar 100: ML prediction = {result.prediction if result else 0}")
            if result and result.prediction != 0:
                print("✅ ML predictions working with sliding window!")
        
        # Update base price for next bar
        base_price = close
    
    print(f"\n✅ Processed {processor.bars_processed} bars successfully!")
    print(f"   Final ML prediction: {processor.ml_model.prediction}")

if __name__ == "__main__":
    # Test with real data
    test_sliding_window()
    
    # Test real-time simulation
    test_real_time_simulation()
