#!/usr/bin/env python3
"""
Direct inspection of SQLite database
"""
import sqlite3
import pandas as pd
import os

def inspect_database():
    """Directly inspect the SQLite database"""
    db_path = "data_cache/market_data.db"
    
    print(f"=== Direct Database Inspection ===\n")
    print(f"Database path: {os.path.abspath(db_path)}")
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found at {db_path}")
        return
    
    # Get file size
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"Database size: {size_mb:.2f} MB\n")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        
        # List all tables
        print("📊 Tables in database:")
        tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
        tables = pd.read_sql_query(tables_query, conn)
        print(tables)
        
        # Check market_data table
        print("\n📈 Checking market_data table:")
        try:
            # Count records
            count_query = "SELECT COUNT(*) as count FROM market_data"
            count = pd.read_sql_query(count_query, conn)
            print(f"Total records: {count['count'][0]}")
            
            # Get unique symbols
            symbols_query = "SELECT DISTINCT symbol, interval, COUNT(*) as records FROM market_data GROUP BY symbol, interval"
            symbols = pd.read_sql_query(symbols_query, conn)
            print(f"\nData by symbol and interval:")
            print(symbols)
            
            # Check ICICIBANK specifically
            icici_query = """
                SELECT 
                    MIN(date) as first_date,
                    MAX(date) as last_date,
                    COUNT(*) as total_records
                FROM market_data 
                WHERE symbol = 'ICICIBANK' AND interval = 'day'
            """
            icici_data = pd.read_sql_query(icici_query, conn)
            print(f"\nICICIBANK daily data:")
            print(icici_data)
            
            # Get sample records
            sample_query = """
                SELECT * FROM market_data 
                WHERE symbol = 'ICICIBANK' AND interval = 'day'
                ORDER BY date DESC
                LIMIT 5
            """
            sample = pd.read_sql_query(sample_query, conn)
            print(f"\nSample records (last 5):")
            print(sample)
            
        except Exception as e:
            print(f"Error querying market_data table: {e}")
        
        # Check cache_metadata table
        print("\n📋 Checking cache_metadata table:")
        try:
            metadata_query = "SELECT * FROM cache_metadata"
            metadata = pd.read_sql_query(metadata_query, conn)
            print(metadata)
        except Exception as e:
            print(f"Error querying cache_metadata table: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
    
    print("\n✅ Inspection complete!")

if __name__ == "__main__":
    inspect_database()