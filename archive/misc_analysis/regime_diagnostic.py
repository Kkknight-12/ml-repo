#!/usr/bin/env python3
"""Diagnostic test for regime filter to see internal values"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.ml_extensions import regime_filter
import random

print("=== Regime Filter Diagnostic Test ===\n")

# Test 1: Clear uptrend
print("1. Testing with STRONG UPTREND:")
uptrend = [100.0 + i * 0.5 for i in range(250)]
uptrend_high = [val + 0.5 for val in uptrend]
uptrend_low = [val - 0.5 for val in uptrend]

# Test 2: Clear downtrend  
print("\n2. Testing with STRONG DOWNTREND:")
downtrend = [150.0 - i * 0.5 for i in range(250)]
downtrend_high = [val + 0.5 for val in downtrend]
downtrend_low = [val - 0.5 for val in downtrend]

# Test 3: Ranging/sideways market
print("\n3. Testing with RANGING MARKET:")
ranging = [100.0 + random.uniform(-2, 2) for i in range(250)]
ranging_high = [val + 1.0 for val in ranging]
ranging_low = [val - 1.0 for val in ranging]

# Test 4: Volatile market
print("\n4. Testing with VOLATILE MARKET:")
volatile = []
for i in range(250):
    if i % 20 < 10:
        volatile.append(100.0 + i * 0.1)  # Uptrend
    else:
        volatile.append(110.0 - i * 0.1)  # Downtrend
volatile_high = [val + 2.0 for val in volatile]
volatile_low = [val - 2.0 for val in volatile]

# Run tests with different thresholds
test_data = [
    ("Uptrend", uptrend, uptrend_high, uptrend_low),
    ("Downtrend", downtrend, downtrend_high, downtrend_low),
    ("Ranging", ranging, ranging_high, ranging_low),
    ("Volatile", volatile, volatile_high, volatile_low)
]

print("\nResults (threshold = -0.1):")
print("Market Type | Result | Expected")
print("------------|--------|----------")

for name, ohlc4, high, low in test_data:
    result = regime_filter(ohlc4, -0.1, True, high, low)
    expected = "True" if name in ["Uptrend", "Downtrend"] else "False"
    status = "✅" if str(result) == expected else "❌"
    print(f"{name:11} | {str(result):6} | {expected:8} {status}")

# Let's also check if disabling works
print("\n5. Testing with filter DISABLED:")
result_disabled = regime_filter(uptrend, -0.1, False, uptrend_high, uptrend_low)
print(f"Filter disabled result: {result_disabled} (should be True)")

print("\n=== Diagnostic Complete ===")
