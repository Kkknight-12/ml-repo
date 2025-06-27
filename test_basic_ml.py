#!/usr/bin/env python3
"""
Test Basic ML Functionality
===========================

Simple test to verify ML predictions are working
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import json

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def test_basic_ml():
    """Test basic ML prediction generation"""
    
    print("="*80)
    print("🧪 TESTING BASIC ML FUNCTIONALITY")
    print("="*80)
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    # Get data
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("❌ No cached data available")
        return
    
    print(f"\n✅ Data loaded: {len(df)} bars")
    print(f"   From: {df.index[0]}")
    print(f"   To: {df.index[-1]}")
    
    # Create processor
    config = TradingConfig()
    print(f"\n📋 Configuration:")
    print(f"   Max bars back: {config.max_bars_back}")
    print(f"   Neighbors count: {config.neighbors_count}")
    print(f"   Feature count: {config.feature_count}")
    
    processor = EnhancedBarProcessor(config, symbol, "5minute")
    
    # Process bars and check ML
    print(f"\n🔄 Processing bars...")
    
    predictions = []
    signals = []
    entries = []
    
    # Process enough bars to get past warmup
    bars_to_process = min(len(df), config.max_bars_back + 500)
    
    for i in range(bars_to_process):
        if i % 500 == 0:
            print(f"   Processed {i}/{bars_to_process} bars...")
        
        row = df.iloc[i]
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # After warmup
        if i >= config.max_bars_back:
            predictions.append(result.prediction)
            signals.append(result.signal)
            if result.start_long_trade or result.start_short_trade:
                entries.append({
                    'bar': i,
                    'type': 'long' if result.start_long_trade else 'short',
                    'prediction': result.prediction
                })
            
            # Show first few predictions
            if len(predictions) <= 5:
                print(f"   Bar {i}: ML prediction = {result.prediction:.2f}, signal = {result.signal}")
    
    # Analyze results
    print(f"\n📊 RESULTS:")
    print(f"Bars processed: {bars_to_process}")
    print(f"Bars after warmup: {len(predictions)}")
    
    if predictions:
        import numpy as np
        pred_array = np.array(predictions)
        non_zero = sum(1 for p in predictions if abs(p) > 0.1)
        
        print(f"\nML Predictions:")
        print(f"  Total: {len(predictions)}")
        print(f"  Non-zero: {non_zero} ({non_zero/len(predictions)*100:.1f}%)")
        print(f"  Range: [{pred_array.min():.1f}, {pred_array.max():.1f}]")
        print(f"  Mean: {pred_array.mean():.2f}")
        print(f"  Std: {pred_array.std():.2f}")
        
        # Check signals
        non_zero_signals = sum(1 for s in signals if s != 0)
        print(f"\nML Signals:")
        print(f"  Non-zero: {non_zero_signals} ({non_zero_signals/len(signals)*100:.1f}%)")
        
        print(f"\nEntries:")
        print(f"  Total: {len(entries)}")
        if entries:
            for i, entry in enumerate(entries[:5]):  # Show first 5
                print(f"  Entry {i+1}: Bar {entry['bar']}, {entry['type']}, ML={entry['prediction']:.2f}")
    
    # Check ML model state
    print(f"\n🔍 ML Model State:")
    print(f"  Training labels: {len(processor.ml_model.y_train_array)}")
    print(f"  Current neighbors: {len(processor.ml_model.predictions)}")
    print(f"  Max neighbors seen: {processor.ml_model.max_neighbors_seen}")
    
    if len(processor.ml_model.y_train_array) > 0:
        # Check label distribution
        labels = processor.ml_model.y_train_array[-100:]  # Last 100
        long_labels = sum(1 for l in labels if l > 0)
        short_labels = sum(1 for l in labels if l < 0)
        neutral_labels = sum(1 for l in labels if l == 0)
        
        print(f"\n  Recent labels (last 100):")
        print(f"    Long: {long_labels}")
        print(f"    Short: {short_labels}")
        print(f"    Neutral: {neutral_labels}")


if __name__ == "__main__":
    test_basic_ml()