#!/usr/bin/env python3
"""Debug regime filter internals"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import math

print("=== Regime Filter Internal Debug ===\n")

# Simulate the regime filter calculation for a simple case
print("Simulating regime filter calculation:")

# Simple uptrend data (50 bars for easier debugging)
src_chronological = [100.0 + i * 0.5 for i in range(50)]
high_chronological = [val + 0.5 for val in src_chronological]
low_chronological = [val - 0.5 for val in src_chronological]

# Initialize variables like in regime_filter
value1 = 0.0
value2 = 0.0
klmf = 0.0
klmf_values = []
abs_curve_slopes = []

print(f"Processing {len(src_chronological)} bars...")

# Process last 10 bars to see values
for i in range(1, len(src_chronological)):
    # Update value1 and value2
    value1 = 0.2 * (src_chronological[i] - src_chronological[i-1]) + 0.8 * value1
    
    # Use actual high-low range
    high_low_range = high_chronological[i] - low_chronological[i]
    value2 = 0.1 * high_low_range + 0.8 * value2
    
    # Calculate omega and alpha
    omega = abs(value1 / value2) if value2 != 0 else 0
    alpha = (-omega * omega + math.sqrt(omega ** 4 + 16 * omega ** 2)) / 8
    
    # Update KLMF
    klmf = alpha * src_chronological[i] + (1 - alpha) * klmf
    klmf_values.append(klmf)
    
    # Calculate absolute curve slope
    if i > 1 and len(klmf_values) > 1:
        abs_curve_slope = abs(klmf - klmf_values[-2])
        abs_curve_slopes.append(abs_curve_slope)
    
    # Print last few values
    if i >= len(src_chronological) - 5:
        print(f"\nBar {i}:")
        print(f"  Price: {src_chronological[i]:.2f}")
        print(f"  value1: {value1:.4f}, value2: {value2:.4f}")
        print(f"  omega: {omega:.4f}, alpha: {alpha:.4f}")
        print(f"  KLMF: {klmf:.2f}")
        if abs_curve_slopes:
            print(f"  Abs Slope: {abs_curve_slopes[-1]:.4f}")

# Calculate final normalized slope decline
if len(abs_curve_slopes) >= 20:
    # EMA of slopes
    ema_length = min(200, len(abs_curve_slopes))
    multiplier = 2.0 / (ema_length + 1)
    exp_avg_slope = abs_curve_slopes[0]
    
    for slope in abs_curve_slopes[1:]:
        exp_avg_slope = slope * multiplier + exp_avg_slope * (1 - multiplier)
    
    current_slope = abs_curve_slopes[-1]
    normalized_slope_decline = (current_slope - exp_avg_slope) / exp_avg_slope if exp_avg_slope > 0 else 0
    
    print(f"\n=== Final Calculation ===")
    print(f"Current slope: {current_slope:.6f}")
    print(f"Avg slope (EMA): {exp_avg_slope:.6f}")
    print(f"Normalized decline: {normalized_slope_decline:.6f}")
    print(f"\nWith threshold -0.1: {normalized_slope_decline >= -0.1}")

print("\n=== Debug Complete ===")
