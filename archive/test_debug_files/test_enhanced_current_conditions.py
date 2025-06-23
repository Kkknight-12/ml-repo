#!/usr/bin/env python3
"""
Enhanced Test Script - Test ML with current conditions
Shows detailed debug info for entry signal generation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from utils.sample_data import generate_trending_data, generate_volatile_data
import json


def analyze_entry_conditions(processor: EnhancedBarProcessor, result):
    """Detailed analysis of why entry signals are/aren't generated"""
    
    # Get current states
    signal = result.signal
    prediction = result.prediction
    
    # Get historical data for checks
    signal_history = processor.signal_history
    
    # Check each condition
    conditions = {
        "ML Prediction": {
            "value": prediction,
            "requirement": "Must be non-zero",
            "passed": prediction != 0
        },
        "Signal Direction": {
            "value": signal,
            "requirement": "1 for long, -1 for short",
            "passed": signal != 0
        },
        "Signal Changed": {
            "value": f"Current: {signal}, Previous: {signal_history[0] if signal_history else 'None'}",
            "requirement": "Must be different from previous",
            "passed": len(signal_history) == 0 or signal != signal_history[0]
        },
        "Filters Passed": {
            "value": result.filter_states,
            "requirement": "All must be True",
            "passed": all(result.filter_states.values())
        }
    }
    
    # Get filter details
    if processor.config.use_kernel_filter:
        is_bullish = processor._calculate_kernel_bullish()
        is_bearish = processor._calculate_kernel_bearish()
        conditions["Kernel Filter"] = {
            "value": f"Bullish: {is_bullish}, Bearish: {is_bearish}",
            "requirement": "Must match signal direction",
            "passed": (signal > 0 and is_bullish) or (signal < 0 and is_bearish)
        }
    
    # EMA/SMA filters
    if processor.config.use_ema_filter:
        ema_up, ema_down = processor._calculate_ema_trend()
        conditions["EMA Filter"] = {
            "value": f"Uptrend: {ema_up}, Downtrend: {ema_down}",
            "requirement": "Must match signal direction",
            "passed": (signal > 0 and ema_up) or (signal < 0 and ema_down)
        }
        
    if processor.config.use_sma_filter:
        sma_up, sma_down = processor._calculate_sma_trend()
        conditions["SMA Filter"] = {
            "value": f"Uptrend: {sma_up}, Downtrend: {sma_down}",
            "requirement": "Must match signal direction",
            "passed": (signal > 0 and sma_up) or (signal < 0 and sma_down)
        }
    
    return conditions


