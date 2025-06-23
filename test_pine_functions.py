#!/usr/bin/env python3
"""
Test Pine Script functions
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pine_functions import nz, na, iff
import math
import numpy as np


def test_nz_function():
    """Test nz() function with various inputs"""
    print("🧪 Testing nz() function:")
    
    # Test cases
    test_cases = [
        (None, 0, "None input"),
        (5.0, 0, "Valid float"),
        (float('nan'), 0, "NaN input"),
        (float('inf'), 0, "Infinity input"),
        ([1, 2, None, float('nan'), 5], 0, "List with None/NaN"),
        (np.array([1, 2, np.nan, 4]), 0, "NumPy array with NaN"),
    ]
    
    for value, replacement, description in test_cases:
        result = nz(value, replacement)
        print(f"\n  {description}:")
        print(f"    Input: {value}")
        print(f"    Output: {result}")
        print(f"    Expected behavior: Replace None/NaN with {replacement}")
        
        # Verify
        if isinstance(value, list):
            expected = [v if v is not None and not (isinstance(v, float) and math.isnan(v)) else replacement for v in value]
            assert result == expected, f"List test failed: {result} != {expected}"
        elif isinstance(value, np.ndarray):
            expected = np.where(np.isnan(value), replacement, value)
            assert np.array_equal(result, expected), "NumPy test failed"
        elif value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
            assert result == replacement, f"Single value test failed: {result} != {replacement}"
        else:
            assert result == value, f"Valid value test failed: {result} != {value}"
    
    print("\n✅ All nz() tests passed!")


def test_na_function():
    """Test na() function"""
    print("\n🧪 Testing na() function:")
    
    test_cases = [
        (None, True, "None input"),
        (5.0, False, "Valid float"),
        (float('nan'), True, "NaN input"),
        (float('inf'), True, "Infinity input"),
        (0, False, "Zero"),
        ("test", False, "String input"),
    ]
    
    for value, expected, description in test_cases:
        result = na(value)
        print(f"  {description}: {value} -> {result} (expected: {expected})")
        assert result == expected, f"Test failed for {description}"
    
    print("\n✅ All na() tests passed!")


if __name__ == "__main__":
    test_nz_function()
    test_na_function()
    print("\n🎉 All Pine Script function tests passed!")
