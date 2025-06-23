#!/usr/bin/env python3
"""
Check when ML predictions actually start in Python implementation
"""

import sys
sys.path.append('/Users/knight/Desktop/projects/mcp-testing/lorentzian_classifier')

from data.zerodha_client import ZerodhaClient
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
import pandas as pd

def check_ml_warmup():
    # Initialize
    client = ZerodhaClient()
    config = TradingConfig()
    processor = BarProcessor(config)
    
    symbol = "ICICIBANK"
    print(f"=== ML WARMUP ANALYSIS FOR {symbol} ===\n")
    print(f"Config Settings:")
    print(f"  Max Bars Back: {config.max_bars_back}")
    print(f"  Neighbors Count: {config.neighbors_count}")
    print(f"  Feature Count: {config.feature_count}")
    
    # Get more historical data to see warmup
    historical_data = client.get_historical_data(
        symbol,
        interval="day",
        days=500  # Get extra data to see warmup period
    )
    
    if not historical_data:
        print(f"Failed to fetch data for {symbol}")
        return
    
    print(f"\nProcessing {len(historical_data)} bars...")
    
    # Track when predictions start
    prediction_log = []
    first_non_zero_prediction = None
    first_signal_change = None
    
    for i, candle in enumerate(historical_data):
        result = processor.process_bar(
            candle['open'],
            candle['high'],
            candle['low'], 
            candle['close'],
            candle['volume']
        )
        
        # Track when we get first non-zero prediction
        if first_non_zero_prediction is None and result.prediction != 0:
            first_non_zero_prediction = {
                'bar': i,
                'date': candle['date'],
                'prediction': result.prediction
            }
        
        # Track prediction values
        prediction_log.append({
            'bar': i,
            'date': candle['date'],
            'prediction': result.prediction,
            'signal': result.signal,
            'arrays_size': i + 1,  # How many bars in arrays
            'can_predict': i >= 50  # Assuming some minimum bars needed
        })
    
    df = pd.DataFrame(prediction_log)
    
    print("\n=== WARMUP PERIOD ANALYSIS ===")
    
    # Check early predictions
    early_bars = df.head(100)
    print(f"\nFirst 100 bars prediction summary:")
    print(f"  Predictions = 0: {(early_bars['prediction'] == 0).sum()}")
    print(f"  Predictions != 0: {(early_bars['prediction'] != 0).sum()}")
    
    if first_non_zero_prediction:
        print(f"\nFirst non-zero prediction:")
        print(f"  Bar: {first_non_zero_prediction['bar']}")
        print(f"  Date: {first_non_zero_prediction['date']}")
        print(f"  Prediction: {first_non_zero_prediction['prediction']}")
    
    # Check prediction patterns over time
    print("\n=== PREDICTION PATTERNS BY BAR RANGE ===")
    
    ranges = [
        (0, 50, "Bars 0-50"),
        (50, 100, "Bars 50-100"),
        (100, 200, "Bars 100-200"),
        (200, 300, "Bars 200-300"),
        (300, len(df), "Bars 300+")
    ]
    
    for start, end, label in ranges:
        if start < len(df):
            subset = df.iloc[start:min(end, len(df))]
            if len(subset) > 0:
                non_zero = (subset['prediction'] != 0).sum()
                avg_pred = subset['prediction'].abs().mean()
                print(f"\n{label}:")
                print(f"  Non-zero predictions: {non_zero} / {len(subset)} ({non_zero/len(subset)*100:.1f}%)")
                print(f"  Avg |prediction|: {avg_pred:.2f}")
                print(f"  Unique predictions: {subset['prediction'].nunique()}")
    
    # Check if we need minimum bars
    print("\n=== MINIMUM BARS CHECK ===")
    print(f"\nChecking if ML needs minimum bars before starting...")
    
    # In Pine Script: bar_index >= maxBarsBackIndex
    # maxBarsBackIndex = last_bar_index >= maxBarsBack ? last_bar_index - maxBarsBack : 0
    
    # This means:
    # - If we have < 2000 bars total: maxBarsBackIndex = 0 (start from beginning)
    # - If we have >= 2000 bars total: maxBarsBackIndex = last_bar - 2000
    
    total_bars = len(df)
    if total_bars >= config.max_bars_back:
        expected_ml_start = total_bars - config.max_bars_back
        print(f"\nExpected ML start (Pine Script logic):")
        print(f"  Total bars: {total_bars}")
        print(f"  Max bars back: {config.max_bars_back}")
        print(f"  ML should start at bar: {expected_ml_start}")
        print(f"  That's {config.max_bars_back} bars for training")
    else:
        print(f"\nTotal bars ({total_bars}) < max_bars_back ({config.max_bars_back})")
        print(f"  ML should process all bars from start")
    
    # Save for inspection
    df.to_csv('debug_ml_warmup.csv', index=False)
    print(f"\n✓ Saved warmup analysis to debug_ml_warmup.csv")
    
    # Final insight
    print("\n=== KEY INSIGHT ===")
    print("Pine Script logic:")
    print("1. Accumulates feature arrays for ALL bars")
    print("2. But only runs ML on RECENT bars (last 2000)")
    print("3. This gives good training data but recent predictions")
    print("\nPython might be:")
    print("1. Not accumulating enough training data")
    print("2. Or starting predictions too early")
    print("3. Or not following the bar_index >= maxBarsBackIndex logic")

if __name__ == "__main__":
    check_ml_warmup()
