#!/usr/bin/env python3
"""
Test with Potential Fixes
=========================
Purpose: Try different configurations to get signals working
- Adjust filter thresholds
- Try different max_bars_back
- Test with kernel filter OFF
"""

import pandas as pd
import os
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor

def test_with_fixes():
    """Test with various fixes to get signals"""
    
    print("=" * 60)
    print("🔧 Testing with Potential Fixes")
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
            'name': 'Fix 1: Smaller max_bars_back',
            'config': TradingConfig(
                max_bars_back=500,  # Smaller window
                neighbors_count=8,
                feature_count=5,
                use_volatility_filter=True,
                use_regime_filter=True,
                use_adx_filter=False,
                use_kernel_filter=True,
                use_ema_filter=False,
                use_sma_filter=False,
                regime_threshold=-0.1
            )
        },
        {
            'name': 'Fix 2: Kernel Filter OFF',
            'config': TradingConfig(
                max_bars_back=500,
                neighbors_count=8,
                feature_count=5,
                use_volatility_filter=True,
                use_regime_filter=True,
                use_adx_filter=False,
                use_kernel_filter=False,  # Turn OFF kernel
                use_ema_filter=False,
                use_sma_filter=False,
                regime_threshold=-0.1
            )
        },
        {
            'name': 'Fix 3: Relaxed Regime Threshold',
            'config': TradingConfig(
                max_bars_back=500,
                neighbors_count=8,
                feature_count=5,
                use_volatility_filter=True,
                use_regime_filter=True,
                use_adx_filter=False,
                use_kernel_filter=False,
                use_ema_filter=False,
                use_sma_filter=False,
                regime_threshold=0.5  # More relaxed (was -0.1)
            )
        },
        {
            'name': 'Fix 4: Only Volatility Filter',
            'config': TradingConfig(
                max_bars_back=500,
                neighbors_count=8,
                feature_count=5,
                use_volatility_filter=True,
                use_regime_filter=False,  # OFF
                use_adx_filter=False,
                use_kernel_filter=False,
                use_ema_filter=False,
                use_sma_filter=False
            )
        },
        {
            'name': 'Fix 5: No ML Filters (only entry filters)',
            'config': TradingConfig(
                max_bars_back=500,
                neighbors_count=8,
                feature_count=5,
                use_volatility_filter=False,
                use_regime_filter=False,
                use_adx_filter=False,
                use_kernel_filter=True,  # Only entry layer filter
                use_ema_filter=False,
                use_sma_filter=False
            )
        }
    ]
    
    for test in test_configs:
        print(f"\n{'='*50}")
        print(f"🧪 {test['name']}")
        print(f"{'='*50}")
        
        processor = BarProcessor(test['config'])
        
        # Track signals
        buy_signals = []
        sell_signals = []
        ml_predictions_count = 0
        filter_stats = {
            'vol_pass': 0,
            'regime_pass': 0,
            'total_bars': 0
        }
        
        # Process bars
        for i in range(len(df)):
            bar = df.iloc[i]
            
            result = processor.process_bar(
                open_price=bar['open'],
                high=bar['high'],
                low=bar['low'],
                close=bar['close'],
                volume=bar['volume']
            )
            
            # Track ML predictions
            if result.prediction != 0:
                ml_predictions_count += 1
            
            # Track filter pass rates after ML starts
            if i >= test['config'].max_bars_back:
                filter_stats['total_bars'] += 1
                if result.filter_states.get('volatility', True):
                    filter_stats['vol_pass'] += 1
                if result.filter_states.get('regime', True):
                    filter_stats['regime_pass'] += 1
            
            # Track signals
            if result.start_long_trade:
                buy_signals.append(i)
            if result.start_short_trade:
                sell_signals.append(i)
        
        # Results
        print(f"\n📊 Results:")
        print(f"  ML Predictions: {ml_predictions_count}")
        print(f"  Buy Signals: {len(buy_signals)}")
        print(f"  Sell Signals: {len(sell_signals)}")
        print(f"  Total Signals: {len(buy_signals) + len(sell_signals)}")
        
        if filter_stats['total_bars'] > 0:
            print(f"\n  Filter Pass Rates:")
            print(f"  - Volatility: {filter_stats['vol_pass']/filter_stats['total_bars']*100:.1f}%")
            print(f"  - Regime: {filter_stats['regime_pass']/filter_stats['total_bars']*100:.1f}%")
        
        if buy_signals or sell_signals:
            print(f"\n  ✅ SUCCESS! Signals generated!")
            print(f"  First buy signal at bar: {buy_signals[0] if buy_signals else 'N/A'}")
            print(f"  First sell signal at bar: {sell_signals[0] if sell_signals else 'N/A'}")
    
    print("\n" + "="*60)
    print("🎯 Testing Complete!")
    print("="*60)
    
    print("\n💡 Recommendations:")
    print("1. If Fix 2 (Kernel OFF) works → Kernel filter is too restrictive")
    print("2. If Fix 3 (Relaxed Regime) works → Regime threshold needs adjustment")
    print("3. If Fix 5 (No ML filters) works → ML layer filters are the issue")
    print("4. If none work → Need to debug ML predictions themselves")

if __name__ == "__main__":
    test_with_fixes()
