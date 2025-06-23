#!/usr/bin/env python3
"""
Script to cache historical data for all NIFTY 50 stocks
This pre-loads the SQLite database with data for backtesting
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import time
import json
import pandas as pd
from data.zerodha_client import ZerodhaClient

# NIFTY 50 stocks as of 2024
NIFTY_50_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY",
    "HDFC", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "HCLTECH", "AXISBANK", "ASIANPAINT", "MARUTI",
    "SUNPHARMA", "TITAN", "ULTRACEMCO", "ONGC", "NTPC",
    "NESTLEIND", "WIPRO", "POWERGRID", "M&M", "HDFCLIFE",
    "BAJFINANCE", "TECHM", "TATAMOTORS", "HINDUNILVR", "INDUSINDBK",
    "TATASTEEL", "SBILIFE", "ADANIENT", "BAJAJFINSV", "CIPLA",
    "GRASIM", "DRREDDY", "BRITANNIA", "HINDALCO", "DIVISLAB",
    "EICHERMOT", "COALINDIA", "UPL", "HEROMOTOCO", "BAJAJ-AUTO",
    "TATACONSUM", "JSWSTEEL", "APOLLOHOSP", "ADANIPORTS", "BPCL"
]

def cache_nifty50_data(days: int = 3000, interval: str = "day"):
    """
    Cache historical data for all NIFTY 50 stocks
    
    Args:
        days: Number of days of history to fetch (3000 = ~8 years of trading days)
        interval: Timeframe (day, 5minute, etc.)
    """
    print(f"=== NIFTY 50 Data Caching Script ===\n")
    print(f"Fetching {days} days of {interval} data for {len(NIFTY_50_STOCKS)} stocks\n")
    
    # Check for saved session
    if not os.path.exists('.kite_session.json'):
        print("❌ No access token found. Run auth_helper.py first")
        return
    
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
    
    # Set token in environment
    os.environ['KITE_ACCESS_TOKEN'] = access_token
    
    # Initialize client with cache
    print("Initializing Zerodha client with SQLite cache...")
    client = ZerodhaClient(use_cache=True, cache_dir="data_cache")
    print("✅ Client initialized\n")
    
    # Get initial cache info
    initial_cache = client.get_cache_info()
    initial_symbols = set(initial_cache['symbol'].unique()) if not initial_cache.empty else set()
    
    # Track progress
    successful = []
    failed = []
    
    # Process each stock
    for i, symbol in enumerate(NIFTY_50_STOCKS, 1):
        print(f"[{i}/{len(NIFTY_50_STOCKS)}] Processing {symbol}...")
        
        try:
            # Check if already cached
            if symbol in initial_symbols:
                symbol_cache = initial_cache[initial_cache['symbol'] == symbol]
                if not symbol_cache.empty:
                    records = symbol_cache.iloc[0]['total_records']
                    print(f"  ✓ Already cached: {records} records")
                    successful.append(symbol)
                    continue
            
            # Fetch data
            start_time = time.time()
            data = client.get_historical_data(symbol, interval, days=days)
            end_time = time.time()
            
            if data:
                print(f"  ✅ Cached {len(data)} bars in {end_time - start_time:.2f}s")
                successful.append(symbol)
            else:
                print(f"  ⚠️ No data returned")
                failed.append(symbol)
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            failed.append(symbol)
        
        # Respect rate limits (3 requests/second for historical API)
        time.sleep(0.35)  # ~2.8 requests/second to be safe
    
    # Summary
    print("\n" + "="*50)
    print("CACHING COMPLETE")
    print("="*50)
    print(f"✅ Successful: {len(successful)} stocks")
    print(f"❌ Failed: {len(failed)} stocks")
    
    if failed:
        print(f"\nFailed stocks: {', '.join(failed)}")
    
    # Show final cache status
    print("\nFinal cache status:")
    final_cache = client.get_cache_info()
    if not final_cache.empty:
        print(final_cache)
        
        # Calculate total records and size
        total_records = final_cache['total_records'].sum()
        print(f"\n📊 Total records cached: {total_records:,}")
        
        # Check database size
        db_path = os.path.join("data_cache", "market_data.db")
        if os.path.exists(db_path):
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
            print(f"💾 Database size: {size_mb:.2f} MB")
            print(f"📈 Average per stock: {size_mb/len(successful):.2f} MB")
    
    print("\n✅ All NIFTY 50 stocks cached and ready for backtesting!")
    print("\nNext steps:")
    print("1. Run your trading strategy on any cached stock")
    print("2. Data loads instantly from local SQLite database")
    print("3. No API calls needed until you want to update with recent data")

def update_recent_data(days: int = 30):
    """
    Update cache with recent data for all cached stocks
    Useful for keeping the cache current
    """
    print(f"\n=== Updating Recent Data ({days} days) ===\n")
    
    # Initialize client
    client = ZerodhaClient(use_cache=True, cache_dir="data_cache")
    
    # Get current cache info
    cache_info = client.get_cache_info()
    if cache_info.empty:
        print("❌ No cached data found")
        return
    
    # Update each cached symbol
    symbols = cache_info['symbol'].unique()
    for symbol in symbols:
        print(f"Updating {symbol}...")
        try:
            data = client.get_historical_data(symbol, "day", days=days)
            print(f"  ✅ Updated with {len(data)} bars")
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
        time.sleep(0.35)  # Rate limit

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Cache NIFTY 50 historical data")
    parser.add_argument("--days", type=int, default=3000, 
                       help="Number of days to fetch (default: 3000)")
    parser.add_argument("--update", action="store_true",
                       help="Update recent data for cached stocks")
    parser.add_argument("--update-days", type=int, default=30,
                       help="Days to update when using --update (default: 30)")
    
    args = parser.parse_args()
    
    if args.update:
        update_recent_data(args.update_days)
    else:
        cache_nifty50_data(days=args.days)