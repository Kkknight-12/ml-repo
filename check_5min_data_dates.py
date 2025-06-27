#!/usr/bin/env python3
"""
Check 5-minute data dates
========================
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import json

from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def check_dates():
    """Check date ranges in 5-minute data"""
    
    print("🔍 CHECKING 5-MINUTE DATA DATES")
    print("="*60)
    
    # Get different date ranges
    symbol = "RELIANCE"
    end_date = datetime.now()
    
    # Test different start dates
    date_ranges = [
        ("30 days", end_date - timedelta(days=30)),
        ("60 days", end_date - timedelta(days=60)),
        ("90 days", end_date - timedelta(days=90)),
        ("180 days", end_date - timedelta(days=180))
    ]
    
    cache = MarketDataCache()
    
    for label, start_date in date_ranges:
        df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
        
        if df is None or df.empty:
            print(f"\n{label}: No data")
            continue
        
        print(f"\n{label}:")
        print(f"  Total bars: {len(df)}")
        print(f"  First bar: {df.index[0]}")
        print(f"  Last bar: {df.index[-1]}")
        print(f"  Bars after 2000 warmup: {len(df) - 2000}")
        
        # Check if we have the problematic period from verify_5min_final
        if len(df) > 2000:
            print(f"  Bar 2000: {df.index[2000] if len(df) > 2000 else 'N/A'}")
            print(f"  Bar 2001: {df.index[2001] if len(df) > 2001 else 'N/A'}")


if __name__ == "__main__":
    check_dates()