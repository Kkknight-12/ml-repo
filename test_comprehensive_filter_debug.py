#!/usr/bin/env python3
"""
Focused test to debug comprehensive test filter issue
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
print("COMPREHENSIVE TEST FILTER DEBUG")
print("="*70)

# Initialize exactly like comprehensive test
config = TradingConfig(
    neighbors_count=8,
    max_bars_back=2000,
    feature_count=5,
    use_volatility_filter=True,
    use_regime_filter=True,
    use_adx_filter=False,
    use_kernel_filter=True,
    use_kernel_smoothing=False
)

print(f"\nConfig matches comprehensive test:")
print(f"  Filters: vol={config.use_volatility_filter}, regime={config.use_regime_filter}, adx={config.use_adx_filter}")

# Get some real data
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        os.environ['KITE_ACCESS_TOKEN'] = session_data.get('access_token')
    
    kite_client = ZerodhaClient()
    kite_client.get_instruments("NSE")
    
    if 'ICICIBANK' in kite_client.symbol_token_map:
        token = kite_client.symbol_token_map['ICICIBANK']
        
        # Get 60 days to ensure we pass warmup
        to_date = datetime(2025, 6, 22)
        from_date = to_date - timedelta(days=60)
        
        data = kite_client.kite.historical_data(
            instrument_token=token,
            from_date=from_date.strftime("%Y-%m-%d"),
            to_date=to_date.strftime("%Y-%m-%d"),
            interval="day"
        )
        
        print(f"\nFetched {len(data)} bars")
        
        # Create processor
        processor = EnhancedBarProcessor(config, 'ICICIBANK', 'day')
        
        # Initialize tracking like comprehensive test
        filter_tracking = {
            'volatility_passes': 0,
            'regime_passes': 0,
            'adx_passes': 0,
            'all_pass': 0
        }
        bars_processed = 0
        warmup_bars = 0
        
        print(f"\nProcessing bars...")
        
        for idx, bar in enumerate(data):
            result = processor.process_bar(
                bar['open'], bar['high'], bar['low'], bar['close'], bar['volume']
            )
            
            if result:
                # Skip warmup like comprehensive test
                if result.bar_index < 50:
                    warmup_bars += 1
                    if result.bar_index % 10 == 0:
                        print(f"  Warmup bar {result.bar_index}")
                    continue
                
                bars_processed += 1
                
                # Debug first few bars after warmup
                if bars_processed <= 5:
                    print(f"\nBar {result.bar_index} (processed #{bars_processed}):")
                    print(f"  Date: {bar['date']}")
                    print(f"  Close: {result.close}")
                    print(f"  filter_states is None? {result.filter_states is None}")
                    print(f"  filter_states: {result.filter_states}")
                
                # Track filters exactly like comprehensive test
                if result.filter_states:
                    for filter_name, passed in result.filter_states.items():
                        key = f"{filter_name}_passes"
                        if passed and key in filter_tracking:
                            filter_tracking[key] += 1
                            if bars_processed <= 3:
                                print(f"    ✅ {filter_name} passed, count now {filter_tracking[key]}")
                    
                    if all(result.filter_states.values()):
                        filter_tracking['all_pass'] += 1
        
        print(f"\n{'='*50}")
        print(f"RESULTS:")
        print(f"  Total bars: {len(data)}")
        print(f"  Warmup bars: {warmup_bars}")
        print(f"  Bars processed: {bars_processed}")
        print(f"\nFilter counts:")
        for key, value in filter_tracking.items():
            print(f"  {key}: {value}")
        
        print(f"\nCalculated pass rates:")
        if bars_processed > 0:
            for filter_name in ['volatility', 'regime', 'adx', 'all']:
                key = f"{filter_name}_passes"
                if key in filter_tracking:
                    pass_rate = filter_tracking[key] / bars_processed * 100
                    print(f"  {filter_name}: {pass_rate:.1f}%")
        
        print(f"\nAverage filter pass rate: {filter_tracking['all_pass'] / bars_processed * 100 if bars_processed > 0 else 0:.1f}%")
else:
    print("No access token found")

print("\n✅ Debug test complete!")
