#!/usr/bin/env python3
"""
Quick test to verify filter tracking fix
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from data.zerodha_client import ZerodhaClient
import json

print("=" * 70)
print("🧪 TESTING FILTER TRACKING FIX")
print("=" * 70)

# Initialize Zerodha
print("\n1️⃣ Initializing Zerodha...")
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        os.environ['KITE_ACCESS_TOKEN'] = session_data.get('access_token')
    
    kite_client = ZerodhaClient()
    print("✅ Connected to Zerodha")
else:
    print("❌ No access token found")
    exit(1)

# Fetch data
print("\n2️⃣ Fetching ICICIBANK data...")
to_date = datetime(2025, 6, 22)
from_date = to_date - timedelta(days=100)

kite_client.get_instruments("NSE")
instrument_token = kite_client.symbol_token_map.get('ICICIBANK')

if instrument_token:
    data = kite_client.kite.historical_data(
        instrument_token=instrument_token,
        from_date=from_date.strftime("%Y-%m-%d"),
        to_date=to_date.strftime("%Y-%m-%d"),
        interval="day"
    )
    print(f"✅ Fetched {len(data)} bars")
else:
    print("❌ Symbol not found")
    exit(1)

# Create processor
print("\n3️⃣ Creating Enhanced Bar Processor...")
config = TradingConfig(
    use_volatility_filter=True,
    use_regime_filter=True,
    use_adx_filter=False
)
processor = EnhancedBarProcessor(config, 'ICICIBANK', 'day')

# Track filters manually
filter_stats = {
    'volatility_passes': 0,
    'regime_passes': 0,
    'adx_passes': 0,
    'all_pass': 0,
    'bars_processed': 0
}

print("\n4️⃣ Processing bars and tracking filters...")
for bar in data[:50]:  # Process first 50 bars
    result = processor.process_bar(
        bar['open'], bar['high'], bar['low'], bar['close'], bar['volume']
    )
    
    if result and result.bar_index >= 20:  # Skip warmup
        filter_stats['bars_processed'] += 1
        
        # Track filter states correctly
        if result.filter_states:
            for filter_name, passed in result.filter_states.items():
                key = f"{filter_name}_passes"
                if passed and key in filter_stats:
                    filter_stats[key] += 1
            
            # All filters pass
            if all(result.filter_states.values()):
                filter_stats['all_pass'] += 1
        
        # Debug output every 10 bars
        if filter_stats['bars_processed'] % 10 == 0:
            print(f"   Bar {result.bar_index}: Filters={result.filter_states}")

# Calculate and display results
print("\n5️⃣ Results:")
print(f"   Total bars processed: {filter_stats['bars_processed']}")
print(f"   Filter pass counts:")
for key, value in filter_stats.items():
    if key.endswith('_passes'):
        filter_name = key.replace('_passes', '')
        pass_rate = value / filter_stats['bars_processed'] * 100 if filter_stats['bars_processed'] > 0 else 0
        print(f"     {filter_name.capitalize()}: {value}/{filter_stats['bars_processed']} ({pass_rate:.1f}%)")

print("\n✅ Test complete - filter tracking should now work correctly!")
