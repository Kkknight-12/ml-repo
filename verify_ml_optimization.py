#!/usr/bin/env python3
"""
Verify ML Optimization Implementation
=====================================

Final verification that ML optimization is working correctly:
1. ML threshold is being applied
2. Win rate improves to 50%+
3. Risk/Reward improves to 2:1+
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import json
import pandas as pd

from backtest_framework_enhanced import EnhancedBacktestEngine
from config.settings import TradingConfig
from config.ml_optimized_settings import MLOptimizedTradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from scanner.enhanced_bar_processor_ml_optimized import MLOptimizedBarProcessor
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def verify_ml_threshold_filtering():
    """Verify that ML threshold is actually filtering trades"""
    
    print("="*80)
    print("🔍 VERIFYING ML THRESHOLD FILTERING")
    print("="*80)
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Get some data
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return
    
    # Test without ML threshold
    print("\n1️⃣ Testing WITHOUT ML threshold:")
    config_no_threshold = TradingConfig()
    processor_no_threshold = EnhancedBarProcessor(config_no_threshold, symbol, "5minute")
    
    entries_no_threshold = 0
    signals_no_threshold = 0
    
    # Test with ML threshold
    print("\n2️⃣ Testing WITH ML threshold (>=3):")
    config_with_threshold = MLOptimizedTradingConfig()
    processor_with_threshold = MLOptimizedBarProcessor(config_with_threshold, symbol, "5minute")
    
    entries_with_threshold = 0
    signals_with_threshold = 0
    ml_blocked = 0
    
    # Process bars
    for i, (idx, row) in enumerate(df.iterrows()):
        if i >= 2200:  # Process 200 bars after warmup
            break
        
        # Without threshold
        result1 = processor_no_threshold.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # With threshold
        result2 = processor_with_threshold.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # Count after warmup
        if i >= config_no_threshold.max_bars_back:
            # Signals
            if result1.signal != 0:
                signals_no_threshold += 1
            if result2.signal != 0:
                signals_with_threshold += 1
            
            # Entries
            if result1.start_long_trade or result1.start_short_trade:
                entries_no_threshold += 1
            if result2.start_long_trade or result2.start_short_trade:
                entries_with_threshold += 1
            
            # Check if ML threshold blocked an entry
            if (result1.start_long_trade or result1.start_short_trade) and \
               not (result2.start_long_trade or result2.start_short_trade):
                if abs(result1.prediction) < 3.0:
                    ml_blocked += 1
    
    print(f"\n📊 ML Threshold Filtering Results:")
    print(f"Without threshold: {entries_no_threshold} entries from {signals_no_threshold} signals")
    print(f"With threshold: {entries_with_threshold} entries from {signals_with_threshold} signals")
    print(f"Entries blocked by ML threshold: {ml_blocked}")
    
    if entries_with_threshold < entries_no_threshold:
        print(f"✅ ML threshold is working! Reduced entries by {entries_no_threshold - entries_with_threshold}")
    else:
        print("❌ ML threshold may not be working correctly")


def verify_performance_improvements():
    """Verify that performance actually improves"""
    
    print("\n" + "="*80)
    print("📈 VERIFYING PERFORMANCE IMPROVEMENTS")
    print("="*80)
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    engine = EnhancedBacktestEngine()
    
    # Test configurations
    configs = [
        ("Baseline", TradingConfig()),
        ("Baseline + Dynamic", create_dynamic_baseline()),
        ("ML-Optimized", MLOptimizedTradingConfig())
    ]
    
    results = {}
    
    for name, config in configs:
        print(f"\nTesting {name}...")
        
        try:
            metrics = engine.run_backtest(
                symbol, start_date, end_date, config
            )
            
            risk_reward = abs(metrics.average_win / metrics.average_loss) if metrics.average_loss != 0 else 0
            
            results[name] = {
                'trades': metrics.total_trades,
                'win_rate': metrics.win_rate,
                'risk_reward': risk_reward,
                'total_return': metrics.total_return
            }
            
            print(f"  Trades: {metrics.total_trades}")
            print(f"  Win Rate: {metrics.win_rate:.1f}%")
            print(f"  Risk/Reward: {risk_reward:.2f}")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # Verify improvements
    print("\n" + "="*80)
    print("✅ VERIFICATION RESULTS")
    print("="*80)
    
    baseline = results.get("Baseline", {})
    ml_optimized = results.get("ML-Optimized", {})
    
    if baseline and ml_optimized:
        # Check win rate improvement
        wr_improved = ml_optimized['win_rate'] > baseline['win_rate']
        wr_target_met = ml_optimized['win_rate'] >= 50
        
        # Check risk/reward improvement
        rr_improved = ml_optimized['risk_reward'] > baseline['risk_reward']
        rr_target_met = ml_optimized['risk_reward'] >= 2.0
        
        print(f"\n1. Win Rate:")
        print(f"   Baseline: {baseline['win_rate']:.1f}%")
        print(f"   ML-Optimized: {ml_optimized['win_rate']:.1f}%")
        print(f"   Improved: {'✅ YES' if wr_improved else '❌ NO'}")
        print(f"   Target Met (50%+): {'✅ YES' if wr_target_met else '❌ NO'}")
        
        print(f"\n2. Risk/Reward:")
        print(f"   Baseline: {baseline['risk_reward']:.2f}")
        print(f"   ML-Optimized: {ml_optimized['risk_reward']:.2f}")
        print(f"   Improved: {'✅ YES' if rr_improved else '❌ NO'}")
        print(f"   Target Met (2:1+): {'✅ YES' if rr_target_met else '❌ NO'}")
        
        print(f"\n3. Trade Count:")
        print(f"   Baseline: {baseline['trades']}")
        print(f"   ML-Optimized: {ml_optimized['trades']}")
        print(f"   Reasonable (20+): {'✅ YES' if ml_optimized['trades'] >= 20 else '❌ NO'}")
        
        # Overall success
        if wr_target_met and rr_target_met and ml_optimized['trades'] >= 20:
            print("\n🎉 SUCCESS! All targets achieved:")
            print("   ✅ 50%+ win rate")
            print("   ✅ 2:1+ risk/reward")
            print("   ✅ Reasonable trade count")
        else:
            print("\n⚠️  Some targets not yet achieved. May need further tuning.")


def create_dynamic_baseline():
    """Create baseline config with dynamic exits"""
    config = TradingConfig()
    config.use_dynamic_exits = True
    return config


def main():
    """Run all verifications"""
    
    print("🚀 ML OPTIMIZATION VERIFICATION")
    print("="*80)
    print("This script verifies that:")
    print("1. ML threshold filtering is working")
    print("2. Performance targets are achieved")
    print("3. Implementation is correct")
    
    # Run verifications
    verify_ml_threshold_filtering()
    verify_performance_improvements()
    
    print("\n" + "="*80)
    print("📋 FINAL CHECKLIST")
    print("="*80)
    print("☐ ML threshold reduces entry count")
    print("☐ Win rate improves to 50%+")
    print("☐ Risk/Reward improves to 2:1+")
    print("☐ Trade count remains reasonable (20+)")
    print("☐ Multi-target exits working")
    print("\nIf all checks pass, the ML optimization is ready for production!")


if __name__ == "__main__":
    main()