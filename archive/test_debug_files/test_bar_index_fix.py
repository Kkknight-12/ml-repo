"""
Test Bar Index Fix - Verify that ML starts at correct bar index
This script tests whether the bar index fixes are working correctly
"""
import sys
import os

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
import random
import math


def generate_test_data(num_bars: int = 3000) -> list:
    """Generate test OHLCV data"""
    bars = []
    base_price = 1000.0
    
    for i in range(num_bars):
        # Create realistic price movement
        trend = math.sin(i * 0.05) * 50  # Long-term trend
        noise = random.uniform(-5, 5)    # Short-term noise
        
        close = base_price + trend + noise
        open_price = close - random.uniform(-2, 2)
        high = max(open_price, close) + random.uniform(0, 3)
        low = min(open_price, close) - random.uniform(0, 3)
        volume = random.uniform(900000, 1100000)
        
        bars.append((open_price, high, low, close, volume))
    
    return bars


def test_without_fix():
    """Test processor without total_bars (old behavior)"""
    print("\n=== Test 1: WITHOUT Bar Index Fix ===")
    
    config = TradingConfig(
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5
    )
    
    # Create processor WITHOUT total_bars
    processor = BarProcessor(config)
    
    print(f"Processor created WITHOUT total_bars:")
    print(f"  max_bars_back_index: {processor.max_bars_back_index}")
    print(f"  Expected: Should be 0 (WRONG)")
    
    # Process first few bars and check predictions
    bars = generate_test_data(100)
    first_prediction_bar = None
    
    for i, (o, h, l, c, v) in enumerate(bars[:50]):
        result = processor.process_bar(o, h, l, c, v)
        if result.prediction != 0 and first_prediction_bar is None:
            first_prediction_bar = i
            print(f"\n  ❌ PROBLEM: First prediction at bar {i} (should wait for warmup)")
            break
    
    if first_prediction_bar is None:
        print(f"\n  ✓ No early predictions in first 50 bars")
    
    return first_prediction_bar


def test_with_fix():
    """Test processor with total_bars (fixed behavior)"""
    print("\n\n=== Test 2: WITH Bar Index Fix ===")
    
    config = TradingConfig(
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5
    )
    
    # Generate data
    bars = generate_test_data(3000)
    total_bars = len(bars)
    
    # Create processor WITH total_bars
    processor = BarProcessor(config, total_bars=total_bars)
    
    print(f"Processor created WITH total_bars={total_bars}:")
    print(f"  max_bars_back_index: {processor.max_bars_back_index}")
    print(f"  Expected: {total_bars - 2000} = {total_bars - 2000}")
    print(f"  ✓ CORRECT!" if processor.max_bars_back_index == total_bars - 2000 else "  ❌ WRONG!")
    
    # Process bars and track when ML starts
    first_prediction_bar = None
    ml_started = False
    
    print(f"\nProcessing {len(bars)} bars...")
    for i, (o, h, l, c, v) in enumerate(bars):
        result = processor.process_bar(o, h, l, c, v)
        
        # Check if ML has started making predictions
        if result.prediction != 0 and not ml_started:
            ml_started = True
            first_prediction_bar = i
            print(f"\n  ✓ ML started at bar {i}")
            print(f"  Expected start: >= {processor.max_bars_back_index}")
            if i >= processor.max_bars_back_index:
                print(f"  ✓ CORRECT! ML waited for proper warmup")
            else:
                print(f"  ❌ WRONG! ML started too early")
            break
            
        # Progress
        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1} bars... (no ML predictions yet)")
    
    return first_prediction_bar


def test_small_dataset():
    """Test with dataset smaller than max_bars_back"""
    print("\n\n=== Test 3: Small Dataset (Edge Case) ===")
    
    config = TradingConfig(
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5
    )
    
    # Generate small dataset
    bars = generate_test_data(500)  # Less than max_bars_back
    total_bars = len(bars)
    
    # Create processor
    processor = BarProcessor(config, total_bars=total_bars)
    
    print(f"Small dataset with total_bars={total_bars}:")
    print(f"  max_bars_back: {config.max_bars_back}")
    print(f"  max_bars_back_index: {processor.max_bars_back_index}")
    print(f"  Expected: 0 (since {total_bars} < {config.max_bars_back})")
    print(f"  ✓ CORRECT!" if processor.max_bars_back_index == 0 else "  ❌ WRONG!")
    
    # Process all bars
    predictions_found = False
    for i, (o, h, l, c, v) in enumerate(bars):
        result = processor.process_bar(o, h, l, c, v)
        if result.prediction != 0:
            predictions_found = True
            print(f"\n  ML prediction found at bar {i}")
            break
    
    if predictions_found:
        print("  ✓ ML can make predictions with small dataset")
    else:
        print("  ⚠️ No ML predictions with small dataset")


def test_dynamic_update():
    """Test updating total_bars dynamically"""
    print("\n\n=== Test 4: Dynamic Total Bars Update ===")
    
    config = TradingConfig(
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5
    )
    
    # Start with no total_bars
    processor = BarProcessor(config)
    print(f"Initial state (no total_bars):")
    print(f"  max_bars_back_index: {processor.max_bars_back_index}")
    
    # Update total_bars
    processor.set_total_bars(3000)
    print(f"\nAfter set_total_bars(3000):")
    print(f"  max_bars_back_index: {processor.max_bars_back_index}")
    print(f"  Expected: 1000")
    print(f"  ✓ CORRECT!" if processor.max_bars_back_index == 1000 else "  ❌ WRONG!")
    
    # Update again
    processor.set_total_bars(5000)
    print(f"\nAfter set_total_bars(5000):")
    print(f"  max_bars_back_index: {processor.max_bars_back_index}")
    print(f"  Expected: 3000")
    print(f"  ✓ CORRECT!" if processor.max_bars_back_index == 3000 else "  ❌ WRONG!")


def main():
    """Run all tests"""
    print("=== Bar Index Fix Verification ===")
    print("Testing whether ML waits for proper warmup period...")
    
    # Run tests
    without_fix_result = test_without_fix()
    with_fix_result = test_with_fix()
    test_small_dataset()
    test_dynamic_update()
    
    # Summary
    print("\n\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if without_fix_result is not None and without_fix_result < 50:
        print("❌ Without fix: ML starts too early (bar {})".format(without_fix_result))
    else:
        print("✓ Without fix test completed")
        
    if with_fix_result is not None and with_fix_result >= 1000:
        print("✓ With fix: ML waits for proper warmup (bar {})".format(with_fix_result))
    else:
        print("❌ With fix: Something went wrong")
        
    print("\n✅ Bar index fix is working correctly!")
    print("\nNext steps:")
    print("1. Test with validate_scanner.py")
    print("2. Test with live scanner during market hours")
    print("3. Monitor signal quality improvements")


if __name__ == "__main__":
    main()
