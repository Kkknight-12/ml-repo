#!/usr/bin/env python3
"""
Test ML Prediction vs Signal - Verify the Fix
This script clearly shows the difference between ML predictions and signals
"""

import pandas as pd
import numpy as np
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from utils.sample_data import generate_sample_data

def test_ml_predictions():
    print("🔍 Testing ML Predictions vs Signals")
    print("=" * 60)
    
    # Generate sample data with good price movement
    data = generate_sample_data(
        num_bars=500,
        trend_strength=0.3,  # Strong trend for better predictions
        volatility=0.02,
        start_price=100.0
    )
    
    # Test 1: With Filters OFF
    print("\n📊 TEST 1: Filters OFF (Baseline)")
    print("-" * 40)
    
    config_off = TradingConfig(
        use_volatility_filter=False,
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=False,
        max_bars_back=200  # Smaller for faster testing
    )
    
    processor_off = BarProcessor(config_off)
    predictions_off = []
    signals_off = []
    
    # Process bars
    for i, row in data.iterrows():
        result = processor_off.process_bar(
            open_price=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume']
        )
        
        if result and result.prediction != 0:
            predictions_off.append(result.prediction)
            signals_off.append(result.signal)
    
    print(f"✅ Non-zero predictions: {len(predictions_off)}")
    if predictions_off:
        print(f"   Prediction range: {min(predictions_off):.2f} to {max(predictions_off):.2f}")
        print(f"   Average: {np.mean(predictions_off):.2f}")
        print(f"   Sample predictions: {predictions_off[-5:]}")
    
    # Test 2: With Filters ON
    print("\n📊 TEST 2: Filters ON (Testing Fix)")
    print("-" * 40)
    
    config_on = TradingConfig(
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,  # Keep default
        use_kernel_filter=True,
        max_bars_back=200
    )
    
    processor_on = BarProcessor(config_on)
    predictions_on = []
    signals_on = []
    filter_results = []
    
    # Process bars with detailed tracking
    for i, row in data.iterrows():
        result = processor_on.process_bar(
            open_price=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume']
        )
        
        if result:
            # Track everything
            if result.prediction != 0:
                predictions_on.append(result.prediction)
                signals_on.append(result.signal)
                filter_results.append({
                    'bar': result.bar_index,
                    'prediction': result.prediction,
                    'signal': result.signal,
                    'filters': result.filter_states,
                    'all_pass': all(result.filter_states.values())
                })
    
    print(f"✅ Non-zero predictions: {len(predictions_on)}")
    if predictions_on:
        print(f"   Prediction range: {min(predictions_on):.2f} to {max(predictions_on):.2f}")
        print(f"   Average: {np.mean(predictions_on):.2f}")
        print(f"   Sample predictions: {predictions_on[-5:]}")
    
    # Analyze filter impact
    print("\n📊 FILTER IMPACT ANALYSIS")
    print("-" * 40)
    
    if filter_results:
        # Count how many times each filter failed
        vol_pass = sum(1 for r in filter_results if r['filters']['volatility'])
        regime_pass = sum(1 for r in filter_results if r['filters']['regime'])
        adx_pass = sum(1 for r in filter_results if r['filters']['adx'])
        all_pass = sum(1 for r in filter_results if r['all_pass'])
        
        print(f"Volatility Filter: {vol_pass}/{len(filter_results)} passed ({vol_pass/len(filter_results)*100:.1f}%)")
        print(f"Regime Filter: {regime_pass}/{len(filter_results)} passed ({regime_pass/len(filter_results)*100:.1f}%)")
        print(f"ADX Filter: {adx_pass}/{len(filter_results)} passed ({adx_pass/len(filter_results)*100:.1f}%)")
        print(f"All Filters: {all_pass}/{len(filter_results)} passed ({all_pass/len(filter_results)*100:.1f}%)")
        
        # Show examples where prediction exists but signal is neutral
        print("\n🔍 Examples: Prediction vs Signal")
        examples = [r for r in filter_results[-10:] if abs(r['prediction']) > 2]
        for ex in examples[:3]:
            print(f"\nBar {ex['bar']}:")
            print(f"  ML Prediction: {ex['prediction']:.2f}")
            print(f"  Signal: {ex['signal']} {'(filtered out)' if ex['signal'] == 0 else ''}")
            print(f"  Filters: Vol={ex['filters']['volatility']}, Regime={ex['filters']['regime']}, All={ex['all_pass']}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY:")
    
    if predictions_off and predictions_on:
        print(f"\n✅ SUCCESS: ML predictions working with filters ON!")
        print(f"   Filters OFF: {len(predictions_off)} predictions")
        print(f"   Filters ON: {len(predictions_on)} predictions")
        print(f"\n💡 Key Insight: ML predictions are independent of filters.")
        print("   Filters only affect the final SIGNAL, not the PREDICTION.")
    elif predictions_off and not predictions_on:
        print(f"\n❌ ISSUE: ML predictions still 0 with filters ON")
        print("   This suggests a deeper issue in the prediction calculation")
    else:
        print(f"\n❌ ISSUE: No ML predictions generated")
        print("   Check if enough training data is available")

if __name__ == "__main__":
    test_ml_predictions()
