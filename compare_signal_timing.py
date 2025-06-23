#!/usr/bin/env python3
"""
Compare exact signal timing between Pine Script and Python
"""

import csv

# Pine Script signals from ICICIBANK CSV
def get_pine_signals(filename):
    signals = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            bar_num = i + 1
            # Check Buy column
            if row['Buy'] and row['Buy'] != 'NaN':
                signals.append({
                    'bar': bar_num,
                    'type': 'BUY',
                    'price': float(row['Buy']),
                    'time': row['time'],
                    'close': float(row['close'])
                })
            # Check Sell column
            if row['Sell'] and row['Sell'] != 'NaN':
                signals.append({
                    'bar': bar_num,
                    'type': 'SELL',
                    'price': float(row['Sell']),
                    'time': row['time'],
                    'close': float(row['close'])
                })
    return signals

# Python signals from output
python_signals_icici = [
    {'bar': 5, 'type': 'SELL', 'price': 1420.50},
    {'bar': 32, 'type': 'BUY', 'price': 1422.80},
    {'bar': 55, 'type': 'BUY', 'price': 1425.60},
    {'bar': 70, 'type': 'BUY', 'price': 1426.00},
    {'bar': 76, 'type': 'BUY', 'price': 1425.90},
    {'bar': 82, 'type': 'SELL', 'price': 1425.70},
    {'bar': 100, 'type': 'SELL', 'price': 1423.30},
    {'bar': 118, 'type': 'SELL', 'price': 1420.90},
    {'bar': 131, 'type': 'SELL', 'price': 1420.00},
    {'bar': 134, 'type': 'BUY', 'price': 1421.00},
    {'bar': 146, 'type': 'BUY', 'price': 1422.20}
]

# Get Pine Script signals
pine_signals = get_pine_signals('NSE_ICICIBANK, 5.csv')

print("=== SIGNAL TIMING COMPARISON (ICICIBANK) ===\n")

# Find matching signals
matching_signals = []
pine_only = []
python_only = []

# Check each Pine signal
pine_bars = {sig['bar']: sig for sig in pine_signals}
python_bars = {sig['bar']: sig for sig in python_signals_icici}

# Find matches and mismatches
all_bars = set(pine_bars.keys()) | set(python_bars.keys())

for bar in sorted(all_bars):
    if bar in pine_bars and bar in python_bars:
        # Match found!
        pine = pine_bars[bar]
        python = python_bars[bar]
        if pine['type'] == python['type']:
            matching_signals.append((bar, pine['type']))
            print(f"✅ MATCH at Bar {bar}: {pine['type']} signal")
            print(f"   Pine: {pine['price']:.2f} | Python: {python['price']:.2f}")
            print(f"   Time: {pine['time']}")
            print()
    elif bar in pine_bars:
        pine_only.append(pine_bars[bar])
    elif bar in python_bars:
        python_only.append(python_bars[bar])

print(f"\n=== SUMMARY ===")
print(f"Matching signals: {len(matching_signals)}")
print(f"Pine-only signals: {len(pine_only)}")
print(f"Python-only signals: {len(python_only)}")

# Show Pine-only signals
if pine_only:
    print(f"\n=== PINE SCRIPT ONLY (Missing in Python) ===")
    for sig in pine_only:
        print(f"Bar {sig['bar']:3}: {sig['type']} @ {sig['price']:.2f} - {sig['time']}")

# Show Python-only signals
if python_only:
    print(f"\n=== PYTHON ONLY (Extra signals) ===")
    for sig in python_only:
        print(f"Bar {sig['bar']:3}: {sig['type']} @ ₹{sig['price']:.2f}")

# Check for nearby signals (within 2 bars)
print(f"\n=== NEARBY SIGNALS (within 2 bars) ===")
for pine_sig in pine_signals:
    for python_sig in python_signals_icici:
        bar_diff = abs(pine_sig['bar'] - python_sig['bar'])
        if bar_diff > 0 and bar_diff <= 2 and pine_sig['type'] == python_sig['type']:
            print(f"Near match: Pine Bar {pine_sig['bar']} ≈ Python Bar {python_sig['bar']} "
                  f"({python_sig['type']}, {bar_diff} bar diff)")
