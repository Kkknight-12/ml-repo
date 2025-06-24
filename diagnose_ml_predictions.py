#!/usr/bin/env python3
"""
Diagnose ML prediction differences between Pine Script and Python
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


def diagnose_ml_predictions():
    """Analyze why ML predictions differ from Pine Script expectations"""
    
    print("="*70)
    print("ML PREDICTION DIAGNOSIS")
    print("="*70)
    
    # Pine Script signal expectations
    pine_expectations = [
        ('2024-04-18', 'SELL'),
        ('2024-04-25', 'BUY'),
        ('2024-05-29', 'SELL'),
        ('2024-06-03', 'BUY'),
        ('2024-07-25', 'SELL'),
        ('2024-08-27', 'BUY'),
    ]
    
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
    
    # Load data
    db_path = os.path.join("data_cache", "market_data.db")
    with sqlite3.connect(db_path) as conn:
        query = """
        SELECT date, open, high, low, close, volume
        FROM market_data
        WHERE symbol = 'ICICIBANK' AND interval = 'day'
        ORDER BY date
        """
        df = pd.read_sql_query(query, conn, parse_dates=['date'])
    
    # Process bars and collect ML data
    ml_data = []
    
    for idx, row in df.iterrows():
        result = processor.process_bar(
            nz(row['open'], row['close']),
            nz(row['high'], row['close']),
            nz(row['low'], row['close']),
            nz(row['close'], 0.0),
            nz(row['volume'], 0.0)
        )
        
        if result and idx >= config.max_bars_back:
            ml_data.append({
                'date': row['date'],
                'close': row['close'],
                'prediction': result.prediction,
                'signal': result.signal,
                'neighbors': len(processor.ml_model.predictions) if hasattr(processor, 'ml_model') else 0
            })
    
    df_ml = pd.DataFrame(ml_data)
    
    # Analyze specific dates
    print(f"\n🔍 ANALYZING PINE SCRIPT SIGNAL DATES:")
    
    for date_str, expected_signal in pine_expectations:
        date_data = df_ml[df_ml['date'].dt.strftime('%Y-%m-%d') == date_str]
        
        if not date_data.empty:
            row = date_data.iloc[0]
            expected_pred = 1 if expected_signal == 'BUY' else -1
            actual_pred = row['prediction']
            
            print(f"\n📅 {date_str}:")
            print(f"   Expected: {expected_signal} (pred={expected_pred})")
            print(f"   Actual: pred={actual_pred}, signal={row['signal']}")
            print(f"   Neighbors: {row['neighbors']}")
            
            if (expected_pred > 0 and actual_pred < 0) or (expected_pred < 0 and actual_pred > 0):
                print(f"   ❌ MISMATCH: Python predicts opposite direction!")
    
    # Analyze prediction distribution
    print(f"\n📊 ML PREDICTION DISTRIBUTION:")
    pred_counts = df_ml['prediction'].value_counts().sort_index()
    for pred_val, count in pred_counts.items():
        print(f"   Prediction {pred_val}: {count} times ({count/len(df_ml)*100:.1f}%)")
    
    # Look for patterns in mismatches
    print(f"\n🔍 MISMATCH PATTERN ANALYSIS:")
    
    # Check if predictions are consistently inverted
    inversions = 0
    matches = 0
    
    for date_str, expected_signal in pine_expectations:
        date_data = df_ml[df_ml['date'].dt.strftime('%Y-%m-%d') == date_str]
        if not date_data.empty:
            expected_pred = 1 if expected_signal == 'BUY' else -1
            actual_pred = date_data.iloc[0]['prediction']
            
            if actual_pred != 0:
                if (expected_pred > 0 and actual_pred < 0) or (expected_pred < 0 and actual_pred > 0):
                    inversions += 1
                elif (expected_pred > 0 and actual_pred > 0) or (expected_pred < 0 and actual_pred < 0):
                    matches += 1
    
    print(f"   Matches: {matches}")
    print(f"   Inversions: {inversions}")
    print(f"   Match rate: {matches/(matches+inversions)*100:.1f}%" if (matches+inversions) > 0 else "N/A")
    
    # Check training data labels
    print(f"\n📊 TRAINING DATA ANALYSIS:")
    if hasattr(processor, 'ml_model') and hasattr(processor.ml_model, 'y_train_array'):
        y_train = processor.ml_model.y_train_array
        if len(y_train) > 0:
            print(f"   Training labels: {len(y_train)}")
            print(f"   Long labels: {sum(1 for y in y_train if y == 1)} ({sum(1 for y in y_train if y == 1)/len(y_train)*100:.1f}%)")
            print(f"   Short labels: {sum(1 for y in y_train if y == -1)} ({sum(1 for y in y_train if y == -1)/len(y_train)*100:.1f}%)")
            print(f"   Neutral labels: {sum(1 for y in y_train if y == 0)} ({sum(1 for y in y_train if y == 0)/len(y_train)*100:.1f}%)")
    
    # SUMMARY
    print(f"\n" + "="*70)
    print("SUMMARY - ML PREDICTION DIAGNOSIS")
    print("="*70)
    print(f"Analysis of {len(pine_expectations)} Pine Script signal dates:")
    print(f"  - Matches: {matches}")
    print(f"  - Inversions: {inversions}")
    
    if inversions > matches:
        print(f"\n⚠️  CRITICAL: ML predictions are often INVERTED from Pine Script!")
        print(f"This suggests a fundamental difference in:")
        print(f"  1. Label generation (close[4] < close[0] logic)")
        print(f"  2. Feature calculation or normalization")
        print(f"  3. Distance calculation in KNN")
    else:
        print(f"\n✅ ML predictions generally match Pine Script expectations")
    
    print("="*70)


if __name__ == "__main__":
    diagnose_ml_predictions()