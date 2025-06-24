#!/usr/bin/env python3
"""
Compare ML predictions between Pine Script expectations and Python implementation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import sqlite3
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from core.pine_functions import nz
import numpy as np


def ml_prediction_comparison():
    """Compare ML predictions in detail"""
    
    print("="*70)
    print("ML PREDICTION COMPARISON ANALYSIS")
    print("="*70)
    
    # Load Pine Script data
    pine_file = "archive/data_files/NSE_ICICIBANK, 1D.csv"
    df_pine = pd.read_csv(pine_file)
    df_pine['time'] = pd.to_datetime(df_pine['time'])
    
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
    
    print(f"\n📊 Processing {len(df)} bars...")
    
    # Collect ML predictions and feature data
    ml_data = []
    
    for idx, row in df.iterrows():
        result = processor.process_bar(
            nz(row['open'], row['close']),
            nz(row['high'], row['close']),
            nz(row['low'], row['close']),
            nz(row['close'], 0.0),
            nz(row['volume'], 0.0)
        )
        
        if result and result.bar_index >= config.max_bars_back:
            # Get current feature values
            if hasattr(processor, 'feature_arrays'):
                current_features = {
                    'f1': processor.feature_arrays.f1[-1] if processor.feature_arrays.f1 else 0,
                    'f2': processor.feature_arrays.f2[-1] if processor.feature_arrays.f2 else 0,
                    'f3': processor.feature_arrays.f3[-1] if processor.feature_arrays.f3 else 0,
                    'f4': processor.feature_arrays.f4[-1] if processor.feature_arrays.f4 else 0,
                    'f5': processor.feature_arrays.f5[-1] if processor.feature_arrays.f5 else 0
                }
            else:
                current_features = {'f1': 0, 'f2': 0, 'f3': 0, 'f4': 0, 'f5': 0}
            
            ml_data.append({
                'date': row['date'],
                'close': row['close'],
                'ml_prediction': result.prediction,
                'signal': result.signal,
                'features': current_features,
                'training_size': len(processor.ml_model.y_train_array) if hasattr(processor.ml_model, 'y_train_array') else 0
            })
        
        if idx % 500 == 0:
            print(f"   Processed {idx}/{len(df)} bars...")
    
    df_ml = pd.DataFrame(ml_data)
    
    # Analyze ML predictions on Pine signal dates
    print(f"\n📊 ML PREDICTIONS ON PINE SIGNAL DATES:")
    
    correct_predictions = 0
    total_pine_signals = 0
    
    for idx, row in df_pine.iterrows():
        has_signal = False
        signal_type = None
        
        if pd.notna(row['Buy']):
            has_signal = True
            signal_type = 'BUY'
        elif pd.notna(row['Sell']):
            has_signal = True
            signal_type = 'SELL'
        
        if has_signal:
            total_pine_signals += 1
            
            # Find corresponding ML prediction
            ml_row = df_ml[df_ml['date'].dt.date == row['time'].date()]
            
            if not ml_row.empty:
                ml_pred = ml_row.iloc[0]['ml_prediction']
                features = ml_row.iloc[0]['features']
                
                # Check if prediction matches expected direction
                if (signal_type == 'BUY' and ml_pred > 0) or (signal_type == 'SELL' and ml_pred < 0):
                    correct_predictions += 1
                else:
                    # Print mismatch details
                    if total_pine_signals <= 10:  # First 10 mismatches
                        print(f"\n❌ Mismatch on {row['time'].strftime('%Y-%m-%d')}:")
                        print(f"   Pine: {signal_type}")
                        print(f"   Python ML: {ml_pred:.2f}")
                        print(f"   Features: {', '.join([f'{k}={v:.2f}' for k, v in features.items()])}")
                        print(f"   Training size: {ml_row.iloc[0]['training_size']}")
    
    accuracy = correct_predictions / total_pine_signals * 100 if total_pine_signals > 0 else 0
    
    print(f"\n📊 ML PREDICTION ACCURACY:")
    print(f"   Correct predictions: {correct_predictions}/{total_pine_signals} ({accuracy:.1f}%)")
    
    # Analyze prediction distribution
    print(f"\n📊 ML PREDICTION DISTRIBUTION:")
    
    # During Pine period only
    pine_start = df_pine['time'].min()
    pine_end = df_pine['time'].max()
    pine_period_ml = df_ml[(df_ml['date'] >= pine_start) & (df_ml['date'] <= pine_end)]
    
    # Categorize predictions
    bullish = (pine_period_ml['ml_prediction'] > 0).sum()
    bearish = (pine_period_ml['ml_prediction'] < 0).sum()
    neutral = (pine_period_ml['ml_prediction'] == 0).sum()
    
    print(f"   Bullish (>0): {bullish} ({bullish/len(pine_period_ml)*100:.1f}%)")
    print(f"   Bearish (<0): {bearish} ({bearish/len(pine_period_ml)*100:.1f}%)")
    print(f"   Neutral (=0): {neutral} ({neutral/len(pine_period_ml)*100:.1f}%)")
    
    # Check prediction stability
    print(f"\n📊 PREDICTION STABILITY:")
    
    # Count consecutive same predictions
    prediction_runs = []
    current_run = 1
    
    for i in range(1, len(pine_period_ml)):
        curr_sign = np.sign(pine_period_ml.iloc[i]['ml_prediction'])
        prev_sign = np.sign(pine_period_ml.iloc[i-1]['ml_prediction'])
        
        if curr_sign == prev_sign:
            current_run += 1
        else:
            prediction_runs.append(current_run)
            current_run = 1
    
    if prediction_runs:
        avg_run = np.mean(prediction_runs)
        max_run = np.max(prediction_runs)
        print(f"   Average consecutive same direction: {avg_run:.1f} bars")
        print(f"   Maximum consecutive same direction: {max_run} bars")
    
    # SUMMARY
    print(f"\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    print(f"Key findings:")
    print(f"1. ML predictions match Pine expectations only {accuracy:.1f}% of the time")
    print(f"2. Prediction distribution: {bullish} bullish, {bearish} bearish, {neutral} neutral")
    
    if accuracy < 60:
        print(f"\n⚠️  Low accuracy suggests fundamental differences in:")
        print(f"   - Feature calculation (RSI, ADX, WaveTrend, etc.)")
        print(f"   - Feature normalization/rescaling")
        print(f"   - Training label generation")
        print(f"   - Lorentzian distance calculation")
        print(f"   - Neighbor weight calculation")
    
    print("="*70)


if __name__ == "__main__":
    ml_prediction_comparison()