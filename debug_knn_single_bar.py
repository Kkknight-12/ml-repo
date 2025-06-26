#!/usr/bin/env python3
"""
Debug k-NN for a Single Bar
===========================

Trace through the k-NN algorithm for one specific bar to understand
why predictions might be 0.
"""

import sys
import os
sys.path.append('.')

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
from data.cache_manager import MarketDataCache
from datetime import datetime, timedelta
import numpy as np

# Set up access token
if os.path.exists('.kite_session.json'):
    import json
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token

def trace_knn_prediction(processor, feature_series, feature_arrays, bar_index):
    """Trace through k-NN prediction step by step"""
    
    ml_model = processor.ml_model
    settings = processor.settings
    
    print(f'\n🔍 TRACING k-NN PREDICTION FOR BAR {bar_index}')
    print('='*60)
    
    # Check training data
    print(f'\n📚 Training Data:')
    print(f'Total training labels: {len(ml_model.y_train_array)}')
    if ml_model.y_train_array:
        recent_labels = ml_model.y_train_array[-20:]
        print(f'Last 20 labels: {recent_labels}')
        non_zero = sum(1 for y in recent_labels if y != 0)
        print(f'Non-zero in last 20: {non_zero}')
    
    # Current features
    print(f'\n📊 Current Features:')
    for i, (name, value) in enumerate(feature_series.items()):
        print(f'  {name}: {value:.4f}')
    
    # Initialize tracking
    neighbors_found = []
    distances_calculated = []
    
    # Size of historical data to search
    size = min(settings.max_bars_back - 1, len(feature_arrays[0]) - 1)
    size_loop = min(settings.last_bar_index - bar_index - 1, size)
    
    print(f'\n🔄 Search Parameters:')
    print(f'Historical bars to search: {size_loop + 1}')
    print(f'Target neighbors: {settings.neighbors_count}')
    
    # Track algorithm state
    last_distance = -1.0
    current_predictions = []
    current_distances = []
    
    print(f'\n🏃 k-NN Search Process:')
    print('-'*60)
    
    # Search through historical bars
    for i in range(min(size_loop + 1, 50)):  # Limit to first 50 for readability
        # Calculate distance
        d = 0.0
        feature_details = []
        
        for j in range(settings.feature_count):
            if i < len(feature_arrays[j]):
                hist_value = feature_arrays[j][-(i+1)]  # Look back i bars
                curr_value = feature_series[list(feature_series.keys())[j]]
                diff = curr_value - hist_value
                d += abs(diff)
                feature_details.append(f'{list(feature_series.keys())[j]}: {abs(diff):.4f}')
        
        distances_calculated.append(d)
        
        # Check if this neighbor qualifies
        qualifies = d >= last_distance and i % 4 != 0
        
        print(f'\ni={i}: distance={d:.4f}, last_dist={last_distance:.4f}, i%4={i%4}')
        print(f'  Qualifies: {qualifies} (d >= last_dist: {d >= last_distance}, i%4 != 0: {i % 4 != 0})')
        
        if i < 5:  # Show feature breakdown for first few
            print(f'  Distance breakdown: {", ".join(feature_details[:3])}...')
        
        if qualifies:
            # Get training label
            if i < len(ml_model.y_train_array):
                label_idx = -(i + 1)
                label = float(ml_model.y_train_array[label_idx])
                current_predictions.append(label)
                current_distances.append(d)
                neighbors_found.append({
                    'i': i,
                    'distance': d,
                    'label': label,
                    'bar_ago': i
                })
                
                print(f'  ✅ NEIGHBOR ADDED: label={label}, total_neighbors={len(current_predictions)}')
                
                # Update last_distance
                last_distance = d
                
                # Check if we need to maintain k neighbors
                if len(current_predictions) > settings.neighbors_count:
                    # Update threshold
                    k_75 = round(settings.neighbors_count * 3 / 4)
                    if k_75 < len(current_distances):
                        last_distance = current_distances[k_75]
                        print(f'  📏 Updated distance threshold to {last_distance:.4f} (75th percentile)')
                    
                    # Remove oldest
                    removed_pred = current_predictions.pop(0)
                    removed_dist = current_distances.pop(0)
                    print(f'  🗑️  Removed oldest: pred={removed_pred}, dist={removed_dist:.4f}')
    
    # Final prediction
    final_prediction = sum(current_predictions) if current_predictions else 0.0
    
    print(f'\n📈 FINAL RESULTS:')
    print(f'Neighbors found: {len(neighbors_found)}')
    print(f'Final neighbors used: {len(current_predictions)}')
    print(f'Predictions array: {current_predictions}')
    print(f'Sum of predictions: {final_prediction}')
    print(f'Final ML prediction: {final_prediction:.2f}')
    
    # Analysis
    print(f'\n💡 ANALYSIS:')
    if len(current_predictions) == 0:
        print('❌ No neighbors found! Possible reasons:')
        print('   - All distances were decreasing (d < last_distance)')
        print('   - All qualifying bars had i%4 == 0')
        print('   - Not enough training data')
    elif abs(final_prediction) < 0.1:
        print('⚠️  Prediction is zero! Possible reasons:')
        if current_predictions:
            long_count = sum(1 for p in current_predictions if p > 0)
            short_count = sum(1 for p in current_predictions if p < 0)
            neutral_count = sum(1 for p in current_predictions if p == 0)
            print(f'   - Mixed signals: {long_count} long, {short_count} short, {neutral_count} neutral')
            if neutral_count > 0:
                print(f'   - {neutral_count} neutral neighbors contributing 0')
    
    return final_prediction, neighbors_found

# Main execution
if __name__ == "__main__":
    # Get data
    cache = MarketDataCache()
    symbol = 'RELIANCE'
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    df = cache.get_cached_data(symbol, start_date, end_date, '5minute')
    
    if df is not None and not df.empty:
        print(f'Data available: {len(df)} bars')
        
        config = TradingConfig()
        processor = EnhancedBarProcessor(config, symbol, '5minute')
        
        # Process bars until we get past warmup
        print(f'Processing {config.max_bars_back + 10} bars...')
        
        for i, (idx, row) in enumerate(df.iterrows()):
            if i >= config.max_bars_back + 10:
                break
                
            result = processor.process_bar(
                row['open'], row['high'], row['low'], 
                row['close'], row['volume']
            )
            
            # When we get to first bar after warmup
            if i == config.max_bars_back:
                if abs(result.prediction) < 0.1:
                    print(f'\n🎯 Found bar with 0 prediction at index {i}!')
                else:
                    print(f'\n✅ First bar after warmup has non-zero prediction: {result.prediction:.2f}')
                    print('Processing more bars to find one with 0 prediction...')
            
            # Check subsequent bars
            if i > config.max_bars_back and abs(result.prediction) < 0.1:
                print(f'\n🎯 Found bar with 0 prediction at index {i}!')
                
                # Get current state
                feature_series = processor._calculate_features_stateful(
                    row['high'], row['low'], row['close']
                )
                
                # Trace the prediction
                pred, neighbors = trace_knn_prediction(
                    processor, feature_series, processor.feature_arrays, i
                )
                
                break
    else:
        print('No data available')