#!/usr/bin/env python3
"""
Alternative: Use Existing CSV Data for Testing
==============================================
Purpose: If you don't have Zerodha historical API access,
         use existing CSV files for testing
"""

import pandas as pd
import os
from datetime import datetime

def prepare_csv_for_testing():
    """
    Check available CSV files and prepare data for testing
    """
    
    print("=" * 60)
    print("🗂️ CSV Data Preparation for Testing")
    print("=" * 60)
    print()
    
    # Look for ICICIBANK CSV files
    csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'ICICIBANK' in f.upper()]
    
    if not csv_files:
        print("❌ No ICICIBANK CSV files found!")
        print("\n💡 Options:")
        print("   1. Export data from TradingView")
        print("   2. Use Zerodha historical API (₹2000/month)")
        print("   3. Use free data sources like Yahoo Finance")
        return
    
    print("📁 Found CSV files:")
    for i, file in enumerate(csv_files):
        print(f"   {i+1}. {file}")
        # Check file info
        df_temp = pd.read_csv(file)
        print(f"      Rows: {len(df_temp)}")
        if 'date' in df_temp.columns or 'Date' in df_temp.columns or 'time' in df_temp.columns:
            date_col = 'date' if 'date' in df_temp.columns else ('Date' if 'Date' in df_temp.columns else 'time')
            try:
                print(f"      First: {df_temp.iloc[0][date_col]}")
                print(f"      Last: {df_temp.iloc[-1][date_col]}")
            except:
                pass
    
    print()
    
    # Use the most appropriate file
    if 'NSE_ICICIBANK, 5.csv' in csv_files:
        selected_file = 'NSE_ICICIBANK, 5.csv'
        print(f"📊 Using: {selected_file} (5-minute data)")
    else:
        selected_file = csv_files[0]
        print(f"📊 Using: {selected_file}")
    
    # Load and process
    print(f"\n⏳ Processing {selected_file}...")
    df = pd.read_csv(selected_file)
    
    # Standardize column names
    column_mapping = {
        'Date': 'date',
        'Time': 'date',  
        'time': 'date',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    }
    
    df.rename(columns=column_mapping, inplace=True)
    
    # Ensure required columns exist
    required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        print(f"❌ Missing columns: {missing_columns}")
        print("\n📋 Available columns:", list(df.columns))
        return
    
    print(f"✅ Data loaded: {len(df)} bars")
    
    # Take last 2000 bars if more available
    if len(df) > 2000:
        df = df.tail(2000).reset_index(drop=True)
        print(f"📏 Trimmed to last 2000 bars")
    
    # Save as Pine Script style file
    output_file = "pinescript_style_ICICIBANK_2000bars.csv"
    df.to_csv(output_file, index=False)
    
    print(f"\n💾 Saved as: {output_file}")
    print(f"   Ready for test_pinescript_style.py!")
    
    # Show data summary
    print("\n📊 Data Summary:")
    print(f"   First bar: {df.iloc[0]['date']}")
    print(f"   Last bar: {df.iloc[-1]['date']}")
    print(f"   Total bars: {len(df)}")
    
    # Check if it's 5-minute data
    if len(df) > 1:
        # Try to parse dates and check interval
        try:
            date1 = pd.to_datetime(df.iloc[0]['date'])
            date2 = pd.to_datetime(df.iloc[1]['date'])
            diff_minutes = (date2 - date1).total_seconds() / 60
            print(f"   Interval: ~{diff_minutes:.0f} minutes")
        except:
            print("   Interval: Unable to determine")
    
    print("\n✅ Data ready for testing!")
    print("\n📋 Next steps:")
    print("   1. python test_pinescript_style.py")
    print("   2. python debug_ml_predictions.py (if no signals)")

if __name__ == "__main__":
    prepare_csv_for_testing()
