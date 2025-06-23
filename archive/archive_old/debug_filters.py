"""
Debug script to check why filters are always passing
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.ml_extensions import regime_filter, filter_adx
from core.indicators import calculate_adx
import random
import math

print("=== Filter Debug Analysis ===\n")

# Test 1: Regime Filter
print("1. Testing Regime Filter:")

# Create test data - trending market (need 200+ bars)
trending_data = [100 + i * 0.1 for i in range(250)]  # Uptrend
ranging_data = [100 + random.uniform(-1, 1) for i in range(250)]  # Ranging

# Generate high/low values for both datasets
trending_high = [val + 0.5 for val in trending_data]
trending_low = [val - 0.5 for val in trending_data]
ranging_high = [val + 1 for val in ranging_data]
ranging_low = [val - 1 for val in ranging_data]

# Test with different thresholds
for threshold in [-0.5, -0.1, 0, 0.1, 0.5]:
    trend_result = regime_filter(trending_data, threshold, True, trending_high, trending_low)
    range_result = regime_filter(ranging_data, threshold, True, ranging_high, ranging_low)
    print(f"  Threshold {threshold:>4}: Trending={trend_result}, Ranging={range_result}")

# Test 2: ADX Calculation
print("\n2. Testing ADX Calculation:")

# Create test OHLC data
high_values = [102, 103, 104, 103, 102, 101, 102, 103, 104, 105]
low_values = [98, 99, 100, 99, 98, 97, 98, 99, 100, 101]
close_values = [100, 101, 102, 101, 100, 99, 100, 101, 102, 103]

for length in [5, 10, 14]:
    adx = calculate_adx(high_values, low_values, close_values, length)
    print(f"  ADX (period={length}): {adx:.2f}")

# Test 3: Filter ADX with different thresholds
print("\n3. Testing ADX Filter:")
for threshold in [10, 20, 30, 40]:
    result = filter_adx(high_values, low_values, close_values, 14, threshold, True)
    print(f"  Threshold {threshold}: {result}")

# Test 4: Check with CSV data
print("\n4. Testing with actual CSV data:")
# Load a few bars from CSV
import csv
csv_file = "NSE_ICICIBANK, 5.csv"

if os.path.exists(csv_file):
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        ohlc4_values = []
        high_vals = []
        low_vals = []
        close_vals = []
        
        for i, row in enumerate(reader):
            if i < 20:  # First 20 bars
                ohlc4 = (float(row['open']) + float(row['high']) + 
                         float(row['low']) + float(row['close'])) / 4
                ohlc4_values.append(ohlc4)
                high_vals.append(float(row['high']))
                low_vals.append(float(row['low']))
                close_vals.append(float(row['close']))
        
        # Test regime filter with actual data
        regime_result = regime_filter(ohlc4_values, -0.1, True, high_vals, low_vals)
        print(f"  Regime filter with CSV data: {regime_result}")
        
        # Test ADX with actual data
        if len(high_vals) >= 14:
            adx_val = calculate_adx(high_vals, low_vals, close_vals, 14)
            print(f"  ADX with CSV data: {adx_val:.2f}")
            adx_filter_result = filter_adx(high_vals, low_vals, close_vals, 14, 20, True)
            print(f"  ADX filter result (threshold=20): {adx_filter_result}")

print("\n=== Debug Complete ===")
