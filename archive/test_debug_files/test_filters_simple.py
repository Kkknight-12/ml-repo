#!/usr/bin/env python3
"""Simple test to check filter behavior"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.ml_extensions import regime_filter, filter_adx
    from core.indicators import calculate_adx
    import random
    
    print("Successfully imported modules!\n")
    
    # Simple test for regime filter
    print("Testing Regime Filter with simple data:")
    
    # Trending market - clear uptrend
    trending = [100 + i * 0.1 for i in range(250)]
    trend_high = [val + 0.5 for val in trending]
    trend_low = [val - 0.5 for val in trending]
    
    # Test with threshold -0.1
    result = regime_filter(trending, -0.1, True, trend_high, trend_low)
    print(f"Trending market result: {result}")
    
    # Ranging market
    ranging = [100 + random.uniform(-1, 1) for i in range(250)]
    range_high = [val + 1 for val in ranging]
    range_low = [val - 1 for val in ranging]
    
    result2 = regime_filter(ranging, -0.1, True, range_high, range_low)
    print(f"Ranging market result: {result2}")
    
    # Test ADX
    print("\nTesting ADX Calculation:")
    high = [102, 103, 104, 103, 102, 101, 102, 103, 104, 105] * 3  # Repeat to have enough data
    low = [98, 99, 100, 99, 98, 97, 98, 99, 100, 101] * 3
    close = [100, 101, 102, 101, 100, 99, 100, 101, 102, 103] * 3
    
    adx = calculate_adx(high, low, close, 14)
    print(f"ADX value: {adx:.2f}")
    
    # Test ADX filter
    adx_pass = filter_adx(high, low, close, 14, 20, True)
    print(f"ADX Filter (threshold=20): {adx_pass}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
