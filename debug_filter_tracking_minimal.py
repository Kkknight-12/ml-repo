#!/usr/bin/env python3
"""
Minimal test to debug filter tracking
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Simple simulation of what should happen
print("="*50)
print("FILTER TRACKING DEBUG")
print("="*50)

# Simulate result from bar processor
filter_states_from_processor = {
    "volatility": True,
    "regime": False,
    "adx": True
}

# Initialize tracking dict like in comprehensive test
filter_tracking = {
    'volatility_passes': 0,
    'regime_passes': 0,
    'adx_passes': 0,
    'all_pass': 0
}

print(f"\nProcessor returns: {filter_states_from_processor}")
print(f"Tracking dict has keys: {list(filter_tracking.keys())}")

# Apply the fix
print("\nApplying fix logic:")
for filter_name, passed in filter_states_from_processor.items():
    key = f"{filter_name}_passes"
    print(f"  Checking {filter_name}={passed}, key={key}")
    if passed and key in filter_tracking:
        filter_tracking[key] += 1
        print(f"    ✅ Incremented {key}")
    else:
        print(f"    ❌ Not incremented (passed={passed}, key_exists={key in filter_tracking})")

# Check all pass
if all(filter_states_from_processor.values()):
    filter_tracking['all_pass'] += 1
    print("  ✅ All filters passed")
else:
    print("  ❌ Not all filters passed")

print(f"\nFinal tracking: {filter_tracking}")

# Calculate pass rates
bars_processed = 1
print(f"\nPass rates (with {bars_processed} bar):")
for filter_name in ['volatility', 'regime', 'adx', 'all']:
    key = f"{filter_name}_passes"
    if key in filter_tracking:
        pass_rate = filter_tracking[key] / bars_processed * 100
        print(f"  {filter_name}: {pass_rate:.1f}%")

# Test with 100 bars
print("\n" + "="*50)
print("Simulating 100 bars with 38% filter pass rate:")
filter_tracking = {
    'volatility_passes': 48,
    'regime_passes': 81,
    'adx_passes': 100,
    'all_pass': 38
}
bars_processed = 100

print(f"\nRaw counts: {filter_tracking}")
print(f"Bars processed: {bars_processed}")

print("\nCalculated pass rates:")
for filter_name in ['volatility', 'regime', 'adx', 'all']:
    key = f"{filter_name}_passes"
    if key in filter_tracking:
        pass_rate = filter_tracking[key] / bars_processed * 100
        print(f"  {filter_name}: {pass_rate:.1f}%")

# Verify calculation function
def calculate_filter_rates(filter_states, bars_processed):
    if bars_processed > 0:
        for filter_name in ['volatility', 'regime', 'adx', 'all']:
            key = f"{filter_name}_passes"
            if key in filter_states:
                pass_rate = filter_states[key] / bars_processed * 100
                filter_states[f"{filter_name}_pass_rate"] = pass_rate
    return filter_states

print("\nUsing calculation function:")
result = calculate_filter_rates(filter_tracking.copy(), bars_processed)
for key, value in result.items():
    if key.endswith('_pass_rate'):
        print(f"  {key}: {value:.1f}%")
