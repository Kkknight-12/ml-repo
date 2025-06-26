#!/usr/bin/env python3
"""
Analyze ML Predictions
======================

Quick script to check ML prediction distribution
"""

import sys
import os
sys.path.append('.')

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
from data.cache_manager import MarketDataCache
from datetime import datetime, timedelta

# Set up access token
if os.path.exists('.kite_session.json'):
    import json
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token

# Get some data
cache = MarketDataCache()
symbol = 'RELIANCE'
end_date = datetime.now()
# Get more data to ensure we have enough bars after warmup
start_date = end_date - timedelta(days=180)  # Changed from 30 to 180 days
df = cache.get_cached_data(symbol, start_date, end_date, '5minute')

if df is not None and not df.empty:
    print(f'Data available: {len(df)} bars from {df.index[0]} to {df.index[-1]}')
    
    config = TradingConfig()
    print(f'Warmup period: {config.max_bars_back} bars')
    
    processor = EnhancedBarProcessor(config, symbol, '5minute')
    
    # Process all available bars
    bars_with_predictions = 0
    bars_with_zero = 0
    predictions = []
    bars_to_process = min(len(df), 3000)  # Process up to 3000 bars
    
    print(f'Processing {bars_to_process} bars...')
    
    bars_processed = 0
    for i, (idx, row) in enumerate(df.iterrows()):
        if i >= bars_to_process:
            break
            
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        bars_processed = i + 1
        
        # Show progress
        if i % 500 == 0:
            print(f'  Processed {i} bars...')
        
        if i >= config.max_bars_back:
            predictions.append(result.prediction)
            if abs(result.prediction) > 0.1:
                bars_with_predictions += 1
            else:
                bars_with_zero += 1
    
    print(f'\nML Prediction Analysis:')
    print(f'Total bars processed: {bars_processed}')
    print(f'Total bars after warmup: {bars_with_predictions + bars_with_zero}')
    
    if (bars_with_predictions + bars_with_zero) > 0:
        print(f'Bars with non-zero predictions: {bars_with_predictions} ({bars_with_predictions/(bars_with_predictions + bars_with_zero)*100:.1f}%)')
        print(f'Bars with zero predictions: {bars_with_zero} ({bars_with_zero/(bars_with_predictions + bars_with_zero)*100:.1f}%)')
    else:
        print('No bars after warmup period! Need more data.')
    
    # Check training data
    print(f'\nTraining data size: {len(processor.ml_model.y_train_array)}')
    non_zero_labels = sum(1 for y in processor.ml_model.y_train_array if y != 0)
    print(f'Non-zero training labels: {non_zero_labels} ({non_zero_labels/len(processor.ml_model.y_train_array)*100:.1f}%)')
    
    # Check k-NN neighbors
    print(f'\nk-NN Analysis:')
    print(f'Max neighbors seen: {processor.ml_model.max_neighbors_seen}')
    print(f'Current neighbors: {len(processor.ml_model.predictions)}')
    print(f'Current distances: {len(processor.ml_model.distances)}')
    
    # Check prediction distribution
    if predictions:
        import numpy as np
        pred_array = np.array(predictions)
        print(f'\nPrediction Distribution:')
        print(f'Min: {pred_array.min():.2f}')
        print(f'Max: {pred_array.max():.2f}')
        print(f'Mean: {pred_array.mean():.2f}')
        print(f'Std: {pred_array.std():.2f}')
        
        # Histogram
        hist, bins = np.histogram(pred_array, bins=20)
        print(f'\nPrediction Histogram:')
        for i in range(len(hist)):
            if hist[i] > 0:
                print(f'{bins[i]:6.1f} to {bins[i+1]:6.1f}: {"█" * min(hist[i], 50)} ({hist[i]})')
else:
    print('No data available')