#!/usr/bin/env python3
"""
Diagnose ML Prediction Issues
=============================

Specifically focuses on why ML predictions are 0.00 even after warmup period.
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


def diagnose_ml_predictions():
    """Diagnose why ML predictions are returning 0.00"""
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print("="*80)
    print("🧠 ML PREDICTION DIAGNOSTIC")
    print("="*80)
    
    # Get data
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No cached data available")
        return
    
    print(f"Total data points: {len(df)}")
    if isinstance(df.index[0], pd.Timestamp):
        print(f"Date range: {df.index[0]} to {df.index[-1]}")
    else:
        print(f"Index type: {type(df.index[0])}, need to fix data format")
    
    # Initialize processor
    config = TradingConfig()
    processor = EnhancedBarProcessor(config, symbol, "5minute")
    
    # Track ML predictions
    ml_predictions = []
    bars_processed = 0
    first_non_zero = None
    
    # Process ALL bars
    for idx, row in df.iterrows():
        bars_processed += 1
        
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        if result:
            ml_predictions.append({
                'bar': bars_processed,
                'date': idx,
                'prediction': result.prediction,
                'signal': result.signal,
                'filters': result.filter_states
            })
            
            # Track first non-zero prediction
            if result.prediction != 0.0 and first_non_zero is None:
                first_non_zero = bars_processed
                print(f"\n✅ FIRST NON-ZERO PREDICTION at bar {bars_processed}:")
                print(f"   Date: {idx}")
                print(f"   Prediction: {result.prediction:.4f}")
                print(f"   Signal: {result.signal}")
                print(f"   Filters: {result.filter_states}")
        
        # Show warmup period boundary
        if bars_processed == 2000:
            print(f"\n📍 WARMUP PERIOD COMPLETE at bar 2000")
            print(f"   Date: {idx}")
            if result:
                print(f"   Prediction: {result.prediction:.4f}")
                print(f"   Should start getting non-zero predictions now...")
        
        # Show some bars right after warmup
        if 2000 <= bars_processed <= 2010:
            if result:
                print(f"\n   Bar {bars_processed}: prediction={result.prediction:.4f}")
    
    # Analyze predictions
    print(f"\n📊 ML PREDICTION SUMMARY:")
    print(f"Total bars processed: {bars_processed}")
    print(f"Warmup period: 2000 bars")
    print(f"Post-warmup bars: {bars_processed - 2000}")
    
    if first_non_zero:
        print(f"\n✅ First non-zero prediction: bar {first_non_zero}")
        print(f"   Delay after warmup: {first_non_zero - 2000} bars")
    else:
        print(f"\n❌ NO NON-ZERO PREDICTIONS FOUND!")
    
    # Count non-zero predictions
    non_zero_count = sum(1 for p in ml_predictions if p['prediction'] != 0.0)
    print(f"\nNon-zero predictions: {non_zero_count} / {len(ml_predictions)}")
    
    # Show prediction distribution
    predictions_array = [p['prediction'] for p in ml_predictions]
    if any(p != 0 for p in predictions_array):
        print(f"\nPrediction statistics:")
        print(f"   Min: {min(predictions_array):.4f}")
        print(f"   Max: {max(predictions_array):.4f}")
        print(f"   Mean: {np.mean(predictions_array):.4f}")
        print(f"   Std: {np.std(predictions_array):.4f}")
    
    # Check ML model internals
    if hasattr(processor, 'ml_model'):
        ml = processor.ml_model
        print(f"\n🔧 ML MODEL INTERNALS:")
        print(f"   Training data size: {len(ml.y_train_array) if hasattr(ml, 'y_train_array') else 'N/A'}")
        print(f"   Predictions array: {len(ml.predictions) if hasattr(ml, 'predictions') else 'N/A'}")
        print(f"   Distances array: {len(ml.distances) if hasattr(ml, 'distances') else 'N/A'}")
        print(f"   Last valid prediction: {getattr(ml, 'last_valid_prediction', 'N/A')}")
        print(f"   Max neighbors seen: {getattr(ml, 'max_neighbors_seen', 'N/A')}")
    
    # Diagnose common issues
    print(f"\n🚨 DIAGNOSTIC RESULTS:")
    
    if bars_processed < 2000:
        print("❌ INSUFFICIENT DATA: Need at least 2000 bars for warmup")
    elif non_zero_count == 0:
        print("❌ ML MODEL NOT GENERATING PREDICTIONS")
        print("   Possible causes:")
        print("   1. Training data not being collected properly")
        print("   2. Feature calculation errors")
        print("   3. Distance calculation always returning same value")
        print("   4. Neighbors not being added to predictions array")
    elif non_zero_count < (bars_processed - 2000) * 0.1:
        print("⚠️ VERY FEW PREDICTIONS")
        print("   ML model is too selective or filters are too restrictive")
    else:
        print("✅ ML model appears to be working")
    
    # Save detailed log
    if ml_predictions:
        df_predictions = pd.DataFrame(ml_predictions)
        df_predictions.to_csv('ml_predictions_diagnostic.csv', index=False)
        print(f"\n💾 Detailed predictions saved to ml_predictions_diagnostic.csv")


if __name__ == "__main__":
    diagnose_ml_predictions()