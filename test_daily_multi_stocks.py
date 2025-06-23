#!/usr/bin/env python3
"""
Test multiple stocks with DAILY data
Check if banking vs IT stock pattern remains
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.zerodha_client import ZerodhaClient
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
import pandas as pd

print("=== MULTI-STOCK DAILY DATA TEST ===\n")

# Initialize
client = ZerodhaClient()
if not client.access_token:
    print("❌ Not logged in! Run: python auth_helper.py")
    exit(1)

# Test parameters
STOCKS = ["ICICIBANK", "HDFCBANK", "RELIANCE", "TCS", "INFY"]
INTERVAL = "day"
DAYS = 100

# Same config
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

print(f"Testing {len(STOCKS)} stocks with DAILY data")
print(f"Period: Last {DAYS} days\n")

for symbol in STOCKS:
    print(f"=== {symbol} ===")
    
    try:
        # Get daily data
        data = client.get_historical_data(symbol, INTERVAL, days=DAYS)
        
        if not data:
            print(f"No data for {symbol}")
            continue
            
        print(f"Processing {len(data)} daily bars...")
        
        # Process through scanner
        processor = BarProcessor(config)
        signals = []
        
        for idx, bar in enumerate(data):
            result = processor.process_bar(
                float(bar['open']),
                float(bar['high']),
                float(bar['low']),
                float(bar['close']),
                float(bar['volume'])
            )
            
            if result.start_long_trade:
                signals.append({
                    'bar': idx + 1,
                    'type': 'BUY',
                    'date': bar['date'].strftime('%Y-%m-%d'),
                    'price': bar['close']
                })
            elif result.start_short_trade:
                signals.append({
                    'bar': idx + 1,
                    'type': 'SELL',
                    'date': bar['date'].strftime('%Y-%m-%d'),
                    'price': bar['close']
                })
        
        results[symbol] = {
            'bars': len(data),
            'signals': len(signals),
            'signal_list': signals
        }
        
        print(f"✓ Found {len(signals)} signals\n")
        
    except Exception as e:
        print(f"Error: {e}\n")
        results[symbol] = {'bars': 0, 'signals': 0}

# Summary
print("\n=== DAILY DATA SUMMARY ===")
print(f"{'Stock':<12} {'Bars':>6} {'Signals':>8} {'Rate':>8}")
print("-" * 36)

for symbol in STOCKS:
    if symbol in results:
        data = results[symbol]
        if data['bars'] > 0:
            rate = data['signals'] / data['bars'] * 100
            print(f"{symbol:<12} {data['bars']:>6} {data['signals']:>8} {rate:>7.1f}%")

# Show some signals
print("\n=== SAMPLE SIGNALS ===")
for symbol in ["ICICIBANK", "HDFCBANK"]:
    if symbol in results and results[symbol]['signal_list']:
        print(f"\n{symbol} (first 3 signals):")
        for sig in results[symbol]['signal_list'][:3]:
            print(f"  {sig['date']}: {sig['type']} @ ₹{sig['price']:.2f}")

print("\n=== ANALYSIS ===")
banking_avg = (results.get('ICICIBANK', {}).get('signals', 0) + 
               results.get('HDFCBANK', {}).get('signals', 0)) / 2
it_avg = (results.get('TCS', {}).get('signals', 0) + 
          results.get('INFY', {}).get('signals', 0)) / 2

print(f"Banking stocks average: {banking_avg:.1f} signals")
print(f"IT stocks average: {it_avg:.1f} signals")

if banking_avg > it_avg * 1.5:
    print("\n✅ Pattern confirmed: Banking stocks have more signals!")
else:
    print("\n🤔 Pattern different in daily timeframe")

print("\n=== RECOMMENDATION ===")
print("1. Export these exact dates from TradingView")
print("2. Run Pine Script on DAILY timeframe")
print("3. Compare signal dates exactly")
print("\nDaily data advantages:")
print("- Same OHLC across platforms")
print("- Easy date matching")
print("- No missing bars issue")

print("\n=== DONE ===")
