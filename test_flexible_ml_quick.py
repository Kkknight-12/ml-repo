"""
Quick Test of Flexible ML System
=================================

Tests the flexible ML system with relaxed settings to verify
it's working and generating signals.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from data.smart_data_manager import SmartDataManager
from scanner.flexible_bar_processor import FlexibleBarProcessor
from config.settings import TradingConfig
from config.relaxed_settings import RELIANCE_CONFIG


def test_flexible_ml(use_flexible: bool = True):
    """Quick test of flexible ML with relaxed settings"""
    
    print(f"\n{'='*60}")
    print(f"TESTING {'FLEXIBLE' if use_flexible else 'ORIGINAL'} ML SYSTEM")
    print(f"{'='*60}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data('RELIANCE', interval='5minute', days=10)
    
    if df is None or len(df) < 100:
        print("⚠️  Insufficient data")
        return
    
    print(f"\nData loaded: {len(df)} bars")
    
    # Use relaxed config to get more signals
    config = TradingConfig(**RELIANCE_CONFIG)
    
    # Create processor
    processor = FlexibleBarProcessor(
        config,
        symbol='RELIANCE',
        timeframe='5minute',
        use_flexible_ml=use_flexible,
        feature_config={
            'original_features': ['rsi', 'wt', 'cci', 'adx', 'features_4'],
            'phase3_features': ['fisher', 'vwm', 'order_flow'],
            'use_phase3': True
        }
    )
    
    # Process bars
    signals = []
    predictions = []
    feature_data = []
    
    print("\nProcessing bars...")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'],
            row['close'], row['volume']
        )
        
        if result:
            # Track predictions
            predictions.append({
                'bar': i,
                'prediction': result.prediction,
                'signal': result.signal
            })
            
            # Track signals
            if result.signal != 0:
                signals.append({
                    'timestamp': idx,
                    'signal': result.signal,
                    'prediction': result.prediction,
                    'ml_system': result.ml_system_used if hasattr(result, 'ml_system_used') else 'original'
                })
            
            # Track features (for flexible ML)
            if use_flexible and hasattr(result, 'feature_values') and result.feature_values:
                feature_data.append(result.feature_values)
    
    # Display results
    print(f"\nTotal predictions: {len(predictions)}")
    print(f"Total signals: {len(signals)}")
    
    if predictions:
        # Prediction statistics
        pred_values = [p['prediction'] for p in predictions]
        print(f"\nPrediction Statistics:")
        print(f"  Average: {np.mean(pred_values):.2f}")
        print(f"  Std Dev: {np.std(pred_values):.2f}")
        print(f"  Min: {min(pred_values):.2f}")
        print(f"  Max: {max(pred_values):.2f}")
        
        # Signals distribution
        long_signals = sum(1 for s in signals if s['signal'] > 0)
        short_signals = sum(1 for s in signals if s['signal'] < 0)
        print(f"\nSignal Distribution:")
        print(f"  Long signals: {long_signals}")
        print(f"  Short signals: {short_signals}")
    
    if signals and len(signals) >= 3:
        print(f"\nSample Signals:")
        for i, signal in enumerate(signals[:3]):
            print(f"\n{i+1}. {signal['timestamp']}:")
            print(f"   Signal: {'LONG' if signal['signal'] > 0 else 'SHORT'}")
            print(f"   Prediction: {signal['prediction']:.2f}")
            print(f"   ML System: {signal['ml_system']}")
    
    # Feature analysis for flexible ML
    if use_flexible and feature_data:
        print(f"\n{'='*40}")
        print("PHASE 3 FEATURE ANALYSIS")
        print(f"{'='*40}")
        
        # Calculate feature averages
        feature_names = list(feature_data[0].keys())
        phase3_features = ['fisher', 'vwm', 'order_flow']
        
        for feature in phase3_features:
            if feature in feature_names:
                values = [f[feature] for f in feature_data if feature in f]
                if values:
                    print(f"\n{feature.upper()}:")
                    print(f"  Average: {np.mean(values):.3f}")
                    print(f"  Range: [{min(values):.3f}, {max(values):.3f}]")
    
    # Get comparison stats if using flexible ML
    if use_flexible and hasattr(processor, 'get_comparison_stats'):
        stats = processor.get_comparison_stats()
        if stats and stats.get('comparisons', 0) > 0:
            print(f"\n{'='*40}")
            print("ML SYSTEM COMPARISON")
            print(f"{'='*40}")
            print(f"Comparisons made: {stats['comparisons']}")
            print(f"Avg difference: {stats['avg_difference']:.3f}")
            print(f"Max difference: {stats['max_difference']:.3f}")
            if not np.isnan(stats['correlation']):
                print(f"Correlation: {stats['correlation']:.3f}")
    
    return len(signals), len(predictions)


def main():
    """Run quick test of flexible ML"""
    
    print("\n" + "="*60)
    print("FLEXIBLE ML QUICK TEST")
    print("="*60)
    print("\nThis test uses relaxed settings to verify the flexible")
    print("ML system is working and generating signals.")
    
    # Test original
    print("\n1. Testing Original ML...")
    orig_signals, orig_preds = test_flexible_ml(use_flexible=False)
    
    # Test flexible
    print("\n2. Testing Flexible ML...")
    flex_signals, flex_preds = test_flexible_ml(use_flexible=True)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"\nOriginal ML: {orig_signals} signals, {orig_preds} predictions")
    print(f"Flexible ML: {flex_signals} signals, {flex_preds} predictions")
    
    if orig_signals > 0 and flex_signals > 0:
        pct_diff = ((flex_signals - orig_signals) / orig_signals) * 100
        print(f"\nSignal difference: {pct_diff:+.1f}%")
        
        if abs(pct_diff) < 20:
            print("\n✅ Systems are producing similar results!")
        else:
            print(f"\n⚠️  Systems differ by {abs(pct_diff):.1f}%")
    elif orig_signals == 0 and flex_signals == 0:
        print("\n⚠️  No signals generated - try adjusting thresholds")
    
    print("\nTest complete!")


if __name__ == "__main__":
    main()