#!/usr/bin/env python3
"""
Quick test to show filter behavior issue
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Let's check the actual filter functions
print("Checking filter implementation...")

# First, let's see what the filters are actually doing
from core.ml_extensions import filter_volatility

# Check the source code
import inspect
print("\n=== VOLATILITY FILTER SOURCE ===")
print(inspect.getsource(filter_volatility))

# Test with simple data
high = [105, 104, 103, 102, 101, 100, 99, 98, 97, 96]
low = [95, 94, 93, 92, 91, 90, 89, 88, 87, 86]
close = [100, 99, 98, 97, 96, 95, 94, 93, 92, 91]

print("\n=== TESTING VOLATILITY FILTER ===")
result = filter_volatility(high, low, close, 1, 10, True)
print(f"Result with filter ON: {result}")

result_off = filter_volatility(high, low, close, 1, 10, False)
print(f"Result with filter OFF: {result_off}")

# Pine Script says when filter is OFF, it should return TRUE
print(f"\nPine Script behavior: When filter OFF, should return TRUE")
print(f"Our implementation returns: {result_off}")
