"""
Diagnose Exit Configuration Issues
==================================

Understand why scalping strategy shows such high returns.
"""

import pandas as pd
import numpy as np
import json

# Load the detailed results
with open('optimized_results.json', 'r') as f:
    results = json.load(f)

print("="*60)
print("DIAGNOSING EXIT CONFIGURATION ISSUES")
print("="*60)

# Check scalping results
scalping = results['results']['scalping']['individual_results']

print("\nSCALPING STRATEGY ANALYSIS:")
print("-"*40)

for symbol, data in scalping.items():
    print(f"\n{symbol}:")
    print(f"  Total Return: {data['total_return']:.2f}%")
    print(f"  Win Rate: {data['win_rate']:.1f}%")
    print(f"  Avg Win: {data['avg_win']:.3f}%")
    print(f"  Avg Loss: {data['avg_loss']:.3f}%")
    print(f"  Trades: {data['total_trades']}")
    
    # Calculate compound effect
    avg_per_trade = data['expectancy']
    multiplier = (1 + avg_per_trade/100) ** data['total_trades']
    compound_return = (multiplier - 1) * 100
    
    print(f"\n  Expectancy: {avg_per_trade:.3f}%")
    print(f"  Compound multiplier: {multiplier:.4f}x")
    print(f"  Expected compound return: {compound_return:.2f}%")
    print(f"  Actual return: {data['total_return']:.2f}%")
    
    # Check if reasonable
    if abs(compound_return - data['total_return']) > 10:
        print(f"  ⚠️  MISMATCH!")

# Analyze conservative strategy (should have larger targets)
print("\n" + "="*60)
print("CONSERVATIVE STRATEGY ANALYSIS:")
print("-"*40)

conservative = results['results']['conservative']['individual_results']

for symbol, data in conservative.items():
    print(f"\n{symbol}:")
    print(f"  Total Return: {data['total_return']:.2f}%")
    print(f"  Win Rate: {data['win_rate']:.1f}%")
    print(f"  Avg Win: {data['avg_win']:.3f}%")
    print(f"  Avg Loss: {data['avg_loss']:.3f}%")
    
    # Extract config info
    config_str = data['config']
    if 'Stop Loss:' in config_str:
        sl_line = [line for line in config_str.split('\n') if 'Stop Loss:' in line][0]
        target_line = [line for line in config_str.split('\n') if 'Targets:' in line][0]
        print(f"  Config: {sl_line.strip()}")
        print(f"  Config: {target_line.strip()}")

# Key insights
print("\n" + "="*60)
print("KEY INSIGHTS:")
print("="*60)

print("\n1. SCALPING:")
print(f"   - Average win: ~0.4% (very small)")
print(f"   - Average loss: ~0.25% (even smaller)")
print(f"   - Win rate: ~54% (decent)")
print(f"   - Many trades compound to large returns")

print("\n2. CONSERVATIVE:")
print(f"   - Similar small wins/losses")
print(f"   - Lower win rate (42%)")
print(f"   - Negative expectancy")

print("\n3. THE PROBLEM:")
print("   The config shows ADAPTIVE settings (0.11%, 0.2% targets)")
print("   NOT the strategy-specific settings (2% for conservative, 0.5% for scalping)")
print("   This suggests the exit manager is using the wrong config!")

# Let's check what exit types are most common
print("\n" + "="*60)
print("EXIT TYPE ANALYSIS NEEDED")
print("="*60)
print("\nWe need to add logging to see:")
print("1. What targets are ACTUALLY being used")
print("2. What exit reasons are most common")
print("3. Whether the exit config override is working")