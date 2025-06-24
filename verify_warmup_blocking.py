#!/usr/bin/env python3
"""
Verify that entry/exit signals are properly blocked during warmup period
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import sqlite3
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from core.pine_functions import nz


def verify_warmup_blocking():
    """Verify warmup period signal blocking"""
    
    print("="*70)
    print("WARMUP PERIOD SIGNAL BLOCKING VERIFICATION")
    print("="*70)
    
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
    
    processor = EnhancedBarProcessor(config, "ICICIBANK", "day", debug_mode=False)
    
    # Get all available data
    db_path = os.path.join("data_cache", "market_data.db")
    with sqlite3.connect(db_path) as conn:
        query = """
        SELECT date, open, high, low, close, volume
        FROM market_data
        WHERE symbol = 'ICICIBANK' AND interval = 'day'
        ORDER BY date
        """
        df = pd.read_sql_query(query, conn, parse_dates=['date'])
    
    print(f"\n📊 DATA LOADED:")
    print(f"   Total bars: {len(df)}")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"   Warmup requirement: {config.max_bars_back} bars")
    
    # Track signals during and after warmup
    warmup_signals = []
    post_warmup_signals = []
    
    print(f"\n🔄 Processing bars to check warmup blocking...")
    
    for idx, row in df.iterrows():
        result = processor.process_bar(
            nz(row['open'], row['close']),
            nz(row['high'], row['close']),
            nz(row['low'], row['close']),
            nz(row['close'], 0.0),
            nz(row['volume'], 0.0)
        )
        
        if result:
            # During warmup period
            if result.bar_index < config.max_bars_back:
                if result.start_long_trade or result.start_short_trade or result.end_long_trade or result.end_short_trade:
                    warmup_signals.append({
                        'bar': result.bar_index,
                        'date': row['date'],
                        'type': 'entry' if (result.start_long_trade or result.start_short_trade) else 'exit',
                        'direction': 'long' if (result.start_long_trade or result.end_long_trade) else 'short',
                        'ml_prediction': result.prediction,
                        'signal': result.signal
                    })
            
            # After warmup period
            else:
                if result.start_long_trade or result.start_short_trade:
                    post_warmup_signals.append({
                        'bar': result.bar_index,
                        'date': row['date'],
                        'type': 'entry',
                        'direction': 'long' if result.start_long_trade else 'short',
                        'ml_prediction': result.prediction,
                        'signal': result.signal
                    })
        
        # Progress indicator
        if idx % 500 == 0:
            print(f"   Processed {idx}/{len(df)} bars...")
    
    # Results
    print(f"\n📊 WARMUP PERIOD (bars 0-{config.max_bars_back-1}):")
    print(f"   Signals generated: {len(warmup_signals)}")
    
    if warmup_signals:
        print(f"\n   ❌ ERROR: Signals found during warmup period!")
        for sig in warmup_signals[:5]:
            print(f"      Bar {sig['bar']}: {sig['type']} {sig['direction']} (ML={sig['ml_prediction']:.2f})")
    else:
        print(f"   ✅ CORRECT: No signals during warmup period")
    
    print(f"\n📊 POST-WARMUP PERIOD (bars {config.max_bars_back}+):")
    print(f"   Signals generated: {len(post_warmup_signals)}")
    
    if post_warmup_signals:
        print(f"\n   First 5 signals after warmup:")
        for sig in post_warmup_signals[:5]:
            print(f"      Bar {sig['bar']} ({sig['date'].strftime('%Y-%m-%d')}): {sig['direction'].upper()} entry (ML={sig['ml_prediction']:.2f})")
    else:
        print(f"   ⚠️  WARNING: No signals found after warmup period")
    
    # Check Pine Script comparison period
    pine_file = "archive/data_files/NSE_ICICIBANK, 1D.csv"
    df_pine = pd.read_csv(pine_file)
    df_pine['time'] = pd.to_datetime(df_pine['time'])
    
    pine_period_start_idx = df[df['date'].dt.date >= df_pine['time'].min().date()].index[0]
    
    print(f"\n📊 PINE SCRIPT COMPARISON:")
    print(f"   Pine period starts at bar: {pine_period_start_idx}")
    print(f"   Is after warmup? {pine_period_start_idx >= config.max_bars_back}")
    
    # SUMMARY
    print(f"\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if warmup_signals:
        print("❌ FAILED: Signals are being generated during warmup period")
        print("   This violates Pine Script behavior")
    else:
        print("✅ PASSED: No signals during warmup period")
    
    if not post_warmup_signals:
        print("⚠️  WARNING: No signals after warmup - check ML predictions")
    else:
        print(f"✅ Post-warmup signals: {len(post_warmup_signals)}")
    
    print("="*70)


if __name__ == "__main__":
    verify_warmup_blocking()