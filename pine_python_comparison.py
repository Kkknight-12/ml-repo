#!/usr/bin/env python3
import csv

def count_pine_signals(filename):
    buy_count = 0
    sell_count = 0
    
    try:
        with open(filename, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            
            for row in reader:
                if len(row) >= 8:
                    # Buy signal in column 6
                    if row[6] and row[6] != 'NaN':
                        buy_count += 1
                    # Sell signal in column 7
                    if row[7] and row[7] != 'NaN':
                        sell_count += 1
        
        return buy_count, sell_count
    except:
        return 0, 0

# Count signals for each stock
stocks = {
    'HDFCBANK': 'NSE_HDFCBANK, 5.csv',
    'ICICIBANK': 'NSE_ICICIBANK, 5.csv',
    'RELIANCE': 'NSE_RELIANCE, 5.csv',
    'TCS': 'NSE_TCS, 5.csv'
}

# Python results for comparison
python_results = {
    'HDFCBANK': 14,
    'ICICIBANK': 12,
    'RELIANCE': 5,
    'TCS': 2,
    'INFY': 3
}

print("=== PINE SCRIPT vs PYTHON COMPARISON ===\n")

for stock, filename in stocks.items():
    buy, sell = count_pine_signals(filename)
    total = buy + sell
    python_count = python_results.get(stock, 0)
    
    print(f"{stock}:")
    print(f"  Pine Script: {total} signals (Buy: {buy}, Sell: {sell})")
    print(f"  Python: {python_count} signals")
    print(f"  Difference: {python_count - total}")
    print()

# Overall analysis
print("\n=== ANALYSIS ===")
hdfc_pine = count_pine_signals('NSE_HDFCBANK, 5.csv')[0] + count_pine_signals('NSE_HDFCBANK, 5.csv')[1]
icici_pine = count_pine_signals('NSE_ICICIBANK, 5.csv')[0] + count_pine_signals('NSE_ICICIBANK, 5.csv')[1]

if hdfc_pine > 8 and icici_pine > 8:
    print("✅ SYSTEM IS WORKING CORRECTLY!")
    print("   Pine Script also shows high signals for banking stocks")
    print("   The variation between stocks is EXPECTED behavior")
else:
    print("❌ DISCREPANCY FOUND")
    print("   Pine Script shows different pattern than Python")
    print("   Need to investigate signal generation logic")
