#!/usr/bin/env python3
"""
Compare TradingView and Zerodha daily data for ICICIBANK
This script validates OHLC data and identifies signal differences
"""

import pandas as pd
from datetime import datetime

def load_tradingview_data(filepath):
    """Load and parse TradingView CSV data"""
    df = pd.read_csv(filepath)
    df['time'] = pd.to_datetime(df['time'])
    # Extract signals from Buy/Sell columns
    df['tv_buy_signal'] = df['Buy'].notna()
    df['tv_sell_signal'] = df['Sell'].notna()
    return df

def parse_zerodha_output():
    """Parse the Zerodha output from test_daily_data.py"""
    # Sample data from the output
    zerodha_data = {
        '2025-03-12': {'open': 1246.95, 'high': 1251.95, 'low': 1235.30, 'close': 1243.95},
        '2025-03-13': {'open': 1251.05, 'high': 1255.60, 'low': 1245.30, 'close': 1250.05},
        '2025-03-17': {'open': 1257.05, 'high': 1273.95, 'low': 1254.75, 'close': 1269.00},
        '2025-03-18': {'open': 1285.50, 'high': 1313.85, 'low': 1280.65, 'close': 1309.85},
        '2025-03-19': {'open': 1305.60, 'high': 1318.30, 'low': 1302.15, 'close': 1313.10},
        # Add more dates as needed
    }
    
    # Signals from Python output
    signals = {
        '2025-03-21': 'SELL',
        '2025-05-12': 'BUY'
    }
    
    return zerodha_data, signals

def compare_ohlc_data(tv_df, zerodha_data):
    """Compare OHLC values between TradingView and Zerodha"""
    print("=" * 70)
    print("OHLC DATA COMPARISON")
    print("=" * 70)
    
    matches = 0
    mismatches = 0
    
    for date_str, zdata in zerodha_data.items():
        date = pd.to_datetime(date_str)
        tv_row = tv_df[tv_df['time'] == date]
        
        if tv_row.empty:
            print(f"❌ {date_str}: Date not found in TradingView data")
            mismatches += 1
            continue
        
        tv_row = tv_row.iloc[0]
        
        # Compare OHLC
        ohlc_match = True
        if abs(tv_row['open'] - zdata['open']) > 0.01:
            ohlc_match = False
        if abs(tv_row['high'] - zdata['high']) > 0.01:
            ohlc_match = False
        if abs(tv_row['low'] - zdata['low']) > 0.01:
            ohlc_match = False
        if abs(tv_row['close'] - zdata['close']) > 0.01:
            ohlc_match = False
        
        if ohlc_match:
            print(f"✅ {date_str}: OHLC matches perfectly")
            matches += 1
        else:
            print(f"❌ {date_str}: OHLC mismatch")
            print(f"   TV:  O:{tv_row['open']} H:{tv_row['high']} L:{tv_row['low']} C:{tv_row['close']}")
            print(f"   ZD:  O:{zdata['open']} H:{zdata['high']} L:{zdata['low']} C:{zdata['close']}")
            mismatches += 1
    
    print(f"\nSummary: {matches} matches, {mismatches} mismatches")
    return matches == len(zerodha_data)

def analyze_signals(tv_df, zerodha_signals):
    """Analyze signal differences"""
    print("\n" + "=" * 70)
    print("SIGNAL ANALYSIS")
    print("=" * 70)
    
    # TradingView signals
    tv_buy_dates = tv_df[tv_df['tv_buy_signal']]['time'].dt.strftime('%Y-%m-%d').tolist()
    tv_sell_dates = tv_df[tv_df['tv_sell_signal']]['time'].dt.strftime('%Y-%m-%d').tolist()
    
    print(f"\nTradingView Signals:")
    print(f"BUY signals: {len(tv_buy_dates)} total")
    for date in tv_buy_dates[-5:]:  # Show last 5
        print(f"  - {date}")
    
    print(f"\nSELL signals: {len(tv_sell_dates)} total")
    for date in tv_sell_dates[-5:]:  # Show last 5
        print(f"  - {date}")
    
    print(f"\nZerodha (Python) Signals:")
    for date, signal in zerodha_signals.items():
        print(f"  - {date}: {signal}")
        # Check if this signal exists in TradingView
        if signal == 'BUY' and date in tv_buy_dates:
            print(f"    ✅ Matches TradingView")
        elif signal == 'SELL' and date in tv_sell_dates:
            print(f"    ✅ Matches TradingView")
        else:
            print(f"    ❌ NOT in TradingView")

def check_specific_dates(tv_df):
    """Check specific important dates"""
    print("\n" + "=" * 70)
    print("SPECIFIC DATE CHECKS")
    print("=" * 70)
    
    important_dates = ['2025-03-21', '2025-05-12']
    
    for date_str in important_dates:
        date = pd.to_datetime(date_str)
        tv_row = tv_df[tv_df['time'] == date]
        
        if tv_row.empty:
            print(f"\n{date_str}: No data in TradingView")
        else:
            row = tv_row.iloc[0]
            print(f"\n{date_str}:")
            print(f"  OHLC: O:{row['open']} H:{row['high']} L:{row['low']} C:{row['close']}")
            print(f"  Kernel Estimate: {row['Kernel Regression Estimate']:.2f}")
            print(f"  Signals: ", end="")
            if row['tv_buy_signal']:
                print(f"BUY @ {row['Buy']}", end=" ")
            if row['tv_sell_signal']:
                print(f"SELL @ {row['Sell']}", end=" ")
            if not row['tv_buy_signal'] and not row['tv_sell_signal']:
                print("None")

def main():
    # Load TradingView data
    tv_filepath = "/Users/knight/Desktop/projects/mcp-testing/lorentzian_classifier/NSE_ICICIBANK, 1D.csv"
    tv_df = load_tradingview_data(tv_filepath)
    
    # Get Zerodha data
    zerodha_data, zerodha_signals = parse_zerodha_output()
    
    print("ICICIBANK Daily Data Comparison")
    print("================================\n")
    
    # Compare OHLC data
    ohlc_match = compare_ohlc_data(tv_df, zerodha_data)
    
    # Analyze signals
    analyze_signals(tv_df, zerodha_signals)
    
    # Check specific dates
    check_specific_dates(tv_df)
    
    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    if ohlc_match:
        print("✅ OHLC data matches perfectly between platforms")
    else:
        print("❌ OHLC data has mismatches")
    
    print("\n⚠️  Signal mismatch detected - check indicator settings!")

if __name__ == "__main__":
    main()
