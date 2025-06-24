#!/usr/bin/env python3
"""
Verify feature calculations match expected values
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import sqlite3
from config.settings import TradingConfig
from core.enhanced_indicators import (
    enhanced_n_rsi, enhanced_n_wt, enhanced_n_cci, enhanced_n_adx,
    reset_symbol_indicators
)
from core.pine_functions import nz


def verify_features():
    """Verify feature calculations"""
    
    print("="*70)
    print("VERIFY FEATURE CALCULATIONS")
    print("="*70)
    
    # Reset indicators for clean state
    reset_symbol_indicators("ICICIBANK")
    
    # Get data
    db_path = os.path.join("data_cache", "market_data.db")
    with sqlite3.connect(db_path) as conn:
        query = """
        SELECT date, open, high, low, close, volume
        FROM market_data
        WHERE symbol = 'ICICIBANK' AND interval = 'day'
        ORDER BY date
        LIMIT 100
        """
        df = pd.read_sql_query(query, conn, parse_dates=['date'])
    
    print(f"\n📊 Testing feature calculations on first 100 bars...")
    
    # Feature configuration from TradingConfig
    features = {
        "f1": ["RSI", 14, 1],
        "f2": ["WT", 10, 11],
        "f3": ["CCI", 20, 1],
        "f4": ["ADX", 20, 2],
        "f5": ["RSI", 9, 1]
    }
    
    # Calculate features bar by bar
    feature_values = []
    
    for idx, row in df.iterrows():
        close = row['close']
        high = row['high']
        low = row['low']
        
        # Calculate each feature
        f1 = enhanced_n_rsi(close, features["f1"][1], features["f1"][2], "ICICIBANK", "day")
        f2 = enhanced_n_wt(high, low, close, features["f2"][1], features["f2"][2], "ICICIBANK", "day")
        f3 = enhanced_n_cci(high, low, close, features["f3"][1], features["f3"][2], "ICICIBANK", "day")
        f4 = enhanced_n_adx(high, low, close, features["f4"][1], "ICICIBANK", "day")
        f5 = enhanced_n_rsi(close, features["f5"][1], features["f5"][2], "ICICIBANK", "day")
        
        feature_values.append({
            'bar': idx,
            'date': row['date'],
            'close': close,
            'f1_rsi14': f1,
            'f2_wt': f2,
            'f3_cci': f3,
            'f4_adx': f4,
            'f5_rsi9': f5
        })
        
        # Show first few bars in detail
        if idx < 5:
            print(f"\nBar {idx} ({row['date'].strftime('%Y-%m-%d')}):")
            print(f"   Close: ₹{close:.2f}")
            print(f"   F1 (RSI 14,1): {f1:.3f}")
            print(f"   F2 (WT 10,11): {f2:.3f}")
            print(f"   F3 (CCI 20,1): {f3:.3f}")
            print(f"   F4 (ADX 20): {f4:.3f}")
            print(f"   F5 (RSI 9,1): {f5:.3f}")
    
    df_features = pd.DataFrame(feature_values)
    
    # Analyze feature ranges
    print(f"\n📊 FEATURE VALUE RANGES (after warmup):")
    
    # Skip first 20 bars for warmup
    df_warmed = df_features.iloc[20:]
    
    for col in ['f1_rsi14', 'f2_wt', 'f3_cci', 'f4_adx', 'f5_rsi9']:
        min_val = df_warmed[col].min()
        max_val = df_warmed[col].max()
        mean_val = df_warmed[col].mean()
        std_val = df_warmed[col].std()
        
        print(f"\n{col}:")
        print(f"   Range: [{min_val:.3f}, {max_val:.3f}]")
        print(f"   Mean: {mean_val:.3f}")
        print(f"   Std: {std_val:.3f}")
    
    # Check for normalization
    print(f"\n📊 NORMALIZATION CHECK:")
    
    # All features should be normalized to [0, 1] range
    all_normalized = True
    
    for col in ['f1_rsi14', 'f2_wt', 'f3_cci', 'f4_adx', 'f5_rsi9']:
        min_val = df_warmed[col].min()
        max_val = df_warmed[col].max()
        
        if min_val < -0.1 or max_val > 1.1:
            print(f"   ❌ {col} is NOT normalized! Range: [{min_val:.3f}, {max_val:.3f}]")
            all_normalized = False
        else:
            print(f"   ✅ {col} is normalized. Range: [{min_val:.3f}, {max_val:.3f}]")
    
    # Check for NaN or invalid values
    print(f"\n📊 DATA QUALITY CHECK:")
    
    for col in ['f1_rsi14', 'f2_wt', 'f3_cci', 'f4_adx', 'f5_rsi9']:
        nan_count = df_features[col].isna().sum()
        zero_count = (df_features[col] == 0).sum()
        
        print(f"\n{col}:")
        print(f"   NaN values: {nan_count}")
        print(f"   Zero values: {zero_count}")
        
        if nan_count > 0:
            print(f"   ❌ Contains NaN values!")
        if zero_count > 50:
            print(f"   ⚠️  Many zero values - check calculation!")
    
    # Show feature evolution
    print(f"\n📊 FEATURE EVOLUTION (bars 20-30):")
    
    for idx in range(20, 30):
        row = df_features.iloc[idx]
        print(f"\nBar {idx}: RSI14={row['f1_rsi14']:.3f}, WT={row['f2_wt']:.3f}, "
              f"CCI={row['f3_cci']:.3f}, ADX={row['f4_adx']:.3f}, RSI9={row['f5_rsi9']:.3f}")
    
    # SUMMARY
    print(f"\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    print(f"Feature Calculation Verification:")
    print(f"1. All features calculated: ✅")
    print(f"2. Normalization: {'✅ All normalized' if all_normalized else '❌ Some features not normalized'}")
    print(f"3. Data quality: Check output above")
    
    print(f"\nKey Points:")
    print(f"- RSI features should be in [0, 1] range (normalized from [0, 100])")
    print(f"- WaveTrend should be in [0, 1] range")
    print(f"- CCI should be in [0, 1] range (normalized)")
    print(f"- ADX should be in [0, 1] range (normalized from [0, 100])")
    
    print(f"\nNext Steps:")
    print(f"1. Compare these values with Pine Script debug output")
    print(f"2. If values differ, check the normalization logic")
    print(f"3. Verify the indicator calculations match Pine Script exactly")
    
    print("="*70)


if __name__ == "__main__":
    verify_features()