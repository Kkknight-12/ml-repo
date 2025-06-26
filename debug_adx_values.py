#!/usr/bin/env python3
"""
Debug ADX Values
================

Check actual ADX values to understand why filter is always False.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from core.enhanced_indicators import enhanced_dmi, reset_symbol_indicators
from data.cache_manager import MarketDataCache


def debug_adx_values():
    """Check ADX values over time"""
    
    symbol = "RELIANCE"
    timeframe = "5minute"
    
    # Reset indicators for clean state
    reset_symbol_indicators(symbol)
    
    # Get data
    cache = MarketDataCache()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    df = cache.get_cached_data(symbol, start_date, end_date, timeframe)
    if df is None or df.empty:
        print("❌ No cached data available")
        return
    
    # Ensure date index
    if 'date' in df.columns:
        df.set_index('date', inplace=True)
    
    print("="*80)
    print("🔍 ADX VALUES DEBUG")
    print("="*80)
    print(f"Symbol: {symbol}")
    print(f"Total bars: {len(df)}")
    print()
    
    adx_values = []
    
    # Process bars and collect ADX values
    print("Processing ADX values...")
    for i, (idx, row) in enumerate(df.iterrows()):
        _, _, adx = enhanced_dmi(
            row['high'], row['low'], row['close'], 
            14, 14, symbol, timeframe
        )
        
        adx_values.append(adx)
        
        # Log every 100 bars
        if i > 0 and i % 100 == 0:
            print(f"   Bar {i}: ADX = {adx:.2f}")
    
    # Analyze ADX values
    adx_array = np.array([v for v in adx_values if not np.isnan(v)])
    
    if len(adx_array) == 0:
        print("❌ No valid ADX values!")
        return
    
    print(f"\n📊 ADX STATISTICS:")
    print(f"Total values: {len(adx_array)}")
    print(f"Min: {np.min(adx_array):.2f}")
    print(f"Max: {np.max(adx_array):.2f}")
    print(f"Mean: {np.mean(adx_array):.2f}")
    print(f"Median: {np.median(adx_array):.2f}")
    print(f"Std Dev: {np.std(adx_array):.2f}")
    
    # Check distribution vs thresholds
    thresholds = [10, 15, 20, 25, 30, 35, 40]
    print(f"\n📈 ADX DISTRIBUTION:")
    for threshold in thresholds:
        above = np.sum(adx_array > threshold)
        pct = (above / len(adx_array)) * 100
        print(f"ADX > {threshold}: {above} bars ({pct:.1f}%)")
    
    # Show recent values
    print(f"\n🕐 LAST 20 ADX VALUES:")
    for i in range(min(20, len(adx_values))):
        idx = -(i+1)
        print(f"   {i} bars ago: ADX = {adx_values[idx]:.2f}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    # Find optimal threshold
    optimal_threshold = None
    for threshold in [15, 18, 20, 22, 25]:
        pct = (np.sum(adx_array > threshold) / len(adx_array)) * 100
        if 20 <= pct <= 40:  # Target 20-40% pass rate
            optimal_threshold = threshold
            break
    
    if optimal_threshold:
        print(f"✅ Set adx_threshold = {optimal_threshold} for ~30% pass rate")
    else:
        mean_adx = np.mean(adx_array)
        if mean_adx < 20:
            print(f"⚠️ ADX is very low (mean={mean_adx:.1f})")
            print("   Consider:")
            print("   - Disabling ADX filter (use_adx_filter=False)")
            print("   - Or lower threshold to 15")
        else:
            print(f"⚠️ ADX threshold of 20 may be appropriate")
            print("   Check if ADX calculation is correct")


if __name__ == "__main__":
    debug_adx_values()