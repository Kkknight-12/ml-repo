#!/usr/bin/env python3
"""
Comprehensive ML Debug - Test Multiple Scenarios
"""

import pandas as pd
import numpy as np
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor

def create_trending_data(num_bars=300, trend_type='up'):
    """Create data with clear trend for testing"""
    dates = pd.date_range(start='2024-01-01', periods=num_bars, freq='5min')
    
    if trend_type == 'up':
        # Uptrend with noise
        base_price = 100
        prices = []
        for i in range(num_bars):
            trend = i * 0.05  # 5 cents per bar upward
            noise = np.random.normal(0, 0.5)  # Some volatility
            price = base_price + trend + noise
            prices.append(price)
    else:
        # Downtrend
        base_price = 150
        prices = []
        for i in range(num_bars):
            trend = i * -0.05  # 5 cents per bar downward
            noise = np.random.normal(0, 0.5)
            price = base_price + trend + noise
            prices.append(price)
    
    # Create OHLC from prices
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        open_price = prices[i-1] if i > 0 else close
        high = max(open_price, close) + abs(np.random.normal(0, 0.1))
        low = min(open_price, close) - abs(np.random.normal(0, 0.1))
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.randint(1000, 5000)
        })
    
    return pd.DataFrame(data)

def test_scenario(name, config, data):
    """Test a specific scenario"""
    print(f"\n{'='*60}")
    print(f"📊 SCENARIO: {name}")
    print(f"{'='*60}")
    
    processor = BarProcessor(config)
    
    results = {
        'predictions': [],
        'signals': [],
        'filter_passes': 0,
        'entries': 0
    }
    
    # Process all bars
    for i, row in data.iterrows():
        result = processor.process_bar(
            open_price=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume']
        )
        
        if result and result.bar_index > 50:  # After warmup
            results['predictions'].append(result.prediction)
            results['signals'].append(result.signal)
            
            if all(result.filter_states.values()):
                results['filter_passes'] += 1
            
            if result.start_long_trade or result.start_short_trade:
                results['entries'] += 1
    
    # Analyze results
    non_zero_predictions = [p for p in results['predictions'] if p != 0]
    
    print(f"\n📊 Results:")
    print(f"  Total bars processed: {len(data)}")
    print(f"  ML Predictions generated: {len(results['predictions'])}")
    print(f"  Non-zero predictions: {len(non_zero_predictions)}")
    
    if non_zero_predictions:
        print(f"  Prediction range: {min(non_zero_predictions):.2f} to {max(non_zero_predictions):.2f}")
        print(f"  Average prediction: {np.mean(non_zero_predictions):.2f}")
        print(f"  Last 5 predictions: {non_zero_predictions[-5:]}")
    
    print(f"\n  Filter passes: {results['filter_passes']}")
    print(f"  Entry signals: {results['entries']}")
    
    # Check ML model state
    print(f"\n  ML Model State:")
    print(f"    Training data: {len(processor.ml_model.y_train_array)} labels")
    if processor.ml_model.y_train_array:
        last_10_labels = processor.ml_model.y_train_array[-10:]
        long_count = last_10_labels.count(1)
        short_count = last_10_labels.count(-1)
        neutral_count = last_10_labels.count(0)
        print(f"    Last 10 labels: L={long_count}, S={short_count}, N={neutral_count}")
    
    return len(non_zero_predictions) > 0

def main():
    print("🔍 Comprehensive ML Debug Test")
    print("Testing multiple scenarios to isolate the issue")
    
    # Generate test data
    uptrend_data = create_trending_data(300, 'up')
    downtrend_data = create_trending_data(300, 'down')
    
    # Scenario 1: Baseline - No filters
    config1 = TradingConfig(
        use_volatility_filter=False,
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=False,
        max_bars_back=200
    )
    success1 = test_scenario("No Filters (Baseline)", config1, uptrend_data)
    
    # Scenario 2: Only Volatility Filter
    config2 = TradingConfig(
        use_volatility_filter=True,
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=False,
        max_bars_back=200
    )
    success2 = test_scenario("Volatility Filter Only", config2, uptrend_data)
    
    # Scenario 3: Only Regime Filter
    config3 = TradingConfig(
        use_volatility_filter=False,
        use_regime_filter=True,
        use_adx_filter=False,
        use_kernel_filter=False,
        max_bars_back=200,
        regime_threshold=-0.1  # Default from Pine Script
    )
    success3 = test_scenario("Regime Filter Only", config3, uptrend_data)
    
    # Scenario 4: All Filters (Pine Script default)
    config4 = TradingConfig(
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,  # Default OFF
        use_kernel_filter=True,
        max_bars_back=200
    )
    success4 = test_scenario("All Filters ON", config4, uptrend_data)
    
    # Scenario 5: Downtrend with all filters
    success5 = test_scenario("Downtrend - All Filters", config4, downtrend_data)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print(f"{'='*60}")
    print(f"Scenario 1 (No Filters): {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"Scenario 2 (Volatility): {'✅ PASS' if success2 else '❌ FAIL'}")
    print(f"Scenario 3 (Regime): {'✅ PASS' if success3 else '❌ FAIL'}")
    print(f"Scenario 4 (All Filters): {'✅ PASS' if success4 else '❌ FAIL'}")
    print(f"Scenario 5 (Downtrend): {'✅ PASS' if success5 else '❌ FAIL'}")
    
    if success1 and not success4:
        print("\n💡 DIAGNOSIS: Filters are blocking ML predictions")
        print("   The fix should have separated predictions from signals.")
        print("   Check the debug output above for more details.")
    elif not success1:
        print("\n💡 DIAGNOSIS: ML predictions not working even without filters")
        print("   Check training label distribution and neighbor selection.")

if __name__ == "__main__":
    main()
