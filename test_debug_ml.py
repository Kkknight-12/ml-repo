#!/usr/bin/env python3
"""
Test with Debug ML Module
========================
Uses the debug version of LorentzianKNN to trace the issue
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Temporarily replace the ML module with debug version
import ml.lorentzian_knn_debug as lorentzian_knn_module
sys.modules['ml.lorentzian_knn'] = lorentzian_knn_module

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor

def test_with_debug_ml():
    """Test using debug ML module"""
    
    print("=" * 80)
    print("🔍 TESTING WITH DEBUG ML MODULE")
    print("=" * 80)
    
    # Load data
    data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return
    
    df = pd.read_csv(data_file)
    print(f"\n✅ Loaded {len(df)} bars")
    
    # Simple config with small max_bars_back
    config = TradingConfig(
        max_bars_back=100,  # ML will start after 100 bars
        neighbors_count=8,
        feature_count=5,    # Use all 5 features
        
        # Disable all filters
        use_volatility_filter=False,
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=False,
        use_ema_filter=False,
        use_sma_filter=False
    )
    
    # Initialize processor - no total_bars needed with sliding window!
    processor = BarProcessor(config)
    
    # Enable debug for specific bar
    processor.ml_model.debug_bar = 100  # Debug at bar 100
    
    print("\n🏃 Processing bars...")
    
    # Process bars
    for i in range(min(110, len(df))):
        bar = df.iloc[i]
        
        result = processor.process_bar(
            bar['open'], bar['high'], bar['low'], 
            bar['close'], bar['volume']
        )
        
        # Show progress
        if i == 50:
            print(f"\nBar 50: Training labels so far: {len(processor.ml_model.y_train_array)}")
        elif i == 99:
            print(f"\nBar 99: About to start ML predictions...")
            print(f"Training labels: {len(processor.ml_model.y_train_array)}")
            print(f"Feature array lengths: {len(processor.feature_arrays.f1)}")
        elif i == 100:
            print(f"\n{'='*60}")
            print(f"Bar 100 RESULT: Prediction = {result.prediction}")
            print(f"{'='*60}")
            
            if result.prediction == 0:
                print("\n❌ STILL ZERO! Check debug output above.")
            else:
                print(f"\n✅ GOT NON-ZERO PREDICTION: {result.prediction}")

if __name__ == "__main__":
    test_with_debug_ml()
