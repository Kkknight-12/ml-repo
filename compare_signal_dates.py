#!/usr/bin/env python3
"""
Compare signal dates between Pine Script and Python implementation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import sqlite3
from datetime import datetime
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from core.pine_functions import nz


def compare_signal_dates():
    """Compare exact dates when signals are generated"""
    
    print("="*70)
    print("PINE SCRIPT vs PYTHON SIGNAL DATE COMPARISON")
    print("="*70)
    
    # Load Pine Script data
    pine_file = "archive/data_files/NSE_ICICIBANK, 1D.csv"
    df_pine = pd.read_csv(pine_file)
    df_pine['time'] = pd.to_datetime(df_pine['time'])
    
    # Get Pine Script signals
    pine_buy_signals = df_pine[df_pine['Buy'].notna()][['time', 'Buy']].copy()
    pine_sell_signals = df_pine[df_pine['Sell'].notna()][['time', 'Sell']].copy()
    pine_buy_signals['signal_type'] = 'BUY'
    pine_sell_signals['signal_type'] = 'SELL'
    
    # Combine all Pine signals
    pine_signals = pd.concat([
        pine_buy_signals[['time', 'signal_type']],
        pine_sell_signals[['time', 'signal_type']]
    ]).sort_values('time').reset_index(drop=True)
    
    print(f"\n📊 PINE SCRIPT SIGNALS:")
    print(f"   Total signals: {len(pine_signals)}")
    print(f"   Date range: {pine_signals['time'].min()} to {pine_signals['time'].max()}")
    
    # Now run Python implementation for the same date range
    print(f"\n🔄 Running Python implementation for same period...")
    
    # Load data from cache
    db_path = os.path.join("data_cache", "market_data.db")
    with sqlite3.connect(db_path) as conn:
        # Get data for the Pine Script date range
        # Convert timestamps to strings for SQLite
        start_date = pine_signals['time'].min().strftime('%Y-%m-%d')
        end_date = pine_signals['time'].max().strftime('%Y-%m-%d')
        
        query = """
        SELECT date, open, high, low, close, volume
        FROM market_data
        WHERE symbol = 'ICICIBANK' AND interval = 'day'
        AND date >= ? AND date <= ?
        ORDER BY date
        """
        df_python = pd.read_sql_query(
            query, conn, 
            params=(start_date, end_date),
            parse_dates=['date']
        )
    
    # Initialize processor with same config
    config = TradingConfig(
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        source='close',
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        use_kernel_filter=True,
        use_kernel_smoothing=False,
        kernel_lookback=8,
        kernel_relative_weight=8.0,
        kernel_regression_level=25,
        kernel_lag=2
    )
    
    processor = EnhancedBarProcessor(config, "ICICIBANK", "day", debug_mode=False)
    
    # Process all bars and collect signals
    python_signals = []
    
    # Need to process bars before the date range for warmup
    # Get ALL available data to ensure proper warmup
    with sqlite3.connect(db_path) as conn:
        query_all = """
        SELECT date, open, high, low, close, volume
        FROM market_data
        WHERE symbol = 'ICICIBANK' AND interval = 'day'
        ORDER BY date
        """
        df_all = pd.read_sql_query(
            query_all, conn,
            parse_dates=['date']
        )
    
    df_all = df_all.sort_values('date').reset_index(drop=True)
    
    print(f"\n📊 Processing {len(df_all)} total bars for warmup + analysis")
    print(f"   Data range: {df_all['date'].min()} to {df_all['date'].max()}")
    print(f"   Warmup ends at bar: {config.max_bars_back}")
    
    # Track when we start getting signals
    first_signal_bar = None
    bars_in_range = 0
    
    for idx, row in df_all.iterrows():
        result = processor.process_bar(
            nz(row['open'], row['close']),
            nz(row['high'], row['close']),
            nz(row['low'], row['close']),
            nz(row['close'], 0.0),
            nz(row['volume'], 0.0)
        )
        
        # Handle timezone comparison properly
        bar_date = pd.to_datetime(row['date'])
        pine_min_date = pine_signals['time'].min()
        
        # Check if dates have timezone info and handle accordingly
        if bar_date.tz is not None and pine_min_date.tz is None:
            # bar_date is timezone-aware, pine is naive - make bar_date naive
            bar_date = bar_date.replace(tzinfo=None)
        elif bar_date.tz is None and pine_min_date.tz is not None:
            # bar_date is naive, pine is timezone-aware - make pine naive
            pine_min_date = pine_min_date.replace(tzinfo=None)
        
        if result and bar_date >= pine_min_date:
            bars_in_range += 1
            if result.start_long_trade:
                if first_signal_bar is None:
                    first_signal_bar = idx
                python_signals.append({
                    'date': row['date'],
                    'signal_type': 'BUY'
                })
            if result.start_short_trade:
                if first_signal_bar is None:
                    first_signal_bar = idx
                python_signals.append({
                    'date': row['date'],
                    'signal_type': 'SELL'
                })
    
    df_python_signals = pd.DataFrame(python_signals)
    
    print(f"\n📊 PYTHON SIGNALS:")
    print(f"   Total signals: {len(df_python_signals)}")
    print(f"   Bars analyzed in Pine date range: {bars_in_range}")
    if first_signal_bar is not None:
        print(f"   First signal at bar: {first_signal_bar} (warmup + {first_signal_bar - config.max_bars_back} bars)")
    if len(df_python_signals) > 0:
        print(f"   Date range: {df_python_signals['date'].min()} to {df_python_signals['date'].max()}")
    
    # Compare signals
    print(f"\n🔍 DETAILED COMPARISON:")
    
    # Convert to sets for comparison - ensure timezone consistency
    pine_dates = set(pine_signals['time'].dt.date)
    if len(df_python_signals) > 0:
        # Ensure python dates are timezone-naive for comparison
        df_python_signals['date'] = pd.to_datetime(df_python_signals['date']).dt.tz_localize(None)
        python_dates = set(df_python_signals['date'].dt.date)
    else:
        python_dates = set()
    
    # Find matches and differences
    matching_dates = pine_dates & python_dates
    pine_only = pine_dates - python_dates
    python_only = python_dates - pine_dates
    
    print(f"\n   Matching signal dates: {len(matching_dates)}")
    print(f"   Pine Script only: {len(pine_only)}")
    print(f"   Python only: {len(python_only)}")
    
    # Show details
    if matching_dates:
        print(f"\n   ✅ MATCHING DATES:")
        for date in sorted(matching_dates)[:5]:  # Show first 5
            pine_sig = pine_signals[pine_signals['time'].dt.date == date]['signal_type'].values[0]
            py_sig = df_python_signals[df_python_signals['date'].dt.date == date]['signal_type'].values[0]
            print(f"      {date}: Pine={pine_sig}, Python={py_sig}")
    
    if pine_only:
        print(f"\n   ❌ PINE SCRIPT ONLY (first 5):")
        for date in sorted(pine_only)[:5]:
            sig_type = pine_signals[pine_signals['time'].dt.date == date]['signal_type'].values[0]
            print(f"      {date}: {sig_type}")
    
    if python_only:
        print(f"\n   ❌ PYTHON ONLY (first 5):")
        for date in sorted(python_only)[:5]:
            sig_type = df_python_signals[df_python_signals['date'].dt.date == date]['signal_type'].values[0]
            print(f"      {date}: {sig_type}")
    
    # Calculate match rate
    total_unique_dates = len(pine_dates | python_dates)
    match_rate = len(matching_dates) / total_unique_dates * 100 if total_unique_dates > 0 else 0
    
    # SUMMARY
    print(f"\n" + "="*70)
    print("SUMMARY - SIGNAL DATE COMPARISON")
    print("="*70)
    print(f"Pine Script signals: {len(pine_signals)}")
    print(f"Python signals: {len(df_python_signals)}")
    print(f"Matching dates: {len(matching_dates)}")
    print(f"Match rate: {match_rate:.1f}%")
    print(f"\nEntry Rate Comparison:")
    print(f"  Pine Script: {len(pine_signals)/len(df_pine)*100:.2f}%")
    print(f"  Python: {len(df_python_signals)/len(df_python)*100:.2f}%")
    print("="*70)

if __name__ == "__main__":
    compare_signal_dates()