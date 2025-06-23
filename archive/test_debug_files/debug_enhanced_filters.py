#!/usr/bin/env python3
"""
Debug enhanced filters step by step
"""
import sys
sys.path.append('.')

import pandas as pd
from config.settings import TradingConfig
from core.indicators import get_indicator_manager
from core.ml_extensions import enhanced_regime_filter, enhanced_filter_adx, enhanced_filter_volatility
from core.stateful_ta import StatefulATR


def debug_filters():
    """Debug each filter individually"""
    
    print("="*70)
    print("🔍 DEBUGGING ENHANCED FILTERS")
    print("="*70)
    
    # Load data
    df = pd.read_csv('NSE_ICICIBANK, 1D.csv')
    print(f"\n✅ Loaded {len(df)} bars of ICICI data")
    
    # Test parameters
    symbol = "ICICIBANK"
    timeframe = "1D"
    
    # Clear any existing state
    manager = get_indicator_manager()
    manager.clear_symbol(symbol)
    
    # Test volatility filter
    print("\n1️⃣ Testing Volatility Filter (Recent ATR > Historical ATR):")
    print("   Periods: Recent=1, Historical=10")
    
    volatility_passes = 0
    recent_atrs = []
    historical_atrs = []
    
    # Create ATR instances directly
    recent_atr = manager.get_or_create_atr(symbol, timeframe, 1)
    historical_atr = manager.get_or_create_atr(symbol, timeframe, 10)
    
    for i, row in df.head(50).iterrows():
        high = float(row['high'])
        low = float(row['low'])
        close = float(row['close'])
        
        # Update ATRs
        recent_val = recent_atr.update(high, low, close)
        hist_val = historical_atr.update(high, low, close)
        
        recent_atrs.append(recent_val)
        historical_atrs.append(hist_val)
        
        # Test filter
        passes = recent_val > hist_val
        if passes:
            volatility_passes += 1
        
        # Debug output every 10 bars
        if i > 20 and i % 10 == 0:
            print(f"   Bar {i}: Recent ATR={recent_val:.2f}, Historical ATR={hist_val:.2f}, Pass={passes}")
    
    print(f"   Result: {volatility_passes}/30 passed ({volatility_passes/30*100:.1f}%)")
    
    # Test regime filter
    print("\n2️⃣ Testing Regime Filter (KLMF slope detection):")
    print("   Threshold: -0.1")
    
    regime_passes = 0
    
    for i in range(1, 50):
        if i < 1:
            continue
            
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        # Calculate OHLC4
        ohlc4 = (float(row['open']) + float(row['high']) + float(row['low']) + float(row['close'])) / 4
        prev_ohlc4 = (float(prev_row['open']) + float(prev_row['high']) + float(prev_row['low']) + float(prev_row['close'])) / 4
        
        # Test filter
        passes = enhanced_regime_filter(
            ohlc4, float(row['high']), float(row['low']), prev_ohlc4,
            symbol, timeframe, -0.1, True
        )
        
        if passes:
            regime_passes += 1
        
        # Debug output
        if i > 20 and i % 10 == 0:
            print(f"   Bar {i}: OHLC4={ohlc4:.2f}, Prev={prev_ohlc4:.2f}, Pass={passes}")
    
    print(f"   Result: {regime_passes}/49 passed ({regime_passes/49*100:.1f}%)")
    
    # Test ADX filter (even though it's OFF by default)
    print("\n3️⃣ Testing ADX Filter (should pass 100% when OFF):")
    
    adx_on_passes = 0
    adx_off_passes = 0
    
    for i, row in df.head(50).iterrows():
        if i < 30:  # Need warmup for ADX
            continue
            
        high = float(row['high'])
        low = float(row['low'])
        close = float(row['close'])
        
        # Test with filter ON
        passes_on = enhanced_filter_adx(high, low, close, symbol, timeframe, 14, 20, True)
        if passes_on:
            adx_on_passes += 1
        
        # Test with filter OFF
        passes_off = enhanced_filter_adx(high, low, close, symbol, timeframe, 14, 20, False)
        if passes_off:
            adx_off_passes += 1
    
    print(f"   With filter ON: {adx_on_passes}/20 passed")
    print(f"   With filter OFF: {adx_off_passes}/20 passed (should be 100%)")
    
    # Diagnosis
    print("\n💡 DIAGNOSIS:")
    
    if volatility_passes == 0:
        print("   ❌ Volatility filter is TOO RESTRICTIVE!")
        print("      → Recent ATR never exceeds historical ATR")
        print("      → May need different periods for daily data")
    
    if regime_passes == 0:
        print("   ❌ Regime filter is TOO RESTRICTIVE!")
        print("      → KLMF slope never meets threshold")
        print("      → Threshold -0.1 may be too strict for daily data")
    
    if adx_off_passes < 20:
        print("   ⚠️  ADX filter has a bug - should always pass when OFF!")
    
    print("\n📌 RECOMMENDATIONS:")
    print("   1. Check stateful indicator initialization")
    print("   2. Verify warmup periods are sufficient")
    print("   3. Consider adjusting thresholds for daily timeframe")
    print("   4. Compare with non-enhanced versions")


if __name__ == "__main__":
    debug_filters()
