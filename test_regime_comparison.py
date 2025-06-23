#!/usr/bin/env python3
"""
Compare Regime Filter V2 on Different Data Types
===============================================

This compares the regime filter behavior on synthetic vs realistic data patterns.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.regime_filter_fix_v2 import StatefulRegimeFilterV2
import numpy as np
import logging

# Set up logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

print("="*80)
print("REGIME FILTER V2 COMPARISON TEST")
print("="*80)

threshold = -0.1

# Test 1: Synthetic Data (like test_regime_v2.py)
print("\n1. SYNTHETIC DATA TEST (Controlled Patterns)")
print("-" * 80)

regime_filter1 = StatefulRegimeFilterV2()
test_data1 = []
base_price = 100

# Generate trending and ranging periods (same as test_regime_v2.py)
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
    
    test_data1.append({
        'ohlc4': ohlc4,
        'high': high,
        'low': low
    })

# Process synthetic data
passes1 = 0
total1 = 0

for i, bar in enumerate(test_data1):
    nsd = regime_filter1.update(bar['ohlc4'], bar['high'], bar['low'])
    
    if i >= 50:  # Skip warmup
        total1 += 1
        if nsd >= threshold:
            passes1 += 1

pass_rate1 = (passes1 / total1 * 100) if total1 > 0 else 0
print(f"Synthetic Data Results: {passes1}/{total1} bars passed = {pass_rate1:.1f}%")

# Test 2: Realistic Market-Like Data
print("\n2. REALISTIC MARKET DATA TEST (Random Walk with Trends)")
print("-" * 80)

regime_filter2 = StatefulRegimeFilterV2()
test_data2 = []

# Generate more realistic market data using random walk with drift
np.random.seed(42)  # For reproducibility
base_price = 1000  # Starting at 1000 like ICICIBANK

for i in range(200):
    # Add trend components
    if i < 50:
        drift = 0.001  # Slight uptrend
    elif i < 100:
        drift = -0.0005  # Slight downtrend
    elif i < 150:
        drift = 0.0  # Sideways
    else:
        drift = 0.0015  # Stronger uptrend
    
    # Random walk with drift
    daily_return = np.random.normal(drift, 0.015)  # 1.5% daily volatility
    base_price *= (1 + daily_return)
    
    # Generate realistic OHLC
    daily_range = abs(np.random.normal(0, 0.01)) * base_price  # Daily range
    
    if daily_return > 0:
        # Up day
        open_price = base_price - daily_range * 0.3
        close_price = base_price
        high = base_price + daily_range * 0.2
        low = open_price - daily_range * 0.1
    else:
        # Down day
        open_price = base_price + daily_range * 0.3
        close_price = base_price
        high = open_price + daily_range * 0.1
        low = base_price - daily_range * 0.2
    
    # Ensure high/low bounds
    high = max(high, open_price, close_price)
    low = min(low, open_price, close_price)
    
    ohlc4 = (open_price + high + low + close_price) / 4
    
    test_data2.append({
        'ohlc4': ohlc4,
        'high': high,
        'low': low
    })

# Process realistic data
passes2 = 0
total2 = 0
nsd_values2 = []

for i, bar in enumerate(test_data2):
    nsd = regime_filter2.update(bar['ohlc4'], bar['high'], bar['low'])
    
    if i >= 50:  # Skip warmup
        total2 += 1
        nsd_values2.append(nsd)
        if nsd >= threshold:
            passes2 += 1

pass_rate2 = (passes2 / total2 * 100) if total2 > 0 else 0
print(f"Realistic Data Results: {passes2}/{total2} bars passed = {pass_rate2:.1f}%")

# Test 3: Low Volatility Period (might explain ICICIBANK results)
print("\n3. LOW VOLATILITY TEST (Stable Market)")
print("-" * 80)

regime_filter3 = StatefulRegimeFilterV2()
test_data3 = []
base_price = 1000

# Generate low volatility, ranging market
for i in range(200):
    # Very small random movements
    daily_change = np.random.normal(0, 0.003)  # 0.3% daily volatility (very low)
    base_price *= (1 + daily_change)
    
    # Tight daily ranges
    daily_range = abs(np.random.normal(0, 0.002)) * base_price
    
    high = base_price + daily_range / 2
    low = base_price - daily_range / 2
    ohlc4 = base_price  # Approximation for tight range
    
    test_data3.append({
        'ohlc4': ohlc4,
        'high': high,
        'low': low
    })

# Process low volatility data
passes3 = 0
total3 = 0

for i, bar in enumerate(test_data3):
    nsd = regime_filter3.update(bar['ohlc4'], bar['high'], bar['low'])
    
    if i >= 50:  # Skip warmup
        total3 += 1
        if nsd >= threshold:
            passes3 += 1

pass_rate3 = (passes3 / total3 * 100) if total3 > 0 else 0
print(f"Low Volatility Results: {passes3}/{total3} bars passed = {pass_rate3:.1f}%")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"1. Synthetic Data (test_regime_v2.py style): {pass_rate1:.1f}%")
print(f"2. Realistic Market Data (random walk):      {pass_rate2:.1f}%")
print(f"3. Low Volatility Market:                    {pass_rate3:.1f}%")
print(f"\nTarget (Pine Script): ~35%")

# Analyze NSD distribution for realistic data
print("\nNSD Value Distribution (Realistic Data):")
print("-" * 50)
if nsd_values2:
    print(f"Mean NSD: {np.mean(nsd_values2):.4f}")
    print(f"Std Dev:  {np.std(nsd_values2):.4f}")
    print(f"Min NSD:  {np.min(nsd_values2):.4f}")
    print(f"Max NSD:  {np.max(nsd_values2):.4f}")
    
    # Count values in ranges
    very_neg = sum(1 for v in nsd_values2 if v < -0.5)
    neg = sum(1 for v in nsd_values2 if -0.5 <= v < -0.1)
    near = sum(1 for v in nsd_values2 if -0.1 <= v < 0)
    pos = sum(1 for v in nsd_values2 if 0 <= v < 0.5)
    very_pos = sum(1 for v in nsd_values2 if v >= 0.5)
    
    print(f"\nDistribution:")
    print(f"  < -0.5:        {very_neg} ({very_neg/len(nsd_values2)*100:.1f}%)")
    print(f"  -0.5 to -0.1:  {neg} ({neg/len(nsd_values2)*100:.1f}%)")
    print(f"  -0.1 to 0:     {near} ({near/len(nsd_values2)*100:.1f}%)")
    print(f"  0 to 0.5:      {pos} ({pos/len(nsd_values2)*100:.1f}%)")
    print(f"  >= 0.5:        {very_pos} ({very_pos/len(nsd_values2)*100:.1f}%)")

print("\n✅ Comparison complete!")