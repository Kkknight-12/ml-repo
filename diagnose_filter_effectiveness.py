#!/usr/bin/env python3
"""
Diagnose Filter Effectiveness
=============================

Analyze why filters aren't effectively filtering signals.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.fixed_optimized_settings import FixedOptimizedTradingConfig
from data.cache_manager import MarketDataCache


def analyze_filter_effectiveness():
    """Analyze how each filter is performing"""
    
    symbol = "RELIANCE"
    config = FixedOptimizedTradingConfig()
    
    # Get data
    cache = MarketDataCache()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # Need more data for 2000 bar warmup
    
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    if df is None or df.empty:
        print("❌ No cached data available")
        return
    
    # Ensure date index
    if 'date' in df.columns:
        df.set_index('date', inplace=True)
    
    print("="*80)
    print("🔍 FILTER EFFECTIVENESS ANALYSIS")
    print("="*80)
    print(f"Symbol: {symbol}")
    print(f"Config: {config.__class__.__name__}")
    print(f"Total bars: {len(df)}")
    print()
    
    # Initialize processor
    processor = EnhancedBarProcessor(config, symbol, "5minute")
    
    # Track filter results
    filter_stats = {
        'volatility': {'pass': 0, 'fail': 0, 'values': []},
        'regime': {'pass': 0, 'fail': 0, 'values': []},
        'adx': {'pass': 0, 'fail': 0, 'values': []},
        'kernel': {'pass': 0, 'fail': 0, 'values': []}
    }
    
    ml_predictions = []
    signals = []
    all_filters_pass_count = 0
    
    # Process bars
    print("Processing bars...")
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        if result and i >= config.max_bars_back:  # After warmup
            # Track filter states
            for filter_name, state in result.filter_states.items():
                if filter_name in filter_stats:
                    if state:
                        filter_stats[filter_name]['pass'] += 1
                    else:
                        filter_stats[filter_name]['fail'] += 1
            
            # Track ML predictions
            ml_predictions.append(result.prediction)
            signals.append(result.signal)
            
            # Count when all filters pass
            if result.filter_all:
                all_filters_pass_count += 1
    
    # Calculate statistics
    total_bars_after_warmup = len(ml_predictions)
    
    print(f"\n📊 FILTER STATISTICS (after {config.max_bars_back} bar warmup)")
    print(f"Total bars analyzed: {total_bars_after_warmup}")
    
    if total_bars_after_warmup == 0:
        print("⚠️ Not enough data! Need at least", config.max_bars_back, "bars")
        return
    
    print()
    print("Individual Filter Pass Rates:")
    print("-" * 50)
    for filter_name, stats in filter_stats.items():
        total = stats['pass'] + stats['fail']
        if total > 0:
            pass_rate = (stats['pass'] / total) * 100
            print(f"{filter_name.upper():12} Pass: {stats['pass']:5} ({pass_rate:5.1f}%) | "
                  f"Fail: {stats['fail']:5} ({100-pass_rate:5.1f}%)")
    
    print(f"\n🎯 ALL FILTERS PASS: {all_filters_pass_count} times "
          f"({(all_filters_pass_count/total_bars_after_warmup)*100:.1f}%)")
    
    # Analyze ML predictions
    non_zero_predictions = [p for p in ml_predictions if p != 0.0]
    print(f"\n📈 ML PREDICTIONS:")
    print(f"Total predictions: {len(ml_predictions)}")
    print(f"Non-zero predictions: {len(non_zero_predictions)} "
          f"({(len(non_zero_predictions)/len(ml_predictions))*100:.1f}%)")
    
    if non_zero_predictions:
        print(f"Range: [{min(non_zero_predictions):.1f}, {max(non_zero_predictions):.1f}]")
        print(f"Average: {np.mean(non_zero_predictions):.2f}")
        
        # Show distribution
        positive = sum(1 for p in non_zero_predictions if p > 0)
        negative = sum(1 for p in non_zero_predictions if p < 0)
        print(f"Positive: {positive} ({(positive/len(non_zero_predictions))*100:.1f}%)")
        print(f"Negative: {negative} ({(negative/len(non_zero_predictions))*100:.1f}%)")
    
    # Check signal persistence
    signal_changes = sum(1 for i in range(1, len(signals)) if signals[i] != signals[i-1])
    print(f"\n📊 SIGNAL ANALYSIS:")
    print(f"Total signal changes: {signal_changes}")
    print(f"Average bars per signal: {len(signals)/max(signal_changes, 1):.1f}")
    
    # Analyze filter configurations
    print(f"\n⚙️ FILTER CONFIGURATIONS:")
    print(f"Volatility Filter: {'ON' if config.use_volatility_filter else 'OFF'}")
    print(f"Regime Filter: {'ON' if config.use_regime_filter else 'OFF'} "
          f"(threshold: {config.regime_threshold})")
    print(f"ADX Filter: {'ON' if config.use_adx_filter else 'OFF'} "
          f"(threshold: {config.adx_threshold})")
    print(f"Kernel Filter: {'ON' if config.use_kernel_filter else 'OFF'}")
    
    # Check if filters are too permissive
    print("\n🔍 DIAGNOSIS:")
    
    if all(stats['pass'] / (stats['pass'] + stats['fail']) > 0.8 
           for stats in filter_stats.values() if stats['pass'] + stats['fail'] > 0):
        print("⚠️ All filters have >80% pass rate - they may be too permissive!")
    
    if len(non_zero_predictions) < total_bars_after_warmup * 0.1:
        print("⚠️ Less than 10% of bars have non-zero ML predictions")
        print("   This is the primary issue - filters can't work without ML signals")
    
    if all_filters_pass_count > total_bars_after_warmup * 0.5:
        print("⚠️ All filters pass >50% of the time - need tighter thresholds")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    
    for filter_name, stats in filter_stats.items():
        total = stats['pass'] + stats['fail']
        if total > 0:
            pass_rate = stats['pass'] / total
            if pass_rate > 0.9:
                print(f"- Tighten {filter_name} filter (currently {pass_rate*100:.0f}% pass)")
    
    if len(non_zero_predictions) < total_bars_after_warmup * 0.2:
        print("- Focus on fixing ML predictions first before adjusting filters")
        print("- Consider reducing k-NN neighbor requirements")
        print("- Check feature calculation stability")


if __name__ == "__main__":
    analyze_filter_effectiveness()