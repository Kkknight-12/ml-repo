#!/usr/bin/env python3
"""
Test Fixed Implementation
Tests the regime filter fix and ML neighbor issue
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from config.settings import TradingConfig
from scanner.enhanced_bar_processor_debug import EnhancedBarProcessorDebug
from data.zerodha_client import ZerodhaClient
import json
import logging

# Set logging to INFO level for cleaner output
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s]: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)

print("="*70)
print("TESTING FIXED IMPLEMENTATION")
print("="*70)
print("1. Regime Filter Fix - Should show ~35% pass rate (not 52%)")
print("2. ML Neighbor Selection - Should find 8 neighbors eventually")
print("="*70)

# Pine Script default configuration
config = TradingConfig(
    neighbors_count=8,
    max_bars_back=2000,
    feature_count=5,
    use_volatility_filter=True,
    use_regime_filter=True,
    use_adx_filter=False,  # OFF by default
    regime_threshold=-0.1,
    adx_threshold=20,
    use_kernel_filter=True,
    use_kernel_smoothing=False
)

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

if 'ICICIBANK' not in kite_client.symbol_token_map:
    print("❌ ICICIBANK not found in instruments")
    sys.exit(1)

token = kite_client.symbol_token_map['ICICIBANK']

# Get 200 days data for better testing
to_date = datetime(2025, 6, 22)
from_date = to_date - timedelta(days=200)

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

# Create processor
processor = EnhancedBarProcessorDebug(config, 'ICICIBANK', 'day')

# Process all bars
print(f"\nProcessing {len(data)} bars...")

# Track metrics
filter_stats = {
    'volatility_passes': 0,
    'regime_passes': 0,
    'adx_passes': 0,
    'all_pass': 0,
    'bars_counted': 0
}

ml_stats = {
    'predictions': [],
    'neighbor_counts': [],
    'signals': []
}

# Process bars with progress
for i, bar in enumerate(data):
    # Show progress every 50 bars
    if i % 50 == 0:
        print(f"  Processing bar {i}/{len(data)}...")
    
    # Enable debug logging for specific bars
    if i in [100, 150, 180]:  # Debug specific bars
        logging.getLogger().setLevel(logging.DEBUG)
        print(f"\n>>> DEBUG OUTPUT FOR BAR {i}:")
    else:
        logging.getLogger().setLevel(logging.WARNING)
    
    result = processor.process_bar(
        bar['open'], bar['high'], bar['low'], bar['close'], bar['volume']
    )
    
    if result and result.bar_index >= 50:  # Skip warmup period
        filter_stats['bars_counted'] += 1
        
        # Track filter performance
        if result.filter_states:
            if result.filter_states.get('volatility'):
                filter_stats['volatility_passes'] += 1
            if result.filter_states.get('regime'):
                filter_stats['regime_passes'] += 1
            if result.filter_states.get('adx'):
                filter_stats['adx_passes'] += 1
            if all(result.filter_states.values()):
                filter_stats['all_pass'] += 1
        
        # Track ML performance
        if result.prediction != 0:
            ml_stats['predictions'].append(result.prediction)
            # Get neighbor count from ML model
            if hasattr(processor, 'ml_model'):
                neighbor_count = processor.ml_model.get_neighbor_count()
                ml_stats['neighbor_counts'].append(neighbor_count)
        
        ml_stats['signals'].append(result.signal)

# Display results
print("\n" + "="*70)
print("RESULTS:")
print("="*70)

# Filter performance
print("\n1. FILTER PERFORMANCE:")
if filter_stats['bars_counted'] > 0:
    vol_rate = filter_stats['volatility_passes'] / filter_stats['bars_counted'] * 100
    regime_rate = filter_stats['regime_passes'] / filter_stats['bars_counted'] * 100
    adx_rate = filter_stats['adx_passes'] / filter_stats['bars_counted'] * 100
    all_rate = filter_stats['all_pass'] / filter_stats['bars_counted'] * 100
    
    print(f"   Volatility: {vol_rate:.1f}% (Pine Script: ~40.7%)")
    print(f"   Regime: {regime_rate:.1f}% (Pine Script: ~35.7%) {'✅' if 30 <= regime_rate <= 40 else '❌'}")
    print(f"   ADX: {adx_rate:.1f}% (OFF by default)")
    print(f"   All Pass: {all_rate:.1f}%")

# ML performance
print("\n2. ML NEIGHBOR SELECTION:")
if ml_stats['neighbor_counts']:
    avg_neighbors = sum(ml_stats['neighbor_counts']) / len(ml_stats['neighbor_counts'])
    max_neighbors = max(ml_stats['neighbor_counts'])
    min_neighbors = min(ml_stats['neighbor_counts'])
    
    print(f"   Average neighbors: {avg_neighbors:.1f} (Expected: 8)")
    print(f"   Max neighbors: {max_neighbors} {'✅' if max_neighbors == 8 else '❌'}")
    print(f"   Min neighbors: {min_neighbors}")
    print(f"   Total predictions: {len(ml_stats['predictions'])}")
    
    # Show neighbor distribution
    neighbor_dist = {}
    for count in ml_stats['neighbor_counts']:
        neighbor_dist[count] = neighbor_dist.get(count, 0) + 1
    
    print("\n   Neighbor count distribution:")
    for count in sorted(neighbor_dist.keys()):
        print(f"     {count} neighbors: {neighbor_dist[count]} times")

# Signal analysis
print("\n3. SIGNAL ANALYSIS:")
signal_counts = {1: 0, -1: 0, 0: 0}
for signal in ml_stats['signals']:
    signal_counts[signal] = signal_counts.get(signal, 0) + 1

print(f"   Long signals: {signal_counts[1]}")
print(f"   Short signals: {signal_counts[-1]}")
print(f"   Neutral signals: {signal_counts[0]}")

# Summary
print("\n" + "="*70)
print("SUMMARY:")
print("="*70)

issues_fixed = 0
if 30 <= regime_rate <= 40:
    print("✅ Regime filter fixed - now matches Pine Script range")
    issues_fixed += 1
else:
    print("❌ Regime filter still not matching Pine Script")

if max_neighbors == 8:
    print("✅ ML neighbor selection fixed - finding 8 neighbors")
    issues_fixed += 1
else:
    print(f"❌ ML neighbor selection issue - max {max_neighbors} neighbors instead of 8")

print(f"\nFixed {issues_fixed}/2 issues")

# Save detailed results
results = {
    'date': datetime.now().isoformat(),
    'bars_processed': len(data),
    'filter_stats': filter_stats,
    'filter_rates': {
        'volatility': vol_rate,
        'regime': regime_rate,
        'adx': adx_rate,
        'all': all_rate
    },
    'ml_stats': {
        'avg_neighbors': avg_neighbors if ml_stats['neighbor_counts'] else 0,
        'max_neighbors': max_neighbors if ml_stats['neighbor_counts'] else 0,
        'total_predictions': len(ml_stats['predictions']),
        'neighbor_distribution': neighbor_dist if ml_stats['neighbor_counts'] else {}
    },
    'signal_counts': signal_counts
}

import json
with open('test_results/fixed_implementation_test.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nDetailed results saved to test_results/fixed_implementation_test.json")
print("\n✅ Test complete!")
