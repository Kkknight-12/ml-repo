#!/usr/bin/env python3
"""
Test Regime Filter V2
=====================

Quick test to verify the V2 regime filter implementation.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.regime_filter_fix_v2 import StatefulRegimeFilterV2
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

print("="*80)
print("REGIME FILTER V2 TEST")
print("="*80)

# Create regime filter
regime_filter = StatefulRegimeFilterV2()
threshold = -0.1

# Test with synthetic data
test_data = []
base_price = 100

# Generate trending and ranging periods
for i in range(200):
    if i < 50:  # Uptrend
        base_price += 0.5
        volatility = 0.2
    elif i < 100:  # Range
        base_price += 0.1 * (1 if i % 2 == 0 else -1)
        volatility = 0.5
    elif i < 150:  # Downtrend
        base_price -= 0.5
        volatility = 0.3
    else:  # Range
        base_price += 0.2 * (1 if i % 3 == 0 else -1)
        volatility = 0.6
    
    high = base_price + volatility
    low = base_price - volatility
    ohlc4 = (base_price + high + low + base_price) / 4
    
    test_data.append({
        'ohlc4': ohlc4,
        'high': high,
        'low': low
    })

# Process bars
passes = 0
total = 0

print(f"\nProcessing {len(test_data)} bars...")
print("-" * 80)

for i, bar in enumerate(test_data):
    nsd = regime_filter.update(bar['ohlc4'], bar['high'], bar['low'])
    
    # Skip warmup
    if i >= 50:
        total += 1
        if nsd >= threshold:
            passes += 1
        
        # Print some values
        if i in [50, 75, 100, 125, 150, 175]:
            pass_rate = (passes / total * 100) if total > 0 else 0
            print(f"Bar {i}: OHLC4={bar['ohlc4']:.2f}, NSD={nsd:.4f}, "
                  f"Passes={nsd >= threshold}, Rate={pass_rate:.1f}%")

print("-" * 80)
print(f"\nFINAL RESULTS:")
print(f"Total bars: {total}")
print(f"Passes: {passes}")
print(f"Pass rate: {passes/total*100:.1f}%")
print(f"Target: ~35%")

# Print debug values
print(f"\n\nDEBUG VALUES (first few bars):")
print("-" * 80)
for i, debug in enumerate(regime_filter.debug_values[:5]):
    print(f"Bar {debug['bar']}: v1={debug['value1']:.6f}, v2={debug['value2']:.6f}, "
          f"omega={debug['omega']:.6f}, alpha={debug['alpha']:.6f}, "
          f"NSD={debug['nsd']:.6f}")