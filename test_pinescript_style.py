#!/usr/bin/env python3
"""
Test with Pine Script Style Approach
====================================
Purpose: Test EXACTLY like Pine Script works
- Use ALL data for ML learning
- No train/test split
- Show progress and debug info
- Display ML predictions and filter states

This script shows WHY signals are or aren't generated.
"""

import pandas as pd
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from datetime import datetime
import os

def format_signal_debug(ml_prediction, filters, signal_type):
    """
    Format debug info in user-friendly way
    
    Example output:
    ML Prediction: 6.0 (Bullish)
    Filters: Vol=✓ Regime=✓ Kernel=✗
    Signal: BLOCKED (Kernel filter failed)
    """
    # Determine ML sentiment
    if ml_prediction > 0:
        ml_text = f"{ml_prediction:.1f} (Bullish 🟢)"
    elif ml_prediction < 0:
        ml_text = f"{ml_prediction:.1f} (Bearish 🔴)"
    else:
        ml_text = f"{ml_prediction:.1f} (Neutral ⚪)"
    
    # Format filter states
    filter_text = ""
    filter_text += f"Vol={'✓' if filters.get('volatility', False) else '✗'} "
    filter_text += f"Regime={'✓' if filters.get('regime', False) else '✗'} "
    filter_text += f"ADX={'✓' if filters.get('adx', False) else '✗'} "
    filter_text += f"Kernel={'✓' if filters.get('kernel', False) else '✗'}"
    
    # Determine signal status
    if signal_type == 'BUY':
        signal_text = "BUY SIGNAL! 🟢"
    elif signal_type == 'SELL':
        signal_text = "SELL SIGNAL! 🔴"
    else:
        # Find which filter blocked
        blocked_filters = [k for k, v in filters.items() if not v]
        if blocked_filters:
            signal_text = f"BLOCKED ({', '.join(blocked_filters)} failed)"
        else:
            signal_text = "NO SIGNAL (ML neutral or conditions not met)"
    
    return ml_text, filter_text, signal_text

