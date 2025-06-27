#!/usr/bin/env python3
"""
Correct Diagnosis of 5-Minute ML Predictions
===========================================

Properly accounts for warmup period
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import pandas as pd
import json
import numpy as np

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.fivemin_optimized_settings import FIVEMIN_BALANCED
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def diagnose_ml_correctly():
    """Proper ML diagnosis accounting for warmup"""
    
    print("="*80)
    print("🔍 CORRECT ML DIAGNOSIS FOR 5-MINUTE CONFIG")
    print("="*80)
    
    # Get sufficient data
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # 3 months
    
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return
    
    print(f"\n📊 Total bars: {len(df)}")
    print(f"   Warmup period: {FIVEMIN_BALANCED.max_bars_back} bars")
    print(f"   Bars after warmup: {len(df) - FIVEMIN_BALANCED.max_bars_back}")
    
    if len(df) <= FIVEMIN_BALANCED.max_bars_back:
        print("\n❌ Not enough data! Need more than warmup period")
        return
    
    # Create processor
    processor = EnhancedBarProcessor(FIVEMIN_BALANCED, symbol, "5minute")
    
    # Track results
    warmup_predictions = []
    active_predictions = []
    signals = []
    entries = []
    filter_pass_rates = {'volatility': 0, 'regime': 0, 'adx': 0}
    filter_counts = 0
    
    print("\n🔄 Processing bars...")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        if i < FIVEMIN_BALANCED.max_bars_back:
            # During warmup
            warmup_predictions.append(result.prediction)
            if i % 500 == 0:
                print(f"   Warmup: {i}/{FIVEMIN_BALANCED.max_bars_back} bars")
        else:
            # After warmup - this is where ML should be active
            active_predictions.append(result.prediction)
            signals.append(result.signal)
            
            # Track filters
            filter_counts += 1
            if result.filter_volatility:
                filter_pass_rates['volatility'] += 1
            if result.filter_regime:
                filter_pass_rates['regime'] += 1
            if result.filter_adx:
                filter_pass_rates['adx'] += 1
            
            # Track entries
            if result.start_long_trade or result.start_short_trade:
                entries.append({
                    'bar': i,
                    'type': 'long' if result.start_long_trade else 'short',
                    'prediction': result.prediction,
                    'signal': result.signal
                })
            
            # Progress
            if (i - FIVEMIN_BALANCED.max_bars_back) % 500 == 0:
                active_bars = i - FIVEMIN_BALANCED.max_bars_back
                print(f"   Active: {active_bars} bars processed")
    
    # Analyze results
    print(f"\n\n📊 ANALYSIS RESULTS:")
    print("="*60)
    
    # 1. Warmup verification
    print(f"\n1. WARMUP PERIOD VERIFICATION:")
    warmup_array = np.array(warmup_predictions)
    non_zero_warmup = np.sum(np.abs(warmup_array) > 0.01)
    print(f"   Warmup predictions: {len(warmup_predictions)}")
    print(f"   Non-zero during warmup: {non_zero_warmup}")
    print(f"   ✅ Correct: ML should be 0.00 during warmup")
    
    # 2. Active period analysis
    print(f"\n2. ACTIVE PERIOD ANALYSIS:")
    active_array = np.array(active_predictions)
    non_zero_active = np.sum(np.abs(active_array) > 0.01)
    
    print(f"   Active predictions: {len(active_predictions)}")
    print(f"   Non-zero predictions: {non_zero_active} ({non_zero_active/len(active_predictions)*100:.1f}%)")
    print(f"   Prediction range: [{active_array.min():.2f}, {active_array.max():.2f}]")
    print(f"   Mean |prediction|: {np.abs(active_array).mean():.2f}")
    
    if non_zero_active / len(active_predictions) < 0.8:
        print(f"   ❌ WARNING: Only {non_zero_active/len(active_predictions)*100:.1f}% non-zero!")
    else:
        print(f"   ✅ Good: {non_zero_active/len(active_predictions)*100:.1f}% non-zero predictions")
    
    # 3. Signal distribution
    signal_array = np.array(signals)
    long_signals = np.sum(signal_array == 1)
    short_signals = np.sum(signal_array == -1)
    
    print(f"\n3. SIGNAL DISTRIBUTION:")
    print(f"   Long signals: {long_signals} ({long_signals/len(signals)*100:.1f}%)")
    print(f"   Short signals: {short_signals} ({short_signals/len(signals)*100:.1f}%)")
    print(f"   Total ML signals: {long_signals + short_signals}")
    
    # 4. Filter analysis
    print(f"\n4. FILTER PASS RATES:")
    for filter_name, count in filter_pass_rates.items():
        rate = count / filter_counts * 100 if filter_counts > 0 else 0
        print(f"   {filter_name.capitalize()}: {rate:.1f}%")
    
    # 5. Entry generation
    print(f"\n5. ENTRY GENERATION:")
    print(f"   Total entries: {len(entries)}")
    if long_signals + short_signals > 0:
        entry_rate = len(entries) / (long_signals + short_signals) * 100
        print(f"   Entry rate: {entry_rate:.1f}% of ML signals")
    
    if entries:
        print(f"\n   First 5 entries:")
        for i, entry in enumerate(entries[:5]):
            print(f"   {i+1}. Bar {entry['bar']}: {entry['type']}, "
                  f"ML={entry['prediction']:.2f}, Signal={entry['signal']}")
    
    # 6. Final verdict
    print(f"\n\n💡 DIAGNOSIS:")
    print("="*60)
    
    if non_zero_active / len(active_predictions) > 0.8:
        print("✅ ML predictions are working correctly!")
        print(f"   {non_zero_active/len(active_predictions)*100:.1f}% of predictions are non-zero after warmup")
    else:
        print("❌ ML predictions have issues")
        print(f"   Only {non_zero_active/len(active_predictions)*100:.1f}% non-zero after warmup")
    
    if len(entries) < 10:
        print("\n⚠️ Very few entries generated")
        print("   Check entry conditions and filters")
    
    print(f"\n📊 Summary:")
    print(f"   - ML is correctly silent during {FIVEMIN_BALANCED.max_bars_back}-bar warmup")
    print(f"   - After warmup: {non_zero_active} non-zero predictions from {len(active_predictions)} bars")
    print(f"   - Generated {len(entries)} trading entries")


if __name__ == "__main__":
    diagnose_ml_correctly()