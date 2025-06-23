#!/usr/bin/env python3
"""
Comprehensive test with full debug logging and FIXED regime filter
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# IMPORTANT: This test now uses the FIXED regime filter implementation

from datetime import datetime, timedelta
from config.settings import TradingConfig
from scanner.enhanced_bar_processor_debug import EnhancedBarProcessorDebug
from data.zerodha_client import ZerodhaClient
import json
import logging

# Setup FULL DEBUG logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s]: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S.%f'
)

print("="*70)
print("COMPREHENSIVE TEST WITH DEBUG LOGGING")
print("="*70)

# Pine Script default configuration
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
        
        # Get 100 days data
        to_date = datetime(2025, 6, 22)
        from_date = to_date - timedelta(days=100)
        
        data = kite_client.kite.historical_data(
            instrument_token=token,
            from_date=from_date.strftime("%Y-%m-%d"),
            to_date=to_date.strftime("%Y-%m-%d"),
            interval="day"
        )
        
        print(f"\nFetched {len(data)} bars")
        print(f"Processing bars 60-65 with full debug...")
        print("="*70)
        
        # Create processor
        processor = EnhancedBarProcessorDebug(config, 'ICICIBANK', 'day')
        
        # Process initial bars silently to build up history
        print("\nBuilding history (bars 0-59)...")
        old_level = logging.getLogger().level
        logging.getLogger().setLevel(logging.WARNING)
        
        for i, bar in enumerate(data[:60]):
            processor.process_bar(
                bar['open'], bar['high'], bar['low'], bar['close'], bar['volume']
            )
        
        # Now process with full debug
        logging.getLogger().setLevel(logging.DEBUG)
        print(f"\nDEBUG OUTPUT FOR BARS 60-65:")
        print("="*70)
        
        filter_pass_counts = {'volatility': 0, 'regime': 0, 'adx': 0, 'all': 0}
        
        for i, bar in enumerate(data[60:65]):
            print(f"\n>>> Processing bar {60+i}")
            result = processor.process_bar(
                bar['open'], bar['high'], bar['low'], bar['close'], bar['volume']
            )
            
            if result and result.filter_states:
                # Track filter passes
                if result.filter_states.get('volatility'):
                    filter_pass_counts['volatility'] += 1
                if result.filter_states.get('regime'):
                    filter_pass_counts['regime'] += 1
                if result.filter_states.get('adx'):
                    filter_pass_counts['adx'] += 1
                if all(result.filter_states.values()):
                    filter_pass_counts['all'] += 1
        
        # Summary
        print("\n" + "="*70)
        print("FILTER PASS SUMMARY (bars 60-64):")
        print(f"  Volatility: {filter_pass_counts['volatility']}/5 ({filter_pass_counts['volatility']/5*100:.0f}%)")
        print(f"  Regime: {filter_pass_counts['regime']}/5 ({filter_pass_counts['regime']/5*100:.0f}%)")
        print(f"  ADX: {filter_pass_counts['adx']}/5 ({filter_pass_counts['adx']/5*100:.0f}%)")
        print(f"  All Pass: {filter_pass_counts['all']}/5 ({filter_pass_counts['all']/5*100:.0f}%)")
        
        # Check overall filter stats from processor
        print(f"\nOVERALL FILTER STATS (all {processor.bars_processed} bars):")
        if processor.total_bars_for_filters > 0:
            vol_rate = processor.volatility_pass_count / processor.total_bars_for_filters * 100
            regime_rate = processor.regime_pass_count / processor.total_bars_for_filters * 100
            adx_rate = processor.adx_pass_count / processor.total_bars_for_filters * 100
            print(f"  Volatility: {vol_rate:.1f}% ({processor.volatility_pass_count}/{processor.total_bars_for_filters})")
            print(f"  Regime: {regime_rate:.1f}% ({processor.regime_pass_count}/{processor.total_bars_for_filters})")
            print(f"  ADX: {adx_rate:.1f}% ({processor.adx_pass_count}/{processor.total_bars_for_filters})")
        
else:
    print("No access token found")

print("\n✅ Debug test complete!")
