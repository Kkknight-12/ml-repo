#!/usr/bin/env python3
"""
Check data range differences between Pine Script and Python
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import sqlite3


def check_data_range():
    """Compare data ranges"""
    
    print("="*70)
    print("DATA RANGE COMPARISON")
    print("="*70)
    
    # Pine Script data
    pine_file = "archive/data_files/NSE_ICICIBANK, 1D.csv"
    df_pine = pd.read_csv(pine_file)
    df_pine['time'] = pd.to_datetime(df_pine['time'])
    
    print(f"\n📊 PINE SCRIPT DATA:")
    print(f"   Total bars: {len(df_pine)}")
    print(f"   Date range: {df_pine['time'].min()} to {df_pine['time'].max()}")
    print(f"   Signals in this range: 16")
    
    # Python data
    db_path = os.path.join("data_cache", "market_data.db")
    with sqlite3.connect(db_path) as conn:
        query = """
        SELECT COUNT(*) as total, MIN(date) as min_date, MAX(date) as max_date
        FROM market_data
        WHERE symbol = 'ICICIBANK' AND interval = 'day'
        """
        result = pd.read_sql_query(query, conn)
    
    print(f"\n📊 PYTHON DATA:")
    print(f"   Total bars: {result['total'].iloc[0]}")
    print(f"   Date range: {result['min_date'].iloc[0]} to {result['max_date'].iloc[0]}")
    
    # Calculate signals in Pine Script date range
    with sqlite3.connect(db_path) as conn:
        query = """
        SELECT COUNT(*) as count
        FROM market_data
        WHERE symbol = 'ICICIBANK' AND interval = 'day'
        AND date >= ? AND date <= ?
        """
        pine_range_count = pd.read_sql_query(
            query, conn,
            params=(df_pine['time'].min().strftime('%Y-%m-%d'), 
                   df_pine['time'].max().strftime('%Y-%m-%d'))
        )
    
    print(f"   Bars in Pine Script date range: {pine_range_count['count'].iloc[0]}")
    
    print(f"\n⚠️  KEY OBSERVATION:")
    print(f"   Python is processing {result['total'].iloc[0]} bars total")
    print(f"   Pine Script only shows {len(df_pine)} bars")
    print(f"   This explains why Python generates many more signals!")
    
    print(f"\n📊 SIGNAL FREQUENCY:")
    print(f"   Pine Script: 16 signals / 300 bars = {16/300*100:.1f}% signal rate")
    print(f"   Python: 90 signals / {result['total'].iloc[0]} bars = {90/result['total'].iloc[0]*100:.1f}% signal rate")
    
    print("="*70)


if __name__ == "__main__":
    check_data_range()