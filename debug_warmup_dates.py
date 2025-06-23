#!/usr/bin/env python3
"""
Debug script to understand warmup period dates
"""
import pandas as pd
from datetime import datetime, timedelta

def analyze_warmup_dates():
    """Analyze when warmup period ends based on the test data"""
    
    # From the test output
    total_bars = 2471
    warmup_bars = 2000
    bars_after_warmup = total_bars - warmup_bars  # 471
    
    # Assuming data ends around June 2025 (from test output showing 2025-06-23)
    end_date = datetime(2025, 6, 23)
    
    # Calculate approximate start date (assuming ~250 trading days per year)
    total_years = total_bars / 250
    start_date_approx = end_date - timedelta(days=total_years * 365)
    
    # Calculate when warmup would end
    warmup_years = warmup_bars / 250
    warmup_end_approx = start_date_approx + timedelta(days=warmup_years * 365)
    
    # Also calculate from the end
    bars_after_warmup_years = bars_after_warmup / 250
    warmup_end_from_end = end_date - timedelta(days=bars_after_warmup_years * 365)
    
    print("="*70)
    print("WARMUP PERIOD ANALYSIS")
    print("="*70)
    
    print(f"\n1. DATA OVERVIEW:")
    print(f"   Total bars: {total_bars}")
    print(f"   Warmup bars: {warmup_bars}")
    print(f"   Bars after warmup: {bars_after_warmup}")
    print(f"   Total years of data: ~{total_years:.1f}")
    
    print(f"\n2. DATE CALCULATIONS:")
    print(f"   Data end date: {end_date.strftime('%Y-%m-%d')}")
    print(f"   Approx start date: {start_date_approx.strftime('%Y-%m-%d')}")
    print(f"   Warmup ends (from start): {warmup_end_approx.strftime('%Y-%m-%d')}")
    print(f"   Warmup ends (from end): {warmup_end_from_end.strftime('%Y-%m-%d')}")
    
    print(f"\n3. SIGNAL TIMING COMPARISON:")
    # Python signals from output
    python_first_signal = datetime(2023, 8, 14)
    pine_first_signal = datetime(2024, 4, 18)
    
    print(f"   Python first signal: {python_first_signal.strftime('%Y-%m-%d')}")
    print(f"   Pine first signal: {pine_first_signal.strftime('%Y-%m-%d')}")
    print(f"   Difference: {(pine_first_signal - python_first_signal).days} days")
    
    # Check if Python signal is after warmup
    if python_first_signal > warmup_end_from_end:
        print(f"\n   ✅ Python signal IS after warmup period")
        days_after_warmup = (python_first_signal - warmup_end_from_end).days
        print(f"      Signal came {days_after_warmup} days after warmup ended")
    else:
        print(f"\n   ❌ Python signal is DURING warmup period")
        days_before_warmup_end = (warmup_end_from_end - python_first_signal).days
        print(f"      Signal came {days_before_warmup_end} days before warmup ends")
    
    print(f"\n4. POSSIBLE EXPLANATIONS:")
    print(f"   • Pine Script might have different data range")
    print(f"   • Pine Script might have additional signal delay after warmup")
    print(f"   • Entry conditions might be evaluated differently")
    print(f"   • Signal state initialization might differ")
    
    print(f"\n5. BARS AT KEY DATES:")
    # Calculate which bar number corresponds to key dates
    # Assuming linear distribution of bars
    days_per_bar = (end_date - start_date_approx).days / total_bars
    
    python_signal_bar = total_bars - int((end_date - python_first_signal).days / days_per_bar)
    pine_signal_bar = total_bars - int((end_date - pine_first_signal).days / days_per_bar)
    
    print(f"   Python first signal at approximately bar: {python_signal_bar}")
    print(f"   Pine first signal at approximately bar: {pine_signal_bar}")
    print(f"   Warmup ends at bar: {warmup_bars}")
    
    if python_signal_bar > warmup_bars:
        print(f"\n   ✅ Python signal bar ({python_signal_bar}) > warmup bars ({warmup_bars})")
    else:
        print(f"\n   ❌ Python signal bar ({python_signal_bar}) <= warmup bars ({warmup_bars})")

if __name__ == "__main__":
    analyze_warmup_dates()