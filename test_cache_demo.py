#!/usr/bin/env python3
"""
Demo script to test the SQLite caching functionality
Shows how to use the cache with Zerodha client
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
from data.zerodha_client import ZerodhaClient
import json

def main():
    """Demo the caching functionality"""
    print("=== SQLite Data Cache Demo ===\n")
    
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
    print("1. Initializing Zerodha client with SQLite cache...")
    client = ZerodhaClient(use_cache=True, cache_dir="data_cache")
    print("✅ Client initialized with cache\n")
    
    # Check current cache status
    print("2. Checking current cache status...")
    cache_info = client.get_cache_info()
    if cache_info.empty:
        print("   📂 Cache is empty\n")
    else:
        print("   📊 Cached data:")
        print(cache_info)
        print()
    
    # Fetch some data (will be cached)
    symbol = "RELIANCE"
    print(f"3. Fetching 30 days of {symbol} data...")
    print("   ⏳ First fetch will hit the API and cache the data...")
    
    start_time = datetime.now()
    data = client.get_historical_data(symbol, "day", days=30)
    end_time = datetime.now()
    
    print(f"   ✅ Fetched {len(data)} bars in {(end_time - start_time).total_seconds():.2f} seconds")
    
    if data:
        df = pd.DataFrame(data)
        print(f"   📅 Date range: {df['date'].min()} to {df['date'].max()}\n")
    
    # Fetch same data again (should be from cache)
    print("4. Fetching same data again (should be from cache)...")
    start_time = datetime.now()
    data2 = client.get_historical_data(symbol, "day", days=30)
    end_time = datetime.now()
    
    print(f"   ⚡ Fetched {len(data2)} bars in {(end_time - start_time).total_seconds():.2f} seconds (from cache!)\n")
    
    # Fetch older data (will merge)
    print("5. Fetching 60 days of data (will fetch missing data and merge)...")
    start_time = datetime.now()
    data3 = client.get_historical_data(symbol, "day", days=60)
    end_time = datetime.now()
    
    print(f"   ✅ Fetched {len(data3)} bars in {(end_time - start_time).total_seconds():.2f} seconds")
    
    if data3:
        df3 = pd.DataFrame(data3)
        print(f"   📅 Date range: {df3['date'].min()} to {df3['date'].max()}\n")
    
    # Show updated cache info
    print("6. Updated cache status:")
    cache_info = client.get_cache_info()
    if not cache_info.empty:
        print(cache_info)
        print()
    
    # Demonstrate fetching different symbol
    symbol2 = "ICICIBANK"
    print(f"7. Fetching data for different symbol: {symbol2}")
    data4 = client.get_historical_data(symbol2, "day", days=10)
    print(f"   ✅ Fetched {len(data4)} bars\n")
    
    # Final cache status
    print("8. Final cache status:")
    cache_info = client.get_cache_info()
    if not cache_info.empty:
        print(cache_info)
        print()
        
        # Calculate cache size
        db_path = os.path.join("data_cache", "market_data.db")
        if os.path.exists(db_path):
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
            print(f"   💾 Cache database size: {size_mb:.2f} MB")
    
    print("\n✅ Cache demo complete!")
    print("\nKey benefits of SQLite caching:")
    print("- ⚡ Instant data access after first fetch")
    print("- 📊 Automatic merging when fetching overlapping periods")
    print("- 💾 All data stored locally in SQLite database")
    print("- 🔄 Incremental updates - only fetch what's missing")
    print("- 🗂️ No external database needed - just a local file")

if __name__ == "__main__":
    main()