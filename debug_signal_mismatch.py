#!/usr/bin/env python3
"""
Debug script to investigate why Pine Script and Python signals don't match
"""
import pandas as pd
import csv
from datetime import datetime

def analyze_signal_mismatch():
    """Analyze the differences between Pine Script and Python signals"""
    
    # Pine Script signals from the output
    pine_signals = [
        ('2024-04-18', 'SELL', 1078.05),
        ('2024-04-25', 'BUY', 1089.95),
        ('2024-05-29', 'SELL', 1123.55),
        ('2024-06-03', 'BUY', 1136.30),
        ('2024-07-25', 'SELL', 1218.25),
        ('2024-08-27', 'BUY', 1208.90),
        ('2024-10-03', 'SELL', 1265.75),
        ('2024-10-22', 'BUY', 1259.75),
        ('2024-11-11', 'SELL', 1275.90),
        ('2024-11-25', 'BUY', 1290.00),
        ('2024-12-19', 'SELL', 1303.00),
        ('2025-01-28', 'BUY', 1236.00),
        ('2025-02-24', 'SELL', 1231.90),
        ('2025-03-17', 'BUY', 1254.20),
        ('2025-04-11', 'SELL', 1365.80),
        ('2025-04-15', 'BUY', 1336.20),
    ]
    
    # Python signals from the output
    python_signals = [
        ('2023-08-14', 'SELL', 962.90),
        ('2023-12-08', 'BUY', 993.25),
        ('2024-01-23', 'BUY', 1021.20),
        ('2024-03-06', 'BUY', 1080.30),
        ('2024-04-18', 'SELL', 1078.05),
        ('2024-06-19', 'BUY', 1126.15),
        ('2024-10-07', 'SELL', 1262.95),
        ('2024-11-25', 'BUY', 1290.00),
        ('2024-12-19', 'SELL', 1303.00),
        ('2025-04-15', 'BUY', 1336.20),
    ]
    
    # Convert to DataFrames for easier analysis
    pine_df = pd.DataFrame(pine_signals, columns=['date', 'type', 'price'])
    pine_df['date'] = pd.to_datetime(pine_df['date'])
    pine_df['source'] = 'Pine'
    
    python_df = pd.DataFrame(python_signals, columns=['date', 'type', 'price'])
    python_df['date'] = pd.to_datetime(python_df['date'])
    python_df['source'] = 'Python'
    
    # Merge to find matches and differences
    all_signals = pd.concat([pine_df, python_df]).sort_values('date')
    
    print("="*70)
    print("SIGNAL TIMING ANALYSIS")
    print("="*70)
    
    # Group by date to find matches
    date_groups = all_signals.groupby('date')
    
    print("\n1. MATCHING SIGNALS (same date, same type):")
    matches = []
    for date, group in date_groups:
        if len(group) == 2:  # Both Pine and Python have signals
            pine_sig = group[group['source'] == 'Pine'].iloc[0]
            py_sig = group[group['source'] == 'Python'].iloc[0]
            if pine_sig['type'] == py_sig['type']:
                matches.append(date)
                print(f"   ✓ {date.strftime('%Y-%m-%d')}: {pine_sig['type']} "
                      f"(Pine: ₹{pine_sig['price']:.2f}, Python: ₹{py_sig['price']:.2f})")
    
    print(f"\nTotal matches: {len(matches)}")
    
    print("\n2. PYTHON EARLY SIGNALS (Python signals before Pine):")
    python_early = python_df[python_df['date'] < pine_df['date'].min()]
    for _, row in python_early.iterrows():
        print(f"   🐍 {row['date'].strftime('%Y-%m-%d')}: {row['type']} @ ₹{row['price']:.2f}")
    
    print("\n3. PINE-ONLY SIGNALS (no matching Python signal):")
    pine_only_dates = []
    for _, pine_row in pine_df.iterrows():
        if pine_row['date'] not in python_df['date'].values:
            pine_only_dates.append(pine_row['date'])
            print(f"   📌 {pine_row['date'].strftime('%Y-%m-%d')}: {pine_row['type']} @ ₹{pine_row['price']:.2f}")
    
    print("\n4. SIGNAL FREQUENCY ANALYSIS:")
    pine_date_range = (pine_df['date'].max() - pine_df['date'].min()).days
    python_date_range = (python_df['date'].max() - python_df['date'].min()).days
    
    print(f"   Pine Script: {len(pine_df)} signals over {pine_date_range} days "
          f"({pine_date_range/len(pine_df):.1f} days/signal)")
    print(f"   Python: {len(python_df)} signals over {python_date_range} days "
          f"({python_date_range/len(python_df):.1f} days/signal)")
    
    print("\n5. SIGNAL CLUSTERING:")
    # Check if signals cluster around specific periods
    pine_df['month'] = pine_df['date'].dt.to_period('M')
    python_df['month'] = python_df['date'].dt.to_period('M')
    
    print("\n   Pine signals by month:")
    for month, count in pine_df['month'].value_counts().sort_index().items():
        print(f"      {month}: {count} signals")
    
    print("\n   Python signals by month:")
    for month, count in python_df['month'].value_counts().sort_index().items():
        print(f"      {month}: {count} signals")
    
    print("\n6. KEY OBSERVATIONS:")
    print("   • Python generates signals earlier (Aug 2023) than Pine (Apr 2024)")
    print("   • Pine generates more frequent signals in mid-2024")
    print("   • Both agree on recent signals (Nov 2024 - Apr 2025)")
    print("   • Signal mismatch concentrated in Apr-Oct 2024 period")
    
    print("\n7. POTENTIAL CAUSES:")
    print("   • Different filter calculations during volatile periods")
    print("   • Regime filter sensitivity differences")
    print("   • Entry condition timing (signal transitions vs new signals)")
    print("   • Warmup period effects on early signals")

if __name__ == "__main__":
    analyze_signal_mismatch()