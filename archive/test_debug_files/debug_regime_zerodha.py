#!/usr/bin/env python3
"""
Debug Regime Filter with Zerodha Data
=====================================

This script debugs the regime filter using real Zerodha data.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import json
import logging
from core.regime_filter_fix import StatefulRegimeFilter

# Set up logging to see debug messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

print("="*80)
print("REGIME FILTER DEBUG WITH ZERODHA DATA")
print("="*80)

# Initialize Zerodha
if not os.path.exists('.kite_session.json'):
    print("❌ No access token found. Run auth_helper.py first")
    sys.exit(1)

with open('.kite_session.json', 'r') as f:
    session_data = json.load(f)
    os.environ['KITE_ACCESS_TOKEN'] = session_data.get('access_token')

try:
    # Import after setting token
    from data.zerodha_client import ZerodhaClient
    
    kite_client = ZerodhaClient()
    kite_client.get_instruments("NSE")
    print("✅ Zerodha connection established")
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
from_date = to_date - timedelta(days=150)  # Get 150 days

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
values_log = []

# Process each bar
for i, bar in enumerate(data):
    ohlc4 = (bar['open'] + bar['high'] + bar['low'] + bar['close']) / 4
    
    # Update regime filter
    normalized_slope_decline = regime_filter.update(ohlc4, bar['high'], bar['low'])
    
    # Skip warmup period
    if i >= 50:  # Give enough warmup time
        total += 1
        if normalized_slope_decline >= threshold:
            passes += 1
        
        values_log.append(normalized_slope_decline)
        
        # Print debug info for specific bars
        if i in [50, 60, 70, 80, 90, 100, 110, 120]:
            pass_rate = (passes / total * 100) if total > 0 else 0
            print(f"Bar {i}: Date={bar['date'].strftime('%Y-%m-%d')}, "
                  f"OHLC4={ohlc4:.2f}, NSD={normalized_slope_decline:7.4f}, "
                  f"Passes={normalized_slope_decline >= threshold}, "
                  f"Rate={pass_rate:.1f}% ({passes}/{total})")

# Analyze the distribution of values
if values_log:
    import numpy as np
    values_array = np.array(values_log)
    
    min_val = values_array.min()
    max_val = values_array.max()
    avg_val = values_array.mean()
    std_val = values_array.std()
    
    # Count values in different ranges
    ranges = {
        "< -1.0": np.sum(values_array < -1.0),
        "-1.0 to -0.5": np.sum((values_array >= -1.0) & (values_array < -0.5)),
        "-0.5 to -0.1": np.sum((values_array >= -0.5) & (values_array < -0.1)),
        "-0.1 to 0": np.sum((values_array >= -0.1) & (values_array < 0)),
        "0 to 0.5": np.sum((values_array >= 0) & (values_array < 0.5)),
        "> 0.5": np.sum(values_array >= 0.5),
    }

print("-" * 80)
print(f"\nVALUE DISTRIBUTION ANALYSIS:")
print(f"Min value: {min_val:.4f}")
print(f"Max value: {max_val:.4f}")
print(f"Mean value: {avg_val:.4f}")
print(f"Std deviation: {std_val:.4f}")

print(f"\nValue ranges:")
for range_name, count in ranges.items():
    pct = count / len(values_log) * 100
    print(f"  {range_name}: {count} ({pct:.1f}%)")

# Check percentiles
percentiles = [10, 25, 35, 50, 75, 90]
print(f"\nPercentiles:")
for p in percentiles:
    val = np.percentile(values_array, p)
    print(f"  {p}th percentile: {val:.4f}")

print("-" * 80)
print(f"\nFINAL RESULTS:")
print(f"Total bars processed: {total}")
print(f"Bars that passed filter (NSD >= -0.1): {passes}")
print(f"Pass rate: {passes/total*100:.1f}%")
print(f"Expected: ~35%")
print(f"Status: {'✅ CORRECT' if 30 <= passes/total*100 <= 40 else '❌ INCORRECT'}")

# Debug: Show filter state
print(f"\nFILTER STATE AT END:")
print(f"  value1: {regime_filter.value1:.6f}")
print(f"  value2: {regime_filter.value2:.6f}")
print(f"  klmf: {regime_filter.klmf:.2f}")
print(f"  bars_processed: {regime_filter.bars_processed}")

# Compare with enhanced processor
print(f"\n\nNow testing with enhanced processor to compare...")
from scanner.enhanced_bar_processor_debug import EnhancedBarProcessorDebug
from config.settings import TradingConfig

config = TradingConfig(
    neighbors_count=8,
    max_bars_back=2000,
    feature_count=5,
    use_volatility_filter=True,
    use_regime_filter=True,
    use_adx_filter=False,
    regime_threshold=-0.1,
    use_kernel_filter=True,
    use_kernel_smoothing=False
)

processor = EnhancedBarProcessorDebug(config, symbol, 'day')

# Track filter results from processor
processor_regime_passes = 0
processor_total = 0

for i, bar in enumerate(data):
    result = processor.process_bar(
        bar['open'], bar['high'], bar['low'], bar['close'], bar.get('volume', 0)
    )
    
    if result and result.bar_index >= 50:
        processor_total += 1
        if result.filter_states and result.filter_states.get('regime'):
            processor_regime_passes += 1

if processor_total > 0:
    processor_rate = processor_regime_passes / processor_total * 100
    print(f"\nPROCESSOR RESULTS:")
    print(f"Regime filter pass rate: {processor_rate:.1f}% ({processor_regime_passes}/{processor_total})")
    print(f"Standalone filter rate: {passes/total*100:.1f}% ({passes}/{total})")
    print(f"Difference: {abs(processor_rate - passes/total*100):.1f}%")