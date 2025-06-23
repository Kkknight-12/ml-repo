#!/usr/bin/env python3
"""
Fetch 2000 bars of ICICIBANK data - Pine Script Style
=====================================
Purpose: Fetch EXACTLY how Pine Script would use data
- No train/test split
- ALL data used for ML learning
- Continuous learning approach

This follows Pine Script's approach where ALL available historical data
is used for the ML algorithm.
"""

import pandas as pd
from datetime import datetime, timedelta
from data.zerodha_client import ZerodhaClient
import os
from dotenv import load_dotenv

def fetch_pinescript_style_data():
    """
    Fetch 2000 bars of ICICIBANK data for Pine Script style testing
    
    Pine Script approach:
    - Uses ALL available data
    - No concept of train/test split
    - max_bars_back is just a memory/computation limit
    - Continuous learning on every bar
    """
    
    print("=" * 60)
    print("🎯 Pine Script Style Data Fetcher")
    print("=" * 60)
    print()
    
    # Load environment variables
    load_dotenv()
    
    # Configuration
    symbol = "ICICIBANK"
    interval = "5minute"  # 5-minute bars as per your requirement
    bars_needed = 2000    # As per your requirement - stick to 2000 bars
    
    print(f"📊 Fetching Configuration:")
    print(f"   Symbol: {symbol}")
    print(f"   Interval: {interval}")
    print(f"   Bars needed: {bars_needed}")
    print()
    
    # Initialize Zerodha client
    print("🔌 Connecting to Zerodha...")
    client = ZerodhaClient()
    
    # Load instruments to populate symbol-token mapping
    print("📊 Loading NSE instruments...")
    client.get_instruments("NSE")
    
    # Calculate days needed
    # For 5-minute bars: ~6.5 hours per day, ~390 minutes = 78 bars per day
    # 2000 bars ÷ 78 = ~26 trading days needed
    # Add buffer for weekends/holidays
    days_needed = 45  # Generous buffer to ensure we get 2000 bars
    
    print(f"📅 Fetching last {days_needed} days of data")
    print("   (This should give us more than 2000 bars)")
    print()
    
    # Fetch data
    print("⬇️  Fetching data from Zerodha...")
    try:
        data = client.get_historical_data(
            symbol=symbol,
            interval=interval,
            days=days_needed
        )
        
        if not data:
            print("❌ No data received from Zerodha!")
            return
            
        print(f"✅ Received {len(data)} bars")
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Take exactly 2000 most recent bars
        if len(df) > bars_needed:
            df = df.tail(bars_needed).reset_index(drop=True)
            print(f"📏 Trimmed to exactly {bars_needed} bars")
        
        # Pine Script approach - ALL data is used
        print()
        print("🎯 Pine Script Approach:")
        print(f"   - ALL {len(df)} bars will be used for ML")
        print(f"   - No train/test split")
        print(f"   - Continuous learning on each bar")
        print(f"   - ML starts after max_bars_back warmup")
        print()
        
        # Show data info
        print("📊 Data Summary:")
        print(f"   First bar: {df.iloc[0]['date']}")
        print(f"   Last bar: {df.iloc[-1]['date']}")
        print(f"   Total bars: {len(df)}")
        print()
        
        # Save the data
        filename = f"pinescript_style_{symbol}_{bars_needed}bars.csv"
        df.to_csv(filename, index=False)
        print(f"💾 Saved to: {filename}")
        
        # Important note about Pine Script behavior
        print()
        print("📌 Important Notes:")
        print("   1. Pine Script uses ALL this data")
        print("   2. max_bars_back determines when ML starts predicting")
        print("   3. With max_bars_back=2000, ML won't predict on this dataset")
        print("   4. Consider using max_bars_back=1000 or less for testing")
        
        return df
        
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return None

if __name__ == "__main__":
    fetch_pinescript_style_data()
