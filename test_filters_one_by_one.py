#!/usr/bin/env python3
"""
Test filters one by one to identify which is blocking signals
Following Pine Script defaults exactly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
import random

print("="*70)
print("FILTER TEST - One by One (Pine Script Defaults)")
print("="*70)

def test_configuration(name, volatility=False, regime=False, adx=False):
    """Test a specific filter configuration"""
    print(f"\n{'='*50}")
    print(f"Testing: {name}")
    print(f"{'='*50}")
    
    config = TradingConfig(
        # Core settings
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        
        # Filter settings
        use_volatility_filter=volatility,
        use_regime_filter=regime,
        use_adx_filter=adx,
        
        # Pine Script defaults
        regime_threshold=-0.1,
        adx_threshold=20,
        use_kernel_filter=True,
        use_kernel_smoothing=False,
    )
    
    print(f"Filters: Volatility={volatility}, Regime={regime}, ADX={adx}")
    
    # Create processor
    processor = EnhancedBarProcessor(config, "TEST", "day")
    
    # Generate realistic daily data
    prices = []
    base = 1000.0
    
    for i in range(200):
        # Add trend and volatility
        trend = i * 0.3
        volatility = random.gauss(0, 10)
        price = base + trend + volatility
        prices.append(price)
    
    # Process bars
    ml_predictions = []
    signal_changes = 0
    last_signal = None
    filter_passes = 0
    
    for i in range(4, len(prices)):
        close = prices[i]
        open_price = prices[i-1]
        high = max(close, open_price) + abs(random.gauss(0, 2))
        low = min(close, open_price) - abs(random.gauss(0, 2))
        volume = random.uniform(1000000, 2000000)
        
        result = processor.process_bar(open_price, high, low, close, volume)
        
        if result:
            if result.prediction != 0:
                ml_predictions.append(result.prediction)
            
            # Check filter passes
            if all(result.filter_states.values()):
                filter_passes += 1
            
            # Track signal changes
            if last_signal is not None and result.signal != last_signal:
                signal_changes += 1
            last_signal = result.signal
    
    # Results
    print(f"\nResults:")
    print(f"  ML Predictions: {len(ml_predictions)}")
    print(f"  Filter pass rate: {filter_passes}/{len(prices)-4} = {filter_passes/(len(prices)-4)*100:.1f}%")
    print(f"  Signal changes: {signal_changes}")
    
    return filter_passes > 0

# Test configurations
print("\n" + "="*70)
print("TESTING EACH FILTER INDIVIDUALLY")
print("="*70)

# Test 1: All OFF (baseline)
test_configuration("ALL FILTERS OFF", False, False, False)

# Test 2: Only Volatility ON
vol_passes = test_configuration("ONLY VOLATILITY ON", True, False, False)

# Test 3: Only Regime ON
regime_passes = test_configuration("ONLY REGIME ON", False, True, False)

# Test 4: Only ADX ON
adx_passes = test_configuration("ONLY ADX ON", False, False, True)

# Test 5: Volatility + Regime (Pine Script default)
both_passes = test_configuration("VOLATILITY + REGIME (Pine Default)", True, True, False)

# Test 6: All ON
all_passes = test_configuration("ALL FILTERS ON", True, True, True)

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"Volatility filter passes: {vol_passes}")
print(f"Regime filter passes: {regime_passes}")
print(f"ADX filter passes: {adx_passes}")
print(f"Pine Script default (Vol+Regime): {both_passes}")

print("\nCONCLUSION:")
if not vol_passes and not regime_passes:
    print("❌ Both main filters are too restrictive for daily data!")
    print("   This is why you see 0% pass rate in your report.")
    print("\nSOLUTIONS:")
    print("1. Use intraday data (5min, 15min) for more volatility")
    print("2. OR adjust thresholds (but this deviates from Pine Script)")
    print("3. OR accept that daily data produces fewer signals")
