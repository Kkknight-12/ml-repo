#!/usr/bin/env python3
"""
Add comprehensive debug logging to ML prediction process
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import sqlite3
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from core.pine_functions import nz
import json


class DebugMLProcessor(EnhancedBarProcessor):
    """Extended processor with ML debug logging"""
    
    def __init__(self, config, symbol, timeframe, debug_mode=True):
        super().__init__(config, symbol, timeframe, debug_mode)
        self.ml_debug_log = []
        
    def process_bar(self, open_price, high, low, close, volume=0.0):
        """Override to capture ML debug info"""
        result = super().process_bar(open_price, high, low, close, volume)
        
        if result and result.bar_index >= self.settings.max_bars_back:
            # Capture ML debug info
            debug_info = {
                'bar_index': result.bar_index,
                'close': close,
                'ml_prediction': result.prediction,
                'signal': result.signal
            }
            
            # Get feature values
            if hasattr(self, 'feature_arrays') and len(self.feature_arrays.f1) > 0:
                debug_info['features'] = {
                    'f1': self.feature_arrays.f1[-1],
                    'f2': self.feature_arrays.f2[-1],
                    'f3': self.feature_arrays.f3[-1],
                    'f4': self.feature_arrays.f4[-1],
                    'f5': self.feature_arrays.f5[-1]
                }
            
            # Get ML model internals if available
            if hasattr(self.ml_model, 'last_distances'):
                debug_info['distances'] = self.ml_model.last_distances[:5]  # Top 5
            
            if hasattr(self.ml_model, 'last_predictions'):
                debug_info['neighbor_predictions'] = self.ml_model.last_predictions[:5]
                
            if hasattr(self.ml_model, 'last_weights'):
                debug_info['weights'] = self.ml_model.last_weights[:5]
            
            self.ml_debug_log.append(debug_info)
            
        return result


def add_ml_debug_logging():
    """Test ML with enhanced debug logging"""
    
    print("="*70)
    print("ML DEBUG LOGGING TEST")
    print("="*70)
    
    # Load Pine Script data
    pine_file = "archive/data_files/NSE_ICICIBANK, 1D.csv"
    df_pine = pd.read_csv(pine_file)
    df_pine['time'] = pd.to_datetime(df_pine['time'])
    
    # Get first few Pine signals
    pine_signals = []
    for idx, row in df_pine.iterrows():
        if pd.notna(row['Buy']):
            pine_signals.append({'date': row['time'], 'type': 'BUY'})
        if pd.notna(row['Sell']):
            pine_signals.append({'date': row['time'], 'type': 'SELL'})
    
    print(f"\n📊 Testing with first 5 Pine signals:")
    for sig in pine_signals[:5]:
        print(f"   {sig['date'].strftime('%Y-%m-%d')}: {sig['type']}")
    
    # Initialize debug processor
    config = TradingConfig(
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        source='close',
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        use_kernel_filter=True,
        use_kernel_smoothing=False,
        kernel_lookback=8,
        kernel_relative_weight=8.0,
        kernel_regression_level=25,
        kernel_lag=2
    )
    
    processor = DebugMLProcessor(config, "ICICIBANK", "day", debug_mode=True)
    
    # Get all data
    db_path = os.path.join("data_cache", "market_data.db")
    with sqlite3.connect(db_path) as conn:
        query = """
        SELECT date, open, high, low, close, volume
        FROM market_data
        WHERE symbol = 'ICICIBANK' AND interval = 'day'
        ORDER BY date
        """
        df = pd.read_sql_query(query, conn, parse_dates=['date'])
    
    print(f"\n📊 Processing {len(df)} bars with debug logging...")
    
    # Process all bars
    for idx, row in df.iterrows():
        result = processor.process_bar(
            nz(row['open'], row['close']),
            nz(row['high'], row['close']),
            nz(row['low'], row['close']),
            nz(row['close'], 0.0),
            nz(row['volume'], 0.0)
        )
        
        # Check if this is a Pine signal date
        is_pine_signal = any(sig['date'].date() == row['date'].date() for sig in pine_signals[:5])
        
        if is_pine_signal and result and result.bar_index >= config.max_bars_back:
            pine_sig = next(s for s in pine_signals if s['date'].date() == row['date'].date())
            
            print(f"\n📅 {row['date'].strftime('%Y-%m-%d')} - Pine: {pine_sig['type']}")
            print(f"   ML Prediction: {result.prediction:.3f}")
            print(f"   Signal: {result.signal}")
            
            # Find debug info for this bar
            debug_info = next((d for d in processor.ml_debug_log if d['bar_index'] == result.bar_index), None)
            
            if debug_info and 'features' in debug_info:
                print(f"\n   Features:")
                for feat, val in debug_info['features'].items():
                    print(f"      {feat}: {val:.3f}")
            
            if debug_info and 'distances' in debug_info:
                print(f"\n   Top 5 Neighbor Distances:")
                for i, dist in enumerate(debug_info['distances']):
                    print(f"      {i+1}: {dist:.3f}")
            
            if debug_info and 'neighbor_predictions' in debug_info:
                print(f"\n   Neighbor Predictions:")
                for i, pred in enumerate(debug_info['neighbor_predictions']):
                    print(f"      {i+1}: {pred}")
            
            if debug_info and 'weights' in debug_info:
                print(f"\n   Neighbor Weights:")
                for i, weight in enumerate(debug_info['weights']):
                    print(f"      {i+1}: {weight:.3f}")
        
        if idx % 500 == 0:
            print(f"   Processed {idx}/{len(df)} bars...")
    
    # Save debug log
    debug_file = "ml_debug_log.json"
    with open(debug_file, 'w') as f:
        json.dump(processor.ml_debug_log[-100:], f, indent=2, default=str)
    
    print(f"\n📊 Debug log saved to {debug_file}")
    
    # SUMMARY
    print(f"\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    print(f"To fix ML prediction accuracy:")
    print(f"1. Compare the feature values with Pine Script debug output")
    print(f"2. Check if neighbor selection is finding the same historical patterns")
    print(f"3. Verify the Lorentzian distance calculation")
    print(f"4. Ensure training labels (4-bar future price) match Pine Script")
    
    print(f"\nNext steps:")
    print(f"1. Modify ml/lorentzian_knn_fixed.py to add:")
    print(f"   - self.last_distances = distances[:k]")
    print(f"   - self.last_predictions = [y_train[i] for i in indices[:k]]")
    print(f"   - self.last_weights = weights[:k]")
    print(f"2. Run this script again to capture detailed ML internals")
    print(f"3. Compare with Pine Script debug logs")
    
    print("="*70)


if __name__ == "__main__":
    add_ml_debug_logging()