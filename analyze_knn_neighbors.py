#!/usr/bin/env python3
"""
Analyze k-NN Neighbor Selection Process
=======================================

Deep dive into why ML predictions are returning 0.00
"""

import sys
import os
sys.path.append('.')

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
from data.cache_manager import MarketDataCache
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# Set up access token
if os.path.exists('.kite_session.json'):
    import json
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token

# Get data
cache = MarketDataCache()
symbol = 'RELIANCE'
end_date = datetime.now()
start_date = end_date - timedelta(days=180)
df = cache.get_cached_data(symbol, start_date, end_date, '5minute')

if df is not None and not df.empty:
    print(f'Data available: {len(df)} bars from {df.index[0]} to {df.index[-1]}')
    
    config = TradingConfig()
    print(f'Warmup period: {config.max_bars_back} bars')
    print(f'Neighbors count: {config.neighbors_count}')
    
    # Enable debug mode
    config.debug = True
    
    processor = EnhancedBarProcessor(config, symbol, '5minute')
    
    # Track statistics
    predictions_dist = []
    neighbor_counts = []
    distance_stats = []
    training_label_dist = []
    bars_with_zero_neighbors = 0
    
    # Process enough bars to get past warmup and analyze
    bars_to_process = min(len(df), config.max_bars_back + 500)
    
    print(f'\nProcessing {bars_to_process} bars...')
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if i >= bars_to_process:
            break
            
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # Show progress
        if i % 500 == 0 and i > 0:
            print(f'  Processed {i} bars...')
        
        # After warmup, collect detailed stats
        if i >= config.max_bars_back:
            ml_model = processor.ml_model
            
            # Store prediction
            predictions_dist.append(result.prediction)
            
            # Store neighbor count
            current_neighbors = len(ml_model.predictions)
            neighbor_counts.append(current_neighbors)
            
            if current_neighbors == 0:
                bars_with_zero_neighbors += 1
            
            # Store distance statistics if available
            if ml_model.distances:
                distance_stats.append({
                    'min': min(ml_model.distances),
                    'max': max(ml_model.distances),
                    'mean': np.mean(ml_model.distances)
                })
    
    # Analyze training labels
    if processor.ml_model.y_train_array:
        training_labels = processor.ml_model.y_train_array
        print(f'\n📊 TRAINING LABEL ANALYSIS:')
        print(f'Total training labels: {len(training_labels)}')
        
        # Count label distribution
        long_labels = sum(1 for y in training_labels if y > 0)
        short_labels = sum(1 for y in training_labels if y < 0)
        neutral_labels = sum(1 for y in training_labels if y == 0)
        
        print(f'Long labels (1): {long_labels} ({long_labels/len(training_labels)*100:.1f}%)')
        print(f'Short labels (-1): {short_labels} ({short_labels/len(training_labels)*100:.1f}%)')
        print(f'Neutral labels (0): {neutral_labels} ({neutral_labels/len(training_labels)*100:.1f}%)')
        
        # Check recent vs old labels
        recent_100 = training_labels[-100:] if len(training_labels) >= 100 else training_labels
        recent_long = sum(1 for y in recent_100 if y > 0)
        recent_short = sum(1 for y in recent_100 if y < 0)
        
        print(f'\nRecent 100 bars:')
        print(f'Long: {recent_long}, Short: {recent_short}, Neutral: {100-recent_long-recent_short}')
    
    # Analyze predictions
    if predictions_dist:
        print(f'\n🔮 ML PREDICTION ANALYSIS:')
        print(f'Total predictions: {len(predictions_dist)}')
        
        # Count zero predictions
        zero_preds = sum(1 for p in predictions_dist if abs(p) < 0.1)
        non_zero_preds = len(predictions_dist) - zero_preds
        
        print(f'Zero predictions: {zero_preds} ({zero_preds/len(predictions_dist)*100:.1f}%)')
        print(f'Non-zero predictions: {non_zero_preds} ({non_zero_preds/len(predictions_dist)*100:.1f}%)')
        
        # Prediction statistics for non-zero
        non_zero_values = [p for p in predictions_dist if abs(p) >= 0.1]
        if non_zero_values:
            print(f'\nNon-zero prediction stats:')
            print(f'Min: {min(non_zero_values):.2f}')
            print(f'Max: {max(non_zero_values):.2f}')
            print(f'Mean: {np.mean(non_zero_values):.2f}')
            print(f'Std: {np.std(non_zero_values):.2f}')
    
    # Analyze neighbor counts
    if neighbor_counts:
        print(f'\n👥 k-NN NEIGHBOR ANALYSIS:')
        print(f'Bars with 0 neighbors: {bars_with_zero_neighbors} ({bars_with_zero_neighbors/len(neighbor_counts)*100:.1f}%)')
        
        # Neighbor count distribution
        neighbor_hist = {}
        for count in neighbor_counts:
            neighbor_hist[count] = neighbor_hist.get(count, 0) + 1
        
        print(f'\nNeighbor count distribution:')
        for count in sorted(neighbor_hist.keys()):
            pct = neighbor_hist[count] / len(neighbor_counts) * 100
            print(f'{count} neighbors: {neighbor_hist[count]} bars ({pct:.1f}%)')
        
        print(f'\nAverage neighbors: {np.mean(neighbor_counts):.2f}')
        print(f'Max neighbors seen: {max(neighbor_counts)}')
    
    # Analyze distances
    if distance_stats:
        print(f'\n📏 DISTANCE ANALYSIS:')
        all_mins = [d['min'] for d in distance_stats]
        all_maxs = [d['max'] for d in distance_stats]
        all_means = [d['mean'] for d in distance_stats]
        
        print(f'Distance ranges:')
        print(f'Min distances: {np.min(all_mins):.4f} to {np.max(all_mins):.4f}')
        print(f'Max distances: {np.min(all_maxs):.4f} to {np.max(all_maxs):.4f}')
        print(f'Mean distance: {np.mean(all_means):.4f}')
    
    # Check for specific issues
    print(f'\n⚠️  POTENTIAL ISSUES:')
    
    if neutral_labels > (long_labels + short_labels) * 2:
        print('❌ Too many neutral labels - market may be ranging')
        print('   → This causes k-NN to return 0 when neighbors have mixed signals')
    
    if bars_with_zero_neighbors > len(neighbor_counts) * 0.1:
        print('❌ Many bars have 0 neighbors - distance threshold may be too strict')
        print('   → Consider adjusting distance calculation or threshold logic')
    
    if np.mean(neighbor_counts) < config.neighbors_count * 0.5:
        print(f'❌ Average neighbors ({np.mean(neighbor_counts):.1f}) is less than half of target ({config.neighbors_count})')
        print('   → k-NN is not finding enough similar patterns')
    
    # Save detailed analysis
    analysis_df = pd.DataFrame({
        'prediction': predictions_dist,
        'neighbor_count': neighbor_counts,
        'distance_min': [d['min'] if i < len(distance_stats) else np.nan for i, d in enumerate(distance_stats)],
        'distance_max': [d['max'] if i < len(distance_stats) else np.nan for i, d in enumerate(distance_stats)],
        'distance_mean': [d['mean'] if i < len(distance_stats) else np.nan for i, d in enumerate(distance_stats)]
    })
    
    analysis_df.to_csv('knn_neighbor_analysis.csv', index=False)
    print(f'\n💾 Detailed analysis saved to knn_neighbor_analysis.csv')
    
else:
    print('No data available')