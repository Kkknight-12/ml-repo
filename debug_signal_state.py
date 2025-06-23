#!/usr/bin/env python3
"""
Debug script to trace signal state during warmup transition
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import pandas as pd
from config.settings import TradingConfig
from scanner import BarProcessor

def trace_signal_state():
    """Trace signal state around the warmup transition"""
    
    # Create test data around warmup transition
    # Bar 1990-2010 (around warmup end at 2000)
    test_bars = []
    base_price = 1000.0
    
    for i in range(1990, 2010):
        # Create some price movement
        price = base_price + (i - 2000) * 2  # Price increases after warmup
        test_bars.append({
            'bar_index': i,
            'open': price,
            'high': price + 1,
            'low': price - 1,
            'close': price,
            'volume': 100000
        })
    
    # Initialize processor
    config = TradingConfig(
        max_bars_back=2000,
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False
    )
    
    processor = BarProcessor(config, "TEST", "day", debug_mode=True)
    
    print("="*70)
    print("SIGNAL STATE TRACE DURING WARMUP TRANSITION")
    print("="*70)
    print(f"\nWarmup ends at bar: {config.max_bars_back}")
    print("\nBar Index | Prediction | Signal | Signal History | Entry Signals")
    print("-"*70)
    
    for bar in test_bars:
        result = processor.process_bar(
            bar['open'], bar['high'], bar['low'], bar['close'], bar['volume']
        )
        
        if result:
            # Get signal history from processor
            signal_history = processor.signal_history if hasattr(processor, 'signal_history') else []
            
            # Format signal history for display
            history_str = str(signal_history[:3]) if signal_history else "[]"
            
            # Check entry signals
            entry_str = ""
            if result.start_long_trade:
                entry_str = "LONG ENTRY"
            elif result.start_short_trade:
                entry_str = "SHORT ENTRY"
            
            print(f"{result.bar_index:9d} | {result.prediction:10.1f} | {result.signal:6d} | "
                  f"{history_str:20s} | {entry_str}")
            
            # Special logging at warmup boundary
            if result.bar_index == config.max_bars_back - 1:
                print("\n>>> LAST BAR OF WARMUP <<<")
            elif result.bar_index == config.max_bars_back:
                print("\n>>> FIRST BAR AFTER WARMUP <<<")
                print(f"    ML Model predictions array size: {len(processor.ml_model.predictions)}")
                print(f"    ML Model training data size: {len(processor.ml_model.y_train_array)}")
                print()

if __name__ == "__main__":
    trace_signal_state()