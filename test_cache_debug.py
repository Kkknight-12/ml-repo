#!/usr/bin/env python3
"""
Debug cache functionality step by step
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import json
import logging

# Enable DEBUG logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_cache_step_by_step():
    """Test cache functionality step by step"""
    print("=== Cache Debug Test ===\n")
    
    # Step 1: Set up environment
    print("Step 1: Setting up environment...")
    if os.path.exists('.kite_session.json'):
        with open('.kite_session.json', 'r') as f:
            session_data = json.load(f)
            os.environ['KITE_ACCESS_TOKEN'] = session_data.get('access_token')
        print("✅ Access token loaded\n")
    else:
        print("❌ No access token found\n")
        return
    
    # Step 2: Initialize client
    print("Step 2: Initializing Zerodha client...")
    try:
        # Check if kiteconnect is available
        try:
            from kiteconnect import KiteConnect
            print("✅ KiteConnect is available")
        except ImportError:
            print("❌ KiteConnect not installed")
            # Try to continue anyway
        
        from data.zerodha_client import ZerodhaClient
        client = ZerodhaClient(use_cache=True, cache_dir="data_cache")
        print("✅ Client initialized with cache\n")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}\n")
        return
    
    # Step 3: Test cache manager directly
    print("Step 3: Testing cache manager directly...")
    from data.cache_manager import MarketDataCache
    cache = MarketDataCache("data_cache")
    print("✅ Cache manager created\n")
    
    # Step 4: Check initial cache status
    print("Step 4: Checking initial cache status...")
    cache_info = cache.get_cache_info()
    print(f"Cache has {len(cache_info)} entries")
    if not cache_info.empty:
        print(cache_info)
    print()
    
    # Step 5: Test fetching recent data
    print("Step 5: Fetching last 30 days of ICICIBANK data...")
    try:
        data = client.get_historical_data('ICICIBANK', 'day', days=30)
        print(f"✅ Fetched {len(data)} records")
        
        # Check if data was saved to cache
        cache_info_after = cache.get_cache_info()
        if len(cache_info_after) > len(cache_info):
            print("✅ Data was saved to cache!")
        else:
            print("❌ Data was NOT saved to cache")
            
            # Let's check the database directly
            import sqlite3
            db_path = "data_cache/market_data.db"
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM market_data")
                count = cursor.fetchone()[0]
                print(f"   Database has {count} records in market_data table")
                
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Debug test complete!")

if __name__ == "__main__":
    test_cache_step_by_step()