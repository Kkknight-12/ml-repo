#!/usr/bin/env python3
"""
Test multiple stocks with Zerodha data
Check if signal issue is stock-specific or universal
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.zerodha_client import ZerodhaClient
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from datetime import datetime, timedelta
import pandas as pd

print("=== MULTIPLE STOCKS VALIDATION ===\n")

# Initialize Zerodha client
client = ZerodhaClient()

# Check if logged in
if not client.access_token:
    print("❌ Not logged in to Zerodha!")
    print("Please run: python auth_helper.py")
    exit(1)

print("✅ Connected to Zerodha")

# Test parameters
STOCKS = ["ICICIBANK", "RELIANCE", "TCS", "INFY", "HDFCBANK"]
EXCHANGE = "NSE"
INTERVAL = "5minute"
DAYS = 5  # Last 5 days

# Get all instruments
print("\nLoading instruments...")
instruments = client.get_instruments(EXCHANGE)
instrument_map = {}
for inst in instruments:
    if inst['tradingsymbol'] in STOCKS:
        instrument_map[inst['tradingsymbol']] = inst

print(f"Found {len(instrument_map)} stocks")

# Configuration
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

results = {}

# Process each stock
for symbol in STOCKS:
    if symbol not in instrument_map:
        print(f"\n❌ {symbol} not found, skipping...")
        continue
        
    print(f"\n=== Processing {symbol} ===")
    
    try:
        # Fetch data
        historical_data = client.get_historical_data(symbol, INTERVAL, days=DAYS)
        
        if not historical_data:
            print(f"No data for {symbol}")
            continue
            
        print(f"Processing {len(historical_data)} bars...")
        
        # Process through scanner
        processor = BarProcessor(config)
        signals = []
        
        for idx, bar in enumerate(historical_data):
            result = processor.process_bar(
                float(bar['open']),
                float(bar['high']),
                float(bar['low']),
                float(bar['close']),
                float(bar['volume'])
            )
            
            # Track signals
            if result.start_long_trade:
                signals.append({
                    'bar': idx + 1,
                    'type': 'BUY',
                    'time': bar['date'],
                    'price': bar['close']
                })
            elif result.start_short_trade:
                signals.append({
                    'bar': idx + 1,
                    'type': 'SELL',
                    'time': bar['date'],
                    'price': bar['close']
                })
        
        results[symbol] = {
            'bars': len(historical_data),
            'signals': len(signals),
            'signal_list': signals
        }
        
        print(f"✓ Found {len(signals)} signals")
        
    except Exception as e:
        print(f"Error processing {symbol}: {e}")
        results[symbol] = {
            'bars': 0,
            'signals': 0,
            'signal_list': [],
            'error': str(e)
        }

# Summary
print("\n=== SUMMARY ===")
print(f"{'Stock':<12} {'Bars':>8} {'Signals':>8} {'Signals/100 bars':>18}")
print("-" * 50)

total_signals = 0
total_bars = 0

for symbol, data in results.items():
    if 'error' not in data and data['bars'] > 0:
        signals_per_100 = (data['signals'] / data['bars']) * 100
        print(f"{symbol:<12} {data['bars']:>8} {data['signals']:>8} {signals_per_100:>18.2f}")
        total_signals += data['signals']
        total_bars += data['bars']

if total_bars > 0:
    avg_signals_per_100 = (total_signals / total_bars) * 100
    print("-" * 50)
    print(f"{'AVERAGE':<12} {total_bars:>8} {total_signals:>8} {avg_signals_per_100:>18.2f}")

# Detailed signals for first stock
if results and STOCKS[0] in results:
    first_stock = STOCKS[0]
    if results[first_stock]['signal_list']:
        print(f"\n=== {first_stock} Signal Details ===")
        for sig in results[first_stock]['signal_list'][:10]:  # First 10 signals
            print(f"  Bar {sig['bar']:3}: {sig['type']} @ ₹{sig['price']:.2f} - {sig['time']}")

# Analysis
print("\n=== ANALYSIS ===")
if total_bars > 0:
    if avg_signals_per_100 > 3:
        print("❌ HIGH signal frequency across all stocks")
        print("   Suggests systematic issue in signal generation")
    elif avg_signals_per_100 < 1:
        print("⚠️ LOW signal frequency across all stocks")
        print("   Filters might be too restrictive")
    else:
        print("✅ Signal frequency seems reasonable")
        print("   Pine Script expects ~2.67 signals per 100 bars (8/300)")

# Check consistency
signal_counts = [data['signals'] for data in results.values() if 'error' not in data]
if signal_counts:
    min_signals = min(signal_counts)
    max_signals = max(signal_counts)
    if max_signals > min_signals * 2:
        print("\n⚠️ Large variation in signal counts between stocks")
        print("   Could be stock-specific behavior")
    else:
        print("\n✅ Consistent signal counts across stocks")

print("\n=== DONE ===")
