#!/usr/bin/env python3
"""
Debug Regime Filter Values
==========================

This script helps debug why the regime filter pass rate is lower than expected.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from core.regime_filter_fix import StatefulRegimeFilter
import json
import logging

# Set up logging to see debug messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

print("="*80)
print("REGIME FILTER DEBUG TEST")
print("="*80)

# Initialize Zerodha
if not os.path.exists('.kite_session.json'):
    print("❌ No access token found. Run auth_helper.py first")
    sys.exit(1)

with open('.kite_session.json', 'r') as f:
    session_data = json.load(f)
    os.environ['KITE_ACCESS_TOKEN'] = session_data.get('access_token')

try:
    from data.zerodha_client import ZerodhaClient
    kite_client = ZerodhaClient()
    kite_client.get_instruments("NSE")
except Exception as e:
    print(f"❌ Zerodha error: {str(e)}")
    sys.exit(1)

# Test with ICICIBANK
symbol = 'ICICIBANK'
if symbol not in kite_client.symbol_token_map:
    print(f"❌ {symbol} not found in instruments")
    sys.exit(1)

token = kite_client.symbol_token_map[symbol]

# Get data
to_date = datetime(2025, 6, 22)
from_date = to_date - timedelta(days=100)  # Get 100 days

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

# Create standalone regime filter
regime_filter = StatefulRegimeFilter()
threshold = -0.1

print(f"\nProcessing bars with threshold={threshold}...")
print("-" * 80)

passes = 0
total = 0

for i, bar in enumerate(data):
    ohlc4 = (bar['open'] + bar['high'] + bar['low'] + bar['close']) / 4
    
    # Update regime filter
    normalized_slope_decline = regime_filter.update(ohlc4, bar['high'], bar['low'])
    
    # Skip warmup period
    if i >= 20:  # Give some warmup time
        total += 1
        if normalized_slope_decline >= threshold:
            passes += 1
        
        # Print every 10th bar for debugging
        if (i - 20) % 10 == 0 or (passes > 0 and (i - 20) < 50):
            pass_rate = (passes / total * 100) if total > 0 else 0
            print(f"Bar {i}: NSD={normalized_slope_decline:7.4f}, "
                  f"Passes={normalized_slope_decline >= threshold}, "
                  f"Rate={pass_rate:.1f}% ({passes}/{total})")

print("-" * 80)
print(f"\nFINAL RESULTS:")
print(f"Total bars processed: {total}")
print(f"Bars that passed filter: {passes}")
print(f"Pass rate: {passes/total*100:.1f}%")
print(f"Expected: ~35%")
print(f"Status: {'✅ CORRECT' if 30 <= passes/total*100 <= 40 else '❌ INCORRECT'}")