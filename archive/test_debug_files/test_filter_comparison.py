#!/usr/bin/env python3
"""
Compare filter pass rates: enhanced_fixes.py vs comprehensive test
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
print("FILTER PASS RATE COMPARISON")
print("="*70)

# Same config as comprehensive test
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
    use_kernel_smoothing=False
)

print("\nConfiguration:")
print(f"  Volatility: {config.use_volatility_filter}")
print(f"  Regime: {config.use_regime_filter} (threshold: {config.regime_threshold})")
print(f"  ADX: {config.use_adx_filter} (threshold: {config.adx_threshold})")

# Initialize Zerodha
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        os.environ['KITE_ACCESS_TOKEN'] = session_data.get('access_token')
    
    kite_client = ZerodhaClient()
    kite_client.get_instruments("NSE")
    
    if 'ICICIBANK' in kite_client.symbol_token_map:
        token = kite_client.symbol_token_map['ICICIBANK']
        
        # Test 1: Recent 21 bars (like enhanced_fixes.py)
        print("\n" + "="*50)
        print("TEST 1: Recent 21 bars (like enhanced_fixes.py)")
        to_date = datetime(2025, 6, 22)
        from_date = to_date - timedelta(days=30)
        
        data = kite_client.kite.historical_data(
            instrument_token=token,
            from_date=from_date.strftime("%Y-%m-%d"),
            to_date=to_date.strftime("%Y-%m-%d"),
            interval="day"
        )
        
        processor1 = EnhancedBarProcessor(config, 'ICICIBANK', 'day')
        
        filter_stats = {
            'volatility_passes': 0,
            'regime_passes': 0,
            'adx_passes': 0,
            'all_pass': 0,
            'bars_processed': 0
        }
        
        for bar in data[-21:]:  # Last 21 bars
            result = processor1.process_bar(
                bar['open'], bar['high'], bar['low'], bar['close'], bar['volume']
            )
            
            if result and result.bar_index >= 20:  # Skip warmup
                filter_stats['bars_processed'] += 1
                
                if result.filter_states:
                    for filter_name, passed in result.filter_states.items():
                        key = f"{filter_name}_passes"
                        if passed and key in filter_stats:
                            filter_stats[key] += 1
                    
                    if all(result.filter_states.values()):
                        filter_stats['all_pass'] += 1
        
        print(f"\nResults (21 bars):")
        print(f"  Bars processed: {filter_stats['bars_processed']}")
        for key, value in filter_stats.items():
            if key.endswith('_passes'):
                filter_name = key.replace('_passes', '')
                pass_rate = value / filter_stats['bars_processed'] * 100 if filter_stats['bars_processed'] > 0 else 0
                print(f"  {filter_name.capitalize()}: {value}/{filter_stats['bars_processed']} ({pass_rate:.1f}%)")
        
        # Test 2: Full year (like comprehensive test)
        print("\n" + "="*50)
        print("TEST 2: Full year (like comprehensive test)")
        to_date = datetime(2025, 6, 22)
        from_date = to_date - timedelta(days=365)
        
        data = kite_client.kite.historical_data(
            instrument_token=token,
            from_date=from_date.strftime("%Y-%m-%d"),
            to_date=to_date.strftime("%Y-%m-%d"),
            interval="day"
        )
        
        processor2 = EnhancedBarProcessor(config, 'ICICIBANK', 'day')
        
        filter_stats2 = {
            'volatility_passes': 0,
            'regime_passes': 0,
            'adx_passes': 0,
            'all_pass': 0,
            'bars_processed': 0
        }
        
        for bar in data:
            result = processor2.process_bar(
                bar['open'], bar['high'], bar['low'], bar['close'], bar['volume']
            )
            
            if result and result.bar_index >= 50:  # Skip warmup like comprehensive
                filter_stats2['bars_processed'] += 1
                
                if result.filter_states:
                    for filter_name, passed in result.filter_states.items():
                        key = f"{filter_name}_passes"
                        if passed and key in filter_stats2:
                            filter_stats2[key] += 1
                    
                    if all(result.filter_states.values()):
                        filter_stats2['all_pass'] += 1
        
        print(f"\nResults (full year):")
        print(f"  Bars processed: {filter_stats2['bars_processed']}")
        for key, value in filter_stats2.items():
            if key.endswith('_passes'):
                filter_name = key.replace('_passes', '')
                pass_rate = value / filter_stats2['bars_processed'] * 100 if filter_stats2['bars_processed'] > 0 else 0
                print(f"  {filter_name.capitalize()}: {value}/{filter_stats2['bars_processed']} ({pass_rate:.1f}%)")
        
        # Compare
        print("\n" + "="*50)
        print("COMPARISON:")
        print("Filter pass rates should be similar between tests")
        print("If full year shows 0%, there's a tracking bug in comprehensive test")
else:
    print("No access token found")

print("\n✅ Comparison test complete!")
