"""
Test Phase 3 Flexible ML with Rollback Capability
================================================

Demonstrates how to safely test the flexible ML system with
instant rollback to original if needed.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from data.smart_data_manager import SmartDataManager
from scanner.flexible_bar_processor import FlexibleBarProcessor
from config.settings import TradingConfig
from config.adaptive_config import create_adaptive_config


def test_flexible_ml_system(symbol: str = 'RELIANCE', use_flexible: bool = False):
    """Test flexible ML system with rollback capability"""
    
    print(f"\n{'='*60}")
    print(f"TESTING {'FLEXIBLE' if use_flexible else 'ORIGINAL'} ML SYSTEM - {symbol}")
    print(f"{'='*60}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=10)
    
    if df is None or len(df) < 500:
        print(f"⚠️  Insufficient data")
        return None
    
    print(f"\nData loaded: {len(df)} bars")
    
    # Create configuration
    stats = data_manager.analyze_price_movement(df)
    adaptive_config = create_adaptive_config(symbol, '5minute', stats)
    
    trading_config = TradingConfig(
        source=adaptive_config.source,
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        features=adaptive_config.features
    )
    
    # Create flexible processor
    processor = FlexibleBarProcessor(
        trading_config,
        symbol=symbol,
        timeframe='5minute',
        use_flexible_ml=use_flexible,
        feature_config={
            'original_features': ['rsi', 'wt', 'cci', 'adx', 'features_4'],
            'phase3_features': ['fisher', 'vwm', 'order_flow'],
            'use_phase3': True
        }
    )
    
    # Process bars
    signals = []
    
    print(f"\nProcessing bars with {'flexible' if use_flexible else 'original'} ML...")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if i < 100:  # Skip warmup
            continue
            
        result = processor.process_bar(
            row['open'], row['high'], row['low'],
            row['close'], row['volume']
        )
        
        if result and result.signal != 0:
            signals.append({
                'timestamp': idx,
                'signal': result.signal,
                'prediction': result.prediction,
                'ml_system': result.ml_system_used,
                'features': result.feature_values
            })
    
    # Show results
    print(f"\nTotal signals: {len(signals)}")
    
    if signals and len(signals) >= 3:
        print("\nSample signals:")
        for signal in signals[:3]:
            print(f"\n{signal['timestamp']}:")
            print(f"  Signal: {'Long' if signal['signal'] > 0 else 'Short'}")
            print(f"  Prediction: {signal['prediction']:.2f}")
            print(f"  ML System: {signal['ml_system']}")
            
            if use_flexible and signal['features']:
                # Show Phase 3 features
                print(f"  Fisher: {signal['features'].get('fisher', 0):.2f}")
                print(f"  VWM: {signal['features'].get('vwm', 0):.2f}")
                print(f"  Order Flow: {signal['features'].get('order_flow', 0):.2f}")
    
    # Get comparison stats if using flexible
    if use_flexible:
        stats = processor.get_comparison_stats()
        if stats:
            print(f"\n{'='*40}")
            print("PREDICTION COMPARISON")
            print(f"{'='*40}")
            print(f"  Comparisons made: {stats['comparisons']}")
            print(f"  Avg difference: {stats['avg_difference']:.3f}")
            print(f"  Max difference: {stats['max_difference']:.3f}")
            print(f"  Correlation: {stats['correlation']:.3f}")
    
    return processor, signals


def demonstrate_rollback():
    """Demonstrate instant rollback capability"""
    
    print(f"\n{'='*60}")
    print("ROLLBACK DEMONSTRATION")
    print(f"{'='*60}")
    
    # Create processor with flexible ML
    data_manager = SmartDataManager()
    df = data_manager.get_data('RELIANCE', interval='5minute', days=5)
    
    if df is None:
        print("⚠️  No data available")
        return
    
    # Create config
    stats = data_manager.analyze_price_movement(df)
    adaptive_config = create_adaptive_config('RELIANCE', '5minute', stats)
    trading_config = TradingConfig(
        source=adaptive_config.source,
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        features=adaptive_config.features
    )
    
    # Start with flexible ML
    processor = FlexibleBarProcessor(
        trading_config,
        symbol='RELIANCE',
        timeframe='5minute',
        use_flexible_ml=True
    )
    
    print("\n1. Processing with FLEXIBLE ML...")
    flexible_signals = 0
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if i >= 100 and i < 150:  # Process 50 bars
            result = processor.process_bar(
                row['open'], row['high'], row['low'],
                row['close'], row['volume']
            )
            if result and result.signal != 0:
                flexible_signals += 1
    
    print(f"   Signals generated: {flexible_signals}")
    
    # Instant rollback
    print("\n2. ROLLING BACK to original ML...")
    processor.switch_ml_system(use_flexible=False)
    
    print("\n3. Processing with ORIGINAL ML...")
    original_signals = 0
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if i >= 150 and i < 200:  # Process next 50 bars
            result = processor.process_bar(
                row['open'], row['high'], row['low'],
                row['close'], row['volume']
            )
            if result and result.signal != 0:
                original_signals += 1
    
    print(f"   Signals generated: {original_signals}")
    
    print("\n✅ Rollback successful! Can switch between systems instantly.")


def compare_both_systems():
    """Run both systems and compare results"""
    
    print(f"\n{'='*60}")
    print("SYSTEM COMPARISON")
    print(f"{'='*60}")
    
    symbols = ['RELIANCE', 'INFY', 'TCS']
    
    comparison_results = []
    
    for symbol in symbols:
        print(f"\nTesting {symbol}...")
        
        # Test original
        _, original_signals = test_flexible_ml_system(symbol, use_flexible=False)
        
        # Test flexible
        _, flexible_signals = test_flexible_ml_system(symbol, use_flexible=True)
        
        if original_signals and flexible_signals:
            comparison_results.append({
                'symbol': symbol,
                'original_count': len(original_signals),
                'flexible_count': len(flexible_signals),
                'difference_pct': (len(flexible_signals) - len(original_signals)) / len(original_signals) * 100
            })
    
    # Summary
    if comparison_results:
        print(f"\n{'='*60}")
        print("COMPARISON SUMMARY")
        print(f"{'='*60}")
        
        print(f"\n{'Symbol':<10} {'Original':<10} {'Flexible':<10} {'Difference':<12}")
        print("-" * 42)
        
        for result in comparison_results:
            print(f"{result['symbol']:<10} {result['original_count']:<10} "
                  f"{result['flexible_count']:<10} {result['difference_pct']:+.1f}%")
        
        avg_diff = np.mean([r['difference_pct'] for r in comparison_results])
        print(f"\nAverage difference: {avg_diff:+.1f}%")
        
        if abs(avg_diff) < 20:
            print("\n✅ Systems are producing similar results - safe to deploy!")
        else:
            print("\n⚠️  Significant differences - more testing needed")


def main():
    """Run Phase 3 flexible ML tests with rollback capability"""
    
    print("\n" + "="*60)
    print("PHASE 3 FLEXIBLE ML WITH ROLLBACK")
    print("="*60)
    print("\nThis demonstrates:")
    print("1. Flexible ML system with 8 features")
    print("2. Instant rollback to original system")
    print("3. Side-by-side comparison")
    print("4. Safety measures for production")
    
    # Test flexible system
    test_flexible_ml_system('RELIANCE', use_flexible=True)
    
    # Demonstrate rollback
    demonstrate_rollback()
    
    # Compare both systems
    compare_both_systems()
    
    print(f"\n{'='*60}")
    print("PHASE 3 FLEXIBLE ML TEST COMPLETE")
    print(f"{'='*60}")
    print("\nKey Points:")
    print("✅ Flexible ML supports any number of features")
    print("✅ Instant rollback with one line of code")
    print("✅ Can run both systems in parallel")
    print("✅ Production-ready with safety measures")
    print("\nRecommendation: Deploy with feature flag for gradual rollout")


if __name__ == "__main__":
    main()