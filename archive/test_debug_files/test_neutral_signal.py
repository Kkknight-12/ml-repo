#!/usr/bin/env python3
"""
Test with neutral signal initialization
Quick test to see if starting with neutral signal helps
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from utils.sample_data import generate_trending_data


def test_neutral_signal():
    """Test if neutral signal initialization helps"""
    
    print("=" * 70)
    print("🧪 TESTING NEUTRAL SIGNAL INITIALIZATION")
    print("=" * 70)
    
    # Simple config with most filters off
    config = TradingConfig(
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,  # OFF by default
        use_kernel_filter=False,  # OFF for testing
        use_ema_filter=False,
        use_sma_filter=False,
        max_bars_back=200
    )
    
    processor = EnhancedBarProcessor(config, "TEST", "5minute")
    
    # Check initial signal state
    print(f"\n📊 Initial ML Model State:")
    print(f"   Signal: {processor.ml_model.signal}")
    print(f"   Label values - Long: {processor.ml_model.label.long}, Short: {processor.ml_model.label.short}, Neutral: {processor.ml_model.label.neutral}")
    
    # Generate test data
    data = generate_trending_data(300)
    
    # Track signals
    signals = []
    predictions = []
    entries = []
    signal_changes = 0
    last_signal = None
    
    print(f"\n🔄 Processing {len(data)} bars...")
    
    for i, (o, h, l, c, v) in enumerate(data):
        result = processor.process_bar(o, h, l, c, v)
        
        if result and i >= 50:  # After warmup
            signals.append(result.signal)
            predictions.append(result.prediction)
            
            # Track signal changes
            if last_signal is not None and result.signal != last_signal:
                signal_changes += 1
                print(f"\n🔔 Signal Change at bar {i}:")
                print(f"   From: {last_signal} → To: {result.signal}")
                print(f"   ML Prediction: {result.prediction:.2f}")
                print(f"   Filters: {result.filter_states}")
            
            last_signal = result.signal
            
            # Track entries
            if result.start_long_trade or result.start_short_trade:
                entry_type = 'LONG' if result.start_long_trade else 'SHORT'
                entries.append((i, entry_type))
                print(f"\n✅ ENTRY SIGNAL at bar {i}: {entry_type}")
    
    # Analysis
    print(f"\n\n{'='*70}")
    print("📊 RESULTS ANALYSIS")
    print(f"{'='*70}")
    
    # Signal distribution
    if signals:
        unique_signals = set(signals)
        print(f"\n1️⃣ Signal Distribution:")
        for sig in sorted(unique_signals):
            count = signals.count(sig)
            pct = (count / len(signals)) * 100
            sig_name = 'LONG' if sig == 1 else 'SHORT' if sig == -1 else 'NEUTRAL'
            print(f"   {sig_name} ({sig}): {count} ({pct:.1f}%)")
    
    # ML predictions
    if predictions:
        non_zero = [p for p in predictions if p != 0]
        if non_zero:
            print(f"\n2️⃣ ML Predictions:")
            print(f"   Non-zero: {len(non_zero)}")
            print(f"   Range: {min(non_zero):.2f} to {max(non_zero):.2f}")
            print(f"   Positive: {sum(1 for p in non_zero if p > 0)}")
            print(f"   Negative: {sum(1 for p in non_zero if p < 0)}")
    
    print(f"\n3️⃣ Signal Transitions:")
    print(f"   Total changes: {signal_changes}")
    
    print(f"\n4️⃣ Entry Signals:")
    print(f"   Total entries: {len(entries)}")
    if entries:
        for bar, entry_type in entries[:5]:
            print(f"   Bar {bar}: {entry_type}")
    
    # Diagnosis
    print(f"\n\n💡 DIAGNOSIS:")
    if signal_changes == 0:
        print("   ❌ No signal changes - Signal is stuck!")
        print("   📍 Check if ML model signal is initialized properly")
        print("   📍 Verify signal update logic when filters pass/fail")
    elif len(entries) == 0:
        print("   ⚠️  Signal changes but no entries")
        print("   📍 Check entry conditions (kernel, trends)")
    else:
        print("   ✅ System working - entries generated!")
    
    return len(entries) > 0


if __name__ == "__main__":
    success = test_neutral_signal()
    print(f"\n{'='*70}")
    print(f"Test {'PASSED' if success else 'FAILED'}")
