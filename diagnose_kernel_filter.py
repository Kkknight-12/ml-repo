#!/usr/bin/env python3
"""
Diagnose kernel filter differences causing 170-bar signal delay
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Tuple

from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from core.pine_functions import nz
from core.kernel_functions import is_kernel_bullish, is_kernel_bearish, calculate_kernel_values


def diagnose_kernel_filter_delay():
    """
    Diagnose why Pine Script shows 170-bar delay after warmup
    Focus on kernel filter behavior
    """
    print("="*70)
    print("KERNEL FILTER DELAY DIAGNOSIS")
    print("="*70)
    
    # Pine Script configuration
    config = TradingConfig(
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        color_compression=1,
        source='close',
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        regime_threshold=-0.1,
        adx_threshold=20,
        use_kernel_filter=True,
        use_kernel_smoothing=False,
        kernel_lookback=8,
        kernel_relative_weight=8.0,
        kernel_regression_level=25,
        kernel_lag=2,
        use_ema_filter=False,
        ema_period=200,
        use_sma_filter=False,
        sma_period=200
    )
    
    # Load data from cache
    db_path = os.path.join("data_cache", "market_data.db")
    with sqlite3.connect(db_path) as conn:
        query = """
        SELECT date, open, high, low, close, volume
        FROM market_data
        WHERE symbol = 'ICICIBANK' AND interval = 'day'
        ORDER BY date
        """
        df = pd.read_sql_query(query, conn, parse_dates=['date'])
    
    print(f"\n✅ Loaded {len(df)} bars from cache")
    df = df.reset_index(drop=True)
    
    # Initialize processor
    processor = EnhancedBarProcessor(config, "ICICIBANK", "day", debug_mode=False)
    
    # Focus on bars around warmup end and first signals
    warmup_end = config.max_bars_back
    analysis_start = warmup_end - 10
    analysis_end = warmup_end + 200
    
    print(f"\n📊 Analyzing bars {analysis_start} to {analysis_end}")
    print(f"   Warmup ends at bar: {warmup_end}")
    
    # Process bars and track kernel states
    kernel_states = []
    close_prices = []
    
    for idx, row in df.iterrows():
        # Process bar
        result = processor.process_bar(
            nz(row['open'], row['close']),
            nz(row['high'], row['close']),
            nz(row['low'], row['close']),
            nz(row['close'], 0.0),
            nz(row['volume'], 0.0)
        )
        
        # Track close prices for kernel calculation
        close_prices.append(row['close'])
        
        # Only analyze in our range
        if idx < analysis_start:
            continue
        if idx > analysis_end:
            break
        
        if result:
            # Get kernel state
            if len(close_prices) >= config.kernel_lookback:
                # Get last N prices for kernel calculation
                src_values = close_prices[-config.kernel_lookback-10:][::-1]  # Reverse for newest first
                
                is_bullish = is_kernel_bullish(
                    src_values, 
                    config.kernel_lookback,
                    config.kernel_relative_weight,
                    config.kernel_regression_level,
                    config.use_kernel_smoothing,
                    config.kernel_lag
                )
                
                is_bearish = is_kernel_bearish(
                    src_values,
                    config.kernel_lookback,
                    config.kernel_relative_weight,
                    config.kernel_regression_level,
                    config.use_kernel_smoothing,
                    config.kernel_lag
                )
                
                # Get kernel values for analysis
                if len(src_values) >= config.kernel_lookback:
                    yhat1, yhat1_prev, yhat2, yhat2_prev = calculate_kernel_values(
                        src_values,
                        config.kernel_lookback,
                        config.kernel_relative_weight,
                        config.kernel_regression_level,
                        config.kernel_lag
                    )
                else:
                    yhat1 = yhat1_prev = yhat2 = yhat2_prev = 0.0
            else:
                is_bullish = is_bearish = False
                yhat1 = yhat1_prev = yhat2 = yhat2_prev = 0.0
            
            kernel_state = {
                'bar': idx,
                'date': row['date'].strftime('%Y-%m-%d'),
                'close': row['close'],
                'ml_pred': result.prediction,
                'signal': result.signal,
                'kernel_bull': is_bullish,
                'kernel_bear': is_bearish,
                'kernel_val': yhat1,
                'kernel_prev': yhat1_prev,
                'kernel_trend': 'UP' if yhat1 > yhat1_prev else 'DOWN',
                'filters_pass': all(result.filter_states.values()),
                'entry_long': result.start_long_trade,
                'entry_short': result.start_short_trade
            }
            
            kernel_states.append(kernel_state)
            
            # Print key transitions
            if idx == warmup_end:
                print(f"\n>>> WARMUP ENDS at bar {idx} <<<")
                print(f"   Date: {row['date'].strftime('%Y-%m-%d')}")
                print(f"   Kernel: Bullish={is_bullish}, Bearish={is_bearish}")
                print(f"   Kernel Value: {yhat1:.2f}, Trend: {kernel_state['kernel_trend']}")
                print(f"   ML Prediction: {result.prediction}")
                print(f"   Filters Pass: {kernel_state['filters_pass']}")
            
            if result.start_long_trade or result.start_short_trade:
                entry_type = "LONG" if result.start_long_trade else "SHORT"
                print(f"\n>>> {entry_type} ENTRY at bar {idx} <<<")
                print(f"   Date: {row['date'].strftime('%Y-%m-%d')}")
                print(f"   Kernel: Bullish={is_bullish}, Bearish={is_bearish}")
                print(f"   Kernel Value: {yhat1:.2f}, Trend: {kernel_state['kernel_trend']}")
                print(f"   ML Prediction: {result.prediction}")
                print(f"   Days after warmup: {idx - warmup_end}")
    
    # Analyze kernel behavior
    if kernel_states:
        df_kernel = pd.DataFrame(kernel_states)
        
        # Find periods where kernel prevents entries
        post_warmup = df_kernel[df_kernel['bar'] >= warmup_end]
        
        print(f"\n📊 Kernel Filter Analysis (Post-Warmup):")
        print(f"   Total bars analyzed: {len(post_warmup)}")
        
        # Count kernel states
        bullish_count = post_warmup['kernel_bull'].sum()
        bearish_count = post_warmup['kernel_bear'].sum()
        
        print(f"\n   Kernel States:")
        print(f"   - Bullish: {bullish_count} bars ({bullish_count/len(post_warmup)*100:.1f}%)")
        print(f"   - Bearish: {bearish_count} bars ({bearish_count/len(post_warmup)*100:.1f}%)")
        
        # Check signal alignment with kernel
        long_signals = post_warmup[post_warmup['signal'] == 1]
        short_signals = post_warmup[post_warmup['signal'] == -1]
        
        if len(long_signals) > 0:
            long_with_bullish = long_signals[long_signals['kernel_bull']].shape[0]
            print(f"\n   Long signals with bullish kernel: {long_with_bullish}/{len(long_signals)}")
        
        if len(short_signals) > 0:
            short_with_bearish = short_signals[short_signals['kernel_bear']].shape[0]
            print(f"   Short signals with bearish kernel: {short_with_bearish}/{len(short_signals)}")
        
        # Find first kernel alignment after warmup
        for idx, row in post_warmup.iterrows():
            if row['ml_pred'] != 0:  # Has ML prediction
                if (row['signal'] == 1 and row['kernel_bull']) or \
                   (row['signal'] == -1 and row['kernel_bear']):
                    print(f"\n   First kernel alignment at bar {row['bar']} ({row['bar'] - warmup_end} bars after warmup)")
                    print(f"   Date: {row['date']}")
                    print(f"   Signal: {row['signal']}, Kernel: Bull={row['kernel_bull']}, Bear={row['kernel_bear']}")
                    break
        
        # Export detailed kernel states
        output_file = f"kernel_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_kernel.to_csv(output_file, index=False)
        print(f"\n💾 Exported detailed kernel states to: {output_file}")
        
        print(f"\n🔍 KEY INSIGHTS:")
        print(f"1. Kernel filter may be preventing entries if:")
        print(f"   - Long signals occur when kernel is bearish")
        print(f"   - Short signals occur when kernel is bullish")
        print(f"2. The 170-bar delay suggests kernel takes time to align with ML signals")
        print(f"3. Check if Pine Script has stricter kernel conditions")
        print(f"4. Verify kernel calculation matches Pine Script exactly")
        
        # SUMMARY FOR QUICK REFERENCE
        print(f"\n" + "="*70)
        print("SUMMARY - KERNEL FILTER DELAY ANALYSIS")
        print("="*70)
        print(f"Warmup ends at bar: {warmup_end}")
        print(f"First entry signal at bar: {post_warmup[post_warmup['entry_long'] | post_warmup['entry_short']].iloc[0]['bar'] if any(post_warmup['entry_long'] | post_warmup['entry_short']) else 'None'}")
        print(f"Kernel bullish rate: {bullish_count/len(post_warmup)*100:.1f}%")
        print(f"Kernel bearish rate: {bearish_count/len(post_warmup)*100:.1f}%")
        
        # Find delay
        first_entry = post_warmup[post_warmup['entry_long'] | post_warmup['entry_short']]
        if not first_entry.empty:
            delay_bars = first_entry.iloc[0]['bar'] - warmup_end
            print(f"Signal delay after warmup: {delay_bars} bars")
        else:
            print(f"Signal delay after warmup: No entries found in analysis range")
        
        print("="*70)


if __name__ == "__main__":
    diagnose_kernel_filter_delay()