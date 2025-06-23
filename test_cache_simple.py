#!/usr/bin/env python3
"""
Simple test to verify cache is working correctly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from data.zerodha_client import ZerodhaClient
import json

def test_cache():
    """Test basic cache functionality"""
    print("=== Simple Cache Test ===\n")
    
    # Load auth
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        os.environ['KITE_ACCESS_TOKEN'] = session_data.get('access_token')
    
    # Initialize client with cache
    client = ZerodhaClient(use_cache=True, cache_dir="data_cache")
    print("✅ Client initialized with cache\n")
    
    # Test 1: Fetch recent data (should work with cache)
    print("Test 1: Fetching last 30 days of ICICIBANK data...")
    data = client.get_historical_data('ICICIBANK', 'day', days=30)
    print(f"✅ Fetched {len(data)} records\n")
    
    # Check cache
    cache_info = client.get_cache_info()
    print("📦 Cache status after fetch:")
    if not cache_info.empty:
        print(cache_info[['symbol', 'interval', 'first_date', 'last_date', 'total_records']])
    else:
        print("❌ Cache is still empty!")
    
    # Test 2: Fetch same data again (should be from cache)
    print("\n\nTest 2: Fetching same data again...")
    import time
    start = time.time()
    data2 = client.get_historical_data('ICICIBANK', 'day', days=30)
    elapsed = time.time() - start
    print(f"✅ Fetched {len(data2)} records in {elapsed:.3f}s")
    if elapsed < 0.1:
        print("⚡ Data loaded from cache (very fast)!")
    
    # Test 3: Fetch older data 
    print("\n\nTest 3: Fetching 365 days of data...")
    data3 = client.get_historical_data('ICICIBANK', 'day', days=365)
    print(f"✅ Fetched {len(data3)} records")
    
    # Final cache status
    print("\n📦 Final cache status:")
    cache_info = client.get_cache_info()
    if not cache_info.empty:
        print(cache_info[['symbol', 'interval', 'first_date', 'last_date', 'total_records']])
        
        # Show date range
        icici_data = cache_info[cache_info['symbol'] == 'ICICIBANK']
        if not icici_data.empty:
            first_date = icici_data.iloc[0]['first_date']
            last_date = icici_data.iloc[0]['last_date']
            print(f"\nICICIBANK data range: {first_date} to {last_date}")

if __name__ == "__main__":
    test_cache()