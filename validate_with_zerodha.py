#!/usr/bin/env python3
"""
Test with Zerodha Historical Data API
Compare results with Pine Script using real market data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.zerodha_client import ZerodhaClient
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from datetime import datetime, timedelta
import pandas as pd
import time

print("=== ZERODHA HISTORICAL DATA VALIDATION ===\n")

# Initialize Zerodha client
client = ZerodhaClient()

# Check if logged in
if not client.access_token:
    print("❌ Not logged in to Zerodha!")
    print("Please run: python auth_helper.py")
    exit(1)

print("✅ Connected to Zerodha")

# Test parameters
SYMBOL = "ICICIBANK"
EXCHANGE = "NSE"
FROM_DATE = "2025-06-16 09:15:00"  # Match CSV date range
TO_DATE = "2025-06-19 15:30:00"
INTERVAL = "5minute"

# Get instrument token
print(f"\nFetching instrument token for {EXCHANGE}:{SYMBOL}...")
# First load all instruments
instruments = client.get_instruments(EXCHANGE)
# Find ICICIBANK
instrument = None
for inst in instruments:
    if inst['tradingsymbol'] == SYMBOL:
        instrument = inst
        break
        
if not instrument:
    print(f"❌ Could not find {SYMBOL}")
    exit(1)

instrument_token = instrument['instrument_token']
print(f"✓ Found: {instrument['name']} (Token: {instrument_token})")

# Fetch historical data
print(f"\nFetching historical data...")
print(f"  From: {FROM_DATE}")
print(f"  To: {TO_DATE}")
print(f"  Interval: {INTERVAL}")

try:
    # Parse dates
    from_dt = datetime.strptime(FROM_DATE, "%Y-%m-%d %H:%M:%S")
    to_dt = datetime.strptime(TO_DATE, "%Y-%m-%d %H:%M:%S")
    days = (to_dt - from_dt).days + 1
    
    # Use client method which handles dates properly
    historical_data = client.get_historical_data(SYMBOL, INTERVAL, days=days)
    
    # Filter by date range if needed
    if historical_data:
        historical_data = [bar for bar in historical_data 
                          if from_dt <= bar['date'] <= to_dt]
    
    print(f"✓ Fetched {len(historical_data)} bars")
    
except Exception as e:
    print(f"❌ Error fetching data: {e}")
    print("Note: Historical data API requires subscription (₹2000/month)")
    exit(1)

# Convert to DataFrame for easier handling
df = pd.DataFrame(historical_data)
print(f"\nData range: {df['date'].min()} to {df['date'].max()}")
print(f"Price range: ₹{df['low'].min():.2f} - ₹{df['high'].max():.2f}")

# Process through our scanner
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

processor = BarProcessor(config)
signals = []
kernel_values = []

print("\nProcessing bars...")
for idx, row in df.iterrows():
    result = processor.process_bar(
        float(row['open']),
        float(row['high']),
        float(row['low']),
        float(row['close']),
        float(row['volume'])
    )
    
    # Track signals
    if result.start_long_trade:
        signals.append({
            'bar': idx + 1,
            'type': 'BUY',
            'time': row['date'],
            'price': row['close'],
            'prediction': result.prediction
        })
    elif result.start_short_trade:
        signals.append({
            'bar': idx + 1,
            'type': 'SELL',
            'time': row['date'],
            'price': row['close'],
            'prediction': result.prediction
        })
    
    # Calculate kernel value
    from core.kernel_functions import rational_quadratic
    source_values = []
    for i in range(len(processor.bars)):
        source_values.append(processor.bars.get_close(i))
    
    if source_values:
        kernel_val = rational_quadratic(source_values, 8, 8.0, 25)
        kernel_values.append(kernel_val)
    
    # Progress
    if (idx + 1) % 50 == 0:
        print(f"  Processed {idx + 1}/{len(df)} bars...")

print(f"\n✓ Processing complete. Found {len(signals)} signals")

# Display results
print("\n=== ZERODHA DATA RESULTS ===")
print(f"Total Bars: {len(df)}")
print(f"Total Signals: {len(signals)}")

if signals:
    print("\nSignals Found:")
    for sig in signals:
        print(f"  Bar {sig['bar']:3}: {sig['type']} @ ₹{sig['price']:.2f} "
              f"(Pred={sig['prediction']:2.0f}) - {sig['time']}")

# Check for kernel issues
print("\n=== KERNEL ANALYSIS ===")
if kernel_values:
    # Check for stuck values
    stuck_count = 0
    last_val = kernel_values[0]
    max_stuck = 0
    current_stuck = 1
    
    for val in kernel_values[1:]:
        if abs(val - last_val) < 0.01:  # Same value
            current_stuck += 1
            max_stuck = max(max_stuck, current_stuck)
        else:
            current_stuck = 1
        last_val = val
    
    print(f"Max consecutive stuck values: {max_stuck}")
    
    # Check last 50 values
    print(f"\nLast 10 kernel values:")
    for i, val in enumerate(kernel_values[-10:]):
        bar_num = len(kernel_values) - 10 + i + 1
        print(f"  Bar {bar_num}: ₹{val:.2f}")

# Recommendations
print("\n=== COMPARISON WITH CSV DATA ===")
print("CSV Data Results: 12 signals")
print(f"Zerodha Data Results: {len(signals)} signals")
print("Pine Script Expected: 8 signals")

if len(signals) != 12:
    print("\n⚠️ Different results with Zerodha data!")
    print("This suggests data quality issues in CSV")
else:
    print("\n✅ Same results with Zerodha data")
    print("Issue is consistent across data sources")

print("\n=== RECOMMENDATIONS ===")
print("1. Test with different stocks to see if issue is data-specific")
print("2. Test with daily timeframe (more stable)")
print("3. Compare exact OHLCV values between Zerodha and CSV")
print("4. Run same date range in Pine Script with Zerodha data")

# Save results for comparison
output_file = "zerodha_validation_results.csv"
if signals:
    signals_df = pd.DataFrame(signals)
    signals_df.to_csv(output_file, index=False)
    print(f"\n✓ Results saved to {output_file}")

print("\n=== DONE ===")
