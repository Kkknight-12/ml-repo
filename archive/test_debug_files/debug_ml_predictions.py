#!/usr/bin/env python3
"""
Debug ML Predictions in Detail
==============================
Purpose: Deep dive into WHY signals aren't being generated
- Show ML prediction distribution
- Analyze filter blocking patterns
- Check entry conditions
- Compare with expected behavior

Use this when test_pinescript_style.py shows no signals.
"""

import pandas as pd
import numpy as np
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
import matplotlib.pyplot as plt
from collections import Counter

def debug_ml_predictions():
    """
    Detailed analysis of ML predictions and signal generation
    """
    
    print("=" * 60)
    print("🔍 ML Predictions Deep Debug")
    print("=" * 60)
    print()
    
    # Load data
    data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    df = pd.read_csv(data_file)
    total_bars = len(df)
    
    print(f"📂 Loaded {total_bars} bars")
    print()
    
    # Test with different configurations
    configs_to_test = [
        {
            'name': 'Original (max_bars=1000)',
            'max_bars_back': 1000,
            'use_kernel_filter': True
        },
        {
            'name': 'Smaller window (max_bars=500)',
            'max_bars_back': 500,
            'use_kernel_filter': True
        },
        {
            'name': 'No kernel filter',
            'max_bars_back': 1000,
            'use_kernel_filter': False
        },
        {
            'name': 'Minimal (max_bars=100)',
            'max_bars_back': 100,
            'use_kernel_filter': True
        }
    ]
    
    for config_test in configs_to_test:
        print(f"🧪 Testing: {config_test['name']}")
        print("-" * 40)
        
        # Create config
        config = TradingConfig(
            max_bars_back=config_test['max_bars_back'],
            use_kernel_filter=config_test['use_kernel_filter'],
            neighbors_count=8,
            feature_count=5,
            use_volatility_filter=True,
            use_regime_filter=True,
            use_adx_filter=False,
            use_ema_filter=False,
            use_sma_filter=False,
            kernel_lookback=8,
            kernel_relative_weight=8.0,
            kernel_regression_level=25,
            use_kernel_smoothing=False
        )
        
        # Initialize processor
        processor = BarProcessor(config, total_bars=total_bars)
        
        # Storage for analysis
        ml_predictions = []
        filter_states = []
        signal_conditions = []
        
        # Process bars
        ml_start_bar = config.max_bars_back
        
        for i in range(total_bars):
            bar = df.iloc[i]
            
            result = processor.process_bar(
                open_price=bar['open'],  # Fixed parameter name
                high=bar['high'],
                low=bar['low'],
                close=bar['close'],
                volume=bar['volume']
            )
            
            # Store data after ML starts
            if i >= ml_start_bar:
                ml_predictions.append(result.prediction)
                
                # Store filter states
                filter_states.append({
                    'bar': i,
                    'volatility': result.filter_volatility,
                    'regime': result.filter_regime,
                    'adx': result.filter_adx,
                    'kernel_bull': result.is_bullish,
                    'kernel_bear': result.is_bearish,
                    'all_pass': (result.filter_volatility and 
                               result.filter_regime and 
                               result.filter_adx)
                })
                
                # Check signal conditions
                signal_conditions.append({
                    'bar': i,
                    'ml_prediction': result.prediction,
                    'is_buy_signal': result.start_long_trade,
                    'is_sell_signal': result.start_short_trade,
                    'signal': result.signal,
                    'bars_held': result.bars_held if hasattr(result, 'bars_held') else 0
                })
        
        # Analyze ML predictions
        ml_array = np.array(ml_predictions)
        
        print(f"📊 ML Prediction Statistics:")
        print(f"   Bars with ML: {len(ml_predictions)}")
        print(f"   Mean: {np.mean(ml_array):.2f}")
        print(f"   Std: {np.std(ml_array):.2f}")
        print(f"   Min: {np.min(ml_array):.2f}")
        print(f"   Max: {np.max(ml_array):.2f}")
        print(f"   Positive predictions: {np.sum(ml_array > 0)} ({np.sum(ml_array > 0)/len(ml_array)*100:.1f}%)")
        print(f"   Negative predictions: {np.sum(ml_array < 0)} ({np.sum(ml_array < 0)/len(ml_array)*100:.1f}%)")
        print()
        
        # Analyze filter blocking
        filter_df = pd.DataFrame(filter_states)
        
        print(f"🚦 Filter Pass Rates:")
        print(f"   Volatility: {filter_df['volatility'].sum()}/{len(filter_df)} ({filter_df['volatility'].mean()*100:.1f}%)")
        print(f"   Regime: {filter_df['regime'].sum()}/{len(filter_df)} ({filter_df['regime'].mean()*100:.1f}%)")
        print(f"   ADX: {filter_df['adx'].sum()}/{len(filter_df)} ({filter_df['adx'].mean()*100:.1f}%)")
        print(f"   All filters: {filter_df['all_pass'].sum()}/{len(filter_df)} ({filter_df['all_pass'].mean()*100:.1f}%)")
        print()
        
        # Check signal generation
        signals_df = pd.DataFrame(signal_conditions)
        buy_signals = signals_df['is_buy_signal'].sum()
        sell_signals = signals_df['is_sell_signal'].sum()
        
        print(f"📈 Signals Generated:")
        print(f"   Buy signals: {buy_signals}")
        print(f"   Sell signals: {sell_signals}")
        print(f"   Total: {buy_signals + sell_signals}")
        print()
        
        # Find potential signal bars (strong ML predictions with filters passing)
        potential_buys = signals_df[
            (signals_df['ml_prediction'] >= 4) & 
            (filter_df['all_pass'] == True)
        ]
        
        potential_sells = signals_df[
            (signals_df['ml_prediction'] <= -4) & 
            (filter_df['all_pass'] == True)
        ]
        
        print(f"🎯 Potential Signal Opportunities:")
        print(f"   Strong buy conditions (ML >= 4): {len(potential_buys)}")
        print(f"   Strong sell conditions (ML <= -4): {len(potential_sells)}")
        print()
        
        # Show why signals might be blocked
        if buy_signals == 0 and sell_signals == 0:
            print("❌ No signals generated - Analyzing why:")
            
            # Check ML prediction strength
            strong_predictions = np.abs(ml_array) >= 4
            print(f"   - Strong ML predictions (|pred| >= 4): {np.sum(strong_predictions)}")
            
            # Check filter combinations
            if filter_df['all_pass'].sum() == 0:
                print("   - ⚠️ No bars where all filters pass!")
                
                # Which filter blocks most?
                print("   - Filter blocking analysis:")
                if filter_df['volatility'].mean() < 0.5:
                    print("     * Volatility filter blocks most bars")
                if filter_df['regime'].mean() < 0.5:
                    print("     * Regime filter blocks most bars")
                if filter_df['adx'].mean() < 0.5:
                    print("     * ADX filter blocks most bars")
            
            # Check kernel filter impact
            if config.use_kernel_filter:
                kernel_aligned = 0
                for idx, row in signals_df.iterrows():
                    if row['ml_prediction'] > 0 and filter_states[idx]['kernel_bull']:
                        kernel_aligned += 1
                    elif row['ml_prediction'] < 0 and filter_states[idx]['kernel_bear']:
                        kernel_aligned += 1
                
                print(f"   - Kernel alignment with ML: {kernel_aligned}/{len(signals_df)} ({kernel_aligned/len(signals_df)*100:.1f}%)")
        
        print()
        print("=" * 40)
        print()
    
    # Create visualization of ML predictions
    print("📊 Creating ML prediction visualization...")
    
    # Re-run with original config for visualization
    config = TradingConfig(
        max_bars_back=1000,
        neighbors_count=8,
        feature_count=5,
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        use_kernel_filter=True
    )
    
    processor = BarProcessor(config, total_bars=total_bars)
    ml_preds = []
    prices = []
    
    for i in range(total_bars):
        bar = df.iloc[i]
        result = processor.process_bar(
            open_price=bar['open'],  # Fixed parameter name
            high=bar['high'], 
            low=bar['low'],
            close=bar['close'],
            volume=bar['volume']
        )
        
        if i >= config.max_bars_back:
            ml_preds.append(result.prediction)
            prices.append(bar['close'])
    
    # Save detailed debug data
    debug_df = pd.DataFrame({
        'bar_index': range(config.max_bars_back, total_bars),
        'ml_prediction': ml_preds,
        'close_price': prices
    })
    
    debug_df.to_csv('ml_predictions_debug.csv', index=False)
    print(f"💾 Detailed predictions saved to: ml_predictions_debug.csv")
    
    print()
    print("🎯 Recommendations:")
    print("   1. If ML predictions are weak (mostly 0-3), try:")
    print("      - Different feature parameters")
    print("      - More historical data")
    print("   2. If filters block everything, try:")
    print("      - Disable kernel filter first")
    print("      - Adjust regime threshold")
    print("      - Check volatility in your data period")
    print("   3. If still no signals:")
    print("      - Compare feature calculations with Pine Script")
    print("      - Verify Lorentzian distance calculation")
    
    print()
    print("✅ Debug analysis complete!")

if __name__ == "__main__":
    debug_ml_predictions()
