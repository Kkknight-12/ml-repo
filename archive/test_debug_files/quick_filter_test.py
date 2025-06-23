#!/usr/bin/env python3
"""Quick test to verify filter fixes"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.ml_extensions import regime_filter
from core.indicators import calculate_adx

# Test 1: Simple regime filter test
print("=== Testing Regime Filter ===")

# Create a clear trending market (values increase steadily)
trending_ohlc4 = [100.0 + i * 0.5 for i in range(250)]
trending_high = [val + 1.0 for val in trending_ohlc4]
trending_low = [val - 1.0 for val in trending_ohlc4]

# Test with different thresholds
for threshold in [-0.5, -0.1, 0.0, 0.1]:
    result = regime_filter(trending_ohlc4, threshold, True, trending_high, trending_low)
    print(f"Threshold {threshold}: Result = {result}")

# Test 2: ADX calculation
print("\n=== Testing ADX Calculation ===")

# Simple test data
high = [105, 106, 107, 106, 105, 104, 105, 106, 107, 108] * 3
low = [100, 101, 102, 101, 100, 99, 100, 101, 102, 103] * 3  
close = [102, 103, 104, 103, 102, 101, 102, 103, 104, 105] * 3

adx_value = calculate_adx(high, low, close, 14)
print(f"ADX Value: {adx_value:.2f}")

print("\n=== Test Complete ===")
