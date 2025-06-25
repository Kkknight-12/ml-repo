#!/usr/bin/env python3
"""
Debug ML Zero Predictions
=========================

Systematically debug why ML predictions are returning 0.00
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def debug_ml_components():
    """Debug each component of the ML system"""
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=200)  # Extra days for warmup
    
    print("="*80)
    print("🔍 ML ZERO PREDICTION DEBUG")
    print("="*80)
    
    # Get data
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("❌ No cached data available")
        return
    
    # Ensure date index
    if 'date' in df.columns:
        df.set_index('date', inplace=True)
    
    print(f"✅ Data loaded: {len(df)} bars")
    print(f"   Date range: {df.index[0]} to {df.index[-1]}")
    
    # Initialize processor
    config = TradingConfig()
    processor = EnhancedBarProcessor(config, symbol, "5minute")
    
    # Process bars and collect detailed info
    debug_info = {
        'training_data_growth': [],
        'feature_validity': [],
        'predictions_made': [],
        'distances_calculated': []
    }
    
    print("\n📊 Processing bars...")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # Track key milestones
        if i == 10:  # Early check
            print(f"\n🔍 Bar 10 Check:")
            _check_ml_state(processor, i)
        
        if i == 100:  # Mid check
            print(f"\n🔍 Bar 100 Check:")
            _check_ml_state(processor, i)
            
        if i == 2000:  # Warmup complete
            print(f"\n🎯 WARMUP COMPLETE (Bar 2000):")
            _check_ml_state(processor, i)
            
        if i == 2010:  # Just after warmup
            print(f"\n📍 Post-Warmup Check (Bar 2010):")
            detailed_check = _check_ml_state(processor, i)
            
            # Deep dive into ML internals
            ml = processor.ml_model
            print(f"\n🔬 ML INTERNALS:")
            print(f"   Neighbors count setting: {config.neighbors_count}")
            print(f"   Max bars back: {config.max_bars_back}")
            print(f"   Feature count: {config.feature_count}")
            
            # Check feature arrays
            print(f"\n📈 FEATURE ARRAYS:")
            if hasattr(processor, 'feature_arrays'):
                fa = processor.feature_arrays
                print(f"   f1 array size: {len(fa.f1) if hasattr(fa, 'f1') else 'N/A'}")
                print(f"   f2 array size: {len(fa.f2) if hasattr(fa, 'f2') else 'N/A'}")
                print(f"   f3 array size: {len(fa.f3) if hasattr(fa, 'f3') else 'N/A'}")
                print(f"   f4 array size: {len(fa.f4) if hasattr(fa, 'f4') else 'N/A'}")
                print(f"   f5 array size: {len(fa.f5) if hasattr(fa, 'f5') else 'N/A'}")
                
                # Check last few feature values
                if hasattr(fa, 'f1') and len(fa.f1) > 0:
                    print(f"\n   Last 5 f1 values: {fa.f1[-5:]}")
                    
                    # Check for NaN
                    nan_count = sum(1 for v in fa.f1 if np.isnan(v))
                    print(f"   NaN count in f1: {nan_count}")
            
            # Check if prediction logic is running
            if hasattr(ml, 'size_loop'):
                print(f"\n🔄 PREDICTION LOOP:")
                print(f"   Size loop value: {ml.size_loop}")
            
            break
    
    print("\n" + "="*80)
    print("📋 DIAGNOSTIC SUMMARY")
    print("="*80)
    
    # Final check
    final_ml = processor.ml_model
    print(f"\nFinal ML State:")
    print(f"  Training data collected: {len(final_ml.y_train_array)}")
    print(f"  Predictions array: {len(final_ml.predictions)}")
    print(f"  Last prediction: {final_ml.prediction}")
    
    # Diagnosis
    if len(final_ml.y_train_array) < 2000:
        print("\n❌ PROBLEM: Not enough training data collected!")
        print("   This is why ML predictions are 0.00")
    elif len(final_ml.predictions) == 0:
        print("\n❌ PROBLEM: No neighbors being added to predictions array!")
        print("   Check distance calculations and i%4 logic")
    elif final_ml.prediction == 0.0:
        print("\n❌ PROBLEM: Predictions array sums to 0!")
        print("   Check if training labels are balanced (too many neutrals?)")
    else:
        print("\n✅ ML appears to be working")


def _check_ml_state(processor, bar_num):
    """Check ML model state at a specific bar"""
    ml = processor.ml_model
    
    print(f"  Bar index: {processor.bars.bar_index}")
    print(f"  Training data size: {len(ml.y_train_array)}")
    print(f"  Predictions array size: {len(ml.predictions)}")
    print(f"  Distances array size: {len(ml.distances)}")
    print(f"  Current prediction: {ml.prediction}")
    
    # Check training labels distribution
    if len(ml.y_train_array) > 0:
        labels = ml.y_train_array
        long_count = sum(1 for l in labels if l == 1)
        short_count = sum(1 for l in labels if l == -1)
        neutral_count = sum(1 for l in labels if l == 0)
        
        print(f"  Training labels: Long={long_count}, Short={short_count}, Neutral={neutral_count}")
        
        # Show last few labels
        if len(labels) >= 10:
            print(f"  Last 10 labels: {labels[-10:]}")
    
    return {
        'bar_index': processor.bars.bar_index,
        'training_size': len(ml.y_train_array),
        'predictions_size': len(ml.predictions),
        'current_prediction': ml.prediction
    }


if __name__ == "__main__":
    debug_ml_components()