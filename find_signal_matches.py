#!/usr/bin/env python3
"""
Find matching signals between Pine Script manual and our system
"""

import pandas as pd
from datetime import datetime, timedelta

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
    ("2025-05-28 11:00:00", "buy"),
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
    ("2025-06-17 11:35:00", "buy"),
    ("2025-06-17 13:45:00", "sell"),
    ("2025-06-18 09:25:00", "buy"),
    ("2025-06-18 10:45:00", "sell"),
    ("2025-06-18 15:20:00", "buy"),
    ("2025-06-19 13:10:00", "sell"),
    ("2025-06-20 09:40:00", "buy"),
    ("2025-06-20 12:35:00", "sell"),
    ("2025-06-20 13:20:00", "buy"),
    ("2025-06-23 09:15:00", "sell"),
    ("2025-06-23 11:10:00", "buy"),
    ("2025-06-23 14:25:00", "sell"),
    ("2025-06-24 09:15:00", "buy"),
    ("2025-06-24 12:35:00", "sell"),
    ("2025-06-24 15:10:00", "buy"),
    ("2025-06-25 12:45:00", "sell"),
    ("2025-06-26 09:25:00", "buy"),
    ("2025-06-26 14:50:00", "sell"),
    ("2025-06-26 15:00:00", "buy"),
]

def main():
    print("="*80)
    print("FINDING MATCHING SIGNALS")
    print("="*80)
    
    # Load our Pine Script logic results
    our_df = pd.read_csv('5min_final_5-Min_Pine_Script_ml.backtest()_Logic.csv')
    our_df['entry_datetime'] = pd.to_datetime(our_df['entry_date']).dt.tz_localize(None)
    
    # Convert manual signals to dataframe
    manual_df = pd.DataFrame(MANUAL_SIGNALS, columns=['datetime', 'signal'])
    manual_df['datetime'] = pd.to_datetime(manual_df['datetime'])
    
    # Find matches
    matches = []
    for _, manual in manual_df.iterrows():
        manual_time = manual['datetime']
        manual_signal = 'long' if manual['signal'] == 'buy' else 'short'
        
        # Look for our signals within +/- 30 minutes
        for _, our in our_df.iterrows():
            our_time = our['entry_datetime']
            time_diff = abs((manual_time - our_time).total_seconds() / 60)
            
            if time_diff <= 30 and manual_signal == our['type']:
                matches.append({
                    'manual_time': manual_time,
                    'our_time': our_time,
                    'signal': manual_signal,
                    'time_diff_minutes': time_diff,
                    'ml_prediction': our['ml_strength']
                })
                break
    
    print(f"\n✅ Found {len(matches)} matches out of {len(manual_df)} manual signals")
    print(f"Match rate: {len(matches)/len(manual_df)*100:.1f}%")
    
    if matches:
        match_df = pd.DataFrame(matches)
        print("\nMatching signals:")
        for _, match in match_df.iterrows():
            print(f"  Manual: {match['manual_time']} → Our: {match['our_time']} "
                  f"({match['time_diff_minutes']:.0f} min diff) "
                  f"{match['signal']} ML={match['ml_prediction']}")
    
    # Find close matches (look at specific examples)
    print("\n🔍 CHECKING SPECIFIC TIMES:")
    
    # Check 2025-05-22 14:45:00 buy signal
    check_time = pd.to_datetime("2025-05-22 14:45:00")
    print(f"\nLooking for signals around {check_time}:")
    for _, our in our_df.iterrows():
        time_diff = abs((check_time - our['entry_datetime']).total_seconds() / 60)
        if time_diff <= 60:
            print(f"  Our signal: {our['entry_datetime']} {our['type']} "
                  f"(diff: {time_diff:.0f} min) ML={our['ml_strength']}")
    
    # Check what's happening around specific times
    print("\n📊 OUR SIGNALS IN MAY:")
    may_signals = our_df[our_df['entry_datetime'].dt.month == 5]
    for _, sig in may_signals.iterrows():
        print(f"  {sig['entry_datetime']}: {sig['type']} (ML: {sig['ml_strength']})")


if __name__ == "__main__":
    main()