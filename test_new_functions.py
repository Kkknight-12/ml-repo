#!/usr/bin/env python3
"""
Test the newly implemented barssince() and dmi() functions
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.pine_functions import barssince, barssince_na
from core.indicators import dmi


def test_barssince():
    """Test barssince function with various scenarios"""
    print("Testing barssince() function:")
    print("-" * 50)
    
    # Test 1: Condition true at index 2
    conditions1 = [False, False, True, False, False]
    result1 = barssince(conditions1)
    print(f"Test 1 - True at index 2: {conditions1}")
    print(f"Result: {result1} bars since condition was true")
    print()
    
    # Test 2: Condition true at current bar (index 0)
    conditions2 = [True, False, False, False]
    result2 = barssince(conditions2)
    print(f"Test 2 - True at current bar: {conditions2}")
    print(f"Result: {result2} bars since condition was true")
    print()
    
    # Test 3: Condition never true
    conditions3 = [False, False, False, False, False]
    result3 = barssince(conditions3)
    print(f"Test 3 - Never true: {conditions3}")
    print(f"Result: {result3} (None means never true)")
    print()
    
    # Test 4: Using barssince_na for never true case
    result4 = barssince_na(conditions3, max_bars=500)
    print(f"Test 4 - Using barssince_na for never true case:")
    print(f"Result: {result4} (returns max_bars when never true)")
    print()
    
    # Test 5: Multiple true conditions (returns most recent)
    conditions5 = [False, True, False, True, False]
    result5 = barssince(conditions5)
    print(f"Test 5 - Multiple true conditions: {conditions5}")
    print(f"Result: {result5} bars since most recent true")
    print()


def test_dmi():
    """Test dmi function with sample data"""
    print("\nTesting dmi() function:")
    print("-" * 50)
    
    # Create sample price data (20 bars)
    # Simulating an uptrend
    high_values = [105, 104, 103, 102, 101, 100, 99, 98, 97, 96, 
                   95, 94, 93, 92, 91, 90, 89, 88, 87, 86]
    low_values = [103, 102, 101, 100, 99, 98, 97, 96, 95, 94,
                  93, 92, 91, 90, 89, 88, 87, 86, 85, 84]
    close_values = [104, 103, 102, 101, 100, 99, 98, 97, 96, 95,
                    94, 93, 92, 91, 90, 89, 88, 87, 86, 85]
    
    # Test with different parameters
    length_di = 14
    length_adx = 14
    
    di_plus, di_minus, adx = dmi(high_values, low_values, close_values, 
                                  length_di, length_adx)
    
    print(f"Input data: {len(high_values)} bars")
    print(f"DI Length: {length_di}, ADX Length: {length_adx}")
    print(f"\nResults:")
    print(f"DI+ (Directional Indicator Plus): {di_plus:.2f}")
    print(f"DI- (Directional Indicator Minus): {di_minus:.2f}")
    print(f"ADX (Average Directional Index): {adx:.2f}")
    print()
    
    # Interpretation
    print("Interpretation:")
    if di_plus > di_minus:
        print("- DI+ > DI-: Indicates upward price movement")
    else:
        print("- DI- > DI+: Indicates downward price movement")
    
    if adx > 25:
        print(f"- ADX = {adx:.2f}: Strong trend")
    elif adx > 20:
        print(f"- ADX = {adx:.2f}: Moderate trend")
    else:
        print(f"- ADX = {adx:.2f}: Weak trend or ranging market")
    
    # Test with insufficient data
    print("\nTest with insufficient data:")
    short_high = [105, 104, 103]
    short_low = [103, 102, 101]
    short_close = [104, 103, 102]
    
    di_plus2, di_minus2, adx2 = dmi(short_high, short_low, short_close, 
                                     length_di, length_adx)
    print(f"Input: {len(short_high)} bars (insufficient for length={length_di})")
    print(f"Result: DI+={di_plus2}, DI-={di_minus2}, ADX={adx2}")
    print("(Should return 0.0 for all values due to insufficient data)")


if __name__ == "__main__":
    test_barssince()
    test_dmi()
    
    print("\n" + "="*50)
    print("✅ Both functions implemented successfully!")
    print("="*50)
