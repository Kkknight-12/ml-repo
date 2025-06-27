#!/usr/bin/env python3
"""
Analyze Entry Condition Bottlenecks
===================================

Find out which conditions are blocking entries
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import pandas as pd
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


def analyze_entry_bottlenecks():
    """Analyze which conditions block entries"""
    
    print("="*80)
    print("🔍 ANALYZING ENTRY CONDITION BOTTLENECKS")
    print("="*80)
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # Get data
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return
    
    config = TradingConfig()
    processor = EnhancedBarProcessor(config, symbol, "5minute")
    
    # Track conditions
    condition_stats = {
        'total_bars': 0,
        'ml_long_signals': 0,
        'ml_short_signals': 0,
        'different_signal': 0,
        'bullish_kernel': 0,
        'bearish_kernel': 0,
        'ema_uptrend': 0,
        'ema_downtrend': 0,
        'sma_uptrend': 0,
        'sma_downtrend': 0,
        'long_entry_conditions': {
            'signal_only': 0,
            'signal_different': 0,
            'signal_different_kernel': 0,
            'signal_different_kernel_ema': 0,
            'all_conditions': 0
        },
        'short_entry_conditions': {
            'signal_only': 0,
            'signal_different': 0,
            'signal_different_kernel': 0,
            'signal_different_kernel_ema': 0,
            'all_conditions': 0
        }
    }
    
    previous_signal = 0
    
    print(f"\nProcessing {len(df)} bars...")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # After warmup
        if i >= config.max_bars_back:
            condition_stats['total_bars'] += 1
            
            # Track individual conditions
            current_signal = result.signal
            is_different = current_signal != previous_signal
            
            # Get trend states from processor
            # We need to access internal states
            bar_processor = processor
            close = row['close']
            
            # Calculate trends using processor methods
            is_ema_uptrend, is_ema_downtrend = bar_processor._calculate_ema_trend_stateful(close)
            is_sma_uptrend, is_sma_downtrend = bar_processor._calculate_sma_trend_stateful(close)
            is_bullish_kernel = bar_processor._calculate_kernel_bullish()
            is_bearish_kernel = bar_processor._calculate_kernel_bearish()
            
            # Track base conditions
            if current_signal == 1:  # Long
                condition_stats['ml_long_signals'] += 1
            elif current_signal == -1:  # Short
                condition_stats['ml_short_signals'] += 1
            
            if is_different:
                condition_stats['different_signal'] += 1
            if is_bullish_kernel:
                condition_stats['bullish_kernel'] += 1
            if is_bearish_kernel:
                condition_stats['bearish_kernel'] += 1
            if is_ema_uptrend:
                condition_stats['ema_uptrend'] += 1
            if is_ema_downtrend:
                condition_stats['ema_downtrend'] += 1
            if is_sma_uptrend:
                condition_stats['sma_uptrend'] += 1
            if is_sma_downtrend:
                condition_stats['sma_downtrend'] += 1
            
            # Track progressive condition fulfillment for LONG
            if current_signal == 1:  # Long signal
                condition_stats['long_entry_conditions']['signal_only'] += 1
                
                if is_different:
                    condition_stats['long_entry_conditions']['signal_different'] += 1
                    
                    if is_bullish_kernel:
                        condition_stats['long_entry_conditions']['signal_different_kernel'] += 1
                        
                        if is_ema_uptrend:
                            condition_stats['long_entry_conditions']['signal_different_kernel_ema'] += 1
                            
                            if is_sma_uptrend:
                                condition_stats['long_entry_conditions']['all_conditions'] += 1
            
            # Track progressive condition fulfillment for SHORT
            if current_signal == -1:  # Short signal
                condition_stats['short_entry_conditions']['signal_only'] += 1
                
                if is_different:
                    condition_stats['short_entry_conditions']['signal_different'] += 1
                    
                    if is_bearish_kernel:
                        condition_stats['short_entry_conditions']['signal_different_kernel'] += 1
                        
                        if is_ema_downtrend:
                            condition_stats['short_entry_conditions']['signal_different_kernel_ema'] += 1
                            
                            if is_sma_downtrend:
                                condition_stats['short_entry_conditions']['all_conditions'] += 1
            
            previous_signal = current_signal
    
    # Print analysis
    print(f"\n📊 ENTRY CONDITION ANALYSIS:")
    print(f"Total bars analyzed: {condition_stats['total_bars']}")
    
    if condition_stats['total_bars'] > 0:
        print(f"\n1. BASE CONDITIONS:")
        print(f"   ML Long signals: {condition_stats['ml_long_signals']} ({condition_stats['ml_long_signals']/condition_stats['total_bars']*100:.1f}%)")
        print(f"   ML Short signals: {condition_stats['ml_short_signals']} ({condition_stats['ml_short_signals']/condition_stats['total_bars']*100:.1f}%)")
        print(f"   Different from previous: {condition_stats['different_signal']} ({condition_stats['different_signal']/condition_stats['total_bars']*100:.1f}%)")
        
        print(f"\n2. KERNEL CONDITIONS:")
        print(f"   Bullish kernel: {condition_stats['bullish_kernel']} ({condition_stats['bullish_kernel']/condition_stats['total_bars']*100:.1f}%)")
        print(f"   Bearish kernel: {condition_stats['bearish_kernel']} ({condition_stats['bearish_kernel']/condition_stats['total_bars']*100:.1f}%)")
        
        print(f"\n3. TREND CONDITIONS:")
        print(f"   EMA uptrend: {condition_stats['ema_uptrend']} ({condition_stats['ema_uptrend']/condition_stats['total_bars']*100:.1f}%)")
        print(f"   EMA downtrend: {condition_stats['ema_downtrend']} ({condition_stats['ema_downtrend']/condition_stats['total_bars']*100:.1f}%)")
        print(f"   SMA uptrend: {condition_stats['sma_uptrend']} ({condition_stats['sma_uptrend']/condition_stats['total_bars']*100:.1f}%)")
        print(f"   SMA downtrend: {condition_stats['sma_downtrend']} ({condition_stats['sma_downtrend']/condition_stats['total_bars']*100:.1f}%)")
        
        print(f"\n4. LONG ENTRY FUNNEL:")
        long_stats = condition_stats['long_entry_conditions']
        for stage, count in long_stats.items():
            print(f"   {stage}: {count}")
        
        print(f"\n5. SHORT ENTRY FUNNEL:")
        short_stats = condition_stats['short_entry_conditions']
        for stage, count in short_stats.items():
            print(f"   {stage}: {count}")
        
        # Calculate bottlenecks
        print(f"\n🚧 BOTTLENECK ANALYSIS:")
        
        if long_stats['signal_only'] > 0:
            print(f"\nLONG entries:")
            print(f"  Signal → Different: {long_stats['signal_different']/long_stats['signal_only']*100:.1f}% pass")
            if long_stats['signal_different'] > 0:
                print(f"  Different → Kernel: {long_stats['signal_different_kernel']/long_stats['signal_different']*100:.1f}% pass")
            if long_stats['signal_different_kernel'] > 0:
                print(f"  Kernel → EMA: {long_stats['signal_different_kernel_ema']/long_stats['signal_different_kernel']*100:.1f}% pass")
            if long_stats['signal_different_kernel_ema'] > 0:
                print(f"  EMA → SMA: {long_stats['all_conditions']/long_stats['signal_different_kernel_ema']*100:.1f}% pass")
        
        total_entries = long_stats['all_conditions'] + short_stats['all_conditions']
        total_signals = condition_stats['ml_long_signals'] + condition_stats['ml_short_signals']
        
        print(f"\n📈 OVERALL:")
        print(f"  Total ML signals: {total_signals}")
        print(f"  Total entries: {total_entries}")
        print(f"  Conversion rate: {total_entries/total_signals*100:.1f}%")
        
        print(f"\n💡 RECOMMENDATIONS:")
        if total_entries/total_signals < 0.1:
            print("  ⚠️ Entry conditions are too restrictive!")
            print("  Consider:")
            print("  - Removing SMA trend requirement")
            print("  - Relaxing kernel requirements")
            print("  - Using OR conditions instead of AND")


if __name__ == "__main__":
    analyze_entry_bottlenecks()