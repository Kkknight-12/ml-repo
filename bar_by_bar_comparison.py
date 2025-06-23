#!/usr/bin/env python3
"""
Bar-by-bar comparison to identify signal differences
Shows detailed info for each bar to understand why signals differ
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from core.kernel_functions import rational_quadratic
import csv
from datetime import datetime

print("=== BAR-BY-BAR SIGNAL ANALYSIS ===\n")

# Configure with Pine Script defaults
config = TradingConfig(
    neighbors_count=8,
    max_bars_back=2000,
    feature_count=5,
    use_volatility_filter=True,
    use_regime_filter=True,
    use_adx_filter=False,
    regime_threshold=-0.1,
    adx_threshold=20,
    use_kernel_filter=True,
    kernel_lookback=8,
    kernel_relative_weight=8.0,
    kernel_regression_level=25,
    use_kernel_smoothing=False,
    use_ema_filter=False,
    use_sma_filter=False,
)

# Load CSV
csv_file = "NSE_ICICIBANK, 5.csv"
processor = BarProcessor(config)

# Track all bars with signals or near-signals
interesting_bars = []
all_bars_data = []

print("Processing all bars...\n")

with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    csv_data = list(reader)

for i, row in enumerate(csv_data):
    # Process bar
    result = processor.process_bar(
        float(row['open']),
        float(row['high']),
        float(row['low']),
        float(row['close']),
        0
    )
    
    # Get kernel value
    source_values = []
    for j in range(len(processor.bars)):
        source_values.append(processor.bars.get_close(j))
    
    kernel_python = rational_quadratic(source_values, 8, 8.0, 25) if source_values else 0
    kernel_csv = float(row['Kernel Regression Estimate'])
    
    # Store bar data
    bar_data = {
        'bar': i + 1,
        'time': row['time'],
        'close': float(row['close']),
        'prediction': result.prediction,
        'signal': result.signal,
        'filters': result.filter_states.copy(),
        'kernel_python': kernel_python,
        'kernel_csv': kernel_csv,
        'kernel_diff': abs(kernel_python - kernel_csv),
        'start_long': result.start_long_trade,
        'start_short': result.start_short_trade,
        'strength': result.prediction_strength
    }
    
    all_bars_data.append(bar_data)
    
    # Track interesting bars
    if (result.start_long_trade or result.start_short_trade or 
        abs(result.prediction) >= 6 or  # Strong prediction
        bar_data['kernel_diff'] > 5):    # Large kernel difference
        interesting_bars.append(bar_data)

# Find Pine Script signals from CSV
pine_signals = []
for i, row in enumerate(csv_data):
    if row.get('Buy', '') != 'NaN' and row['Buy'] != '':
        pine_signals.append({'bar': i+1, 'type': 'BUY', 'price': float(row['Buy'])})
    if row.get('Sell', '') != 'NaN' and row['Sell'] != '':
        pine_signals.append({'bar': i+1, 'type': 'SELL', 'price': float(row['Sell'])})

# Python signals
python_signals = [bar for bar in all_bars_data if bar['start_long'] or bar['start_short']]

print("=== SIGNAL COMPARISON ===")
print(f"Pine Script Signals: {len(pine_signals)}")
print(f"Python Signals: {len(python_signals)}")
print(f"Difference: {len(python_signals) - len(pine_signals)} extra signals\n")

# Show Pine Script signals
print("Pine Script Signals:")
for sig in pine_signals:
    print(f"  Bar {sig['bar']:3}: {sig['type']} @ ₹{sig['price']:.2f}")

print("\nPython Signals:")
for bar in python_signals:
    sig_type = "BUY" if bar['start_long'] else "SELL"
    print(f"  Bar {bar['bar']:3}: {sig_type} @ ₹{bar['close']:.2f} | "
          f"Pred={bar['prediction']:2.0f} | Filters: V={bar['filters']['volatility']}, "
          f"R={bar['filters']['regime']}, A={bar['filters']['adx']}")

# Find mismatches
print("\n=== SIGNAL MISMATCHES ===")
pine_bars = {sig['bar'] for sig in pine_signals}
python_bars = {bar['bar'] for bar in python_signals}

extra_python = python_bars - pine_bars
missing_python = pine_bars - python_bars

if extra_python:
    print(f"\nExtra Python Signals (not in Pine Script): {sorted(extra_python)}")
    for bar_num in sorted(extra_python):
        bar = all_bars_data[bar_num - 1]
        print(f"\n  Bar {bar_num} Analysis:")
        print(f"    Time: {bar['time']}")
        print(f"    Price: ₹{bar['close']:.2f}")
        print(f"    ML Prediction: {bar['prediction']}")
        print(f"    Filters: Volatility={bar['filters']['volatility']}, "
              f"Regime={bar['filters']['regime']}, ADX={bar['filters']['adx']}")
        print(f"    Kernel: Python={bar['kernel_python']:.2f}, CSV={bar['kernel_csv']:.2f}")
        print(f"    Signal Strength: {bar['strength']:.1%}")

if missing_python:
    print(f"\nMissing Python Signals (in Pine Script but not Python): {sorted(missing_python)}")
    for bar_num in sorted(missing_python):
        bar = all_bars_data[bar_num - 1]
        print(f"\n  Bar {bar_num} Analysis:")
        print(f"    Time: {bar['time']}")
        print(f"    Price: ₹{bar['close']:.2f}")
        print(f"    ML Prediction: {bar['prediction']}")
        print(f"    Filters: Volatility={bar['filters']['volatility']}, "
              f"Regime={bar['filters']['regime']}, ADX={bar['filters']['adx']}")
        print(f"    Why no signal? Check entry conditions")

# Analyze bars around signals
print("\n=== DETAILED BAR ANALYSIS (Around Signals) ===")
for sig in pine_signals[:3]:  # First 3 Pine signals
    bar_num = sig['bar']
    print(f"\nAround Pine Signal at Bar {bar_num}:")
    
    # Show 2 bars before and after
    for offset in range(-2, 3):
        idx = bar_num - 1 + offset
        if 0 <= idx < len(all_bars_data):
            bar = all_bars_data[idx]
            marker = ">>>" if offset == 0 else "   "
            print(f"{marker} Bar {bar['bar']:3}: Close=₹{bar['close']:.2f}, "
                  f"Pred={bar['prediction']:2.0f}, "
                  f"V={int(bar['filters']['volatility'])}, "
                  f"R={int(bar['filters']['regime'])}, "
                  f"Signal={'BUY' if bar['start_long'] else 'SELL' if bar['start_short'] else 'NONE'}")

# High prediction bars without signals
print("\n=== HIGH PREDICTIONS WITHOUT SIGNALS ===")
high_pred_no_signal = [bar for bar in all_bars_data 
                       if abs(bar['prediction']) >= 6 
                       and not bar['start_long'] 
                       and not bar['start_short']]

for bar in high_pred_no_signal[:5]:
    print(f"  Bar {bar['bar']}: Prediction={bar['prediction']}, "
          f"Filters: V={bar['filters']['volatility']}, "
          f"R={bar['filters']['regime']}, A={bar['filters']['adx']}")

print("\n=== RECOMMENDATIONS ===")
print("1. Check entry logic for extra Python signals")
print("2. Verify kernel bullish/bearish conditions")
print("3. Compare exact filter calculations with Pine Script")
print("4. Check if signal history affects entry conditions")

print("\n=== DONE ===")
