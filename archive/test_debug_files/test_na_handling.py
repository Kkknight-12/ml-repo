"""
Test NA/None Handling - Phase 3
Tests edge cases with missing data, None values, and NaN
"""
import sys
import os
import math
import random

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor


def generate_data_with_gaps(num_bars: int, gap_probability: float = 0.1) -> list:
    """Generate OHLCV data with random None values"""
    bars = []
    base_price = 1000.0
    
    for i in range(num_bars):
        # Random chance of None values
        if random.random() < gap_probability:
            # Complete missing bar
            bars.append((None, None, None, None, None))
        else:
            # Normal bar with potential NaN
            trend = math.sin(i * 0.05) * 50
            noise = random.uniform(-5, 5)
            
            close = base_price + trend + noise
            
            # Sometimes inject NaN
            if random.random() < 0.05:
                close = float('nan')
            
            open_price = close - random.uniform(-2, 2) if not math.isnan(close) else float('nan')
            high = max(open_price, close) + random.uniform(0, 3) if not math.isnan(close) else float('nan')
            low = min(open_price, close) - random.uniform(0, 3) if not math.isnan(close) else float('nan')
            
            # Sometimes None volume
            volume = random.uniform(900000, 1100000) if random.random() > 0.1 else None
            
            bars.append((open_price, high, low, close, volume))
    
    return bars


def test_none_handling():
    """Test processor with None values"""
    print("\n=== Test 1: None Value Handling ===")
    
    config = TradingConfig()
    processor = BarProcessor(config, total_bars=100)
    
    test_cases = [
        # Complete None bar
        (None, None, None, None, None),
        # Partial None values
        (100, None, 99, 100.5, 1000),
        (100, 101, None, 100.5, 1000),
        (100, 101, 99, None, 1000),
        # Zero values
        (0, 0, 0, 0, 0),
        # Negative values
        (-100, -99, -101, -100, 1000),
    ]
    
    print("Testing edge cases:")
    for i, bar in enumerate(test_cases):
        try:
            result = processor.process_bar(*bar)
            print(f"  Case {i+1}: {bar[:4]} → ✓ Processed (prediction: {result.prediction})")
        except Exception as e:
            print(f"  Case {i+1}: {bar[:4]} → ✗ Error: {str(e)}")


def test_nan_handling():
    """Test processor with NaN values"""
    print("\n\n=== Test 2: NaN Value Handling ===")
    
    config = TradingConfig()
    processor = BarProcessor(config, total_bars=100)
    
    test_cases = [
        # NaN in different positions
        (float('nan'), 101, 99, 100, 1000),
        (100, float('nan'), 99, 100, 1000),
        (100, 101, float('nan'), 100, 1000),
        (100, 101, 99, float('nan'), 1000),
        # Infinity values
        (float('inf'), 101, 99, 100, 1000),
        (100, 101, 99, float('-inf'), 1000),
    ]
    
    print("Testing NaN/Inf cases:")
    for i, bar in enumerate(test_cases):
        try:
            result = processor.process_bar(*bar)
            print(f"  Case {i+1}: {str(bar[0])[:6]}, {str(bar[3])[:6]} → ✓ Processed")
        except Exception as e:
            print(f"  Case {i+1}: {str(bar[0])[:6]}, {str(bar[3])[:6]} → ✗ Error: {str(e)}")


