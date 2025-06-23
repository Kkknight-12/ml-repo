#!/usr/bin/env python3
"""
Final Test - Verify ML Predictions are Working with Filters ON
This should show that ML predictions work independently of filters
"""

import pandas as pd
import numpy as np
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
import sys

def generate_strong_trend_data(num_bars=500):
    """Generate data with strong trend to ensure good ML predictions"""
    dates = pd.date_range(start='2024-01-01', periods=num_bars, freq='5min')
    
    # Create a strong uptrend with some volatility
    base_price = 100.0
    data = []
    
    for i, date in enumerate(dates):
        # Strong trend component
        trend = i * 0.1  # 10 cents per bar
        
        # Add some sine wave for cyclical movement
        cycle = 2 * np.sin(i * 0.1)
        
        # Add random noise
        noise = np.random.normal(0, 0.5)
        
        close = base_price + trend + cycle + noise
        
        # Create realistic OHLC
        open_price = data[-1]['close'] if data else base_price
        high = max(open_price, close) + abs(np.random.normal(0, 0.2))
        low = min(open_price, close) - abs(np.random.normal(0, 0.2))
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.randint(1000, 5000)
        })
    
    return pd.DataFrame(data)

def main():
    print("🚀 FINAL TEST: ML Predictions with Filters")
    print("=" * 70)
    print("This test verifies that ML predictions work independently of filters")
    print("=" * 70)
    
    # Generate test data
    data = generate_strong_trend_data(500)
    print(f"\n✅ Generated {len(data)} bars of trending data")
    print(f"   Price range: ${data['close'].min():.2f} to ${data['close'].max():.2f}")
    
    # Configuration with ALL filters ON (Pine Script defaults)
    config = TradingConfig(
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,  # Pine Script default
        use_kernel_filter=True,
        use_kernel_smoothing=False,  # Pine Script default
        max_bars_back=200,
        neighbors_count=8,
        feature_count=5
    )
    
    print(f"\n📊 Configuration:")
    print(f"   Volatility Filter: ON")
    print(f"   Regime Filter: ON")
    print(f"   ADX Filter: OFF (default)")
    print(f"   Kernel Filter: ON")
    print(f"   Max Bars Back: {config.max_bars_back}")
    
    # Create processor with symbol and timeframe
    processor = EnhancedBarProcessor(config, "TEST_TREND", "5minute")
    
    # Track results
    ml_predictions = []
    signals = []
    filter_results = []
    entry_signals = []
    
    print(f"\n🔄 Processing bars...")
    
    # Process each bar
    for i, row in data.iterrows():
        result = processor.process_bar(
            open_price=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume']
        )
        
        if result and result.bar_index > 50:  # After warmup period
            # Track ML prediction (raw value)
            ml_predictions.append(result.prediction)
            
            # Track signal (after filters)
            signals.append(result.signal)
            
            # Track filter results
            filter_results.append({
                'bar': result.bar_index,
                'prediction': result.prediction,
                'signal': result.signal,
                'vol_filter': result.filter_states['volatility'],
                'regime_filter': result.filter_states['regime'],
                'all_pass': all(result.filter_states.values())
            })
            
            # Track entry signals
            if result.start_long_trade:
                entry_signals.append(('LONG', result.bar_index, result.close))
            elif result.start_short_trade:
                entry_signals.append(('SHORT', result.bar_index, result.close))
    
    # Analyze results
    print(f"\n📊 RESULTS ANALYSIS")
    print("=" * 50)
    
    # ML Predictions
    non_zero_predictions = [p for p in ml_predictions if p != 0]
    print(f"\n1️⃣ ML PREDICTIONS (Raw Values):")
    print(f"   Total predictions: {len(ml_predictions)}")
    print(f"   Non-zero predictions: {len(non_zero_predictions)}")
    
    if non_zero_predictions:
        print(f"   ✅ Prediction range: {min(non_zero_predictions):.2f} to {max(non_zero_predictions):.2f}")
        print(f"   ✅ Average: {np.mean(non_zero_predictions):.2f}")
        print(f"   ✅ Sample (last 10): {[round(p, 2) for p in non_zero_predictions[-10:]]}")
        
        # Distribution
        positive = len([p for p in non_zero_predictions if p > 0])
        negative = len([p for p in non_zero_predictions if p < 0])
        print(f"   ✅ Distribution: {positive} positive, {negative} negative")
    else:
        print(f"   ❌ NO ML PREDICTIONS GENERATED!")
    
    # Filter Analysis
    print(f"\n2️⃣ FILTER ANALYSIS:")
    if filter_results:
        df_filters = pd.DataFrame(filter_results)
        vol_pass_rate = df_filters['vol_filter'].sum() / len(df_filters) * 100
        regime_pass_rate = df_filters['regime_filter'].sum() / len(df_filters) * 100
        all_pass_rate = df_filters['all_pass'].sum() / len(df_filters) * 100
        
        print(f"   Volatility Filter: {vol_pass_rate:.1f}% pass rate")
        print(f"   Regime Filter: {regime_pass_rate:.1f}% pass rate")
        print(f"   All Filters: {all_pass_rate:.1f}% pass rate")
    
    # Signal Analysis
    print(f"\n3️⃣ SIGNAL ANALYSIS (After Filters):")
    non_zero_signals = [s for s in signals if s != 0]
    print(f"   Total signals: {len(signals)}")
    print(f"   Non-zero signals: {len(non_zero_signals)}")
    
    # Entry Signals
    print(f"\n4️⃣ ENTRY SIGNALS:")
    print(f"   Total entries: {len(entry_signals)}")
    if entry_signals:
        for signal_type, bar, price in entry_signals[-5:]:  # Last 5
            print(f"   {signal_type} at bar {bar}, price ${price:.2f}")
    
    # Key Examples
    print(f"\n5️⃣ KEY EXAMPLES - Prediction vs Signal:")
    examples = [r for r in filter_results[-20:] if abs(r['prediction']) > 2][:5]
    for ex in examples:
        print(f"\n   Bar {ex['bar']}:")
        print(f"     ML Prediction: {ex['prediction']:.2f} (raw ML output)")
        print(f"     Signal: {ex['signal']} (after filters)")
        print(f"     Filters: Vol={ex['vol_filter']}, Regime={ex['regime_filter']}, All={ex['all_pass']}")
    
    # Final Verdict
    print(f"\n{'='*70}")
    print("🎯 FINAL VERDICT:")
    print(f"{'='*70}")
    
    if non_zero_predictions:
        print(f"\n✅ SUCCESS! ML predictions are working!")
        print(f"   - ML generates predictions in range {min(non_zero_predictions):.0f} to {max(non_zero_predictions):.0f}")
        print(f"   - This is independent of filter status")
        print(f"   - Filters only affect the final SIGNAL, not the PREDICTION")
        
        if len(non_zero_signals) < len(non_zero_predictions):
            print(f"\n💡 Filters are working correctly:")
            print(f"   - {len(non_zero_predictions)} ML predictions")
            print(f"   - {len(non_zero_signals)} signals (after filtering)")
            print(f"   - {len(entry_signals)} entry signals generated")
    else:
        print(f"\n❌ ISSUE: ML predictions still returning 0")
        print(f"\n🔍 Debug the following:")
        print(f"   1. Check training labels distribution")
        print(f"   2. Verify neighbor selection in KNN")
        print(f"   3. Check feature calculations")
        print(f"   4. Run diagnose_training_labels.py for more info")
    
    # ML Model State
    print(f"\n📊 ML MODEL STATE:")
    print(f"   Training data size: {len(processor.ml_model.y_train_array)}")
    if processor.ml_model.y_train_array:
        last_20 = processor.ml_model.y_train_array[-20:]
        print(f"   Last 20 labels: L={last_20.count(1)}, S={last_20.count(-1)}, N={last_20.count(0)}")

if __name__ == "__main__":
    main()
