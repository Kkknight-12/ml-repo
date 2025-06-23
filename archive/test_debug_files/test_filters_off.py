#!/usr/bin/env python3
"""
Test filters OFF to verify ML is working
This follows Pine Script logic exactly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor

print("="*70)
print("TESTING WITH FILTERS OFF (Pine Script Style)")
print("="*70)

# Create config with filters OFF
config = TradingConfig(
    # Core settings - same as Pine Script
    neighbors_count=8,
    max_bars_back=2000,
    feature_count=5,
    
    # FILTERS OFF FOR TESTING
    use_volatility_filter=False,  # OFF
    use_regime_filter=False,      # OFF
    use_adx_filter=False,         # OFF (Pine Script default)
    
    # Keep other Pine Script defaults
    regime_threshold=-0.1,
    adx_threshold=20,
    use_kernel_filter=True,
    use_kernel_smoothing=False,
)

print("\nConfiguration:")
print(f"  Volatility Filter: {config.use_volatility_filter} (OFF)")
print(f"  Regime Filter: {config.use_regime_filter} (OFF)")
print(f"  ADX Filter: {config.use_adx_filter} (OFF)")
print(f"  Kernel Filter: {config.use_kernel_filter} (ON)")

# Create processor
processor = EnhancedBarProcessor(config, "TEST", "day")

# Generate simple test data
print("\nGenerating test data...")
prices = []
base = 1000.0

# Create trending data
for i in range(100):
    price = base + i * 0.5  # Upward trend
    prices.append(price)

# Process bars
print("\nProcessing bars with filters OFF...")
ml_predictions = []
signals = []

for i, close in enumerate(prices):
    if i < 4:  # Need history
        continue
        
    # Simple OHLC
    high = close + 1
    low = close - 1
    open_price = close - 0.5
    
    result = processor.process_bar(open_price, high, low, close, 10000)
    
    if result and result.prediction != 0:
        ml_predictions.append(result.prediction)
        signals.append(result.signal)
        
        if i % 20 == 0:
            print(f"\nBar {i}: Price={close:.2f}")
            print(f"  ML Prediction: {result.prediction}")
            print(f"  Signal: {result.signal}")
            print(f"  Filters: {result.filter_states}")

print(f"\n{'='*70}")
print("RESULTS WITH FILTERS OFF:")
print(f"{'='*70}")
print(f"Total ML predictions: {len(ml_predictions)}")
if ml_predictions:
    print(f"Prediction range: {min(ml_predictions)} to {max(ml_predictions)}")
    print(f"Unique signals: {set(signals)}")
else:
    print("⚠️  NO ML PREDICTIONS - Check implementation!")

print("\nNEXT STEPS:")
print("1. If ML predictions work with filters OFF, the issue is filter settings")
print("2. Enable one filter at a time to find which is blocking")
print("3. For daily data, may need to adjust thresholds or use different timeframe")
