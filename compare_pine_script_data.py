#!/usr/bin/env python3
"""
Compare Pine Script export with Python implementation
"""
import pandas as pd
import numpy as np
from datetime import datetime
import os

def analyze_pine_script_data():
    """Analyze Pine Script data and compare with Python"""
    
    print("="*70)
    print("PINE SCRIPT DATA ANALYSIS")
    print("="*70)
    
    # Load Pine Script data
    pine_file = "archive/data_files/NSE_ICICIBANK, 1D.csv"
    df_pine = pd.read_csv(pine_file)
    
    print(f"\n✅ Loaded {len(df_pine)} bars from Pine Script export")
    print(f"   Date range: {df_pine['time'].iloc[0]} to {df_pine['time'].iloc[-1]}")
    
    # Convert time to datetime
    df_pine['time'] = pd.to_datetime(df_pine['time'])
    
    # Analyze signals
    # In Pine Script data, signals are where Buy/Sell are not NaN
    buy_signals = df_pine[df_pine['Buy'].notna()]
    sell_signals = df_pine[df_pine['Sell'].notna()]
    stop_buy_signals = df_pine[df_pine['StopBuy'].notna()]
    stop_sell_signals = df_pine[df_pine['StopSell'].notna()]
    
    print(f"\n📊 SIGNAL ANALYSIS:")
    print(f"   Buy signals: {len(buy_signals)}")
    print(f"   Sell signals: {len(sell_signals)}")
    print(f"   Stop Buy signals: {len(stop_buy_signals)}")
    print(f"   Stop Sell signals: {len(stop_sell_signals)}")
    print(f"   Total entries: {len(buy_signals) + len(sell_signals)}")
    print(f"   Total exits: {len(stop_buy_signals) + len(stop_sell_signals)}")
    
    # Show first few signals
    if len(buy_signals) > 0:
        print(f"\n   First BUY signals:")
        for idx, row in buy_signals.head(3).iterrows():
            print(f"   - {row['time'].strftime('%Y-%m-%d')}: Buy at {row['Buy']:.2f}")
    
    if len(sell_signals) > 0:
        print(f"\n   First SELL signals:")
        for idx, row in sell_signals.head(3).iterrows():
            print(f"   - {row['time'].strftime('%Y-%m-%d')}: Sell at {row['Sell']:.2f}")
    
    # Analyze kernel values
    kernel_values = df_pine['Kernel Regression Estimate']
    print(f"\n📊 KERNEL ANALYSIS:")
    print(f"   Kernel range: {kernel_values.min():.2f} to {kernel_values.max():.2f}")
    print(f"   Kernel mean: {kernel_values.mean():.2f}")
    
    # Check if kernel is bullish/bearish
    df_pine['kernel_bull'] = df_pine['Kernel Regression Estimate'] > df_pine['close']
    df_pine['kernel_bear'] = df_pine['Kernel Regression Estimate'] < df_pine['close']
    
    print(f"   Kernel bullish: {df_pine['kernel_bull'].sum()} bars ({df_pine['kernel_bull'].mean()*100:.1f}%)")
    print(f"   Kernel bearish: {df_pine['kernel_bear'].sum()} bars ({df_pine['kernel_bear'].mean()*100:.1f}%)")
    
    # Signal frequency analysis
    total_bars = len(df_pine)
    entry_rate = (len(buy_signals) + len(sell_signals)) / total_bars * 100
    
    print(f"\n📊 SIGNAL FREQUENCY:")
    print(f"   Entry rate: {entry_rate:.2f}% ({len(buy_signals) + len(sell_signals)} entries in {total_bars} bars)")
    print(f"   Average bars between entries: {total_bars / max(1, len(buy_signals) + len(sell_signals)):.1f}")
    
    # Export summary for comparison
    summary = {
        'total_bars': total_bars,
        'buy_signals': len(buy_signals),
        'sell_signals': len(sell_signals),
        'total_entries': len(buy_signals) + len(sell_signals),
        'entry_rate': entry_rate,
        'kernel_bull_rate': df_pine['kernel_bull'].mean() * 100,
        'kernel_bear_rate': df_pine['kernel_bear'].mean() * 100
    }
    
    # SUMMARY
    print(f"\n" + "="*70)
    print("SUMMARY - PINE SCRIPT ANALYSIS")
    print("="*70)
    print(f"Data Period: {df_pine['time'].iloc[0].strftime('%Y-%m-%d')} to {df_pine['time'].iloc[-1].strftime('%Y-%m-%d')}")
    print(f"Total Bars: {total_bars}")
    print(f"Entry Signals: {summary['total_entries']} (Buy: {summary['buy_signals']}, Sell: {summary['sell_signals']})")
    print(f"Entry Rate: {summary['entry_rate']:.2f}%")
    print(f"Kernel Bullish: {summary['kernel_bull_rate']:.1f}%")
    print(f"Kernel Bearish: {summary['kernel_bear_rate']:.1f}%")
    
    # Compare with Python expectations
    print(f"\n📊 COMPARISON WITH PYTHON:")
    print(f"   Python entry rate (from test): ~5.9% (3 entries in 51 bars)")
    print(f"   Pine Script entry rate: {entry_rate:.2f}%")
    print(f"   Difference: {abs(5.9 - entry_rate):.1f}%")
    print("="*70)
    
    return summary

if __name__ == "__main__":
    analyze_pine_script_data()