#!/usr/bin/env python3
"""
Debug ML Algorithm Internals
============================
Purpose: Deep dive into why ML predictions are 0
- Check training labels distribution
- Verify feature values
- Debug neighbor selection
- Check distance calculations
"""

import pandas as pd
import os
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor

def debug_ml_internals():
    """Debug ML algorithm step by step"""
    
    print("=" * 60)
    print("🔬 Deep Dive: ML Algorithm Internals")
    print("=" * 60)
    print()
    
    # Load data
    data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return
    
    df = pd.read_csv(data_file)
    print(f"📂 Loaded {len(df)} bars\n")
    
    # Simple config - all filters OFF
    config = TradingConfig(
        max_bars_back=100,  # Smaller for easier debugging
        neighbors_count=8,
        feature_count=5,
        # All filters OFF
        use_volatility_filter=False,
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=False,
        use_ema_filter=False,
        use_sma_filter=False
    )
    
    processor = BarProcessor(config)
    
    # Track everything
    training_labels = []
    feature_values = []
    predictions = []
    
    print("📊 Processing bars and tracking internals...\n")
    
    # Process bars
    for i in range(min(200, len(df))):  # Process first 200 bars
        bar = df.iloc[i]
        
        result = processor.process_bar(
            open_price=bar['open'],
            high=bar['high'],
            low=bar['low'],
            close=bar['close'],
            volume=bar['volume']
        )
        
        predictions.append(result.prediction)
        
        # Track feature values at specific bars
        if i in [50, 100, 103, 104, 105, 110, 150]:
            print(f"Bar {i:3d}:")
            print(f"  Prediction: {result.prediction:.2f}")
            
            # Get current state from ML model
            ml_model = processor.ml_model
            
            # Check training labels
            if len(ml_model.y_train_array) > 0:
                recent_labels = ml_model.y_train_array[-10:] if len(ml_model.y_train_array) >= 10 else ml_model.y_train_array
                label_counts = {
                    'long': sum(1 for l in recent_labels if l == 1),
                    'short': sum(1 for l in recent_labels if l == -1),
                    'neutral': sum(1 for l in recent_labels if l == 0)
                }
                print(f"  Recent labels: {recent_labels}")
                print(f"  Label distribution: Long={label_counts['long']}, Short={label_counts['short']}, Neutral={label_counts['neutral']}")
            
            # Check if ML has started
            print(f"  Training array size: {len(ml_model.y_train_array)}")
            print(f"  Should ML run? {len(ml_model.y_train_array) >= config.max_bars_back}")
            
            # If prediction is non-zero, show neighbors
            if result.prediction != 0:
                print(f"  Neighbors found: {len(ml_model.predictions)}")
                if ml_model.predictions:
                    print(f"  Neighbor predictions: {ml_model.predictions}")
            
            print()
    
    # Overall analysis
    print("\n" + "="*50)
    print("📊 Overall Analysis")
    print("="*50)
    
    # Training labels distribution
    if processor.ml_model.y_train_array:
        all_labels = processor.ml_model.y_train_array
        total_long = sum(1 for l in all_labels if l == 1)
        total_short = sum(1 for l in all_labels if l == -1)
        total_neutral = sum(1 for l in all_labels if l == 0)
        
        print(f"\nTraining Labels Distribution:")
        print(f"  Total labels: {len(all_labels)}")
        print(f"  Long: {total_long} ({total_long/len(all_labels)*100:.1f}%)")
        print(f"  Short: {total_short} ({total_short/len(all_labels)*100:.1f}%)")
        print(f"  Neutral: {total_neutral} ({total_neutral/len(all_labels)*100:.1f}%)")
    
    # Predictions analysis
    non_zero_preds = [p for p in predictions if p != 0]
    print(f"\nPredictions Analysis:")
    print(f"  Total bars: {len(predictions)}")
    print(f"  Non-zero predictions: {len(non_zero_preds)}")
    if non_zero_preds:
        print(f"  Range: [{min(non_zero_preds):.2f}, {max(non_zero_preds):.2f}]")
    
    # Debug feature arrays
    print(f"\nFeature Arrays Status:")
    print(f"  F1 array size: {len(processor.feature_arrays.f1)}")
    print(f"  F2 array size: {len(processor.feature_arrays.f2)}")
    if len(processor.feature_arrays.f1) > 0:
        print(f"  F1 last 5 values: {processor.feature_arrays.f1[-5:]}")
        print(f"  F2 last 5 values: {processor.feature_arrays.f2[-5:]}")
    
    print("\n" + "="*60)
    print("💡 Debugging Insights")
    print("="*60)
    
    print("\nPossible Issues:")
    print("1. If all labels are neutral → No price movement in data")
    print("2. If no neighbors found → Distance threshold too restrictive")
    print("3. If features all similar → Normalization issue")
    print("4. If predictions always 0 → Check neighbor selection logic")

if __name__ == "__main__":
    debug_ml_internals()
