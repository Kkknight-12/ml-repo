#!/usr/bin/env python3
"""
Compare Pine Script Manual Signals with Our System
"""

import sys
import os
sys.path.append('.')

# Disable debug output
os.environ['DISABLE_DEBUG'] = '1'

from datetime import datetime, timedelta
import pandas as pd
import json

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.fivemin_exact_settings import FIVEMIN_EXACT
from data.cache_manager import MarketDataCache

# Manual signals from Pine Script
MANUAL_SIGNALS = [
    ("2025-05-21 11:40:00", "sell"),
    ("2025-05-21 11:15:00", "buy"),
    ("2025-05-22 09:15:00", "sell"),
    ("2025-05-22 14:45:00", "buy"),
    ("2025-05-23 13:30:00", "sell"),
    ("2025-05-26 09:15:00", "buy"),
    ("2025-05-26 15:10:00", "sell"),
    ("2025-05-27 11:25:00", "buy"),
    ("2025-05-27 12:25:00", "sell"),
    ("2025-05-27 15:00:00", "buy"),
    ("2025-05-28 09:25:00", "sell"),
    ("2025-05-28 11:00:00", "buy"),  # Note: 11:00 PM seems wrong, assuming AM
    ("2025-05-28 15:10:00", "sell"),
    ("2025-05-29 09:20:00", "buy"),
    ("2025-05-29 10:20:00", "sell"),
    ("2025-05-29 13:00:00", "buy"),
    ("2025-05-30 10:15:00", "sell"),
    ("2025-05-30 15:00:00", "buy"),
    ("2025-06-02 09:15:00", "sell"),
    ("2025-06-02 11:20:00", "buy"),
    ("2025-06-03 11:10:00", "sell"),
    ("2025-06-03 11:30:00", "buy"),
    ("2025-06-03 12:50:00", "sell"),
    ("2025-06-04 11:55:00", "buy"),
    ("2025-06-05 13:30:00", "sell"),
    ("2025-06-06 10:10:00", "buy"),
    ("2025-06-06 12:10:00", "sell"),
    ("2025-06-09 09:15:00", "buy"),
    ("2025-06-09 13:00:00", "sell"),
    ("2025-06-09 15:05:00", "buy"),
    ("2025-06-10 10:50:00", "sell"),
    ("2025-06-11 09:15:00", "buy"),
    ("2025-06-11 13:25:00", "sell"),
    ("2025-06-12 09:20:00", "buy"),
    ("2025-06-12 10:40:00", "sell"),
    ("2025-06-12 15:05:00", "buy"),
    ("2025-06-13 09:15:00", "sell"),
    ("2025-06-13 11:30:00", "buy"),
    ("2025-06-13 14:50:00", "sell"),
    ("2025-06-16 09:20:00", "buy"),
    ("2025-06-16 15:25:00", "sell"),
    ("2025-06-17 11:35:00", "buy"),  # Note: 11:35 PM seems wrong, assuming AM
    ("2025-06-17 13:45:00", "sell"),
    ("2025-06-18 09:25:00", "buy"),
    ("2025-06-18 10:45:00", "sell"),
    ("2025-06-18 15:20:00", "buy"),
    ("2025-06-19 13:10:00", "sell"),
    ("2025-06-20 09:40:00", "buy"),
    ("2025-06-20 12:35:00", "sell"),  # Note: 12:35 AM seems wrong, assuming PM
    ("2025-06-20 13:20:00", "buy"),
    ("2025-06-23 09:15:00", "sell"),
    ("2025-06-23 11:10:00", "buy"),
    ("2025-06-23 14:25:00", "sell"),
    ("2025-06-24 09:15:00", "buy"),
    ("2025-06-24 12:35:00", "sell"),
    ("2025-06-24 15:10:00", "buy"),
    ("2025-06-25 12:45:00", "sell"),
    ("2025-06-26 09:25:00", "buy"),
    ("2025-06-26 14:50:00", "sell"),  # Note: 2:50 AM seems wrong, assuming PM
    ("2025-06-26 15:00:00", "buy"),   # Note: 3:00 AM seems wrong, assuming PM
]

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def main():
    """Compare manual signals with our system"""
    print("="*80)
    print("PINE SCRIPT MANUAL SIGNALS VS PYTHON SYSTEM")
    print("="*80)
    
    # Get data
    config = FIVEMIN_EXACT
    end_date = datetime(2025, 6, 26, 15, 30)
    start_date = end_date - timedelta(days=config.lookback_days)
    
    cache = MarketDataCache()
    df = cache.get_cached_data(config.symbol, start_date, end_date, config.timeframe)
    
    if df is None or df.empty:
        print("No data available")
        return
    
    print(f"\n📊 Data: {len(df)} bars")
    print(f"Index type: {type(df.index)}")
    print(f"First few indices: {df.index[:5].tolist()}")
    
    # Check if we need to set datetime index
    if 'datetime' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df = df.set_index('datetime')
        print("Set datetime as index")
    elif 'date' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df = df.set_index('date')
        print("Set date as index")
    
    # Create processor
    processor = EnhancedBarProcessor(config, config.symbol, config.timeframe)
    
    # Process all bars and collect signals
    our_signals = []
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # Skip warmup period
        if i < config.max_bars_back:
            continue
        
        # Collect entry signals
        if result.start_long_trade:
            # Try to get datetime from index or create from bar number
            if hasattr(idx, 'to_pydatetime'):
                signal_time = idx
            elif isinstance(idx, pd.Timestamp):
                signal_time = idx
            else:
                # If idx is just a number, skip for now
                continue
                
            our_signals.append({
                'datetime': signal_time,
                'signal': 'buy',
                'ml_prediction': result.prediction,
                'filters': result.filter_all
            })
        elif result.start_short_trade:
            # Try to get datetime from index or create from bar number
            if hasattr(idx, 'to_pydatetime'):
                signal_time = idx
            elif isinstance(idx, pd.Timestamp):
                signal_time = idx
            else:
                # If idx is just a number, skip for now
                continue
                
            our_signals.append({
                'datetime': signal_time,
                'signal': 'sell',
                'ml_prediction': result.prediction,
                'filters': result.filter_all
            })
    
    # Convert manual signals to datetime
    manual_df = pd.DataFrame([
        {
            'datetime': pd.to_datetime(dt),
            'signal': sig
        } for dt, sig in MANUAL_SIGNALS
    ])
    
    # Convert our signals to dataframe
    our_df = pd.DataFrame(our_signals)
    
    print(f"\n📊 Signal Count:")
    print(f"  Pine Script Manual: {len(manual_df)} signals")
    print(f"  Our System: {len(our_df)} signals")
    
    # Find matching signals (within 30 minutes)
    matches = []
    unmatched_manual = []
    unmatched_ours = []
    
    for _, manual in manual_df.iterrows():
        matched = False
        for _, our in our_df.iterrows():
            # Handle timestamp comparison properly
            manual_time = pd.Timestamp(manual['datetime']).tz_localize(None)
            our_time = pd.Timestamp(our['datetime']).tz_localize(None)
            time_diff = abs((manual_time - our_time).total_seconds() / 60)
            if time_diff <= 30 and manual['signal'] == our['signal']:
                matches.append({
                    'manual_time': manual['datetime'],
                    'our_time': our['datetime'],
                    'signal': manual['signal'],
                    'time_diff_minutes': time_diff,
                    'ml_prediction': our['ml_prediction']
                })
                matched = True
                break
        
        if not matched:
            unmatched_manual.append(manual)
    
    # Find our signals not in manual
    for _, our in our_df.iterrows():
        matched = False
        for _, match in pd.DataFrame(matches).iterrows() if matches else pd.DataFrame().iterrows():
            if our['datetime'] == match['our_time']:
                matched = True
                break
        
        if not matched:
            unmatched_ours.append(our)
    
    print(f"\n✅ Matching Signals: {len(matches)}")
    if matches:
        match_df = pd.DataFrame(matches)
        print("\nFirst 10 matches:")
        print(match_df.head(10).to_string())
    
    print(f"\n❌ Pine Script signals we missed: {len(unmatched_manual)}")
    if unmatched_manual:
        print("\nFirst 10 missed Pine signals:")
        for i, sig in enumerate(pd.DataFrame(unmatched_manual).head(10).itertuples()):
            print(f"  {sig.datetime}: {sig.signal}")
    
    print(f"\n❓ Our signals not in Pine Script: {len(unmatched_ours)}")
    if unmatched_ours:
        print("\nFirst 10 extra signals:")
        for i, sig in enumerate(pd.DataFrame(unmatched_ours).head(10).itertuples()):
            print(f"  {sig.datetime}: {sig.signal} (ML: {sig.ml_prediction})")
    
    # Calculate accuracy
    if len(manual_df) > 0:
        accuracy = len(matches) / len(manual_df) * 100
        print(f"\n📊 Signal Match Rate: {accuracy:.1f}%")
    
    # Save detailed comparison
    if matches:
        pd.DataFrame(matches).to_csv('pine_manual_vs_python_matches.csv', index=False)
        print("\n💾 Saved matches to pine_manual_vs_python_matches.csv")
    
    # Analyze timing patterns
    print("\n🕐 Signal Timing Analysis:")
    manual_hours = manual_df['datetime'].dt.hour.value_counts().sort_index()
    print("\nPine Script signals by hour:")
    for hour, count in manual_hours.items():
        print(f"  {hour:02d}:00 - {count} signals")


if __name__ == "__main__":
    main()