#!/usr/bin/env python3
"""
Analyze Feature Arrays
======================

Check if feature arrays are being populated correctly and 
if feature values are in reasonable ranges.
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
start_date = end_date - timedelta(days=90)
df = cache.get_cached_data(symbol, start_date, end_date, '5minute')

if df is not None and not df.empty:
    print(f'Data available: {len(df)} bars')
    
    config = TradingConfig()
    processor = EnhancedBarProcessor(config, symbol, '5minute')
    
    # Feature names from settings
    feature_names = [
        'RSI (f1)', 'WT (f2)', 'CCI (f3)', 'ADX (f4)', 'RSI (f5)'
    ]
    
    # Process enough bars to analyze
    bars_to_process = min(len(df), config.max_bars_back + 100)
    print(f'Processing {bars_to_process} bars...')
    
    # Track feature statistics
    feature_snapshots = []
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if i >= bars_to_process:
            break
            
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # After warmup, capture feature array state
        if i == config.max_bars_back:
            print(f'\n📊 FEATURE ARRAYS AT BAR {i} (First ML prediction):')
            print('='*60)
            
            # Check each feature array
            feature_arrays = processor.feature_arrays
            arrays = [feature_arrays.f1, feature_arrays.f2, feature_arrays.f3, 
                     feature_arrays.f4, feature_arrays.f5]
            
            for j, (name, arr) in enumerate(zip(feature_names[:config.feature_count], arrays[:config.feature_count])):
                print(f'\n{name}:')
                print(f'  Array length: {len(arr)}')
                if len(arr) > 0:
                    print(f'  Min: {min(arr):.4f}')
                    print(f'  Max: {max(arr):.4f}')
                    print(f'  Mean: {np.mean(arr):.4f}')
                    print(f'  Std: {np.std(arr):.4f}')
                    print(f'  Last 5 values: {[f"{v:.2f}" for v in arr[-5:]]}')
                    
                    # Check for issues
                    if np.std(arr) < 0.01:
                        print('  ⚠️  WARNING: Very low variance!')
                    if all(v == arr[0] for v in arr):
                        print('  ❌ ERROR: All values are identical!')
        
        # Capture snapshots periodically
        if i >= config.max_bars_back and i % 20 == 0:
            snapshot = {
                'bar': i,
                'prediction': result.prediction,
                'neighbors': len(processor.ml_model.predictions)
            }
            
            # Add feature stats
            feature_arrays = processor.feature_arrays
            arrays = [feature_arrays.f1, feature_arrays.f2, feature_arrays.f3, 
                     feature_arrays.f4, feature_arrays.f5]
            
            for j, (name, arr) in enumerate(zip(feature_names[:config.feature_count], arrays[:config.feature_count])):
                if len(arr) > 0:
                    snapshot[f'{name}_mean'] = np.mean(arr)
                    snapshot[f'{name}_std'] = np.std(arr)
                    snapshot[f'{name}_last'] = arr[-1]
            
            feature_snapshots.append(snapshot)
    
    # Analyze patterns
    if feature_snapshots:
        print(f'\n📈 FEATURE EVOLUTION OVER TIME:')
        print('='*60)
        
        # Convert to DataFrame for analysis
        snapshots_df = pd.DataFrame(feature_snapshots)
        
        # Check if features are updating
        for name in feature_names[:config.feature_count]:
            mean_col = f'{name}_mean'
            if mean_col in snapshots_df.columns:
                mean_changes = snapshots_df[mean_col].diff().abs().sum()
                if mean_changes < 0.01:
                    print(f'❌ {name} mean is not changing over time!')
                else:
                    print(f'✅ {name} mean is updating properly')
        
        # Check correlation with predictions
        print(f'\n🔗 FEATURE-PREDICTION CORRELATION:')
        
        # Only check non-zero predictions
        non_zero_df = snapshots_df[snapshots_df['prediction'].abs() > 0.1]
        if len(non_zero_df) > 2:
            for name in feature_names[:config.feature_count]:
                last_col = f'{name}_last'
                if last_col in non_zero_df.columns:
                    corr = non_zero_df['prediction'].corr(non_zero_df[last_col])
                    print(f'{name}: {corr:.3f}')
        else:
            print('Not enough non-zero predictions for correlation analysis')
        
        # Save snapshots
        snapshots_df.to_csv('feature_array_snapshots.csv', index=False)
        print(f'\n💾 Feature snapshots saved to feature_array_snapshots.csv')
    
    # Final analysis
    print(f'\n🔍 FINAL ANALYSIS:')
    
    # Check array initialization
    print(f'\nFeature array sizes:')
    feature_arrays = processor.feature_arrays
    arrays = [feature_arrays.f1, feature_arrays.f2, feature_arrays.f3, 
             feature_arrays.f4, feature_arrays.f5]
    
    for j in range(config.feature_count):
        if j < len(arrays):
            print(f'  Feature {j+1}: {len(arrays[j])} values')
    
    # Check if arrays are properly bounded
    expected_size = config.max_bars_back
    feature_arrays = processor.feature_arrays
    arrays = [feature_arrays.f1, feature_arrays.f2, feature_arrays.f3, 
             feature_arrays.f4, feature_arrays.f5]
    actual_sizes = [len(arr) for arr in arrays[:config.feature_count]]
    
    if actual_sizes and max(actual_sizes) > expected_size * 1.1:
        print(f'\n⚠️  WARNING: Feature arrays may be growing too large!')
        print(f'Expected max size: ~{expected_size}')
        print(f'Actual max size: {max(actual_sizes)}')
    
    # Check for NaN or infinite values
    has_issues = False
    feature_arrays = processor.feature_arrays
    arrays = [feature_arrays.f1, feature_arrays.f2, feature_arrays.f3, 
             feature_arrays.f4, feature_arrays.f5]
    
    for j, arr in enumerate(arrays[:config.feature_count]):
        if arr:
            arr_np = np.array(arr)
            if np.any(np.isnan(arr_np)):
                print(f'\n❌ Feature {j+1} contains NaN values!')
                has_issues = True
            if np.any(np.isinf(arr_np)):
                print(f'\n❌ Feature {j+1} contains infinite values!')
                has_issues = True
    
    if not has_issues:
        print('\n✅ No NaN or infinite values detected in features')
    
else:
    print('No data available')