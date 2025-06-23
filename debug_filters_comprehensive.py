#!/usr/bin/env python3
"""
Debug why all filters are showing 0% pass rate
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ml_extensions import regime_filter, filter_volatility, filter_adx
from core.indicators import calculate_adx
from core.math_helpers import pine_atr
import random

print("="*70)
print("FILTER DEBUG - Checking why all filters show 0% pass rate")
print("="*70)

# Generate realistic daily price data (5 years)
def generate_realistic_daily_data(days=1250):
    """Generate realistic stock price data"""
    data = {
        'high': [],
        'low': [], 
        'close': [],
        'ohlc4': []
    }
    
    # Starting price (like RELIANCE at 1000)
    base_price = 1000.0
    
    for i in range(days):
        # Add trend component
        trend = i * 0.2  # Upward trend
        
        # Add volatility
        daily_return = random.gauss(0, 0.015)  # 1.5% daily volatility
        
        close = base_price + trend + base_price * daily_return
        
        # Generate realistic OHLC
        daily_range = abs(random.gauss(close * 0.01, close * 0.005))  # 1% range
        
        if random.random() > 0.5:  # Bullish day
            open_price = close - random.uniform(0, daily_range * 0.7)
            high = close + random.uniform(0, daily_range * 0.3)
            low = open_price - random.uniform(0, daily_range * 0.2)
        else:  # Bearish day
            open_price = close + random.uniform(0, daily_range * 0.7)
            low = close - random.uniform(0, daily_range * 0.3)
            high = open_price + random.uniform(0, daily_range * 0.2)
        
        # Ensure constraints
        high = max(open_price, close, high)
        low = min(open_price, close, low)
        ohlc4 = (open_price + high + low + close) / 4
        
        # Add to arrays (newest first for Python)
        data['high'].insert(0, high)
        data['low'].insert(0, low)
        data['close'].insert(0, close)
        data['ohlc4'].insert(0, ohlc4)
    
    return data

# Generate test data
print("\n1. Generating realistic market data...")
data = generate_realistic_daily_data(1250)
print(f"   Generated {len(data['close'])} days of data")
print(f"   Price range: {min(data['close']):.2f} to {max(data['close']):.2f}")

# Test Volatility Filter
print("\n2. Testing VOLATILITY FILTER:")
print("   Filter logic: recentATR > historicalATR")

# Calculate ATRs at different points
test_points = [50, 100, 200, 500, 1000]
for point in test_points:
    if point < len(data['close']):
        subset_high = data['high'][:point]
        subset_low = data['low'][:point]
        subset_close = data['close'][:point]
        
        recent_atr = pine_atr(subset_high, subset_low, subset_close, 1)
        historical_atr = pine_atr(subset_high, subset_low, subset_close, 10)
        
        result = filter_volatility(subset_high, subset_low, subset_close, 1, 10, True)
        
        print(f"\n   At bar {point}:")
        print(f"   Recent ATR (1): {recent_atr:.4f}")
        print(f"   Historical ATR (10): {historical_atr:.4f}")
        print(f"   Filter passes: {result} (recent > historical: {recent_atr > historical_atr})")

# Test Regime Filter
print("\n3. Testing REGIME FILTER:")
print("   Filter logic: normalized_slope_decline >= threshold")

# Test with different data subsets
for point in test_points:
    if point >= 200:  # Need at least 200 bars
        subset_ohlc4 = data['ohlc4'][:point]
        subset_high = data['high'][:point]
        subset_low = data['low'][:point]
        
        # Test with default threshold
        result = regime_filter(subset_ohlc4, -0.1, True, subset_high, subset_low)
        
        print(f"\n   At bar {point}:")
        print(f"   Threshold: -0.1")
        print(f"   Filter passes: {result}")

# Test ADX Filter
print("\n4. Testing ADX FILTER:")
print("   Filter logic: ADX > threshold (20)")

for point in test_points:
    if point >= 50:  # Need enough data for ADX
        subset_high = data['high'][:point]
        subset_low = data['low'][:point]
        subset_close = data['close'][:point]
        
        adx_value = calculate_adx(subset_high, subset_low, subset_close, 14)
        result = filter_adx(subset_high, subset_low, subset_close, 14, 20, True)
        
        print(f"\n   At bar {point}:")
        print(f"   ADX value: {adx_value:.2f}")
        print(f"   Threshold: 20")
        print(f"   Filter passes: {result} (ADX > 20: {adx_value > 20})")

# Test Pine Script behavior - What happens when filter is OFF?
print("\n5. Testing Pine Script DEFAULT behavior (filter OFF):")
print("   According to Pine Script:")
print("   - When useVolatilityFilter=false, filter returns TRUE")
print("   - When useRegimeFilter=false, filter returns TRUE")
print("   - When useAdxFilter=false, filter returns TRUE")

# Test with filters OFF
vol_off = filter_volatility(data['high'][:100], data['low'][:100], data['close'][:100], 1, 10, False)
regime_off = regime_filter(data['ohlc4'][:200], -0.1, False, data['high'][:200], data['low'][:200])
adx_off = filter_adx(data['high'][:100], data['low'][:100], data['close'][:100], 14, 20, False)

print(f"\n   Volatility filter (OFF): {vol_off} (should be True)")
print(f"   Regime filter (OFF): {regime_off} (should be True)")
print(f"   ADX filter (OFF): {adx_off} (should be True)")

# Check actual implementation
print("\n6. CRITICAL CHECK - Filter pass logic:")
print("   In Pine Script, filter_all = filter.volatility AND filter.regime AND filter.adx")
print("   If ANY filter returns False, filter_all = False")
print("   If filter_all = False, signal NEVER changes!")

# Simulate full filter check
vol_result = filter_volatility(data['high'][:100], data['low'][:100], data['close'][:100], 1, 10, True)
regime_result = regime_filter(data['ohlc4'][:200], -0.1, True, data['high'][:200], data['low'][:200])
adx_result = filter_adx(data['high'][:100], data['low'][:100], data['close'][:100], 14, 20, False)  # OFF by default

filter_all = vol_result and regime_result and adx_result

print(f"\n   Volatility: {vol_result}")
print(f"   Regime: {regime_result}")
print(f"   ADX (OFF): {adx_result}")
print(f"   filter_all: {filter_all}")

print("\n" + "="*70)
print("CONCLUSION:")
print("="*70)
print("If filters are too restrictive or have bugs, signals will NEVER change!")
print("This explains why signals stay stuck at their initial values.")