def test_gap_data():
    """Test with realistic data gaps"""
    print("\n\n=== Test 3: Data with Gaps ===")
    
    config = TradingConfig()
    
    # Generate data with gaps
    bars = generate_data_with_gaps(200, gap_probability=0.15)
    processor = BarProcessor(config, total_bars=len(bars))
    
    print(f"Processing {len(bars)} bars with ~15% gaps...")
    
    errors = 0
    none_bars = 0
    nan_bars = 0
    successful = 0
    
    for i, bar in enumerate(bars):
        try:
            # Count None bars
            if bar[0] is None or bar[3] is None:
                none_bars += 1
                continue
            
            # Count NaN bars
            if any(v is not None and isinstance(v, float) and math.isnan(v) for v in bar):
                nan_bars += 1
            
            result = processor.process_bar(*bar)
            successful += 1
            
        except Exception as e:
            errors += 1
            if i < 5:  # Show first few errors
                print(f"  Error at bar {i}: {str(e)}")
    
    print(f"\nResults:")
    print(f"  Total bars: {len(bars)}")
    print(f"  None bars skipped: {none_bars}")
    print(f"  NaN bars found: {nan_bars}")
    print(f"  Successfully processed: {successful}")
    print(f"  Errors: {errors}")


def test_indicator_edge_cases():
    """Test indicators with edge case data"""
    print("\n\n=== Test 4: Indicator Edge Cases ===")
    
    from core.indicators import calculate_rsi, calculate_cci, n_adx
    
    print("Testing RSI with edge cases:")
    # Empty data
    print(f"  Empty list: RSI = {calculate_rsi([], 14)}")
    # Single value
    print(f"  Single value: RSI = {calculate_rsi([100], 14)}")
    # All same values
    print(f"  Same values: RSI = {calculate_rsi([100]*20, 14)}")
    # With None (will crash)
    try:
        print(f"  With None: RSI = {calculate_rsi([100, None, 100], 14)}")
    except Exception as e:
        print(f"  With None: Error - {str(e)}")
    
    print("\nTesting ADX with edge cases:")
    # Empty data
    print(f"  Empty lists: ADX = {n_adx([], [], [], 14)}")
    # Mismatched lengths
    print(f"  Mismatched: ADX = {n_adx([100, 101], [99], [100, 100, 100], 14)}")


def test_ml_with_missing_features():
    """Test ML predictions with missing features"""
    print("\n\n=== Test 5: ML with Missing Features ===")
    
    from ml.lorentzian_knn import get_lorentzian_distance
    from data.data_types import FeatureSeries, FeatureArrays
    
    # Create feature series with None/NaN
    features = FeatureSeries(
        f1=0.5,
        f2=float('nan'),  # NaN feature
        f3=0.7,
        f4=None,  # This will cause error
        f5=0.3
    )
    
    # Create feature arrays
    arrays = FeatureArrays()
    arrays.f1 = [0.4, 0.5, 0.6]
    arrays.f2 = [0.3, float('nan'), 0.5]  # NaN in history
    arrays.f3 = [0.8, 0.7, 0.6]
    arrays.f4 = [0.2, 0.3, 0.4]
    arrays.f5 = [0.1, 0.2, 0.3]
    
    print("Testing Lorentzian distance with NaN:")
    try:
        distance = get_lorentzian_distance(0, 5, features, arrays)
        print(f"  Distance calculated: {distance}")
    except Exception as e:
        print(f"  Error: {str(e)}")


def main():
    """Run all NA/None handling tests"""
    print("=== NA/None Value Handling Tests ===")
    print("Testing edge cases and missing data scenarios...")
    
    test_none_handling()
    test_nan_handling()
    test_gap_data()
    test_indicator_edge_cases()
    test_ml_with_missing_features()
    
    print("\n\n=== Summary ===")
    print("Current issues found:")
    print("1. ❌ No None value validation in price data")
    print("2. ❌ NaN values not checked before calculations")
    print("3. ❌ Indicators crash with None in lists")
    print("4. ❌ ML features don't validate for None/NaN")
    print("5. ⚠️  Default values returned may hide problems")
    
    print("\nRecommendations:")
    print("1. Add None/NaN validation at bar processor input")
    print("2. Filter None values from indicator calculations")
    print("3. Use numpy.nanmean, nanstd for statistics")
    print("4. Add try-except blocks in critical paths")
    print("5. Log warnings when data is missing")


if __name__ == "__main__":
    main()
