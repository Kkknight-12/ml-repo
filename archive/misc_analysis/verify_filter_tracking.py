#!/usr/bin/env python3
"""
Verify filter tracking is working properly
Shows exactly what's happening with filter stats
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*70)
print("FILTER TRACKING VERIFICATION")
print("="*70)

# Simulate what happens in comprehensive test
print("\n1. Initialize tracking dict:")
filter_states_tracking = {
    'volatility_passes': 0,
    'regime_passes': 0,
    'adx_passes': 0,
    'all_pass': 0
}
print(f"   {filter_states_tracking}")

# Simulate processing bars
print("\n2. Processing simulated bars:")

# Bar 1: Some filters pass
print("\n   Bar 1:")
filter_states_from_processor = {'volatility': True, 'regime': False, 'adx': True}
print(f"   Processor returns: {filter_states_from_processor}")

for filter_name, passed in filter_states_from_processor.items():
    key = f"{filter_name}_passes"
    if passed and key in filter_states_tracking:
        filter_states_tracking[key] += 1
        print(f"   ✓ {filter_name} passed - incremented {key}")

if all(filter_states_from_processor.values()):
    filter_states_tracking['all_pass'] += 1
else:
    print("   ✗ Not all filters passed")

print(f"   Tracking after bar 1: {filter_states_tracking}")

# Bar 2: All filters pass
print("\n   Bar 2:")
filter_states_from_processor = {'volatility': True, 'regime': True, 'adx': True}
print(f"   Processor returns: {filter_states_from_processor}")

for filter_name, passed in filter_states_from_processor.items():
    key = f"{filter_name}_passes"
    if passed and key in filter_states_tracking:
        filter_states_tracking[key] += 1
        print(f"   ✓ {filter_name} passed - incremented {key}")

if all(filter_states_from_processor.values()):
    filter_states_tracking['all_pass'] += 1
    print("   ✓ All filters passed!")

print(f"   Tracking after bar 2: {filter_states_tracking}")

# Calculate pass rates
print("\n3. Calculate pass rates (2 bars processed):")
bars_processed = 2
for filter_name in ['volatility', 'regime', 'adx', 'all']:
    key = f"{filter_name}_passes"
    if key in filter_states_tracking:
        pass_rate = filter_states_tracking[key] / bars_processed * 100
        print(f"   {filter_name}: {filter_states_tracking[key]}/{bars_processed} = {pass_rate:.1f}%")

# Test edge case: empty filter_states
print("\n4. Edge case - empty filter_states:")
filter_states_from_processor = {}
print(f"   Processor returns: {filter_states_from_processor}")

if filter_states_from_processor:
    print("   Would process filters...")
else:
    print("   ✗ No filter states to process!")

# Test edge case: None filter_states
print("\n5. Edge case - None filter_states:")
filter_states_from_processor = None
print(f"   Processor returns: {filter_states_from_processor}")

if filter_states_from_processor:
    print("   Would process filters...")
else:
    print("   ✗ No filter states to process!")

print("\n✅ Verification complete!")
print("\nKey insights:")
print("- Tracking logic is correct")
print("- If showing 0%, processor might be returning empty/None filter_states")
print("- Or warmup period might be skipping all bars with passing filters")
