#!/usr/bin/env python3
"""
Verify Array Indices Are Correct
=================================
Make sure we're accessing the right elements after array order fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_array_indexing():
    """Test Python list indexing to be absolutely sure"""
    
    print("=" * 80)
    print("📊 ARRAY INDEXING VERIFICATION")
    print("=" * 80)
    
    # Test 1: Basic append behavior
    print("\n1. TESTING APPEND BEHAVIOR:")
    arr = []
    for i in range(5):
        arr.append(i)
        print(f"   After append({i}): {arr}")
    
    print(f"\n   arr[0] = {arr[0]} (should be 0 - oldest)")
    print(f"   arr[-1] = {arr[-1]} (should be 4 - newest)")
    
    # Test 2: Pine Script style array operations
    print("\n2. PINE SCRIPT STYLE OPERATIONS:")
    print("   Pine: array.push() → Python: list.append()")
    print("   Pine: array.get(arr, 0) → Python: arr[0]")
    print("   Pine: array.shift() → Python: arr.pop(0)")
    
    # Test 3: Training data access
    print("\n3. TRAINING DATA ACCESS TEST:")
    y_train = []
    labels = [1, -1, 1, -1, 0, 1, -1]
    for label in labels:
        y_train.append(label)
    
    print(f"   Training array: {y_train}")
    print(f"   Accessing with i=0: {y_train[0]} (oldest)")
    print(f"   Accessing with i=1: {y_train[1]}")
    print(f"   Accessing with i=2: {y_train[2]}")
    
    # Test 4: Feature array access
    print("\n4. FEATURE ARRAY ACCESS TEST:")
    features = []
    for i in range(10):
        features.append(0.5 + i * 0.05)
    
    print(f"   Feature array: {[f'{x:.2f}' for x in features]}")
    print(f"   features[0] = {features[0]:.2f} (oldest)")
    print(f"   features[5] = {features[5]:.2f}")
    print(f"   features[-1] = {features[-1]:.2f} (newest)")
    
    # Test 5: Distance calculation simulation
    print("\n5. DISTANCE CALCULATION SIMULATION:")
    current = 0.75
    for i in range(5):
        historical = features[i]
        distance = abs(current - historical)
        print(f"   i={i}: current={current}, hist={historical:.2f}, distance={distance:.3f}")
    
    # Test 6: Modulo check
    print("\n6. MODULO CHECK (i % 4 != 0):")
    for i in range(12):
        passes = i % 4 != 0
        print(f"   i={i}: i%4={i%4}, passes={passes}")
    
    print("\n✅ All checks complete!")

if __name__ == "__main__":
    test_array_indexing()
