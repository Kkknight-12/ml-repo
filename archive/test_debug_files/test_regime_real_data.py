#!/usr/bin/env python3
"""
Test Regime Filter V2 with Real Market Data
===========================================

This tests the V2 regime filter directly with real ICICIBANK data
to compare with the comprehensive test results.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from core.regime_filter_fix_v2 import StatefulRegimeFilterV2
from data.zerodha_client import ZerodhaClient
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

print("="*80)
print("REGIME FILTER V2 TEST WITH REAL DATA")
print("="*80)

# Initialize Zerodha
if not os.path.exists('.kite_session.json'):
    print("❌ No access token found. Run auth_helper.py first")
    sys.exit(1)

with open('.kite_session.json', 'r') as f:
    session_data = json.load(f)
    os.environ['KITE_ACCESS_TOKEN'] = session_data.get('access_token')

try:
    kite_client = ZerodhaClient()
    kite_client.get_instruments("NSE")
except Exception as e:
    print(f"❌ Zerodha error: {str(e)}")
    sys.exit(1)

# Test with ICICIBANK (same as comprehensive test)
symbol = 'ICICIBANK'
if symbol not in kite_client.symbol_token_map:
    print(f"❌ {symbol} not found in instruments")
    sys.exit(1)

token = kite_client.symbol_token_map[symbol]

# Get same date range as comprehensive test
to_date = datetime(2025, 6, 22)
from_date = to_date - timedelta(days=250)

print(f"\nFetching data from {from_date.date()} to {to_date.date()}...")

try:
    data = kite_client.kite.historical_data(
        instrument_token=token,
        from_date=from_date.strftime("%Y-%m-%d"),
        to_date=to_date.strftime("%Y-%m-%d"),
        interval="day"
    )
    print(f"✅ Fetched {len(data)} bars")
except Exception as e:
    print(f"❌ Error fetching data: {str(e)}")
    sys.exit(1)

# Create regime filter
regime_filter = StatefulRegimeFilterV2()
threshold = -0.1

# Process bars
passes = 0
total = 0
results_by_bar = []

print(f"\nProcessing {len(data)} bars...")
print("-" * 80)

for i, bar in enumerate(data):
    # Calculate OHLC4
    ohlc4 = (bar['open'] + bar['high'] + bar['low'] + bar['close']) / 4
    
    # Update regime filter
    nsd = regime_filter.update(ohlc4, bar['high'], bar['low'])
    
    # Skip warmup (same as comprehensive test)
    if i >= 50:
        total += 1
        is_pass = nsd >= threshold
        if is_pass:
            passes += 1
        
        results_by_bar.append({
            'bar': i,
            'ohlc4': ohlc4,
            'nsd': nsd,
            'pass': is_pass
        })
        
        # Print some values
        if i in [50, 75, 100, 125, 150]:
            pass_rate = (passes / total * 100) if total > 0 else 0
            print(f"Bar {i}: OHLC4={ohlc4:.2f}, NSD={nsd:.4f}, "
                  f"Passes={is_pass}, Rate={pass_rate:.1f}%")

print("-" * 80)
print(f"\nFINAL RESULTS:")
print(f"Total bars (after warmup): {total}")
print(f"Passes: {passes}")
print(f"Pass rate: {passes/total*100:.1f}%")
print(f"Target: ~35%")

# Compare debug values between bars 100-150
print(f"\n\nDEBUG VALUES (sample):")
print("-" * 80)
for debug in regime_filter.debug_values[-5:]:
    if debug['bar'] >= 100:
        print(f"Bar {debug['bar']}: v1={debug['value1']:.6f}, v2={debug['value2']:.6f}, "
              f"omega={debug['omega']:.6f}, alpha={debug['alpha']:.6f}, "
              f"NSD={debug['nsd']:.6f}")

# Show distribution of NSD values
print(f"\n\nNSD DISTRIBUTION:")
print("-" * 80)
nsd_ranges = {
    'Very negative (< -0.5)': 0,
    'Negative (-0.5 to -0.1)': 0,
    'Near threshold (-0.1 to 0)': 0,
    'Positive (0 to 0.5)': 0,
    'Very positive (> 0.5)': 0
}

for result in results_by_bar:
    nsd = result['nsd']
    if nsd < -0.5:
        nsd_ranges['Very negative (< -0.5)'] += 1
    elif nsd < -0.1:
        nsd_ranges['Negative (-0.5 to -0.1)'] += 1
    elif nsd < 0:
        nsd_ranges['Near threshold (-0.1 to 0)'] += 1
    elif nsd < 0.5:
        nsd_ranges['Positive (0 to 0.5)'] += 1
    else:
        nsd_ranges['Very positive (> 0.5)'] += 1

for range_name, count in nsd_ranges.items():
    pct = (count / total * 100) if total > 0 else 0
    print(f"{range_name}: {count} bars ({pct:.1f}%)")

print(f"\n✅ Test complete!")