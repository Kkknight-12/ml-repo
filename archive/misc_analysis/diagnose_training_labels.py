#!/usr/bin/env python3
"""
Diagnose Training Labels - Check if all labels are neutral
"""

import pandas as pd
import numpy as np
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from utils.sample_data import generate_sample_data

def diagnose_training_labels():
    print("🔍 Diagnosing Training Labels")
    print("=" * 60)
    
    # Generate data with varying price movements
    data = generate_sample_data(
        num_bars=300,
        trend_strength=0.3,  # Good trend
        volatility=0.02,
        start_price=100.0
    )
    
    # Simple config - no filters to isolate ML behavior
    config = TradingConfig(
        use_volatility_filter=False,
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=False,
        max_bars_back=200
    )
    
    processor = BarProcessor(config)
    
    # Track training labels
    training_labels = []
    close_prices = []
    
    print("\n📊 Processing bars and tracking labels...")
    
    for i, row in data.iterrows():
        close_prices.append(row['close'])
        
        # Process bar
        result = processor.process_bar(
            open_price=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume']
        )
        
        # After 5 bars, we can check what label was assigned
        if len(close_prices) > 4:
            # Pine Script logic: src[4] < src[0] ? short : src[4] > src[0] ? long : neutral
            current_close = close_prices[-1]
            close_4_bars_ago = close_prices[-5]
            
            if close_4_bars_ago < current_close:
                label = -1  # short
            elif close_4_bars_ago > current_close:
                label = 1   # long
            else:
                label = 0   # neutral
            
            training_labels.append({
                'bar': i,
                'current_close': current_close,
                'close_4_bars_ago': close_4_bars_ago,
                'price_change': current_close - close_4_bars_ago,
                'pct_change': ((current_close - close_4_bars_ago) / close_4_bars_ago) * 100,
                'label': label
            })
    
    # Analyze labels
    print(f"\n📊 Training Label Analysis:")
    print(f"Total labels: {len(training_labels)}")
    
    if training_labels:
        df_labels = pd.DataFrame(training_labels)
        
        # Count each label type
        label_counts = df_labels['label'].value_counts()
        print(f"\nLabel Distribution:")
        print(f"  Long (1): {label_counts.get(1, 0)} ({label_counts.get(1, 0)/len(df_labels)*100:.1f}%)")
        print(f"  Short (-1): {label_counts.get(-1, 0)} ({label_counts.get(-1, 0)/len(df_labels)*100:.1f}%)")
        print(f"  Neutral (0): {label_counts.get(0, 0)} ({label_counts.get(0, 0)/len(df_labels)*100:.1f}%)")
        
        # Price movement stats
        print(f"\nPrice Movement Statistics:")
        print(f"  Average change: {df_labels['price_change'].mean():.4f}")
        print(f"  Average % change: {df_labels['pct_change'].mean():.2f}%")
        print(f"  Max % change: {df_labels['pct_change'].max():.2f}%")
        print(f"  Min % change: {df_labels['pct_change'].min():.2f}%")
        
        # Show some examples
        print(f"\n📊 Sample Labels (last 10):")
        for _, row in df_labels.tail(10).iterrows():
            label_str = "LONG" if row['label'] == 1 else "SHORT" if row['label'] == -1 else "NEUTRAL"
            print(f"  Bar {row['bar']}: {row['close_4_bars_ago']:.2f} → {row['current_close']:.2f} "
                  f"({row['pct_change']:+.2f}%) = {label_str}")
        
        # Check if all neutral
        if label_counts.get(0, 0) == len(df_labels):
            print("\n❌ PROBLEM FOUND: All training labels are NEUTRAL!")
            print("   This means price isn't moving enough over 4 bars.")
            print("   ML predictions will always sum to 0.")
            print("\n💡 SOLUTIONS:")
            print("   1. Use data with more price movement")
            print("   2. Reduce the 4-bar lookback period")
            print("   3. Use a different price source (hlc3 instead of close)")
        elif label_counts.get(1, 0) == 0 or label_counts.get(-1, 0) == 0:
            print("\n⚠️  WARNING: Missing LONG or SHORT labels!")
            print("   This will bias predictions heavily.")
        else:
            print("\n✅ Label distribution looks good!")
            
    # Also check the actual ML model's training array
    print(f"\n📊 ML Model Training Array:")
    if processor.ml_model.y_train_array:
        ml_labels = processor.ml_model.y_train_array[-20:]  # Last 20
        label_counts = {-1: 0, 0: 0, 1: 0}
        for label in ml_labels:
            label_counts[label] = label_counts.get(label, 0) + 1
        
        print(f"Last 20 labels in ML model:")
        print(f"  Long: {label_counts[1]}, Short: {label_counts[-1]}, Neutral: {label_counts[0]}")
        print(f"  Actual values: {ml_labels}")

if __name__ == "__main__":
    diagnose_training_labels()
