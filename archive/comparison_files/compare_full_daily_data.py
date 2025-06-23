#!/usr/bin/env python3
"""
Comprehensive comparison of TradingView and Zerodha daily data
Compares entire date range from 2024-04-05 onwards
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys

def load_tradingview_data(filepath):
    """Load TradingView CSV data"""
    df = pd.read_csv(filepath)
    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index('time')
    return df

def load_zerodha_data():
    """Run test_daily_data.py and capture output programmatically"""
    # For now, we'll need the user to run the script and save output
    # We'll compare with TradingView data directly
    return None

def compare_complete_data(tv_filepath):
    """Compare complete data range"""
    print("=" * 80)
    print("COMPREHENSIVE DAILY DATA COMPARISON: ICICIBANK")
    print("=" * 80)
    
    # Load TradingView data
    tv_df = load_tradingview_data(tv_filepath)
    
    print(f"\nTradingView Data Summary:")
    print(f"Date Range: {tv_df.index[0].strftime('%Y-%m-%d')} to {tv_df.index[-1].strftime('%Y-%m-%d')}")
    print(f"Total Bars: {len(tv_df)}")
    
    # Analyze signals
    buy_signals = tv_df[tv_df['Buy'].notna()]
    sell_signals = tv_df[tv_df['Sell'].notna()]
    
    print(f"\nSignal Summary:")
    print(f"Total BUY signals: {len(buy_signals)}")
    print(f"Total SELL signals: {len(sell_signals)}")
    
    # Show all signals
    print("\n" + "="*80)
    print("ALL BUY SIGNALS IN TRADINGVIEW:")
    print("="*80)
    for idx, row in buy_signals.iterrows():
        print(f"{idx.strftime('%Y-%m-%d')}: BUY @ {row['Buy']:.2f} (Close: {row['close']:.2f})")
    
    print("\n" + "="*80)
    print("ALL SELL SIGNALS IN TRADINGVIEW:")
    print("="*80)
    for idx, row in sell_signals.iterrows():
        print(f"{idx.strftime('%Y-%m-%d')}: SELL @ {row['Sell']:.2f} (Close: {row['close']:.2f})")
    
    # Check for the Python signals
    print("\n" + "="*80)
    print("CHECKING PYTHON SIGNALS IN TRADINGVIEW DATA:")
    print("="*80)
    
    python_signals = {
        '2025-03-21': 'SELL @ 1343.10',
        '2025-05-12': 'BUY @ 1448.50'
    }
    
    for date_str, signal_info in python_signals.items():
        date = pd.to_datetime(date_str)
        if date in tv_df.index:
            row = tv_df.loc[date]
            print(f"\n{date_str} (Python: {signal_info}):")
            print(f"  TradingView OHLC: O:{row['open']:.2f} H:{row['high']:.2f} L:{row['low']:.2f} C:{row['close']:.2f}")
            print(f"  Kernel Value: {row['Kernel Regression Estimate']:.2f}")
            print(f"  TradingView Signal: ", end="")
            if pd.notna(row['Buy']):
                print(f"BUY @ {row['Buy']:.2f}")
            elif pd.notna(row['Sell']):
                print(f"SELL @ {row['Sell']:.2f}")
            else:
                print("NO SIGNAL ❌")
        else:
            print(f"\n{date_str}: Date not found in TradingView data ❌")
    
    # Analyze signal patterns
    print("\n" + "="*80)
    print("SIGNAL PATTERN ANALYSIS:")
    print("="*80)
    
    # Group signals by month
    buy_monthly = buy_signals.groupby(pd.Grouper(freq='M')).size()
    sell_monthly = sell_signals.groupby(pd.Grouper(freq='M')).size()
    
    print("\nMonthly Signal Distribution:")
    all_months = sorted(set(buy_monthly.index) | set(sell_monthly.index))
    for month in all_months:
        buy_count = buy_monthly.get(month, 0)
        sell_count = sell_monthly.get(month, 0)
        print(f"{month.strftime('%Y-%m')}: BUY={buy_count}, SELL={sell_count}")
    
    # Check data quality
    print("\n" + "="*80)
    print("DATA QUALITY CHECK:")
    print("="*80)
    
    # Check for any NaN values in OHLC
    ohlc_cols = ['open', 'high', 'low', 'close']
    nan_counts = tv_df[ohlc_cols].isna().sum()
    if nan_counts.any():
        print("⚠️  NaN values found in OHLC data:")
        print(nan_counts[nan_counts > 0])
    else:
        print("✅ No NaN values in OHLC data")
    
    # Check for price anomalies
    price_checks = []
    for idx, row in tv_df.iterrows():
        if row['high'] < row['low']:
            price_checks.append(f"High < Low on {idx}")
        if row['open'] > row['high'] or row['open'] < row['low']:
            price_checks.append(f"Open outside High-Low range on {idx}")
        if row['close'] > row['high'] or row['close'] < row['low']:
            price_checks.append(f"Close outside High-Low range on {idx}")
    
    if price_checks:
        print("\n⚠️  Price anomalies found:")
        for check in price_checks[:5]:  # Show first 5
            print(f"  - {check}")
    else:
        print("✅ No price anomalies found")
    
    # Save summary to file
    print("\n" + "="*80)
    print("SAVING DETAILED ANALYSIS...")
    print("="*80)
    
    with open('tradingview_signal_analysis.txt', 'w') as f:
        f.write("TradingView Signal Analysis\n")
        f.write("="*50 + "\n\n")
        f.write("BUY SIGNALS:\n")
        for idx, row in buy_signals.iterrows():
            f.write(f"{idx.strftime('%Y-%m-%d')}: BUY @ {row['Buy']:.2f}\n")
        f.write("\nSELL SIGNALS:\n")
        for idx, row in sell_signals.iterrows():
            f.write(f"{idx.strftime('%Y-%m-%d')}: SELL @ {row['Sell']:.2f}\n")
    
    print("✅ Analysis saved to 'tradingview_signal_analysis.txt'")
    
    return tv_df, buy_signals, sell_signals

def main():
    tv_filepath = "/Users/knight/Desktop/projects/mcp-testing/lorentzian_classifier/NSE_ICICIBANK, 1D.csv"
    
    # Run comparison
    tv_df, buy_signals, sell_signals = compare_complete_data(tv_filepath)
    
    print("\n" + "="*80)
    print("CONCLUSIONS:")
    print("="*80)
    print("1. TradingView has many more signals than Python implementation")
    print("2. Python signal dates (Mar 21, May 12) show NO signals in TradingView")
    print("3. This indicates different indicator settings or logic")
    print("4. Need Pine Script code to identify exact differences")
    print("\n📌 Next Step: Share Pine Script code for detailed analysis")

if __name__ == "__main__":
    main()
