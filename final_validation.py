#!/usr/bin/env python3
"""Comprehensive validation after fixes"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
import csv

print("=== COMPREHENSIVE VALIDATION ===\n")

# Configure with Pine Script defaults
config = TradingConfig(
    # ML settings (matching Pine Script)
    neighbors_count=8,
    max_bars_back=2000,
    feature_count=5,
    
    # Filter settings (matching Pine Script defaults)
    use_volatility_filter=True,
    use_regime_filter=True,
    use_adx_filter=False,  # Pine Script default
    regime_threshold=-0.1,
    adx_threshold=20,
    
    # Kernel settings (matching Pine Script)
    use_kernel_filter=True,
    kernel_lookback=8,
    kernel_relative_weight=8.0,
    kernel_regression_level=25,
    use_kernel_smoothing=False,
    kernel_lag=2,
    
    # Other settings
    use_ema_filter=False,  # Pine Script default
    use_sma_filter=False,  # Pine Script default
)

print("Configuration Summary:")
print(f"  ADX Filter: {config.use_adx_filter} (Pine Script default: false)")
print(f"  Regime Filter: {config.use_regime_filter}")
print(f"  Volatility Filter: {config.use_volatility_filter}")
print(f"  Kernel Settings: h={config.kernel_lookback}, r={config.kernel_relative_weight}, x={config.kernel_regression_level}")

# Process CSV
csv_file = "NSE_ICICIBANK, 5.csv"
processor = BarProcessor(config)

with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    csv_data = list(reader)

print(f"\nProcessing {len(csv_data)} bars...")

signals_found = []
kernel_issues = []

for i, row in enumerate(csv_data):
    result = processor.process_bar(
        float(row['open']),
        float(row['high']),
        float(row['low']),
        float(row['close']),
        0
    )
    
    # Track signals
    if result.start_long_trade:
        signals_found.append({
            'bar': i+1,
            'type': 'BUY',
            'price': float(row['close']),
            'time': row['time']
        })
    elif result.start_short_trade:
        signals_found.append({
            'bar': i+1,
            'type': 'SELL',
            'price': float(row['close']),
            'time': row['time']
        })
    
    # Check kernel calculation around problem area
    if 235 <= i <= 250:
        from core.kernel_functions import rational_quadratic
        
        source_values = []
        for j in range(len(processor.bars)):
            source_values.append(processor.bars.get_close(j))
        
        if source_values:
            kernel_est = rational_quadratic(source_values, 8, 8.0, 25)
            csv_kernel = float(row['Kernel Regression Estimate'])
            diff = abs(kernel_est - csv_kernel)
            
            if diff > 10:  # Large difference
                kernel_issues.append({
                    'bar': i+1,
                    'python': kernel_est,
                    'csv': csv_kernel,
                    'diff': diff
                })
    
    # Show progress
    if (i+1) % 100 == 0:
        print(f"  Processed {i+1} bars...")

print(f"\n✓ Processing complete!")

# Results Summary
print("\n=== RESULTS SUMMARY ===")
print(f"Total Signals: {len(signals_found)}")
print(f"Pine Script Expected: ~8 signals")
print(f"Status: {'✅ Close match!' if 6 <= len(signals_found) <= 10 else '⚠️ Still different'}")

# Signal Details
if signals_found:
    print("\nSignal Details:")
    for sig in signals_found:
        print(f"  {sig['type']} at bar {sig['bar']} (₹{sig['price']:.2f}) - {sig['time']}")

# Kernel Issues
if kernel_issues:
    print(f"\n⚠️ Kernel Issues Found: {len(kernel_issues)}")
    print("First 3 issues:")
    for issue in kernel_issues[:3]:
        print(f"  Bar {issue['bar']}: Python={issue['python']:.2f}, CSV={issue['csv']:.2f}, Diff={issue['diff']:.2f}")
else:
    print("\n✅ No major kernel issues!")

# Filter Analysis
print("\n=== FILTER BEHAVIOR ===")
print("Expected:")
print("  - Volatility: ~30-50% pass rate")
print("  - Regime: ~30-50% pass rate") 
print("  - ADX: 100% (disabled)")
print("\nNote: Run validate_scanner.py for detailed filter statistics")

print("\n=== RECOMMENDATIONS ===")
if len(signals_found) > 10:
    print("1. ❌ Too many signals - check filter thresholds")
    print("2. Consider enabling ADX filter")
    print("3. Adjust kernel parameters if needed")
elif len(signals_found) < 6:
    print("1. ❌ Too few signals - filters might be too strict")
    print("2. Check regime filter threshold")
    print("3. Verify feature calculations")
else:
    print("1. ✅ Signal count looks good!")
    print("2. Verify exact signal timing with Pine Script")
    print("3. Check if kernel values match closely")

print("\n=== DONE ===")
