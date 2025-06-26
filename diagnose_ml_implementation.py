#!/usr/bin/env python3
"""
Diagnose ML Implementation Issues
=================================

Figure out why ML threshold isn't improving win rate
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


def analyze_ml_vs_entries():
    """Analyze relationship between ML predictions and entry quality"""
    
    print("="*80)
    print("🔍 ANALYZING ML PREDICTIONS VS ENTRY QUALITY")
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
    config.use_dynamic_exits = True
    processor = EnhancedBarProcessor(config, symbol, "5minute")
    
    # Track all potential entries with their ML predictions
    entries = []
    
    print(f"\nProcessing {len(df)} bars...")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # After warmup
        if i >= config.max_bars_back:
            # Record potential entry
            if result.start_long_trade or result.start_short_trade:
                entry = {
                    'bar': i,
                    'date': idx,
                    'type': 'long' if result.start_long_trade else 'short',
                    'ml_prediction': result.prediction,
                    'price': row['close'],
                    'signal': result.signal
                }
                
                # Simulate exit after 5 bars to check if it would be profitable
                exit_bar = min(i + 5, len(df) - 1)
                exit_price = df.iloc[exit_bar]['close']
                
                if entry['type'] == 'long':
                    pnl = (exit_price - entry['price']) / entry['price'] * 100
                else:
                    pnl = (entry['price'] - exit_price) / entry['price'] * 100
                
                entry['pnl'] = pnl
                entry['is_winner'] = pnl > 0
                entries.append(entry)
    
    if not entries:
        print("No entries found!")
        return
    
    # Analyze entries by ML prediction strength
    print(f"\nFound {len(entries)} entries")
    
    # Convert to DataFrame for analysis
    entries_df = pd.DataFrame(entries)
    
    # Group by ML prediction strength
    bins = [-10, -5, -3, -1, 0, 1, 3, 5, 10]
    entries_df['ml_bin'] = pd.cut(entries_df['ml_prediction'], bins=bins)
    
    print("\n📊 WIN RATE BY ML PREDICTION STRENGTH:")
    print("-"*60)
    
    for ml_range in entries_df['ml_bin'].unique():
        if pd.isna(ml_range):
            continue
            
        subset = entries_df[entries_df['ml_bin'] == ml_range]
        if len(subset) > 0:
            win_rate = subset['is_winner'].mean() * 100
            avg_pnl = subset['pnl'].mean()
            count = len(subset)
            
            print(f"ML {ml_range}: {count} trades, {win_rate:.1f}% win rate, {avg_pnl:.2f}% avg PnL")
    
    # Test different thresholds
    print("\n📊 IMPACT OF ML THRESHOLD:")
    print("-"*60)
    
    for threshold in [0, 1, 2, 3, 4, 5]:
        filtered = entries_df[entries_df['ml_prediction'].abs() >= threshold]
        if len(filtered) > 0:
            win_rate = filtered['is_winner'].mean() * 100
            avg_pnl = filtered['pnl'].mean()
            count = len(filtered)
            print(f"Threshold >= {threshold}: {count} trades, {win_rate:.1f}% win rate, {avg_pnl:.2f}% avg PnL")
    
    # Check if stronger predictions are actually better
    print("\n🔍 CORRELATION ANALYSIS:")
    if len(entries_df) > 5:
        corr = entries_df['ml_prediction'].abs().corr(entries_df['pnl'])
        print(f"Correlation between |ML prediction| and PnL: {corr:.3f}")
        
        if corr < 0.1:
            print("⚠️ WARNING: ML prediction strength has weak correlation with profitability!")
            print("   This explains why ML threshold doesn't improve win rate")
    
    # Save detailed results
    entries_df.to_csv('ml_prediction_analysis.csv', index=False)
    print(f"\n💾 Detailed results saved to ml_prediction_analysis.csv")


def test_entry_logic():
    """Test if entries are being generated correctly"""
    
    print("\n" + "="*80)
    print("🔍 TESTING ENTRY GENERATION LOGIC")
    print("="*80)
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return
    
    config = TradingConfig()
    config.use_dynamic_exits = True
    processor = EnhancedBarProcessor(config, symbol, "5minute")
    
    # Track signals vs entries
    ml_signals = 0  # When ML says long/short
    filter_pass = 0  # When filters pass
    entries = 0      # Actual entries
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        if i >= config.max_bars_back:
            if result.signal != 0:
                ml_signals += 1
                
                # Check if filters passed
                all_filters = all([
                    result.filter_states.get('volatility', True),
                    result.filter_states.get('regime', True),
                    result.filter_states.get('adx', True)
                ])
                
                if all_filters:
                    filter_pass += 1
            
            if result.start_long_trade or result.start_short_trade:
                entries += 1
    
    print(f"\nSignal Flow Analysis:")
    print(f"ML Signals (non-zero): {ml_signals}")
    print(f"After filters: {filter_pass}")
    print(f"Final entries: {entries}")
    print(f"\nConversion rate: {entries/ml_signals*100:.1f}% of ML signals become entries")
    
    if entries < ml_signals * 0.1:
        print("\n⚠️ WARNING: Very few ML signals convert to entries!")
        print("   Check if entry conditions are too restrictive")


if __name__ == "__main__":
    analyze_ml_vs_entries()
    test_entry_logic()