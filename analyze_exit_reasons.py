"""
Analyze Exit Reasons from Results
=================================

Quick analysis of why trades are exiting.
"""

import json
import pandas as pd

# Load the results
with open('optimized_results.json', 'r') as f:
    results = json.load(f)

print("="*60)
print("EXIT REASON ANALYSIS")
print("="*60)

# Analyze each strategy
for strategy in ['conservative', 'scalping', 'adaptive', 'atr']:
    print(f"\n{strategy.upper()} STRATEGY:")
    print("-"*40)
    
    # Get one stock's data for analysis
    stock_data = results['results'][strategy]['individual_results']
    
    # Look at average win/loss across all stocks
    total_avg_win = 0
    total_avg_loss = 0
    count = 0
    
    for stock, data in stock_data.items():
        total_avg_win += data['avg_win']
        total_avg_loss += data['avg_loss']
        count += 1
    
    avg_win = total_avg_win / count
    avg_loss = total_avg_loss / count
    
    print(f"Average Win: {avg_win:.3f}%")
    print(f"Average Loss: {avg_loss:.3f}%")
    
    # Expected vs actual
    if strategy == 'conservative':
        print(f"Expected Win: ~2.0% (target)")
        print(f"Ratio: {avg_win/2.0:.1%} of expected")
    elif strategy == 'scalping':
        print(f"Expected Win: ~0.5-1.0% (targets)")
        print(f"Ratio: {avg_win/0.75:.1%} of expected")
    elif strategy == 'adaptive':
        print(f"Expected Win: ~1.0-3.0% (targets)")
        print(f"Ratio: {avg_win/2.0:.1%} of expected")
    
    # Check max_holding_bars from config
    if strategy == 'conservative':
        print(f"\nMax holding bars: 78")
    elif strategy == 'scalping':
        print(f"\nMax holding bars: 20")
        print("⚠️  SHORT holding period - might exit before targets!")
    elif strategy == 'adaptive':
        print(f"\nMax holding bars: 40")

print("\n" + "="*60)
print("KEY FINDINGS:")
print("="*60)

print("""
1. ALL strategies show average wins of ~0.3-0.4%
   - Conservative: 0.35% (expected 2.0%)
   - Scalping: 0.40% (expected 0.5-1.0%)
   - This is only 15-20% of expected!

2. Possible causes:
   a) TIME EXITS: Positions held too long hit max_holding_bars
   b) TRAILING STOPS: Activated early and exiting with small profits
   c) SIGNAL CHANGES: ML signal reversing and forcing exits
   d) DAY END: Positions closed at end of day

3. Scalping has max_holding_bars=20 (very short!)
   - At 5min bars, that's only 100 minutes
   - Not enough time to hit 0.5-1.0% targets

4. Need to see ACTUAL exit reasons from trades
""")

print("\nRECOMMENDATIONS:")
print("-"*40)
print("1. Increase max_holding_bars for all strategies")
print("2. Disable or adjust trailing stops")
print("3. Add detailed exit logging to see actual reasons")
print("4. Test with longer holding periods")