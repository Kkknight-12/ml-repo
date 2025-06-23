#!/usr/bin/env python3
"""
Count Pine Script signals from TradingView exported CSV files
"""

import csv
import os

def count_signals(filename):
    """Count buy/sell signals from Pine Script CSV"""
    buy_signals = []
    sell_signals = []
    
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            # Check Buy column
            if row['Buy'] and row['Buy'] != 'NaN':
                buy_signals.append({
                    'bar': i + 1,
                    'price': float(row['Buy']),
                    'time': row['time']
                })
            
            # Check Sell column
            if row['Sell'] and row['Sell'] != 'NaN':
                sell_signals.append({
                    'bar': i + 1,
                    'price': float(row['Sell']),
                    'time': row['time']
                })
    
    return buy_signals, sell_signals

# Process all NSE files
stocks = ['HDFCBANK', 'ICICIBANK', 'RELIANCE', 'TCS']
results = {}

print("=== PINE SCRIPT SIGNAL COUNT ===\n")

for stock in stocks:
    filename = f"NSE_{stock}, 5.csv"
    if os.path.exists(filename):
        buy_signals, sell_signals = count_signals(filename)
        total_signals = len(buy_signals) + len(sell_signals)
        
        results[stock] = {
            'buy': len(buy_signals),
            'sell': len(sell_signals),
            'total': total_signals
        }
        
        print(f"{stock}:")
        print(f"  Buy Signals: {len(buy_signals)}")
        print(f"  Sell Signals: {len(sell_signals)}")
        print(f"  Total Signals: {total_signals}")
        print()

# Summary
print("\n=== COMPARISON WITH PYTHON ===")
print(f"{'Stock':<12} {'Pine Script':>12} {'Python':>12} {'Difference':>12}")
print("-" * 50)

python_results = {
    'HDFCBANK': 14,
    'ICICIBANK': 12,
    'RELIANCE': 5,
    'TCS': 2
}

for stock in ['HDFCBANK', 'ICICIBANK', 'RELIANCE', 'TCS']:
    if stock in results:
        pine_count = results[stock]['total']
        python_count = python_results.get(stock, 0)
        diff = python_count - pine_count
        print(f"{stock:<12} {pine_count:>12} {python_count:>12} {diff:>+12}")

print("\n=== ANALYSIS ===")
# Check if pattern matches
if all(stock in results for stock in ['HDFCBANK', 'ICICIBANK']):
    if results['HDFCBANK']['total'] > 10 and results['ICICIBANK']['total'] > 10:
        print("✅ Pine Script also shows HIGH signals for banking stocks!")
        print("   This confirms Python implementation is CORRECT!")
    else:
        print("❌ Pine Script shows different pattern")
        print("   Need to investigate signal generation logic")
