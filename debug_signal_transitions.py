#!/usr/bin/env python3
"""
Debug why signals are stuck at -1
Track signal history and transitions
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
import numpy as np
import pandas as pd


def generate_mixed_trend_data(num_bars=200):
    """Generate data with clear trend transitions"""
    data = []
    
    # Phase 1: Uptrend (bars 0-50)
    for i in range(50):
        base = 100 + i * 0.5
        close = base + np.random.uniform(-0.2, 0.5)
        open_price = base - 0.2
        high = close + np.random.uniform(0, 0.3)
        low = open_price - np.random.uniform(0, 0.3)
        data.append((open_price, high, low, close, 1000))
    
    # Phase 2: Sideways (bars 50-100)
    for i in range(50):
        base = 125
        close = base + np.random.uniform(-1, 1)
        open_price = base + np.random.uniform(-0.5, 0.5)
        high = max(close, open_price) + np.random.uniform(0, 0.5)
        low = min(close, open_price) - np.random.uniform(0, 0.5)
        data.append((open_price, high, low, close, 1200))
    
    # Phase 3: Downtrend (bars 100-150)
    for i in range(50):
        base = 125 - i * 0.5
        close = base + np.random.uniform(-0.5, 0.2)
        open_price = base + 0.2
        high = open_price + np.random.uniform(0, 0.3)
        low = close - np.random.uniform(0, 0.3)
        data.append((open_price, high, low, close, 1100))
    
    # Phase 4: Recovery (bars 150-200)
    for i in range(50):
        base = 100 + i * 0.3
        close = base + np.random.uniform(-0.2, 0.4)
        open_price = base - 0.1
        high = close + np.random.uniform(0, 0.2)
        low = open_price - np.random.uniform(0, 0.2)
        data.append((open_price, high, low, close, 1300))
    
    return data


def debug_signal_transitions():
    """Debug why signals don't transition"""
    
    print("=" * 70)
    print("🔍 DEBUGGING SIGNAL TRANSITIONS")
    print("=" * 70)
    
    # Test with different filter configurations
    configs = [
        ("All Filters OFF", TradingConfig(
            use_volatility_filter=False,
            use_regime_filter=False,
            use_adx_filter=False,
            use_kernel_filter=False,
            use_ema_filter=False,
            use_sma_filter=False,
            max_bars_back=100
        )),
        ("Only Volatility ON", TradingConfig(
            use_volatility_filter=True,
            use_regime_filter=False,
            use_adx_filter=False,
            use_kernel_filter=False,
            max_bars_back=100
        )),
        ("Default Config", TradingConfig(
            max_bars_back=100
        ))
    ]
    
    # Generate test data with clear trends
    data = generate_mixed_trend_data()
    print(f"\n📊 Generated {len(data)} bars with 4 phases:")
    print("  1. Uptrend (bars 0-50)")
    print("  2. Sideways (bars 50-100)")
    print("  3. Downtrend (bars 100-150)")
    print("  4. Recovery (bars 150-200)")
    
    for config_name, config in configs:
        print(f"\n\n{'='*50}")
        print(f"🧪 Testing: {config_name}")
        print(f"{'='*50}")
        
        processor = EnhancedBarProcessor(config, "DEBUG", "5minute")
        
        # Track everything
        signal_tracker = {
            'bars': [],
            'ml_predictions': [],
            'signals': [],
            'signal_changes': [],
            'entries': [],
            'filter_pass': []
        }
        
        # Process bars
        for i, (o, h, l, c, v) in enumerate(data):
            result = processor.process_bar(o, h, l, c, v)
            
            if result and i >= 50:  # After warmup
                signal_tracker['bars'].append(i)
                signal_tracker['ml_predictions'].append(result.prediction)
                signal_tracker['signals'].append(result.signal)
                signal_tracker['filter_pass'].append(all(result.filter_states.values()))
                
                # Track signal changes
                if len(signal_tracker['signals']) > 1:
                    if signal_tracker['signals'][-1] != signal_tracker['signals'][-2]:
                        signal_tracker['signal_changes'].append({
                            'bar': i,
                            'from': signal_tracker['signals'][-2],
                            'to': signal_tracker['signals'][-1],
                            'ml_pred': result.prediction
                        })
                
                # Track entries
                if result.start_long_trade or result.start_short_trade:
                    signal_tracker['entries'].append({
                        'bar': i,
                        'type': 'LONG' if result.start_long_trade else 'SHORT',
                        'signal': result.signal
                    })
                
                # Debug output for key bars
                if i in [60, 110, 160, 190]:  # Middle of each phase
                    print(f"\n  Bar {i} (Phase {(i//50)+1}):")
                    print(f"    Price: {c:.2f}")
                    print(f"    ML Prediction: {result.prediction:.2f}")
                    print(f"    Signal: {result.signal} ({'LONG' if result.signal > 0 else 'SHORT' if result.signal < 0 else 'NEUTRAL'})")
                    print(f"    Filters Pass: {all(result.filter_states.values())}")
                    print(f"    Filter Details: {result.filter_states}")
        
        # Analysis
        print(f"\n📊 RESULTS for {config_name}:")
        
        # Signal distribution
        if signal_tracker['signals']:
            unique_signals = set(signal_tracker['signals'])
            print(f"\n  Signal Distribution:")
            for sig in sorted(unique_signals):
                count = signal_tracker['signals'].count(sig)
                pct = (count / len(signal_tracker['signals'])) * 100
                sig_name = 'LONG' if sig > 0 else 'SHORT' if sig < 0 else 'NEUTRAL'
                print(f"    {sig_name} ({sig}): {count} bars ({pct:.1f}%)")
        
        # Signal changes
        print(f"\n  Signal Changes: {len(signal_tracker['signal_changes'])}")
        if signal_tracker['signal_changes']:
            for change in signal_tracker['signal_changes'][:5]:  # First 5
                from_name = 'LONG' if change['from'] > 0 else 'SHORT' if change['from'] < 0 else 'NEUTRAL'
                to_name = 'LONG' if change['to'] > 0 else 'SHORT' if change['to'] < 0 else 'NEUTRAL'
                print(f"    Bar {change['bar']}: {from_name} → {to_name} (ML pred: {change['ml_pred']:.2f})")
        
        # Entry signals
        print(f"\n  Entry Signals: {len(signal_tracker['entries'])}")
        if signal_tracker['entries']:
            for entry in signal_tracker['entries'][:5]:
                print(f"    Bar {entry['bar']}: {entry['type']}")
        
        # Filter pass rate
        if signal_tracker['filter_pass']:
            pass_rate = sum(signal_tracker['filter_pass']) / len(signal_tracker['filter_pass']) * 100
            print(f"\n  Filter Pass Rate: {pass_rate:.1f}%")
        
        # ML prediction analysis
        if signal_tracker['ml_predictions']:
            ml_preds = signal_tracker['ml_predictions']
            pos_preds = sum(1 for p in ml_preds if p > 0)
            neg_preds = sum(1 for p in ml_preds if p < 0)
            zero_preds = sum(1 for p in ml_preds if p == 0)
            print(f"\n  ML Predictions:")
            print(f"    Positive: {pos_preds}")
            print(f"    Negative: {neg_preds}")
            print(f"    Zero: {zero_preds}")
            print(f"    Range: {min(ml_preds):.2f} to {max(ml_preds):.2f}")
    
    print("\n" + "=" * 70)
    print("💡 KEY INSIGHTS:")
    print("=" * 70)
    print("\n1. Check if signals are transitioning with different filter configs")
    print("2. Look for pattern in when signals get 'stuck'")
    print("3. Compare ML predictions vs actual signals")
    print("4. Identify which filters block signal changes most")


if __name__ == "__main__":
    debug_signal_transitions()
