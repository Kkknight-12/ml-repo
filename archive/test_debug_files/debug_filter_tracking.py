#!/usr/bin/env python3
"""
Debug filter tracking issue
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Check if we have the right filter tracking logic
print("Checking filter tracking logic...")

# Simulate what happens in comprehensive test
filter_states_from_processor = {
    "volatility": True,
    "regime": False,
    "adx": True
}

# Initialize tracking dict like comprehensive test
tracking_dict = {
    'volatility_passes': 0,
    'regime_passes': 0,
    'adx_passes': 0,
    'all_pass': 0
}

print(f"\nProcessor returns: {filter_states_from_processor}")
print(f"Tracking dict has: {list(tracking_dict.keys())}")

# Test OLD logic (broken)
print("\n❌ OLD Logic (broken):")
for filter_name, passed in filter_states_from_processor.items():
    if passed and filter_name in tracking_dict:
        print(f"  Checking '{filter_name}' in tracking_dict: {filter_name in tracking_dict}")
        
# Test NEW logic (should work)
print("\n✅ NEW Logic (fixed):")
for filter_name, passed in filter_states_from_processor.items():
    key = f"{filter_name}_passes"
    if passed and key in tracking_dict:
        print(f"  Checking '{key}' in tracking_dict: {key in tracking_dict}")
        tracking_dict[key] += 1

print(f"\nFinal counts: {tracking_dict}")

# Now let's check if the comprehensive test has the fix
print("\n" + "="*50)
print("Checking comprehensive test file...")

with open('test_zerodha_comprehensive.py', 'r') as f:
    content = f.read()
    
# Look for the filter tracking section
if 'key = f"{filter_name}_passes"' in content:
    print("✅ Fix IS present in comprehensive test")
else:
    print("❌ Fix NOT found in comprehensive test")

# Check for the specific fixed lines
import re
pattern = r'key = f"\{filter_name\}_passes".*?if passed and key in results\[\'filter_states\'\]'
if re.search(pattern, content, re.DOTALL):
    print("✅ Complete fix pattern found")
    
    # Find and print the actual code
    match = re.search(r'# Track filter performance.*?all_pass.*?\+= 1', content, re.DOTALL)
    if match:
        print("\nActual code in file:")
        print("-" * 40)
        print(match.group())
else:
    print("❌ Fix pattern not found correctly")
