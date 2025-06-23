#!/usr/bin/env python3
"""
Check the current status of cached data in SQLite database
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pandas as pd
from data.cache_manager import MarketDataCache

def check_cache_status():
    """Check what data is currently cached"""
    print("=== SQLite Cache Status Check ===\n")
    
    # Initialize cache manager
    cache = MarketDataCache("data_cache")
    
    # Get overall cache info
    print("📊 Overall Cache Summary:")
    print("-" * 50)
    cache_info = cache.get_cache_info()
    
    if cache_info.empty:
        print("❌ Cache is empty - no data stored yet")
        return
    
    # Display all cached symbols
    print(cache_info.to_string(index=False))
    
    # Check specifically for ICICIBANK
    print("\n\n🏦 ICICIBANK Daily Data Details:")
    print("-" * 50)
    
    icici_cache = cache_info[
        (cache_info['symbol'] == 'ICICIBANK') & 
        (cache_info['interval'] == 'day')
    ]
    
    if icici_cache.empty:
        print("❌ No ICICIBANK daily data found in cache")
    else:
        for idx, row in icici_cache.iterrows():
            print(f"Symbol: {row['symbol']}")
            print(f"Interval: {row['interval']}")
            print(f"Total Records: {row['total_records']:,}")
            print(f"Date Range: {row['first_date']} to {row['last_date']}")
            
            # Calculate years
            first_date = pd.to_datetime(row['first_date'])
            last_date = pd.to_datetime(row['last_date'])
            years = (last_date - first_date).days / 365.25
            print(f"Span: {years:.1f} years")
            print(f"Last Updated: {row['last_updated']}")
    
    # Get some sample data to verify
    print("\n\n📈 Sample Data (first and last 5 records):")
    print("-" * 50)
    
    # Direct SQL query to get sample data
    db_path = os.path.join("data_cache", "market_data.db")
    
    if os.path.exists(db_path):
        with sqlite3.connect(db_path) as conn:
            # First 5 records
            query_first = """
                SELECT date, open, high, low, close, volume
                FROM market_data
                WHERE symbol = 'ICICIBANK' AND interval = 'day'
                ORDER BY date ASC
                LIMIT 5
            """
            df_first = pd.read_sql_query(query_first, conn)
            
            # Last 5 records
            query_last = """
                SELECT date, open, high, low, close, volume
                FROM market_data
                WHERE symbol = 'ICICIBANK' AND interval = 'day'
                ORDER BY date DESC
                LIMIT 5
            """
            df_last = pd.read_sql_query(query_last, conn)
            
            if not df_first.empty:
                print("\nFirst 5 records:")
                print(df_first.to_string(index=False))
                
                print("\nLast 5 records:")
                print(df_last.sort_values('date').to_string(index=False))
            
            # Check for any gaps
            print("\n\n🔍 Checking for data gaps:")
            print("-" * 50)
            
            # Get all dates
            query_all_dates = """
                SELECT date
                FROM market_data
                WHERE symbol = 'ICICIBANK' AND interval = 'day'
                ORDER BY date
            """
            df_dates = pd.read_sql_query(query_all_dates, conn, parse_dates=['date'])
            
            if not df_dates.empty:
                # Check for gaps larger than 5 days (to account for weekends/holidays)
                df_dates['date_diff'] = df_dates['date'].diff()
                large_gaps = df_dates[df_dates['date_diff'] > pd.Timedelta(days=5)]
                
                if not large_gaps.empty:
                    print(f"Found {len(large_gaps)} gaps larger than 5 days:")
                    for idx, row in large_gaps.iterrows():
                        print(f"  Gap: {row['date_diff'].days} days before {row['date'].date()}")
                else:
                    print("✅ No significant gaps found in the data")
    
    # Database file info
    print("\n\n💾 Database File Info:")
    print("-" * 50)
    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        print(f"Database Path: {db_path}")
        print(f"Database Size: {size_mb:.2f} MB")
    
    print("\n✅ Cache check complete!")

if __name__ == "__main__":
    check_cache_status()