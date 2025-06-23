#!/usr/bin/env python3
"""
Debug ML Predictions with Filters
=================================
Purpose: Debug why ML predictions are 0 when filters are ON
- Compare with filters ON vs OFF
- Check exact bar where ML starts
- Verify prediction calculations
"""

import pandas as pd
import os
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor

def debug_ml_with_filters():
    """Debug ML predictions with different filter configurations"""
    
    print("=" * 60)
    print("🔍 Debugging ML Predictions with Filters")
    print("=" * 60)
    print()
    
    # Load data
    data_file = "pinescript_style_ICICIBANK_2000bars.csv"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return
    
    df = pd.read_csv(data_file)
    print(f"📂 Loaded {len(df)} bars\n")
    
    # Test configurations
    test_configs = [
        {
            'name': 'All Filters OFF',
            'config': TradingConfig(
                max_bars_back=1000,
                neighbors_count=8,
                feature_count=5,
                # ALL filters OFF
                use_volatility_filter=False,
                use_regime_filter=False,
                use_adx_filter=False,
                use_kernel_filter=False,
                use_ema_filter=False,
                use_sma_filter=False
            )
        },
        {
            'name': 'Pine Script Defaults (Vol+Regime ON, ADX OFF)',
            'config': TradingConfig(
                max_bars_back=1000,
                neighbors_count=8,
                feature_count=5,
                # Pine Script defaults
                use_volatility_filter=True,
                use_regime_filter=True,
                use_adx_filter=False,  # OFF by default
                use_kernel_filter=True,
                use_ema_filter=False,
                use_sma_filter=False,
                regime_threshold=-0.1
            )
        },
        {
            'name': 'Only ML Filters (Vol+Regime+ADX)',
            'config': TradingConfig(
                max_bars_back=1000,
                neighbors_count=8,
                feature_count=5,
                # Only ML layer filters
                use_volatility_filter=True,
                use_regime_filter=True,
                use_adx_filter=False,
                use_kernel_filter=False,  # Entry layer filter OFF
                use_ema_filter=False,
                use_sma_filter=False
            )
        }
    ]
    
    for test in test_configs:
        print(f"\n{'='*50}")
        print(f"🔧 Testing: {test['name']}")
        print(f"{'='*50}")
        
        processor = BarProcessor(test['config'])
        
        # Track ML start and predictions
        ml_start_bar = None
        first_nonzero_prediction = None
        predictions = []
        filter_pass_count = {
            'volatility': 0,
            'regime': 0,
            'adx': 0,
            'all': 0
        }
        
        # Key bars to check
        check_bars = [998, 999, 1000, 1001, 1002, 1003, 1004, 1005, 1010, 1050, 1100, 1500]
        
        print(f"\n📊 Processing bars...")
        
        for i in range(len(df)):
            bar = df.iloc[i]
            
            result = processor.process_bar(
                open_price=bar['open'],
                high=bar['high'],
                low=bar['low'],
                close=bar['close'],
                volume=bar['volume']
            )
            
            # Track when ML starts
            if result.prediction != 0.0 and ml_start_bar is None:
                ml_start_bar = i
                first_nonzero_prediction = result.prediction
            
            # Track predictions
            predictions.append(result.prediction)
            
            # Track filter pass rates
            if i >= 1000:  # After ML should start
                if result.filter_states.get('volatility', True):
                    filter_pass_count['volatility'] += 1
                if result.filter_states.get('regime', True):
                    filter_pass_count['regime'] += 1
                if result.filter_states.get('adx', True):
                    filter_pass_count['adx'] += 1
                if all(result.filter_states.values()):
                    filter_pass_count['all'] += 1
            
            # Debug specific bars
            if i in check_bars:
                filters = result.filter_states
                print(f"   Bar {i:4d}: Pred={result.prediction:6.2f}, Signal={result.signal:2d}, "
                      f"Vol={'✓' if filters.get('volatility', True) else '✗'}, "
                      f"Reg={'✓' if filters.get('regime', True) else '✗'}, "
                      f"ADX={'✓' if filters.get('adx', True) else '✗'}")
        
        # Summary
        non_zero_predictions = [p for p in predictions if p != 0.0]
        bars_after_ml_start = len(df) - 1000 if ml_start_bar else 0
        
        print(f"\n📈 Results:")
        print(f"   ML started at bar: {ml_start_bar}")
        print(f"   First prediction: {first_nonzero_prediction}")
        print(f"   Total non-zero predictions: {len(non_zero_predictions)}")
        
        if non_zero_predictions:
            print(f"   Prediction range: [{min(non_zero_predictions):.2f}, {max(non_zero_predictions):.2f}]")
        
        if bars_after_ml_start > 0:
            print(f"\n   Filter Pass Rates (after bar 1000):")
            print(f"   - Volatility: {filter_pass_count['volatility']}/{bars_after_ml_start} "
                  f"({filter_pass_count['volatility']/bars_after_ml_start*100:.1f}%)")
            print(f"   - Regime: {filter_pass_count['regime']}/{bars_after_ml_start} "
                  f"({filter_pass_count['regime']/bars_after_ml_start*100:.1f}%)")
            print(f"   - ADX: {filter_pass_count['adx']}/{bars_after_ml_start} "
                  f"({filter_pass_count['adx']/bars_after_ml_start*100:.1f}%)")
            print(f"   - All Pass: {filter_pass_count['all']}/{bars_after_ml_start} "
                  f"({filter_pass_count['all']/bars_after_ml_start*100:.1f}%)")
    
    print("\n" + "="*60)
    print("🔍 Analysis Complete!")
    print("="*60)
    
    print("\n💡 Key Insights:")
    print("1. If ML predictions are 0 with filters ON but work with filters OFF,")
    print("   there might be an issue with filter interaction")
    print("2. If predictions are non-zero but signals aren't generated,")
    print("   filters are blocking signal updates")
    print("3. Check if volatility and regime filters are too restrictive")

if __name__ == "__main__":
    debug_ml_with_filters()
