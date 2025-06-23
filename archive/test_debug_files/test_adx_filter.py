#!/usr/bin/env python3
"""Enable and test ADX filter"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from data.data_manager import DataManager
from data.zerodha_client import ZerodhaClient
import csv
from datetime import datetime

print("=== Testing with ADX Filter Enabled ===\n")

# Create config with ADX enabled
config = TradingConfig(
    # ML settings
    neighbors_count=8,
    max_bars_back=2000,
    feature_count=5,
    
    # Filter settings
    use_volatility_filter=True,
    use_regime_filter=True,
    use_adx_filter=True,  # ENABLE ADX
    regime_threshold=-0.1,
    adx_threshold=20,  # Try 20 as threshold
    
    # Other settings
    use_kernel_filter=True,
    show_trade_stats=True
)

print("Configuration:")
print(f"  ADX Filter: {config.use_adx_filter}")
print(f"  ADX Threshold: {config.adx_threshold}")
print(f"  Regime Filter: {config.use_regime_filter}")
print(f"  Volatility Filter: {config.use_volatility_filter}")

# Load CSV and process
csv_file = "NSE_ICICIBANK, 5.csv"
processor = BarProcessor(config)

print(f"\nProcessing {csv_file}...")

with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    
    signals_found = []
    bars_processed = 0
    
    for row in reader:
        # Parse data
        open_price = float(row['open'])
        high = float(row['high'])
        low = float(row['low'])
        close = float(row['close'])
        volume = 0  # Not in CSV
        
        # Process bar
        result = processor.process_bar(open_price, high, low, close, volume)
        bars_processed += 1
        
        # Track signals
        if result.start_long_trade:
            signals_found.append({
                'bar': bars_processed,
                'type': 'BUY',
                'price': close,
                'filters': result.filter_states
            })
        elif result.start_short_trade:
            signals_found.append({
                'bar': bars_processed,
                'type': 'SELL', 
                'price': close,
                'filters': result.filter_states
            })
        
        # Show filter states every 50 bars
        if bars_processed % 50 == 0:
            print(f"  Bar {bars_processed}: Vol={result.filter_states['volatility']}, "
                  f"Regime={result.filter_states['regime']}, "
                  f"ADX={result.filter_states['adx']}")

print(f"\n✓ Processed {bars_processed} bars")
print(f"✓ Found {len(signals_found)} signals with ADX filter enabled")

# Compare with ADX disabled
print("\n--- Comparison ---")
print(f"With ADX filter: {len(signals_found)} signals")
print("Without ADX filter: 12 signals (from previous run)")
print(f"Reduction: {12 - len(signals_found)} signals filtered out")

# Show signal details
if signals_found:
    print("\nSignal Details:")
    for sig in signals_found[:5]:  # First 5 signals
        print(f"  Bar {sig['bar']}: {sig['type']} @ ₹{sig['price']:.2f}")
        print(f"    Filters: {sig['filters']}")

print("\n=== Test Complete ===")
