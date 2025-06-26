#!/usr/bin/env python3
"""
Analyze i%4 Filter Impact
=========================

Understand how the i%4 != 0 condition affects k-NN neighbor selection
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
    
    # Process to warmup
    print(f'Processing to bar {config.max_bars_back + 1}...')
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if i > config.max_bars_back:
            break
            
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
    
    # Now analyze the i%4 impact
    print("\n" + "="*60)
    print("📊 ANALYZING i%4 FILTER IMPACT")
    print("="*60)
    
    # Get feature arrays and training labels
    feature_arrays = processor.feature_arrays
    arrays = [feature_arrays.f1, feature_arrays.f2, feature_arrays.f3, 
             feature_arrays.f4, feature_arrays.f5]
    training_labels = processor.ml_model.y_train_array
    
    print(f"\nTraining data size: {len(training_labels)}")
    
    # Simulate k-NN search without i%4 filter
    print("\n🔬 Simulating k-NN search WITHOUT i%4 filter:")
    
    # Get current features
    current_features = processor._calculate_features_stateful(
        df.iloc[config.max_bars_back]['high'],
        df.iloc[config.max_bars_back]['low'],
        df.iloc[config.max_bars_back]['close']
    )
    
    # Calculate distances for first 100 historical points
    distances_all = []
    distances_filtered = []
    labels_all = []
    labels_filtered = []
    
    size_loop = min(100, len(arrays[0]) - 1)
    
    for i in range(size_loop + 1):
        # Calculate distance
        d = 0.0
        for j in range(config.feature_count):
            if i < len(arrays[j]):
                hist_value = arrays[j][-(i+1)]
                curr_value = list(current_features.values())[j]
                d += abs(curr_value - hist_value)
        
        # Get label
        if i < len(training_labels):
            label = training_labels[-(i+1)]
            
            # Store for all
            distances_all.append(d)
            labels_all.append(label)
            
            # Store for filtered (i%4 != 0)
            if i % 4 != 0:
                distances_filtered.append(d)
                labels_filtered.append(label)
    
    # Analyze the difference
    print(f"\nTotal historical points checked: {size_loop + 1}")
    print(f"Points that pass i%4 != 0: {len(distances_filtered)} ({len(distances_filtered)/(size_loop+1)*100:.1f}%)")
    print(f"Points rejected by i%4 == 0: {len(distances_all) - len(distances_filtered)} ({(len(distances_all) - len(distances_filtered))/(size_loop+1)*100:.1f}%)")
    
    # Compare distance statistics
    print(f"\n📏 Distance Statistics:")
    print(f"ALL points - Min: {min(distances_all):.4f}, Max: {max(distances_all):.4f}, Mean: {np.mean(distances_all):.4f}")
    if distances_filtered:
        print(f"FILTERED points - Min: {min(distances_filtered):.4f}, Max: {max(distances_filtered):.4f}, Mean: {np.mean(distances_filtered):.4f}")
    
    # Check if we're missing good neighbors
    print(f"\n🎯 Quality of Rejected Points (i%4 == 0):")
    
    rejected_indices = [i for i in range(len(distances_all)) if i % 4 == 0]
    rejected_distances = [distances_all[i] for i in rejected_indices if i < len(distances_all)]
    rejected_labels = [labels_all[i] for i in rejected_indices if i < len(labels_all)]
    
    if rejected_distances:
        # Find how many rejected points had better distances than accepted ones
        if distances_filtered:
            best_filtered_distance = min(distances_filtered)
            better_rejected = sum(1 for d in rejected_distances if d < best_filtered_distance)
            print(f"Rejected points with better distance than best filtered: {better_rejected}")
        
        # Check label distribution of rejected points
        rejected_long = sum(1 for l in rejected_labels if l > 0)
        rejected_short = sum(1 for l in rejected_labels if l < 0)
        rejected_neutral = sum(1 for l in rejected_labels if l == 0)
        
        print(f"\nRejected labels distribution:")
        print(f"  Long: {rejected_long} ({rejected_long/len(rejected_labels)*100:.1f}%)")
        print(f"  Short: {rejected_short} ({rejected_short/len(rejected_labels)*100:.1f}%)")
        print(f"  Neutral: {rejected_neutral} ({rejected_neutral/len(rejected_labels)*100:.1f}%)")
    
    # Simulate predictions with and without filter
    print(f"\n🔮 Prediction Impact:")
    
    # Get 8 best neighbors without filter
    all_sorted = sorted(zip(distances_all, labels_all), key=lambda x: x[0])[:8]
    pred_without_filter = sum(label for _, label in all_sorted)
    
    # Get 8 best neighbors with filter
    filtered_sorted = sorted(zip(distances_filtered, labels_filtered), key=lambda x: x[0])[:8]
    pred_with_filter = sum(label for _, label in filtered_sorted) if len(filtered_sorted) >= 8 else 0
    
    print(f"Prediction WITHOUT i%4 filter: {pred_without_filter}")
    print(f"Prediction WITH i%4 filter: {pred_with_filter}")
    print(f"Difference: {abs(pred_without_filter - pred_with_filter)}")
    
    # Why does Pine Script use i%4?
    print(f"\n💡 Why i%4 != 0?")
    print("The i%4 != 0 condition in Pine Script:")
    print("- Reduces computational load by 25%")
    print("- Avoids using every 4th historical bar")
    print("- May prevent overfitting to very recent patterns")
    print("- But can miss good neighbors with low distances!")
    
else:
    print("No data available")