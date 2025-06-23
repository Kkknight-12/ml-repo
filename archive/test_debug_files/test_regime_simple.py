#!/usr/bin/env python3
"""
Simple Regime Filter Test
=========================

Tests the regime filter with sample data.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.regime_filter_fix import StatefulRegimeFilter
import math
import random

print("="*80)
print("SIMPLE REGIME FILTER TEST")
print("="*80)

# Create regime filter
regime_filter = StatefulRegimeFilter()
threshold = -0.1

# Generate sample data that simulates trending and ranging markets
def generate_sample_data(num_bars=200):
    data = []
    base_price = 1000
    
    for i in range(num_bars):
        # Create trending and ranging periods
        if i < 50:  # Initial uptrend
            base_price += random.uniform(0, 5)
            volatility = 2
        elif i < 100:  # Ranging period
            base_price += random.uniform(-2, 2)
            volatility = 5
        elif i < 150:  # Downtrend
            base_price -= random.uniform(0, 5)
            volatility = 3
        else:  # Another ranging period
            base_price += random.uniform(-3, 3)
            volatility = 6
            
        # Generate OHLC
        open_price = base_price + random.uniform(-volatility, volatility)
        high = open_price + random.uniform(0, volatility)
        low = open_price - random.uniform(0, volatility)
        close = random.uniform(low, high)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close
        })
    
    return data

# Generate data
data = generate_sample_data(200)
print(f"Generated {len(data)} bars of sample data")

# Process bars
passes = 0
total = 0
values_log = []

print(f"\nProcessing with threshold={threshold}...")
print("-" * 80)

for i, bar in enumerate(data):
    ohlc4 = (bar['open'] + bar['high'] + bar['low'] + bar['close']) / 4
    
    # Update regime filter
    normalized_slope_decline = regime_filter.update(ohlc4, bar['high'], bar['low'])
    
    # Skip warmup period
    if i >= 50:  # Give enough warmup time
        total += 1
        if normalized_slope_decline >= threshold:
            passes += 1
        
        values_log.append(normalized_slope_decline)
        
        # Print sample values
        if i in [50, 60, 70, 100, 120, 150, 180]:
            pass_rate = (passes / total * 100) if total > 0 else 0
            print(f"Bar {i}: OHLC4={ohlc4:.2f}, NSD={normalized_slope_decline:7.4f}, "
                  f"Passes={normalized_slope_decline >= threshold}, "
                  f"Rate={pass_rate:.1f}% ({passes}/{total})")

# Analyze the distribution of values
if values_log:
    min_val = min(values_log)
    max_val = max(values_log)
    avg_val = sum(values_log) / len(values_log)
    
    # Count values in different ranges
    ranges = {
        "< -1.0": sum(1 for v in values_log if v < -1.0),
        "-1.0 to -0.5": sum(1 for v in values_log if -1.0 <= v < -0.5),
        "-0.5 to -0.1": sum(1 for v in values_log if -0.5 <= v < -0.1),
        "-0.1 to 0": sum(1 for v in values_log if -0.1 <= v < 0),
        "0 to 0.5": sum(1 for v in values_log if 0 <= v < 0.5),
        "> 0.5": sum(1 for v in values_log if v >= 0.5),
    }

print("-" * 80)
print(f"\nVALUE DISTRIBUTION ANALYSIS:")
print(f"Min value: {min_val:.4f}")
print(f"Max value: {max_val:.4f}")
print(f"Avg value: {avg_val:.4f}")
print(f"\nValue ranges:")
for range_name, count in ranges.items():
    pct = count / len(values_log) * 100
    print(f"  {range_name}: {count} ({pct:.1f}%)")

print("-" * 80)
print(f"\nFINAL RESULTS:")
print(f"Total bars processed: {total}")
print(f"Bars that passed filter (NSD >= -0.1): {passes}")
print(f"Pass rate: {passes/total*100:.1f}%")
print(f"Expected: ~35%")
print(f"Status: {'✅ CLOSE' if 25 <= passes/total*100 <= 45 else '❌ OFF'}")

# Debug: Show what the filter state looks like
print(f"\nFILTER STATE AT END:")
print(f"  value1: {regime_filter.value1:.6f}")
print(f"  value2: {regime_filter.value2:.6f}")
print(f"  klmf: {regime_filter.klmf:.2f}")
print(f"  bars_processed: {regime_filter.bars_processed}")