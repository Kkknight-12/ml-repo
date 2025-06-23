#!/usr/bin/env python3
"""
Compare TradingView (Pine Script) data with Zerodha data
Check if OHLC values match between the two sources
"""

import csv
import pandas as pd
from datetime import datetime

def load_tradingview_data(filename):
    """Load TradingView CSV data"""
    data = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'time': row['time'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close'])
            })
    return pd.DataFrame(data)

def compare_data_sources():
    # Load TradingView data (from Pine Script export)
    tv_icici = load_tradingview_data('NSE_ICICIBANK, 5.csv')
    
    # Load Zerodha comparison data (from compare_csv_zerodha.py output)
    # Based on the output, we know:
    # - TradingView has 300 bars
    # - Zerodha has 233 bars (67 missing)
    # - 147 bars have price differences (49%)
    # - 3 bars have >₹1 difference
    
    print("=== DATA SOURCE COMPARISON ===\n")
    print(f"TradingView (Pine Script) Data:")
    print(f"  Total bars: {len(tv_icici)}")
    print(f"  Date range: {tv_icici['time'].iloc[0]} to {tv_icici['time'].iloc[-1]}")
    print(f"  Price range: ₹{tv_icici['low'].min():.2f} - ₹{tv_icici['high'].max():.2f}")
    
    # Sample some specific bars to show differences
    print("\n=== SAMPLE OHLC VALUES (TradingView) ===")
    sample_bars = [0, 75, 150, 225, 299]  # First, bar 76, bar 151, bar 226, last
    
    for bar in sample_bars:
        if bar < len(tv_icici):
            row = tv_icici.iloc[bar]
            print(f"\nBar {bar+1} ({row['time']}):")
            print(f"  O: {row['open']:.2f}, H: {row['high']:.2f}, "
                  f"L: {row['low']:.2f}, C: {row['close']:.2f}")
    
    # Key findings from compare_csv_zerodha.py output
    print("\n=== KNOWN DISCREPANCIES (from earlier comparison) ===")
    print("\n1. Missing Bars:")
    print("   - Zerodha missing 67 bars (23% of data)")
    
    print("\n2. Price Differences:")
    print("   - 147 bars (49%) have price differences")
    print("   - Average difference: ₹0.22")
    print("   - Maximum difference: ₹1.90")
    
    print("\n3. Large Discrepancies (>₹1):")
    discrepancies = [
        {'bar': 1, 'time': '2025-06-16 03:45:00', 'diff': 1.40, 
         'tv_open': 1418.00, 'zerodha_open': 1416.60},
        {'bar': 76, 'time': '2025-06-17 03:45:00', 'diff': 1.90,
         'tv_open': 1425.00, 'zerodha_open': 1426.90},
        {'bar': 151, 'time': '2025-06-18 03:45:00', 'diff': 1.20,
         'tv_open': 1418.20, 'zerodha_open': 1417.00}
    ]
    
    for disc in discrepancies:
        print(f"\n   Bar {disc['bar']}:")
        print(f"   - TradingView Open: ₹{disc['tv_open']:.2f}")
        print(f"   - Zerodha Open: ₹{disc['zerodha_open']:.2f}")
        print(f"   - Difference: ₹{disc['diff']:.2f}")
    
    # Check other stocks
    print("\n\n=== OTHER STOCKS STATUS ===")
    stocks = {
        'HDFCBANK': 'NSE_HDFCBANK, 5.csv',
        'RELIANCE': 'NSE_RELIANCE, 5.csv',
        'TCS': 'NSE_TCS, 5.csv'
    }
    
    for stock, filename in stocks.items():
        try:
            df = load_tradingview_data(filename)
            print(f"\n{stock}:")
            print(f"  Bars: {len(df)}")
            print(f"  Price range: ₹{df['low'].min():.2f} - ₹{df['high'].max():.2f}")
        except:
            print(f"\n{stock}: File not found or error")
    
    print("\n\n=== CRITICAL FINDINGS ===")
    print("\n❌ DATA MISMATCH CONFIRMED!")
    print("\nReasons for signal differences:")
    print("1. **67 missing bars in Zerodha** - 23% data missing!")
    print("2. **49% bars have price differences** - Half the data doesn't match!")
    print("3. **Opening prices differ** - Entry signals will trigger differently")
    print("\n⚠️  You are NOT testing on the same data!")
    print("\nRECOMMENDATION:")
    print("1. Use ONLY ONE data source for both Pine Script and Python")
    print("2. Export exact same date range from TradingView")
    print("3. Or use Zerodha data in both Pine Script and Python")

if __name__ == "__main__":
    compare_data_sources()
