#!/usr/bin/env python3
"""
Test the filter pass rate fix
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

def test_filter_pass_rate_calculation():
    """Test that the filter pass rate calculation works correctly"""
    
    print("="*70)
    print("TEST FILTER PASS RATE CALCULATION FIX")
    print("="*70)
    
    # Create test data similar to what export creates
    test_data = {
        'bar': list(range(2000, 2050)),
        'warmup': [0] * 50,  # All post-warmup
        'filt_vol': [1, 0, 1, 0, 1] * 10,  # 50% pass rate
        'filt_reg': [1, 1, 0, 0, 0] * 10,  # 40% pass rate  
        'filt_adx': [1] * 50,              # 100% pass rate (disabled)
        'filt_all': [1, 0, 0, 0, 0] * 10   # 20% pass rate
    }
    
    df = pd.DataFrame(test_data)
    
    print("\n1. Test DataFrame created with known pass rates:")
    print(f"   - Volatility: Should be 50%")
    print(f"   - Regime: Should be 40%")
    print(f"   - ADX: Should be 100%")
    print(f"   - All: Should be 20%")
    
    # Test old calculation (might fail if values are strings)
    print("\n2. Testing direct mean() calculation:")
    try:
        vol_old = df['filt_vol'].mean() * 100
        print(f"   - Volatility: {vol_old:.1f}%")
    except Exception as e:
        print(f"   - ERROR: {e}")
    
    # Test new calculation with pd.to_numeric
    print("\n3. Testing with pd.to_numeric():")
    vol_new = pd.to_numeric(df['filt_vol'], errors='coerce').mean() * 100
    reg_new = pd.to_numeric(df['filt_reg'], errors='coerce').mean() * 100
    adx_new = pd.to_numeric(df['filt_adx'], errors='coerce').mean() * 100
    all_new = pd.to_numeric(df['filt_all'], errors='coerce').mean() * 100
    
    print(f"   - Volatility: {vol_new:.1f}%")
    print(f"   - Regime: {reg_new:.1f}%")
    print(f"   - ADX: {adx_new:.1f}%")
    print(f"   - All: {all_new:.1f}%")
    
    # Test with string values (simulating potential CSV read issue)
    print("\n4. Testing with string values (simulating CSV issue):")
    df_str = df.copy()
    df_str['filt_vol'] = df_str['filt_vol'].astype(str)
    df_str['filt_reg'] = df_str['filt_reg'].astype(str)
    
    # This would fail with direct mean()
    try:
        vol_str_old = df_str['filt_vol'].mean() * 100
        print(f"   - Direct mean() on strings: {vol_str_old:.1f}%")
    except Exception as e:
        print(f"   - Direct mean() on strings: ERROR - {type(e).__name__}")
    
    # This should work with pd.to_numeric
    vol_str_new = pd.to_numeric(df_str['filt_vol'], errors='coerce').mean() * 100
    reg_str_new = pd.to_numeric(df_str['filt_reg'], errors='coerce').mean() * 100
    
    print(f"   - With pd.to_numeric - Volatility: {vol_str_new:.1f}%")
    print(f"   - With pd.to_numeric - Regime: {reg_str_new:.1f}%")
    
    # SUMMARY
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("The fix using pd.to_numeric() ensures that:")
    print("1. String values are converted to numeric before calculation")
    print("2. Invalid values are converted to NaN and ignored in mean()")
    print("3. Filter pass rates are calculated correctly regardless of data type")
    print("\nThis should resolve the 0.0% filter pass rate issue!")
    print("="*70)

if __name__ == "__main__":
    test_filter_pass_rate_calculation()