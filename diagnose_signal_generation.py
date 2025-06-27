#!/usr/bin/env python3
"""
Diagnose Signal Generation Issues
=================================

Understand why signals aren't being generated
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def diagnose_signals():
    """Deep dive into signal generation"""
    
    print("="*80)
    print("🔍 DIAGNOSING SIGNAL GENERATION")
    print("="*80)
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # Use 180 days
    
    # Get data
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return
    
    print(f"\nData: {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    
    config = TradingConfig()
    config.use_dynamic_exits = True
    processor = EnhancedBarProcessor(config, symbol, "5minute")
    
    # Track everything
    stats = {
        'total_bars': 0,
        'ml_predictions_non_zero': 0,
        'ml_signals_non_zero': 0,
        'filter_volatility_pass': 0,
        'filter_regime_pass': 0,
        'filter_adx_pass': 0,
        'filter_all_pass': 0,
        'kernel_bullish': 0,
        'kernel_bearish': 0,
        'ema_uptrend': 0,
        'ema_downtrend': 0,
        'sma_uptrend': 0,
        'sma_downtrend': 0,
        'entries_long': 0,
        'entries_short': 0
    }
    
    ml_predictions = []
    signals = []
    
    print(f"\nProcessing {len(df)} bars...")
    print(f"Warmup period: {config.max_bars_back} bars")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # Show progress
        if i % 1000 == 0:
            print(f"  Processed {i} bars...")
        
        # After warmup
        if i >= config.max_bars_back:
            stats['total_bars'] += 1
            
            # ML predictions
            ml_predictions.append(result.prediction)
            if abs(result.prediction) > 0.1:
                stats['ml_predictions_non_zero'] += 1
            
            # ML signals
            signals.append(result.signal)
            if result.signal != 0:
                stats['ml_signals_non_zero'] += 1
            
            # Filters
            if result.filter_states.get('volatility', False):
                stats['filter_volatility_pass'] += 1
            if result.filter_states.get('regime', False):
                stats['filter_regime_pass'] += 1
            if result.filter_states.get('adx', False):
                stats['filter_adx_pass'] += 1
            if result.filter_all:
                stats['filter_all_pass'] += 1
            
            # Kernel states (from result attributes)
            if hasattr(result, 'is_bullish_kernel') and result.is_bullish_kernel:
                stats['kernel_bullish'] += 1
            if hasattr(result, 'is_bearish_kernel') and result.is_bearish_kernel:
                stats['kernel_bearish'] += 1
            
            # Trend states
            if hasattr(result, 'is_ema_uptrend') and result.is_ema_uptrend:
                stats['ema_uptrend'] += 1
            if hasattr(result, 'is_ema_downtrend') and result.is_ema_downtrend:
                stats['ema_downtrend'] += 1
            if hasattr(result, 'is_sma_uptrend') and result.is_sma_uptrend:
                stats['sma_uptrend'] += 1
            if hasattr(result, 'is_sma_downtrend') and result.is_sma_downtrend:
                stats['sma_downtrend'] += 1
            
            # Entries
            if result.start_long_trade:
                stats['entries_long'] += 1
            if result.start_short_trade:
                stats['entries_short'] += 1
    
    # Print analysis
    print(f"\n📊 SIGNAL GENERATION ANALYSIS:")
    print(f"Total bars after warmup: {stats['total_bars']}")
    
    if stats['total_bars'] > 0:
        print(f"\n1. ML PREDICTIONS:")
        print(f"   Non-zero predictions: {stats['ml_predictions_non_zero']} ({stats['ml_predictions_non_zero']/stats['total_bars']*100:.1f}%)")
        if ml_predictions:
            pred_array = np.array(ml_predictions)
            print(f"   Prediction range: [{pred_array.min():.1f}, {pred_array.max():.1f}]")
            print(f"   Average |prediction|: {np.abs(pred_array).mean():.2f}")
        
        print(f"\n2. ML SIGNALS (after filters):")
        print(f"   Non-zero signals: {stats['ml_signals_non_zero']} ({stats['ml_signals_non_zero']/stats['total_bars']*100:.1f}%)")
        
        print(f"\n3. INDIVIDUAL FILTERS:")
        print(f"   Volatility filter pass: {stats['filter_volatility_pass']} ({stats['filter_volatility_pass']/stats['total_bars']*100:.1f}%)")
        print(f"   Regime filter pass: {stats['filter_regime_pass']} ({stats['filter_regime_pass']/stats['total_bars']*100:.1f}%)")
        print(f"   ADX filter pass: {stats['filter_adx_pass']} ({stats['filter_adx_pass']/stats['total_bars']*100:.1f}%)")
        print(f"   ALL filters pass: {stats['filter_all_pass']} ({stats['filter_all_pass']/stats['total_bars']*100:.1f}%)")
        
        print(f"\n4. KERNEL STATES:")
        print(f"   Bullish kernel: {stats['kernel_bullish']} ({stats['kernel_bullish']/stats['total_bars']*100:.1f}%)")
        print(f"   Bearish kernel: {stats['kernel_bearish']} ({stats['kernel_bearish']/stats['total_bars']*100:.1f}%)")
        
        print(f"\n5. TREND STATES:")
        print(f"   EMA uptrend: {stats['ema_uptrend']} ({stats['ema_uptrend']/stats['total_bars']*100:.1f}%)")
        print(f"   EMA downtrend: {stats['ema_downtrend']} ({stats['ema_downtrend']/stats['total_bars']*100:.1f}%)")
        print(f"   SMA uptrend: {stats['sma_uptrend']} ({stats['sma_uptrend']/stats['total_bars']*100:.1f}%)")
        print(f"   SMA downtrend: {stats['sma_downtrend']} ({stats['sma_downtrend']/stats['total_bars']*100:.1f}%)")
        
        print(f"\n6. FINAL ENTRIES:")
        print(f"   Long entries: {stats['entries_long']}")
        print(f"   Short entries: {stats['entries_short']}")
        print(f"   Total entries: {stats['entries_long'] + stats['entries_short']}")
        
        # Diagnose bottlenecks
        print(f"\n🔍 BOTTLENECK ANALYSIS:")
        
        if stats['ml_predictions_non_zero'] == 0:
            print("❌ No ML predictions! Check if ML model is working")
        elif stats['ml_signals_non_zero'] == 0:
            print("❌ ML predictions exist but no signals generated")
            print("   → Check if filter_all is too restrictive")
        elif stats['entries_long'] + stats['entries_short'] == 0:
            print("❌ Signals exist but no entries generated")
            print("   → Check entry conditions (kernel, trend alignment)")
        
        # Check signal-to-entry conversion
        if stats['ml_signals_non_zero'] > 0:
            conversion = (stats['entries_long'] + stats['entries_short']) / stats['ml_signals_non_zero'] * 100
            print(f"\n📈 Signal to entry conversion: {conversion:.1f}%")
            if conversion < 10:
                print("   ⚠️ Very low conversion rate - entry conditions too strict")
    else:
        print("\n⚠️ No bars processed after warmup period!")
        print(f"   Need at least {config.max_bars_back + 1} bars")


def check_specific_conditions():
    """Check specific conditions that might block entries"""
    
    print("\n" + "="*80)
    print("🔍 CHECKING SPECIFIC CONDITIONS")
    print("="*80)
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        return
    
    config = TradingConfig()
    
    # Check key settings
    print(f"\nConfiguration Check:")
    print(f"  use_volatility_filter: {config.use_volatility_filter}")
    print(f"  use_regime_filter: {config.use_regime_filter}")
    print(f"  use_adx_filter: {config.use_adx_filter}")
    print(f"  use_kernel_filter: {config.use_kernel_filter}")
    print(f"  use_ema_filter: {config.use_ema_filter}")
    print(f"  use_sma_filter: {config.use_sma_filter}")
    print(f"  max_bars_back: {config.max_bars_back}")
    
    # Check if we have enough data
    print(f"\nData Check:")
    print(f"  Total bars: {len(df)}")
    print(f"  Bars after warmup: {max(0, len(df) - config.max_bars_back)}")
    
    if len(df) <= config.max_bars_back:
        print("  ❌ ERROR: Not enough data for warmup period!")
        print(f"     Need {config.max_bars_back + 1} bars, have {len(df)}")


if __name__ == "__main__":
    diagnose_signals()
    check_specific_conditions()