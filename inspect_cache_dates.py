#!/usr/bin/env python3
"""
Quick script to inspect actual dates in the cache database
"""
import sqlite3
import pandas as pd
import os

db_path = os.path.join("data_cache", "market_data.db")

if os.path.exists(db_path):
    with sqlite3.connect(db_path) as conn:
        # Check cache metadata
        print("=== Cache Metadata ===")
        metadata = pd.read_sql_query(
            "SELECT * FROM cache_metadata WHERE symbol = 'ICICIBANK'", 
            conn
        )
        print(metadata)
        
        # Check actual date range in data
        print("\n=== Actual Date Range in Data ===")
        date_range = pd.read_sql_query(
            """
            SELECT 
                MIN(date) as first_date,
                MAX(date) as last_date,
                COUNT(*) as total_records
            FROM market_data 
            WHERE symbol = 'ICICIBANK' AND interval = 'day'
            """, 
            conn
        )
        print(date_range)
        
        # Check last 10 dates
        print("\n=== Last 10 Dates ===")
        last_dates = pd.read_sql_query(
            """
            SELECT date, close 
            FROM market_data 
            WHERE symbol = 'ICICIBANK' AND interval = 'day'
            ORDER BY date DESC
            LIMIT 10
            """, 
            conn
        )
        print(last_dates)
else:
    print(f"Database not found at {db_path}")