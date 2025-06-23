#!/usr/bin/env python3
"""
Test to check if enhanced bar processor returns filter states properly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from data.zerodha_client import ZerodhaClient
import json

print("="*70)
print("TESTING ENHANCED BAR PROCESSOR FILTER STATES")
print("="*70)

# Create simple test data
test_bars = [
    {'open': 900, 'high': 910, 'low': 890, 'close': 905, 'volume': 1000},
    {'open': 905, 'high': 915, 'low': 895, 'close': 910, 'volume': 1100},
    {'open': 910, 'high': 920, 'low': 900, 'close': 915, 'volume': 1200},
    {'open': 915, 'high': 925, 'low': 905, 'close': 920, 'volume': 1300},
    {'open': 920, 'high': 930, 'low': 910, 'close': 925, 'volume': 1400},
]

# Create processor
config = TradingConfig(
    use_volatility_filter=True,
    use_regime_filter=True,
    use_adx_filter=False
)
processor = EnhancedBarProcessor(config, 'TEST', 'day')

print(f"\nProcessing {len(test_bars)} test bars...")
print(f"Config: volatility={config.use_volatility_filter}, regime={config.use_regime_filter}, adx={config.use_adx_filter}")

for i, bar in enumerate(test_bars):
    result = processor.process_bar(
        bar['open'], bar['high'], bar['low'], bar['close'], bar['volume']
    )
    
    if result:
        print(f"\nBar {i} (index={result.bar_index}):")
        print(f"  Price: {result.close}")
        print(f"  filter_states type: {type(result.filter_states)}")
        print(f"  filter_states value: {result.filter_states}")
        
        if result.filter_states is None:
            print("  ❌ filter_states is None!")
        elif len(result.filter_states) == 0:
            print("  ❌ filter_states is empty!")
        else:
            print("  ✅ filter_states has data")
            for name, value in result.filter_states.items():
                print(f"    {name}: {value}")

# Now test with real data if available
print("\n" + "="*50)
print("Testing with Zerodha data (if available)...")

try:
    if os.path.exists('.kite_session.json'):
        with open('.kite_session.json', 'r') as f:
            session_data = json.load(f)
            os.environ['KITE_ACCESS_TOKEN'] = session_data.get('access_token')
        
        kite_client = ZerodhaClient()
        kite_client.get_instruments("NSE")
        
        if 'ICICIBANK' in kite_client.symbol_token_map:
            token = kite_client.symbol_token_map['ICICIBANK']
            
            # Get just a few bars
            to_date = datetime(2025, 6, 22)
            from_date = to_date - timedelta(days=10)
            
            data = kite_client.kite.historical_data(
                instrument_token=token,
                from_date=from_date.strftime("%Y-%m-%d"),
                to_date=to_date.strftime("%Y-%m-%d"),
                interval="day"
            )
            
            if data:
                print(f"\nProcessing {len(data)} real bars...")
                processor2 = EnhancedBarProcessor(config, 'ICICIBANK', 'day')
                
                for i, bar in enumerate(data[-5:]):  # Last 5 bars
                    result = processor2.process_bar(
                        bar['open'], bar['high'], bar['low'], bar['close'], bar['volume']
                    )
                    
                    if result and result.bar_index >= 2:  # Skip first couple for warmup
                        print(f"\nReal Bar {result.bar_index}:")
                        print(f"  Date: {bar['date']}")
                        print(f"  Close: {result.close}")
                        print(f"  filter_states: {result.filter_states}")
                        
                        if result.filter_states:
                            total_passing = sum(1 for v in result.filter_states.values() if v)
                            print(f"  Filters passing: {total_passing}/3")

except Exception as e:
    print(f"Error with real data: {e}")

print("\n✅ Test complete!")
