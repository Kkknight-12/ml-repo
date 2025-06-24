#!/usr/bin/env python3
"""
Comprehensive analysis of signal generation differences
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import sqlite3
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from core.pine_functions import nz


def comprehensive_analysis():
    """Analyze all Pine Script signals vs Python"""
    
    print("="*70)
    print("COMPREHENSIVE SIGNAL ANALYSIS")
    print("="*70)
    
    # Load Pine Script data
    pine_file = "archive/data_files/NSE_ICICIBANK, 1D.csv"
    df_pine = pd.read_csv(pine_file)
    df_pine['time'] = pd.to_datetime(df_pine['time'])
    
    # Get all Pine signals
    pine_signals = []
    for idx, row in df_pine.iterrows():
        if pd.notna(row['Buy']):
            pine_signals.append(('BUY', row['time'], row['Buy']))
        if pd.notna(row['Sell']):
            pine_signals.append(('SELL', row['time'], row['Sell']))
    
    print(f"\n📊 PINE SCRIPT SIGNALS: {len(pine_signals)}")
    
    # Initialize processor
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
    
    # Get ALL available data from cache to match Pine Script's historical context
    db_path = os.path.join("data_cache", "market_data.db")
    with sqlite3.connect(db_path) as conn:
        # Get ALL ICICIBANK data we have (from 2003 onwards)
        query = """
        SELECT date, open, high, low, close, volume
        FROM market_data
        WHERE symbol = 'ICICIBANK' AND interval = 'day'
        ORDER BY date
        """
        df = pd.read_sql_query(query, conn, parse_dates=['date'])
    
    print(f"\n📊 PYTHON DATA:")
    print(f"   Total bars: {len(df)}")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    
    # Process all bars
    processor = EnhancedBarProcessor(config, "ICICIBANK", "day", debug_mode=False)
    python_signals = []
    signal_blocked_reasons = {}
    
    print(f"\n🔄 Processing {len(df)} bars...")
    print(f"   ML will activate after bar {config.max_bars_back}")
    
    for idx, row in df.iterrows():
        # Progress indicator
        if idx % 500 == 0:
            print(f"   Processing bar {idx}/{len(df)} ({idx/len(df)*100:.1f}%)...")
            
        result = processor.process_bar(
            nz(row['open'], row['close']),
            nz(row['high'], row['close']),
            nz(row['low'], row['close']),
            nz(row['close'], 0.0),
            nz(row['volume'], 0.0)
        )
        
        if result and (result.start_long_trade or result.start_short_trade):
            signal_type = 'BUY' if result.start_long_trade else 'SELL'
            python_signals.append((signal_type, row['date'], row['close']))
        
        # Check if this date has a Pine signal but no Python signal
        pine_on_date = [s for s in pine_signals if s[1].date() == row['date'].date()]
        if pine_on_date and result and not (result.start_long_trade or result.start_short_trade):
            pine_type = pine_on_date[0][0]
            reasons = []
            
            if pine_type == 'BUY':
                if result.prediction <= 0:
                    reasons.append(f"ML pred={result.prediction} (not bullish)")
                if hasattr(processor, '_calculate_kernel_bullish') and not processor._calculate_kernel_bullish():
                    reasons.append("Kernel not bullish")
                if result.signal == 1:
                    reasons.append("Signal unchanged (already long)")
            else:  # SELL
                if result.prediction >= 0:
                    reasons.append(f"ML pred={result.prediction} (not bearish)")
                if hasattr(processor, '_calculate_kernel_bearish') and not processor._calculate_kernel_bearish():
                    reasons.append("Kernel not bearish")
                if result.signal == -1:
                    reasons.append("Signal unchanged (already short)")
            
            signal_blocked_reasons[row['date'].strftime('%Y-%m-%d')] = (pine_type, reasons)
    
    print(f"\n📊 PYTHON SIGNALS: {len(python_signals)}")
    
    # Compare signals
    print(f"\n🔍 SIGNAL COMPARISON:")
    matches = 0
    for pine_type, pine_date, _ in pine_signals:
        python_match = [s for s in python_signals if s[1].date() == pine_date.date()]
        if python_match and python_match[0][0] == pine_type:
            matches += 1
    
    print(f"   Matching signals: {matches}/{len(pine_signals)} ({matches/len(pine_signals)*100:.1f}%)")
    
    # Show blocked signals
    print(f"\n❌ PINE SIGNALS BLOCKED IN PYTHON:")
    for date_str, (signal_type, reasons) in signal_blocked_reasons.items():
        print(f"\n   {date_str}: {signal_type} blocked")
        for reason in reasons:
            print(f"      - {reason}")
    
    # Summary statistics
    print(f"\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Pine Script: {len(pine_signals)} signals")
    print(f"Python: {len(python_signals)} signals")
    print(f"Matching: {matches} signals ({matches/len(pine_signals)*100:.1f}%)")
    print(f"Blocked: {len(signal_blocked_reasons)} signals")
    
    # Key patterns in blocked signals
    ml_pred_blocks = sum(1 for _, (_, reasons) in signal_blocked_reasons.items() 
                        if any('ML pred' in r for r in reasons))
    kernel_blocks = sum(1 for _, (_, reasons) in signal_blocked_reasons.items() 
                       if any('Kernel' in r for r in reasons))
    unchanged_blocks = sum(1 for _, (_, reasons) in signal_blocked_reasons.items() 
                          if any('unchanged' in r for r in reasons))
    
    print(f"\nBlocking reasons:")
    print(f"  - Wrong ML prediction: {ml_pred_blocks}")
    print(f"  - Kernel filter: {kernel_blocks}")
    print(f"  - Signal unchanged: {unchanged_blocks}")
    print("="*70)


if __name__ == "__main__":
    comprehensive_analysis()