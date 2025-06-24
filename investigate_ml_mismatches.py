#!/usr/bin/env python3
"""
Investigate ML Prediction Mismatches
====================================

This script investigates the 2 cases where ML predictions differ
between Pine Script and Python.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import sqlite3
from datetime import datetime
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from core.pine_functions import nz


def investigate_ml_mismatches():
    """Deep dive into ML prediction differences"""
    
    print("="*70)
    print("ML PREDICTION MISMATCH INVESTIGATION")
    print("="*70)
    
    # Known mismatches from previous analysis (update these with actual dates)
    known_mismatches = [
        # Add the specific dates/bars where mismatches occur
        # Example: {'bar': 2024, 'date': '2023-05-15', 'pine_pred': 8.0, 'python_pred': -8.0}
    ]
    
    # Initialize processor with debug mode
    config = TradingConfig()
    processor = EnhancedBarProcessor(config, "ICICIBANK", "day", debug_mode=True)
    
    # Load data
    db_path = os.path.join("data_cache", "market_data.db")
    with sqlite3.connect(db_path) as conn:
        query = """
        SELECT date, open, high, low, close, volume
        FROM market_data
        WHERE symbol = 'ICICIBANK' AND interval = 'day'
        ORDER BY date
        """
        df = pd.read_sql_query(query, conn, parse_dates=['date'])
    
    print(f"\nProcessing {len(df)} bars with debug mode ON...")
    
    # Track predictions and feature values
    prediction_tracker = {
        'predictions': [],
        'feature_snapshots': [],
        'neighbor_details': []
    }
    
    # Process bars
    for idx, row in df.iterrows():
        result = processor.process_bar(
            nz(row['open'], row['close']),
            nz(row['high'], row['close']),
            nz(row['low'], row['close']),
            nz(row['close'], 0.0),
            nz(row['volume'], 0.0)
        )
        
        if result and result.bar_index >= config.max_bars_back:
            # Store prediction details
            pred_detail = {
                'bar': result.bar_index,
                'date': row['date'],
                'prediction': result.prediction,
                'signal': result.signal,
                'filters': result.filter_states.copy()
            }
            
            # Get feature values at prediction time
            if processor.feature_arrays.f1:
                pred_detail['features'] = {
                    'f1': processor.feature_arrays.f1[-1] if processor.feature_arrays.f1 else 0,
                    'f2': processor.feature_arrays.f2[-1] if processor.feature_arrays.f2 else 0,
                    'f3': processor.feature_arrays.f3[-1] if processor.feature_arrays.f3 else 0,
                    'f4': processor.feature_arrays.f4[-1] if processor.feature_arrays.f4 else 0,
                    'f5': processor.feature_arrays.f5[-1] if processor.feature_arrays.f5 else 0
                }
            
            # Get neighbor predictions if available
            if hasattr(processor.ml_model, 'predictions'):
                pred_detail['neighbors'] = processor.ml_model.predictions.copy()
                pred_detail['neighbor_count'] = len(processor.ml_model.predictions)
            
            prediction_tracker['predictions'].append(pred_detail)
            
            # Look for extreme prediction changes
            if len(prediction_tracker['predictions']) > 1:
                prev = prediction_tracker['predictions'][-2]
                curr = prediction_tracker['predictions'][-1]
                
                # Check for large swings
                if abs(prev['prediction']) > 5 and abs(curr['prediction']) > 5:
                    if prev['prediction'] * curr['prediction'] < 0:  # Sign change
                        print(f"\n⚠️  Large prediction swing at bar {curr['bar']}:")
                        print(f"   {prev['prediction']:.2f} → {curr['prediction']:.2f}")
                        print(f"   Date: {curr['date'].strftime('%Y-%m-%d')}")
                        
                        if 'features' in curr and 'features' in prev:
                            print(f"   Feature changes:")
                            for feat in ['f1', 'f2', 'f3', 'f4', 'f5']:
                                change = curr['features'][feat] - prev['features'][feat]
                                if abs(change) > 10:
                                    print(f"     {feat}: {prev['features'][feat]:.1f} → {curr['features'][feat]:.1f} (Δ{change:+.1f})")
    
    # Analyze prediction patterns
    print(f"\n\n📊 PREDICTION ANALYSIS")
    print(f"="*70)
    
    # Find potential mismatch candidates
    print(f"\n🔍 Potential Mismatch Patterns:")
    
    # 1. Bars with exactly ±8 predictions (full neighbor agreement)
    full_agreement_bars = [p for p in prediction_tracker['predictions'] 
                          if abs(p['prediction']) == 8.0]
    print(f"\n1. Bars with ±8.0 predictions (full neighbor agreement): {len(full_agreement_bars)}")
    if full_agreement_bars:
        print("   Last 5 occurrences:")
        for p in full_agreement_bars[-5:]:
            print(f"   - Bar {p['bar']} ({p['date'].strftime('%Y-%m-%d')}): {p['prediction']}")
    
    # 2. Bars with rapid prediction changes
    rapid_changes = []
    for i in range(1, len(prediction_tracker['predictions'])):
        curr = prediction_tracker['predictions'][i]
        prev = prediction_tracker['predictions'][i-1]
        if abs(curr['prediction'] - prev['prediction']) > 10:
            rapid_changes.append({
                'bar': curr['bar'],
                'date': curr['date'],
                'change': curr['prediction'] - prev['prediction'],
                'from': prev['prediction'],
                'to': curr['prediction']
            })
    
    print(f"\n2. Rapid prediction changes (>10 points): {len(rapid_changes)}")
    if rapid_changes:
        print("   Last 3 occurrences:")
        for rc in rapid_changes[-3:]:
            print(f"   - Bar {rc['bar']} ({rc['date'].strftime('%Y-%m-%d')}): "
                  f"{rc['from']:.1f} → {rc['to']:.1f} (Δ{rc['change']:+.1f})")
    
    # 3. Check feature calculation precision
    print(f"\n3. Feature Value Ranges:")
    if prediction_tracker['predictions']:
        # Get last prediction with features
        last_with_features = next((p for p in reversed(prediction_tracker['predictions']) 
                                  if 'features' in p), None)
        if last_with_features:
            print(f"   Latest feature values (Bar {last_with_features['bar']}):")
            for feat, val in last_with_features['features'].items():
                print(f"   - {feat}: {val:.2f}")
    
    # SUMMARY
    print(f"\n\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    print(f"\n📌 POSSIBLE CAUSES OF ML MISMATCHES:")
    print(f"1. Feature calculation precision differences")
    print(f"2. Neighbor selection threshold variations")
    print(f"3. Historical data alignment issues")
    print(f"4. Rounding differences in distance calculations")
    
    print(f"\n📌 DEBUGGING RECOMMENDATIONS:")
    print(f"1. Log raw feature values in both Pine and Python")
    print(f"2. Compare exact neighbor selections for mismatch bars")
    print(f"3. Check if k-NN threshold calculations differ")
    print(f"4. Verify array indexing is consistent throughout")
    
    return prediction_tracker


def analyze_specific_mismatch(bar_index: int, prediction_data: dict):
    """Deep dive into a specific mismatch"""
    
    print(f"\n\n🔬 SPECIFIC MISMATCH ANALYSIS - Bar {bar_index}")
    print("="*70)
    
    # Find the prediction for this bar
    bar_data = next((p for p in prediction_data['predictions'] 
                     if p['bar'] == bar_index), None)
    
    if not bar_data:
        print(f"❌ No data found for bar {bar_index}")
        return
    
    print(f"\n📊 Bar {bar_index} Details:")
    print(f"   Date: {bar_data['date'].strftime('%Y-%m-%d')}")
    print(f"   Prediction: {bar_data['prediction']:.2f}")
    print(f"   Signal: {bar_data['signal']}")
    
    if 'neighbors' in bar_data:
        print(f"\n   Neighbor Predictions: {bar_data['neighbors']}")
        print(f"   Neighbor Count: {bar_data['neighbor_count']}")
        print(f"   Sum: {sum(bar_data['neighbors'])}")
    
    if 'features' in bar_data:
        print(f"\n   Feature Values:")
        for feat, val in bar_data['features'].items():
            print(f"   - {feat}: {val:.2f}")
    
    print(f"\n   Filter States:")
    for filt, state in bar_data['filters'].items():
        print(f"   - {filt}: {'PASS' if state else 'FAIL'}")


if __name__ == "__main__":
    # Run ML mismatch investigation
    prediction_data = investigate_ml_mismatches()
    
    # If you know specific mismatch bars, analyze them
    # Example: analyze_specific_mismatch(2024, prediction_data)
    
    print("\n\n💡 Next Steps:")
    print("1. Compare these patterns with Pine Script ML predictions")
    print("2. Focus on bars with ±8.0 predictions for comparison")
    print("3. Check if rapid changes align with mismatch dates")