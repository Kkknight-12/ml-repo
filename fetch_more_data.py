#!/usr/bin/env python3
"""
Fetch More Historical Data for Testing
=====================================

Fetches sufficient 5-minute data for all test stocks
"""

import os
import sys
import json
from datetime import datetime, timedelta
import pandas as pd
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.zerodha_client import ZerodhaClient
from data.cache_manager import MarketDataCache


def fetch_extended_data():
    """Fetch extended historical data for all test stocks"""
    
    # Test stocks
    stocks = ['RELIANCE', 'INFY', 'AXISBANK', 'ITC', 'TCS']
    
    # Target: At least 3000 bars of 5-minute data per stock
    # 3000 bars / 75 bars per day = 40 days minimum
    # But let's fetch 60 days to be safe
    target_days = 60
    
    print(f"\n{'='*60}")
    print("FETCHING EXTENDED HISTORICAL DATA")
    print(f"{'='*60}")
    print(f"Target: {target_days} days of 5-minute data for each stock")
    print(f"Stocks: {', '.join(stocks)}")
    
    # Check for saved session
    if not os.path.exists('.kite_session.json'):
        print("\n❌ No Zerodha session found. Run auth_helper.py first")
        return False
        
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        
    if not access_token:
        print("\n❌ No access token in session")
        return False
        
    # Set token in environment
    os.environ['KITE_ACCESS_TOKEN'] = access_token
    
    try:
        # Initialize Zerodha client with caching
        client = ZerodhaClient(use_cache=True, cache_dir="data_cache")
        cache = MarketDataCache("data_cache")
        
        print("\n✅ Zerodha client initialized")
        
        # Get instruments
        client.get_instruments("NSE")
        
        # Fetch data for each stock
        for symbol in stocks:
            print(f"\n{'='*40}")
            print(f"Processing {symbol}")
            print(f"{'='*40}")
            
            # Check current cache status
            end_date = datetime.now()
            start_date = end_date - timedelta(days=target_days)
            
            # Get current cached data
            cached_df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
            
            if cached_df is not None:
                print(f"  Current cache: {len(cached_df)} bars")
                print(f"  Date range: {cached_df['date'].min()} to {cached_df['date'].max()}")
            else:
                print(f"  No cached data found")
            
            # Fetch using the client (will use smart caching)
            print(f"\n  Fetching {target_days} days of 5-minute data...")
            
            try:
                data = client.get_historical_data(
                    symbol=symbol,
                    interval="5minute",
                    days=target_days
                )
                
                if data:
                    df = pd.DataFrame(data)
                    print(f"  ✅ Fetched {len(df)} bars")
                    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
                    
                    # The client already updates the cache, but let's verify
                    # Check cache again
                    cached_df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
                    if cached_df is not None:
                        print(f"  ✅ Cache updated: {len(cached_df)} bars")
                    
                else:
                    print(f"  ❌ No data received")
                    
            except Exception as e:
                print(f"  ❌ Error fetching data: {str(e)}")
                continue
        
        # Show final cache status
        print(f"\n{'='*60}")
        print("FINAL CACHE STATUS")
        print(f"{'='*60}")
        
        cache_info = cache.get_cache_info()
        if not cache_info.empty:
            for _, row in cache_info.iterrows():
                if row['symbol'] in stocks and row['interval'] == '5minute':
                    print(f"{row['symbol']}: {row['total_records']} bars "
                          f"({row['first_date']} to {row['last_date']})")
        
        print("\n✅ Data fetching complete!")
        return True
        
    except Exception as e:
        logger.error(f"Error in data fetching: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    # First check if we have kiteconnect
    try:
        import kiteconnect
        print("✅ KiteConnect is installed")
    except ImportError:
        print("❌ KiteConnect not installed!")
        print("   Please run: pip install kiteconnect")
        sys.exit(1)
    
    # Fetch the data
    success = fetch_extended_data()
    
    if not success:
        print("\n⚠️  Data fetching failed. Please check the errors above.")
        sys.exit(1)