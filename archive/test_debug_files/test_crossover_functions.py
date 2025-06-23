#!/usr/bin/env python3
"""
Test Script for crossover_value and crossunder_value functions
"""
from core.pine_functions import crossover_value, crossunder_value


def test_crossover_value():
    """Test crossover_value function with various scenarios"""
    print("🧪 Testing crossover_value function...")
    print("=" * 50)
    
    # Test 1: Clear crossover (series1 crosses above series2)
    print("\n1. Clear crossover:")
    prev1, curr1 = 10, 12  # Was below, now above
    prev2, curr2 = 11, 11  # Stays constant
    result = crossover_value(curr1, prev1, curr2, prev2)
    print(f"   Series1: {prev1} → {curr1}")
    print(f"   Series2: {prev2} → {curr2}")
    print(f"   Result: {result} ✅" if result else f"   Result: {result} ❌")
    
    # Test 2: No crossover (already above)
    print("\n2. No crossover (already above):")
    prev1, curr1 = 12, 13  # Was above, still above
    prev2, curr2 = 11, 11
    result = crossover_value(curr1, prev1, curr2, prev2)
    print(f"   Series1: {prev1} → {curr1}")
    print(f"   Series2: {prev2} → {curr2}")
    print(f"   Result: {result} ✅" if not result else f"   Result: {result} ❌")
    
    # Test 3: Equal then above (should be crossover)
    print("\n3. Equal then above:")
    prev1, curr1 = 11, 12  # Was equal, now above
    prev2, curr2 = 11, 11
    result = crossover_value(curr1, prev1, curr2, prev2)
    print(f"   Series1: {prev1} → {curr1}")
    print(f"   Series2: {prev2} → {curr2}")
    print(f"   Result: {result} ✅" if result else f"   Result: {result} ❌")
    
    # Test 4: Crossunder instead (should be False)
    print("\n4. Crossunder instead:")
    prev1, curr1 = 12, 10  # Was above, now below
    prev2, curr2 = 11, 11
    result = crossover_value(curr1, prev1, curr2, prev2)
    print(f"   Series1: {prev1} → {curr1}")
    print(f"   Series2: {prev2} → {curr2}")
    print(f"   Result: {result} ✅" if not result else f"   Result: {result} ❌")


def test_crossunder_value():
    """Test crossunder_value function with various scenarios"""
    print("\n\n🧪 Testing crossunder_value function...")
    print("=" * 50)
    
    # Test 1: Clear crossunder (series1 crosses below series2)
    print("\n1. Clear crossunder:")
    prev1, curr1 = 12, 10  # Was above, now below
    prev2, curr2 = 11, 11  # Stays constant
    result = crossunder_value(curr1, prev1, curr2, prev2)
    print(f"   Series1: {prev1} → {curr1}")
    print(f"   Series2: {prev2} → {curr2}")
    print(f"   Result: {result} ✅" if result else f"   Result: {result} ❌")
    
    # Test 2: No crossunder (already below)
    print("\n2. No crossunder (already below):")
    prev1, curr1 = 9, 8  # Was below, still below
    prev2, curr2 = 11, 11
    result = crossunder_value(curr1, prev1, curr2, prev2)
    print(f"   Series1: {prev1} → {curr1}")
    print(f"   Series2: {prev2} → {curr2}")
    print(f"   Result: {result} ✅" if not result else f"   Result: {result} ❌")
    
    # Test 3: Equal then below (should be crossunder)
    print("\n3. Equal then below:")
    prev1, curr1 = 11, 10  # Was equal, now below
    prev2, curr2 = 11, 11
    result = crossunder_value(curr1, prev1, curr2, prev2)
    print(f"   Series1: {prev1} → {curr1}")
    print(f"   Series2: {prev2} → {curr2}")
    print(f"   Result: {result} ✅" if result else f"   Result: {result} ❌")
    
    # Test 4: Crossover instead (should be False)
    print("\n4. Crossover instead:")
    prev1, curr1 = 10, 12  # Was below, now above
    prev2, curr2 = 11, 11
    result = crossunder_value(curr1, prev1, curr2, prev2)
    print(f"   Series1: {prev1} → {curr1}")
    print(f"   Series2: {prev2} → {curr2}")
    print(f"   Result: {result} ✅" if not result else f"   Result: {result} ❌")


def test_edge_cases():
    """Test edge cases with None/NaN values"""
    print("\n\n🧪 Testing edge cases...")
    print("=" * 50)
    
    # Test with None values
    print("\n1. None values:")
    result1 = crossover_value(12, None, 11, 11)
    result2 = crossunder_value(10, 12, None, 11)
    print(f"   Crossover with None: {result1} (should be False)")
    print(f"   Crossunder with None: {result2} (should be False)")
    
    # Test with NaN values
    print("\n2. NaN values:")
    result3 = crossover_value(12, float('nan'), 11, 11)
    result4 = crossunder_value(10, 12, 11, float('nan'))
    print(f"   Crossover with NaN: {result3} (should be False)")
    print(f"   Crossunder with NaN: {result4} (should be False)")


def test_real_world_example():
    """Test with real-world kernel values"""
    print("\n\n🧪 Testing real-world kernel example...")
    print("=" * 50)
    
    # Simulate kernel values
    yhat1_prev, yhat1_curr = 100.5, 101.2  # Main kernel rising
    yhat2_prev, yhat2_curr = 100.2, 101.5  # Smoothed kernel rising faster
    
    print(f"\nKernel values:")
    print(f"   Main (yhat1): {yhat1_prev} → {yhat1_curr}")
    print(f"   Smoothed (yhat2): {yhat2_prev} → {yhat2_curr}")
    
    # Check if smoothed crosses above main
    bullish_cross = crossover_value(yhat2_curr, yhat2_prev, yhat1_curr, yhat1_prev)
    bearish_cross = crossunder_value(yhat2_curr, yhat2_prev, yhat1_curr, yhat1_prev)
    
    print(f"\nResults:")
    print(f"   Bullish crossover: {bullish_cross}")
    print(f"   Bearish crossunder: {bearish_cross}")
    
    if bullish_cross:
        print("   📈 Bullish signal detected!")
    elif bearish_cross:
        print("   📉 Bearish signal detected!")
    else:
        print("   ➡️ No crossover detected")


if __name__ == "__main__":
    print("Testing Pine Script Crossover Functions")
    print("=" * 60)
    
    test_crossover_value()
    test_crossunder_value()
    test_edge_cases()
    test_real_world_example()
    
    print("\n\n✅ All tests completed!")
    print("\nNow you can run: python test_ml_fix_final.py")
