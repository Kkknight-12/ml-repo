#!/usr/bin/env python3
"""
Deep analysis of signal mismatch - why only 25% match even with full data
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import sqlite3
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from core.pine_functions import nz
from ml.lorentzian_knn_fixed import LorentzianKNNFixed


def deep_analysis():
    """Perform deep analysis of signal mismatches"""
    
    print("="*70)
    print("DEEP SIGNAL MISMATCH ANALYSIS")
    print("="*70)
    
    # Load Pine Script data
    pine_file = "archive/data_files/NSE_ICICIBANK, 1D.csv"
    df_pine = pd.read_csv(pine_file)
    df_pine['time'] = pd.to_datetime(df_pine['time'])
    
    # Get Pine signals
    pine_signals = []
    for idx, row in df_pine.iterrows():
        if pd.notna(row['Buy']):
            pine_signals.append({
                'date': row['time'],
                'type': 'BUY',
                'price': row['Buy']
            })
        if pd.notna(row['Sell']):
            pine_signals.append({
                'date': row['time'],
                'type': 'SELL',
                'price': row['Sell']
            })
    
    print(f"\n📊 PINE SCRIPT:")
    print(f"   Total signals: {len(pine_signals)}")
    print(f"   Period: {df_pine['time'].min()} to {df_pine['time'].max()}")
    
    # Initialize processor with debug mode
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
    
    processor = EnhancedBarProcessor(config, "ICICIBANK", "day", debug_mode=True)
    
    # Get all data
    db_path = os.path.join("data_cache", "market_data.db")
    with sqlite3.connect(db_path) as conn:
        query = """
        SELECT date, open, high, low, close, volume
        FROM market_data
        WHERE symbol = 'ICICIBANK' AND interval = 'day'
        ORDER BY date
        """
        df = pd.read_sql_query(query, conn, parse_dates=['date'])
    
    print(f"\n📊 PYTHON DATA:")
    print(f"   Total bars: {len(df)}")
    print(f"   Years of data: {(df['date'].max() - df['date'].min()).days / 365:.1f}")
    
    # Process all bars and collect detailed data
    detailed_results = []
    
    print(f"\n🔄 Processing with detailed tracking...")
    
    for idx, row in df.iterrows():
        result = processor.process_bar(
            nz(row['open'], row['close']),
            nz(row['high'], row['close']),
            nz(row['low'], row['close']),
            nz(row['close'], 0.0),
            nz(row['volume'], 0.0)
        )
        
        if result and result.bar_index >= config.max_bars_back:
            # Only track after warmup
            detailed_results.append({
                'bar_index': result.bar_index,
                'date': row['date'],
                'close': row['close'],
                'ml_prediction': result.prediction,
                'signal': result.signal,
                'filters': result.filter_states.copy(),
                'start_long': result.start_long_trade,
                'start_short': result.start_short_trade,
                'kernel_bullish': processor._calculate_kernel_bullish(),
                'kernel_bearish': processor._calculate_kernel_bearish()
            })
        
        if idx % 500 == 0:
            print(f"   Processed {idx}/{len(df)} bars...")
    
    df_results = pd.DataFrame(detailed_results)
    
    print(f"\n📊 DETAILED ANALYSIS OF PINE SIGNAL DATES:")
    
    mismatch_reasons = {
        'ml_wrong': 0,
        'kernel_blocked': 0,
        'signal_unchanged': 0,
        'filter_blocked': 0,
        'other': 0
    }
    
    for pine_sig in pine_signals:
        # Find corresponding Python data
        py_data = df_results[df_results['date'].dt.date == pine_sig['date'].date()]
        
        if not py_data.empty:
            row = py_data.iloc[0]
            
            print(f"\n📅 {pine_sig['date'].strftime('%Y-%m-%d')}: Pine {pine_sig['type']}")
            print(f"   Python ML prediction: {row['ml_prediction']:.2f}")
            print(f"   Python signal: {row['signal']}")
            print(f"   Filters: Vol={row['filters']['volatility']}, Reg={row['filters']['regime']}")
            print(f"   Kernel: Bull={row['kernel_bullish']}, Bear={row['kernel_bearish']}")
            
            # Check why signal didn't match
            if pine_sig['type'] == 'BUY' and not row['start_long']:
                if row['ml_prediction'] <= 0:
                    print(f"   ❌ Blocked: ML prediction not bullish ({row['ml_prediction']:.2f})")
                    mismatch_reasons['ml_wrong'] += 1
                elif not row['kernel_bullish']:
                    print(f"   ❌ Blocked: Kernel not bullish")
                    mismatch_reasons['kernel_blocked'] += 1
                elif row['signal'] == 1:
                    print(f"   ❌ Blocked: Signal already long")
                    mismatch_reasons['signal_unchanged'] += 1
                elif not all(row['filters'].values()):
                    print(f"   ❌ Blocked: Filters failed")
                    mismatch_reasons['filter_blocked'] += 1
                else:
                    print(f"   ❌ Blocked: Other reason")
                    mismatch_reasons['other'] += 1
            
            elif pine_sig['type'] == 'SELL' and not row['start_short']:
                if row['ml_prediction'] >= 0:
                    print(f"   ❌ Blocked: ML prediction not bearish ({row['ml_prediction']:.2f})")
                    mismatch_reasons['ml_wrong'] += 1
                elif not row['kernel_bearish']:
                    print(f"   ❌ Blocked: Kernel not bearish")
                    mismatch_reasons['kernel_blocked'] += 1
                elif row['signal'] == -1:
                    print(f"   ❌ Blocked: Signal already short")
                    mismatch_reasons['signal_unchanged'] += 1
                elif not all(row['filters'].values()):
                    print(f"   ❌ Blocked: Filters failed")
                    mismatch_reasons['filter_blocked'] += 1
                else:
                    print(f"   ❌ Blocked: Other reason")
                    mismatch_reasons['other'] += 1
    
    # Analyze ML prediction patterns
    print(f"\n📊 ML PREDICTION ANALYSIS:")
    
    # Count prediction distribution
    pred_dist = df_results['ml_prediction'].value_counts().sort_index()
    print(f"\n   Prediction distribution:")
    for pred, count in pred_dist.items():
        if count > 10:  # Only show significant counts
            print(f"      {pred}: {count} times")
    
    # Check prediction changes around Pine signals
    print(f"\n   ML predictions on Pine signal dates:")
    for pine_sig in pine_signals[:5]:
        # Get few bars before and after
        date_idx = df_results[df_results['date'].dt.date == pine_sig['date'].date()].index
        if len(date_idx) > 0:
            idx = date_idx[0]
            start_idx = max(0, idx - 2)
            end_idx = min(len(df_results), idx + 3)
            
            print(f"\n   Around {pine_sig['date'].strftime('%Y-%m-%d')} (Pine {pine_sig['type']}):")
            for i in range(start_idx, end_idx):
                marker = " <-- Pine signal" if i == idx else ""
                print(f"      {df_results.iloc[i]['date'].strftime('%Y-%m-%d')}: "
                      f"ML={df_results.iloc[i]['ml_prediction']:+.1f}, "
                      f"Signal={df_results.iloc[i]['signal']:+d}{marker}")
    
    # SUMMARY
    print(f"\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    print(f"\nMismatch Reasons (out of {len(pine_signals)} Pine signals):")
    total_mismatches = sum(mismatch_reasons.values())
    for reason, count in sorted(mismatch_reasons.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            pct = count / len(pine_signals) * 100
            print(f"   {reason}: {count} ({pct:.1f}%)")
    
    print(f"\nKey Insights:")
    print(f"1. ML predictions disagree {mismatch_reasons['ml_wrong']/len(pine_signals)*100:.1f}% of the time")
    print(f"2. This suggests feature calculation differences between Pine and Python")
    print(f"3. Need to verify:")
    print(f"   - Feature normalization logic")
    print(f"   - Training label generation")
    print(f"   - Neighbor selection algorithm")
    
    print("="*70)


if __name__ == "__main__":
    deep_analysis()