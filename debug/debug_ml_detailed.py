#!/usr/bin/env python3
"""
Detailed ML Debug Script
========================
This script adds extensive logging to understand why ML predictions are 0
"""

import pandas as pd
import sys
import os
import math
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from data.data_types import FeatureSeries, FeatureArrays
from collections import Counter

class DebugBarProcessor(BarProcessor):
    """Extended BarProcessor with debug logging"""
    
    def __init__(self, config, total_bars=None):
        super().__init__(config, total_bars)
        self.debug_bar = 500  # Bar to debug in detail
    
    def process_bar(self, open_price, high, low, close, volume=0.0):
        """Override to add debug logging"""
        result = super().process_bar(open_price, high, low, close, volume)
        
        # Debug at specific bar
        if self.bars.bar_index == self.debug_bar:
            print("\n" + "="*60)
            print(f"🔍 DETAILED DEBUG AT BAR {self.debug_bar}")
            print("="*60)
            
            # 1. Check feature values
            print("\n1. FEATURE VALUES:")
            features = self._calculate_features()
            print(f"   F1 (RSI): {features.f1:.4f}")
            print(f"   F2 (WT): {features.f2:.4f}")
            print(f"   F3 (CCI): {features.f3:.4f}")
            print(f"   F4 (ADX): {features.f4:.4f}")
            print(f"   F5 (RSI): {features.f5:.4f}")
            
            # 2. Check feature arrays (last 10 values)
            print("\n2. FEATURE ARRAYS (last 10 values):")
            print(f"   F1: {[f'{x:.3f}' for x in self.feature_arrays.f1[:10]]}")
            print(f"   F2: {[f'{x:.3f}' for x in self.feature_arrays.f2[:10]]}")
            
            # 3. Check training labels
            print("\n3. TRAINING LABELS:")
            print(f"   Total labels: {len(self.ml_model.y_train_array)}")
            label_counts = Counter(self.ml_model.y_train_array[-100:])
            print(f"   Last 100 labels: {dict(label_counts)}")
            
            # 4. Debug ML prediction with custom logic
            self._debug_ml_prediction(features, self.feature_arrays)
            
        return result
    
    def _debug_ml_prediction(self, feature_series, feature_arrays):
        """Debug the ML prediction algorithm step by step"""
        print("\n4. ML PREDICTION DEBUG:")
        
        # Copy logic from lorentzian_knn.py predict() method
        last_distance = -1.0
        predictions = []
        distances = []
        
        # Calculate loop size
        size = min(self.settings.max_bars_back - 1, len(self.ml_model.y_train_array) - 1)
        size_loop = min(self.settings.max_bars_back - 1, size)
        
        print(f"   Loop size: {size_loop}")
        print(f"   Max bars back index: {self.max_bars_back_index}")
        print(f"   Current bar index: {self.bars.bar_index}")
        
        # Check if we should process
        if self.bars.bar_index < self.max_bars_back_index:
            print("   ❌ Bar index < max_bars_back_index - SKIPPING!")
            return
        
        # Track iterations
        neighbors_found = 0
        iterations_checked = 0
        
        print("\n   NEIGHBOR SEARCH:")
        
        # Main loop
        for i in range(size_loop + 1):
            iterations_checked += 1
            
            # Calculate distance
            d = self.ml_model.get_lorentzian_distance(
                i, self.settings.feature_count, feature_series, feature_arrays
            )
            
            # Check conditions
            passes_distance = d >= last_distance
            passes_spacing = i % 4 == 0
            
            # Debug first few iterations
            if i < 20:
                print(f"   i={i}: d={d:.4f}, last_d={last_distance:.4f}, "
                      f"passes_dist={passes_distance}, passes_spacing={passes_spacing}")
            
            # Pine Script: if d >= lastDistance and i%4
            if passes_distance and passes_spacing:
                neighbors_found += 1
                last_distance = d
                distances.append(d)
                
                # Get label
                if i < len(self.ml_model.y_train_array):
                    label = self.ml_model.y_train_array[i]
                    predictions.append(float(label))
                    
                    if neighbors_found <= 5:  # Show first 5 neighbors
                        print(f"   ✓ Neighbor {neighbors_found}: i={i}, d={d:.4f}, label={label}")
                
                # Maintain k neighbors
                if len(predictions) > self.settings.neighbors_count:
                    # Update last_distance
                    k_75 = int(self.settings.neighbors_count * 3 / 4)
                    if k_75 < len(distances):
                        old_last = last_distance
                        last_distance = distances[k_75]
                        print(f"   📊 Updated last_distance: {old_last:.4f} → {last_distance:.4f}")
                    
                    distances.pop(0)
                    predictions.pop(0)
        
        # Final results
        print(f"\n   RESULTS:")
        print(f"   Iterations checked: {iterations_checked}")
        print(f"   Neighbors found: {neighbors_found}")
        print(f"   Final neighbors: {len(predictions)}")
        print(f"   Predictions: {predictions}")
        print(f"   Sum: {sum(predictions)}")
        
        # Check specific issues
        if len(predictions) == 0:
            print("\n   ❌ NO NEIGHBORS FOUND!")
            print("   Possible reasons:")
            print("   - Initial last_distance = -1.0 not being exceeded")
            print("   - All distances < -1.0 (impossible with log)")
            print("   - Feature arrays too short")
        elif sum(predictions) == 0:
            print("\n   ⚠️ NEIGHBORS FOUND BUT SUM = 0!")
            print("   Possible reasons:")
            print("   - All neighbors have neutral labels (0)")
            print("   - Equal positive and negative labels canceling out")

def run_detailed_debug():
    """Run detailed ML debug"""
    
    print("=" * 80)
    print("🔬 DETAILED ML DEBUG SCRIPT")
    print("=" * 80)
    
    # Load data
    data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return
    
    df = pd.read_csv(data_file)
    print(f"\n✅ Loaded {len(df)} bars")
    
    # Create config with minimal filters
    config = TradingConfig(
        max_bars_back=500,
        neighbors_count=8,
        feature_count=5,
        
        # Disable all filters for testing
        use_volatility_filter=False,
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=False,
        use_ema_filter=False,
        use_sma_filter=False
    )
    
    # Use debug processor
    processor = DebugBarProcessor(config, total_bars=len(df))
    
    # Process up to debug bar + some extra
    print(f"\nProcessing up to bar 520...")
    for i in range(min(520, len(df))):
        bar = df.iloc[i]
        
        if i % 100 == 0:
            print(f"Progress: Bar {i}")
        
        processor.process_bar(
            bar['open'], bar['high'], bar['low'],
            bar['close'], bar['volume']
        )
    
    print("\n✅ Debug complete! Check output above for details.")

if __name__ == "__main__":
    run_detailed_debug()
