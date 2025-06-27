#!/usr/bin/env python3
"""
Diagnose ML Issues in 5-Minute Configuration
============================================

Check if ML predictions are working correctly
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import pandas as pd
import json
import numpy as np

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.fivemin_optimized_settings import FIVEMIN_BALANCED
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def diagnose_ml_predictions():
    """Check ML prediction quality"""
    
    print("="*80)
    print("🔍 DIAGNOSING ML PREDICTIONS FOR 5-MINUTE CONFIG")
    print("="*80)
    
    # Get data
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # Just 30 days for diagnosis
    
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return
    
    print(f"\n📊 Analyzing {len(df)} bars")
    
    # Create processor
    config = FIVEMIN_BALANCED
    processor = EnhancedBarProcessor(config, symbol, "5minute")
    
    # Track ML behavior
    ml_predictions = []
    ml_signals = []
    filter_results = []
    entries = []
    
    print("\n🔄 Processing bars...")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        if i < config.max_bars_back:
            continue
        
        # Track ML prediction
        ml_predictions.append(result.prediction)
        ml_signals.append(result.signal)
        
        # Track filter states
        filter_results.append({
            'bar': i,
            'signal': result.signal,
            'prediction': result.prediction,
            'volatility': result.filter_volatility,
            'regime': result.filter_regime,
            'adx': result.filter_adx,
            'all_pass': result.filter_all
        })
        
        # Track entries
        if result.start_long_trade or result.start_short_trade:
            entries.append({
                'bar': i,
                'type': 'long' if result.start_long_trade else 'short',
                'prediction': result.prediction,
                'filters': result.filter_states.copy()
            })
    
    # Analyze ML predictions
    print(f"\n📊 ML PREDICTION ANALYSIS:")
    print("="*60)
    
    pred_array = np.array(ml_predictions)
    non_zero = np.sum(np.abs(pred_array) > 0.01)
    
    print(f"\n1. PREDICTION STATISTICS:")
    print(f"   Total predictions: {len(ml_predictions)}")
    print(f"   Non-zero predictions: {non_zero} ({non_zero/len(ml_predictions)*100:.1f}%)")
    print(f"   Prediction range: [{pred_array.min():.2f}, {pred_array.max():.2f}]")
    print(f"   Mean prediction: {pred_array.mean():.4f}")
    print(f"   Std deviation: {pred_array.std():.4f}")
    
    # Check if predictions are mostly 0
    if non_zero / len(ml_predictions) < 0.5:
        print(f"\n   ⚠️ WARNING: {100 - non_zero/len(ml_predictions)*100:.1f}% of predictions are zero!")
        print("   This indicates the ML model may not be working correctly")
    
    # Analyze signals
    signal_array = np.array(ml_signals)
    long_signals = np.sum(signal_array == 1)
    short_signals = np.sum(signal_array == -1)
    neutral_signals = np.sum(signal_array == 0)
    
    print(f"\n2. ML SIGNAL DISTRIBUTION:")
    print(f"   Long signals: {long_signals} ({long_signals/len(ml_signals)*100:.1f}%)")
    print(f"   Short signals: {short_signals} ({short_signals/len(ml_signals)*100:.1f}%)")
    print(f"   Neutral signals: {neutral_signals} ({neutral_signals/len(ml_signals)*100:.1f}%)")
    
    # Analyze filters
    filter_df = pd.DataFrame(filter_results)
    
    print(f"\n3. FILTER ANALYSIS:")
    print(f"   Total bars with signals: {len(filter_df[filter_df['signal'] != 0])}")
    
    for filter_name in ['volatility', 'regime', 'adx']:
        pass_rate = filter_df[filter_name].mean() * 100
        print(f"   {filter_name.capitalize()} filter pass rate: {pass_rate:.1f}%")
    
    # Filter funnel
    signals_df = filter_df[filter_df['signal'] != 0]
    if len(signals_df) > 0:
        print(f"\n4. SIGNAL FILTERING FUNNEL:")
        print(f"   ML signals (non-zero): {len(signals_df)}")
        
        # Progressive filtering
        after_volatility = signals_df[signals_df['volatility'] == True]
        print(f"   After volatility filter: {len(after_volatility)} ({len(after_volatility)/len(signals_df)*100:.1f}%)")
        
        after_regime = after_volatility[after_volatility['regime'] == True]
        print(f"   After regime filter: {len(after_regime)} ({len(after_regime)/len(signals_df)*100:.1f}%)")
        
        after_all = signals_df[signals_df['all_pass'] == True]
        print(f"   After all filters: {len(after_all)} ({len(after_all)/len(signals_df)*100:.1f}%)")
    
    # Entry analysis
    print(f"\n5. ENTRY GENERATION:")
    print(f"   Total entries: {len(entries)}")
    if entries:
        print(f"   First 5 entries:")
        for i, entry in enumerate(entries[:5]):
            print(f"   {i+1}. Bar {entry['bar']}: {entry['type']}, ML={entry['prediction']:.2f}")
    
    # Check ML model internals
    print(f"\n6. ML MODEL STATE:")
    print(f"   Training labels: {len(processor.ml_model.y_train_array)}")
    print(f"   Feature arrays populated: {len(processor.feature_arrays.f1)}")
    print(f"   Neighbors seen: {processor.ml_model.max_neighbors_seen}")
    
    # Training label distribution
    if len(processor.ml_model.y_train_array) > 0:
        labels = processor.ml_model.y_train_array[-100:]  # Last 100
        long_labels = sum(1 for l in labels if l > 0)
        short_labels = sum(1 for l in labels if l < 0)
        neutral_labels = sum(1 for l in labels if l == 0)
        
        print(f"\n   Recent training labels (last 100):")
        print(f"   Long: {long_labels}")
        print(f"   Short: {short_labels}")
        print(f"   Neutral: {neutral_labels}")
    
    # Recommendations
    print(f"\n\n💡 DIAGNOSIS:")
    print("="*60)
    
    if non_zero / len(ml_predictions) < 0.8:
        print("❌ ML predictions are mostly zero - CHECK FEATURE ARRAY TIMING")
        print("   Verify feature arrays are updated AFTER predictions")
    
    if len(entries) < len(signals_df) * 0.01:
        print("❌ Entry conditions are too restrictive")
        print("   Only {:.1f}% of ML signals become entries".format(
            len(entries) / len(signals_df) * 100 if len(signals_df) > 0 else 0
        ))
    
    if filter_df['volatility'].mean() < 0.5:
        print("❌ Volatility filter is too restrictive")
        print("   Consider disabling or adjusting threshold")
    
    if filter_df['regime'].mean() < 0.5:
        print("❌ Regime filter is too restrictive")
        print("   Consider adjusting regime threshold")
    
    # Save detailed results
    filter_df.to_csv('5min_ml_diagnosis.csv', index=False)
    print(f"\n💾 Detailed results saved to 5min_ml_diagnosis.csv")


if __name__ == "__main__":
    diagnose_ml_predictions()