def run_enhanced_test():
    """Run test with detailed debugging"""
    
    print("=" * 70)
    print("🔍 ENHANCED ML TEST WITH CURRENT CONDITIONS")
    print("=" * 70)
    
    # Use default configuration
    config = TradingConfig()
    
    # Show current configuration
    print("\n📋 CURRENT CONFIGURATION:")
    print(f"  Timeframe: User-configurable (not hardcoded)")
    print(f"  Neighbors: {config.neighbors_count}")
    print(f"  Features: {config.feature_count}")
    print(f"  Max bars back: {config.max_bars_back}")
    print(f"\n  FILTERS:")
    print(f"  - Volatility: {'ON' if config.use_volatility_filter else 'OFF'}")
    print(f"  - Regime: {'ON' if config.use_regime_filter else 'OFF'} (threshold: {config.regime_threshold})")
    print(f"  - ADX: {'ON' if config.use_adx_filter else 'OFF'} (threshold: {config.adx_threshold})")
    print(f"  - Kernel: {'ON' if config.use_kernel_filter else 'OFF'}")
    print(f"  - EMA: {'ON' if config.use_ema_filter else 'OFF'} (period: {config.ema_period})")
    print(f"  - SMA: {'ON' if config.use_sma_filter else 'OFF'} (period: {config.sma_period})")
    
    # Generate test data
    print("\n📊 Generating test data...")
    data = generate_trending_data(500)
    
    # Initialize processor with symbol and timeframe
    processor = EnhancedBarProcessor(config, "TEST", "5minute")
    
    # Track results
    ml_predictions = []
    entry_signals = []
    failed_entries = []
    
    print("\n🔄 Processing bars...\n")
    
    # Process bars
    for i, (o, h, l, c, v) in enumerate(data):
        result = processor.process_bar(o, h, l, c, v)
        
        if result:
            # Track ML predictions
            if result.prediction != 0:
                ml_predictions.append({
                    'bar': i,
                    'prediction': result.prediction,
                    'signal': result.signal
                })
            
            # Track entry signals
            if result.start_long_trade or result.start_short_trade:
                entry_signals.append({
                    'bar': i,
                    'type': 'LONG' if result.start_long_trade else 'SHORT',
                    'price': result.close,
                    'prediction': result.prediction
                })
                
            # Detailed debug every 50 bars after warmup
            if i > 100 and i % 50 == 0:
                print(f"Bar {i}:")
                print(f"  ML Prediction: {result.prediction:.2f}")
                print(f"  Signal: {result.signal}")
                print(f"  Filters: {result.filter_states}")
                
                # If we have a signal but no entry, analyze why
                if result.signal != 0 and not (result.start_long_trade or result.start_short_trade):
                    conditions = analyze_entry_conditions(processor, result)
                    
                    print("\n  ❌ Entry Signal NOT Generated - Conditions Analysis:")
                    for name, info in conditions.items():
                        status = "✅" if info['passed'] else "❌"
                        print(f"    {status} {name}:")
                        print(f"       Value: {info['value']}")
                        print(f"       Requirement: {info['requirement']}")
                    
                    failed_entries.append({
                        'bar': i,
                        'conditions': conditions
                    })
                print("-" * 50)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    print(f"\n1️⃣ ML PREDICTIONS:")
    print(f"   Total bars processed: {len(data)}")
    print(f"   Non-zero predictions: {len(ml_predictions)}")
    if ml_predictions:
        pred_values = [p['prediction'] for p in ml_predictions]
        print(f"   Prediction range: {min(pred_values):.2f} to {max(pred_values):.2f}")
        print(f"   Average: {sum(pred_values)/len(pred_values):.2f}")
    
    print(f"\n2️⃣ ENTRY SIGNALS:")
    print(f"   Total entries generated: {len(entry_signals)}")
    if entry_signals:
        for entry in entry_signals[:5]:  # Show first 5
            print(f"   - Bar {entry['bar']}: {entry['type']} @ {entry['price']:.2f}")
    
    print(f"\n3️⃣ FAILED ENTRY ANALYSIS:")
    print(f"   Signals without entries: {len(failed_entries)}")
    
    if failed_entries:
        # Analyze common failure reasons
        failure_reasons = {}
        for failed in failed_entries:
            for name, info in failed['conditions'].items():
                if not info['passed']:
                    failure_reasons[name] = failure_reasons.get(name, 0) + 1
        
        print("\n   Most common failure reasons:")
        for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(failed_entries)) * 100
            print(f"   - {reason}: {count} times ({percentage:.1f}%)")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    if len(entry_signals) == 0:
        print("   ⚠️  No entry signals generated!")
        print("\n   Suggested actions:")
        print("   1. Check if ML predictions are being generated (currently: {})".format(
            "YES ✅" if len(ml_predictions) > 0 else "NO ❌"
        ))
        print("   2. Review filter thresholds:")
        print(f"      - Regime threshold: {config.regime_threshold} (try: -0.5 to 0.5)")
        print(f"      - ADX threshold: {config.adx_threshold} (try: 10-15 for ranging)")
        print("   3. Consider disabling some filters temporarily")
        print("   4. Ensure sufficient historical data (500+ bars recommended)")
    else:
        print(f"   ✅ System generating signals successfully!")
        print(f"   Entry rate: {(len(entry_signals) / len(data)) * 100:.2f}%")
    
    return len(entry_signals) > 0


if __name__ == "__main__":
    success = run_enhanced_test()
    exit(0 if success else 1)
