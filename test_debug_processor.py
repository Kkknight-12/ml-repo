#!/usr/bin/env python3
"""
Test the enhanced debug bar processor
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

# Configure logging to see debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s]: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S.000-00:00'
)

print("="*70)
print("TESTING ENHANCED DEBUG BAR PROCESSOR")
print("="*70)

# Test configuration matching Pine Script
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

# Initialize Zerodha
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        os.environ['KITE_ACCESS_TOKEN'] = session_data.get('access_token')
    
    kite_client = ZerodhaClient()
    kite_client.get_instruments("NSE")
    
    if 'ICICIBANK' in kite_client.symbol_token_map:
        token = kite_client.symbol_token_map['ICICIBANK']
        
        # Get recent data
        to_date = datetime(2025, 6, 22)
        from_date = to_date - timedelta(days=30)
        
        data = kite_client.kite.historical_data(
            instrument_token=token,
            from_date=from_date.strftime("%Y-%m-%d"),
            to_date=to_date.strftime("%Y-%m-%d"),
            interval="day"
        )
        
        print(f"\nFetched {len(data)} bars")
        
        # Create processor with debug
        processor = EnhancedBarProcessorDebug(config, 'ICICIBANK', 'day')
        
        print("\nProcessing bars with debug logging...")
        print("="*70)
        
        # Process only last 5 bars to see debug output
        for i, bar in enumerate(data[-5:]):
            print(f"\n>>> Processing bar {i+1}/5")
            result = processor.process_bar(
                bar['open'], bar['high'], bar['low'], bar['close'], bar['volume']
            )
            
            if result:
                print(f"\nResult Summary:")
                print(f"  Bar Index: {result.bar_index}")
                print(f"  ML Prediction: {result.prediction}")
                print(f"  Signal: {result.signal}")
                print(f"  Filter States: {result.filter_states}")
                print(f"  Entry: Long={result.start_long_trade}, Short={result.start_short_trade}")
                print("="*70)
else:
    print("No access token found")

print("\n✅ Debug test complete!")
