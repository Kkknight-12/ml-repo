#!/usr/bin/env python3
"""
Compare CSV data with Zerodha historical data
Check if data discrepancies are causing signal differences
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.zerodha_client import ZerodhaClient
import pandas as pd
import csv
from datetime import datetime

print("=== CSV vs ZERODHA DATA COMPARISON ===\n")

# Load CSV data
csv_file = "NSE_ICICIBANK, 5.csv"
print(f"Loading CSV data from {csv_file}...")

csv_data = []
with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        csv_data.append({
            'time': datetime.fromisoformat(row['time'].replace('Z', '+00:00')),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close'])
        })

print(f"✓ Loaded {len(csv_data)} bars from CSV")
print(f"  Date range: {csv_data[0]['time']} to {csv_data[-1]['time']}")

# Initialize Zerodha
client = ZerodhaClient()

if not client.access_token:
    print("\n❌ Not logged in! Run: python auth_helper.py")
    print("Skipping Zerodha comparison...")
    exit(1)

# Get ICICIBANK data from Zerodha
print("\nFetching Zerodha data...")
try:
    # instruments = client.search_instruments("NSE:ICICIBANK")
    # if not instruments:
    #     print("❌ Could not find ICICIBANK")
    #     exit(1)
    #
    # instrument_token = instruments[0]['instrument_token']
    # First load all instruments
    instruments = client.get_instruments("NSE")
    # Find ICICIBANK
    icicibank = None
    for inst in instruments:
        if inst['tradingsymbol'] == 'ICICIBANK':
            icicibank = inst
            break

    if not icicibank:
        print("❌ Could not find ICICIBANK")
        exit(1)

    instrument_token = icicibank['instrument_token']
    
    # Use same date range as CSV
    from_date = csv_data[0]['time'].strftime("%Y-%m-%d %H:%M:%S")
    to_date = csv_data[-1]['time'].strftime("%Y-%m-%d %H:%M:%S")
    
    zerodha_data = client.kite.historical_data(
        instrument_token=instrument_token,
        from_date=from_date,
        to_date=to_date,
        interval="5minute"
    )
    
    print(f"✓ Fetched {len(zerodha_data)} bars from Zerodha")
    
except Exception as e:
    print(f"❌ Error fetching Zerodha data: {e}")
    print("\nNote: Historical data requires subscription (₹2000/month)")
    exit(1)

# Compare data
print("\n=== DATA COMPARISON ===")
print(f"CSV bars: {len(csv_data)}")
print(f"Zerodha bars: {len(zerodha_data)}")

# Find matching bars and compare
discrepancies = []
large_diffs = []

for i, csv_bar in enumerate(csv_data):
    # Find matching Zerodha bar by timestamp
    zerodha_bar = None
    for zb in zerodha_data:
        if abs((zb['date'] - csv_bar['time']).total_seconds()) < 60:  # Within 1 minute
            zerodha_bar = zb
            break
    
    if zerodha_bar:
        # Compare OHLC values
        open_diff = abs(csv_bar['open'] - zerodha_bar['open'])
        high_diff = abs(csv_bar['high'] - zerodha_bar['high'])
        low_diff = abs(csv_bar['low'] - zerodha_bar['low'])
        close_diff = abs(csv_bar['close'] - zerodha_bar['close'])
        
        max_diff = max(open_diff, high_diff, low_diff, close_diff)
        
        if max_diff > 0.01:  # More than 1 paisa difference
            discrepancies.append({
                'bar': i + 1,
                'time': csv_bar['time'],
                'csv_ohlc': (csv_bar['open'], csv_bar['high'], csv_bar['low'], csv_bar['close']),
                'zerodha_ohlc': (zerodha_bar['open'], zerodha_bar['high'], zerodha_bar['low'], zerodha_bar['close']),
                'max_diff': max_diff
            })
            
            if max_diff > 1.0:  # More than ₹1 difference
                large_diffs.append(discrepancies[-1])

print(f"\nFound {len(discrepancies)} bars with price differences")
print(f"Large differences (>₹1): {len(large_diffs)}")

if large_diffs:
    print("\n=== LARGE DISCREPANCIES ===")
    for diff in large_diffs[:5]:  # Show first 5
        print(f"\nBar {diff['bar']} ({diff['time']}):")
        print(f"  CSV:     O={diff['csv_ohlc'][0]:.2f}, H={diff['csv_ohlc'][1]:.2f}, "
              f"L={diff['csv_ohlc'][2]:.2f}, C={diff['csv_ohlc'][3]:.2f}")
        print(f"  Zerodha: O={diff['zerodha_ohlc'][0]:.2f}, H={diff['zerodha_ohlc'][1]:.2f}, "
              f"L={diff['zerodha_ohlc'][2]:.2f}, C={diff['zerodha_ohlc'][3]:.2f}")
        print(f"  Max difference: ₹{diff['max_diff']:.2f}")

# Statistical summary
if discrepancies:
    avg_diff = sum(d['max_diff'] for d in discrepancies) / len(discrepancies)
    max_overall_diff = max(d['max_diff'] for d in discrepancies)
    
    print("\n=== STATISTICS ===")
    print(f"Average price difference: ₹{avg_diff:.4f}")
    print(f"Maximum price difference: ₹{max_overall_diff:.2f}")
    print(f"Bars with differences: {len(discrepancies)}/{len(csv_data)} "
          f"({len(discrepancies)/len(csv_data)*100:.1f}%)")

# Check for missing bars
csv_times = {bar['time'] for bar in csv_data}
zerodha_times = {bar['date'] for bar in zerodha_data}

missing_in_csv = zerodha_times - csv_times
missing_in_zerodha = csv_times - zerodha_times

if missing_in_csv or missing_in_zerodha:
    print("\n=== MISSING BARS ===")
    if missing_in_csv:
        print(f"Missing in CSV: {len(missing_in_csv)} bars")
    if missing_in_zerodha:
        print(f"Missing in Zerodha: {len(missing_in_zerodha)} bars")

# Recommendations
print("\n=== RECOMMENDATIONS ===")
if len(large_diffs) > 0:
    print("❌ Significant data discrepancies found!")
    print("   This could explain signal differences")
    print("   Use Zerodha data for accurate testing")
elif len(discrepancies) > len(csv_data) * 0.1:
    print("⚠️ Many small discrepancies found")
    print("   May cause minor signal timing differences")
else:
    print("✅ Data sources are mostly consistent")
    print("   Signal differences likely due to logic issues")

print("\n=== DONE ===")