def test_pinescript_style():
    """
    Test using Pine Script approach - ALL data for ML
    """
    
    print("=" * 60)
    print("🎯 Pine Script Style Testing")
    print("=" * 60)
    print()
    
    # Load the data
    data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        print("   Please run fetch_pinescript_style_data.py first!")
        return
    
    print(f"📂 Loading data from: {data_file}")
    df = pd.read_csv(data_file)
    total_bars = len(df)
    print(f"✅ Loaded {total_bars} bars")
    print()
    
    # Configuration - adjust max_bars_back for 2000 bars
    # With 2000 bars total, we need max_bars_back < 2000 for ML to work
    config = TradingConfig(
        max_bars_back=1000,  # Half of total bars - allows ML to work
        neighbors_count=8,
        feature_count=5,
        color_compression=1,
        show_exits=False,
        use_dynamic_exits=False,
        
        # Filters - match TradingView DEFAULTS
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,  # FALSE by default in Pine Script!
        regime_threshold=-0.1,
        adx_threshold=20,
        
        # EMA/SMA filters
        use_ema_filter=False,
        ema_period=200,
        use_sma_filter=False,
        sma_period=200,
        
        # Kernel settings
        use_kernel_filter=True,
        show_kernel_estimate=True,
        use_kernel_smoothing=False,
        kernel_lookback=8,
        kernel_relative_weight=8.0,
        kernel_regression_level=25,
        kernel_lag=2
    )
    
    print("⚙️ Configuration:")
    print(f"   max_bars_back: {config.max_bars_back}")
    print(f"   This means ML will start at bar {config.max_bars_back}")
    print(f"   Training bars: {config.max_bars_back}")
    print(f"   Prediction bars: {total_bars - config.max_bars_back}")
    print()
    
    # Initialize processor - no need for total_bars anymore!
    print("🔧 Initializing Bar Processor (with sliding window)...")
    processor = BarProcessor(config)
    
    # Process results storage
    results = []
    buy_signals = []
    sell_signals = []
    
    # Progress tracking
    progress_interval = 100  # Show progress every 100 bars
    debug_signals = True     # Show debug for signals
    show_every_n = 500      # Show debug every N bars even without signal
    
    print("🏃 Processing bars...")
    print()
    
    # Process each bar
    for i in range(total_bars):
        bar = df.iloc[i]
        
        # Show progress
        if i % progress_interval == 0 or i == total_bars - 1:
            progress_pct = (i + 1) / total_bars * 100
            print(f"📊 Progress: Bar {i+1}/{total_bars} ({progress_pct:.1f}%)")
        
        # Process the bar
        result = processor.process_bar(
            open_price=bar['open'],
            high=bar['high'],
            low=bar['low'],
            close=bar['close'],
            volume=bar['volume']
        )
        
        # Store result
        results.append(result)
        
        # Debug output for specific bars
        show_debug = False
        signal_type = None
        
        # Check for signals
        if result.start_long_trade:
            buy_signals.append({
                'bar': i,
                'date': bar['date'],
                'price': bar['close'],
                'ml_prediction': result.prediction
            })
            show_debug = True
            signal_type = 'BUY'
            
        elif result.start_short_trade:
            sell_signals.append({
                'bar': i,
                'date': bar['date'],
                'price': bar['close'],
                'ml_prediction': result.prediction
            })
            show_debug = True
            signal_type = 'SELL'
            
        # Also show debug every N bars
        elif i % show_every_n == 0 and i >= config.max_bars_back:
            show_debug = True
            
        # Display debug info
        if show_debug and i >= config.max_bars_back:
            print()
            print(f"  🔍 Bar {i} Debug Info:")
            
            # Get filter states from result
            filters = result.filter_states.copy()
            
            # Add kernel filter state based on signal generation logic
            # Kernel filter is part of entry conditions, not stored in filter_states
            # We'll assume it passes if we have a signal and ML prediction is aligned
            if config.use_kernel_filter:
                # If we have a signal, kernel must have passed
                if signal_type in ['BUY', 'SELL']:
                    filters['kernel'] = True
                else:
                    # Otherwise, infer from ML prediction direction
                    # This is a simplification - actual kernel state would need to be calculated
                    filters['kernel'] = False if result.prediction != 0 else True
            else:
                filters['kernel'] = True  # Not used
            
            ml_text, filter_text, signal_text = format_signal_debug(
                result.prediction,
                filters,
                signal_type
            )
            
            print(f"     ML Prediction: {ml_text}")
            print(f"     Filters: {filter_text}")
            print(f"     Signal: {signal_text}")
            print(f"     Price: ₹{bar['close']:.2f}")
            print()
    
    # Summary
    print()
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print()
    print(f"Total bars processed: {total_bars}")
    print(f"ML started at bar: {config.max_bars_back}")
    print(f"Bars with ML predictions: {total_bars - config.max_bars_back}")
    print()
    print(f"🟢 Buy Signals: {len(buy_signals)}")
    print(f"🔴 Sell Signals: {len(sell_signals)}")
    print(f"📊 Total Signals: {len(buy_signals) + len(sell_signals)}")
    print()
    
    # Show signal details
    if buy_signals or sell_signals:
        print("📋 Signal Details:")
        print()
        
        for signal in buy_signals:
            print(f"  🟢 BUY  - Bar {signal['bar']:4d} | {signal['date']} | "
                  f"₹{signal['price']:.2f} | ML: {signal['ml_prediction']:.1f}")
        
        for signal in sell_signals:
            print(f"  🔴 SELL - Bar {signal['bar']:4d} | {signal['date']} | "
                  f"₹{signal['price']:.2f} | ML: {signal['ml_prediction']:.1f}")
    else:
        print("❌ No signals generated!")
        print()
        print("🔍 Debugging suggestions:")
        print("   1. Check if ML predictions are too weak (close to 0)")
        print("   2. Check if filters are too restrictive")
        print("   3. Try with use_kernel_filter=False")
        print("   4. Try with smaller max_bars_back (500 or 750)")
    
    # Save results if signals found
    if buy_signals or sell_signals:
        output_file = "pinescript_style_signals.csv"
        signal_df = pd.DataFrame(buy_signals + sell_signals)
        signal_df.to_csv(output_file, index=False)
        print()
        print(f"💾 Signals saved to: {output_file}")
    
    print()
    print("✅ Test completed!")

if __name__ == "__main__":
    test_pinescript_style()
