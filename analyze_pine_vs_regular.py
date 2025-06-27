#!/usr/bin/env python3
"""
Analyze Pine Script vs Regular Backtesting Results
"""

import pandas as pd

# Load both CSV files
regular_df = pd.read_csv('5min_final_5-Min_Exact_Pine_Script_Settings.csv')
pine_df = pd.read_csv('5min_final_5-Min_Pine_Script_ml.backtest()_Logic.csv')

print("="*60)
print("PINE SCRIPT VS REGULAR BACKTESTING COMPARISON")
print("="*60)

# Basic stats
print(f"\nTrade Count:")
print(f"  Regular Backtesting: {len(regular_df)} trades")
print(f"  Pine Script Logic: {len(pine_df)} trades")

# Win rate
regular_wins = regular_df[regular_df['pnl_pct'] > 0]
pine_wins = pine_df[pine_df['pnl_pct'] > 0]

print(f"\nWin Rate:")
print(f"  Regular: {len(regular_wins)/len(regular_df)*100:.1f}% ({len(regular_wins)} wins, {len(regular_df)-len(regular_wins)} losses)")
print(f"  Pine Script: {len(pine_wins)/len(pine_df)*100:.1f}% ({len(pine_wins)} wins, {len(pine_df)-len(pine_wins)} losses)")

# Average PnL
print(f"\nAverage PnL per Trade:")
print(f"  Regular: {regular_df['pnl_pct'].mean():.2f}%")
print(f"  Pine Script: {pine_df['pnl_pct'].mean():.2f}%")

# Average holding period
print(f"\nAverage Holding Period:")
print(f"  Regular: {regular_df['bars_held'].mean():.1f} bars")
print(f"  Pine Script: {pine_df['bars_held'].mean():.1f} bars")

# Exit reasons
print(f"\nExit Reasons (Regular):")
for reason, count in regular_df['exit_reason'].value_counts().items():
    print(f"  {reason}: {count} ({count/len(regular_df)*100:.1f}%)")

print(f"\nExit Reasons (Pine Script):")
for reason, count in pine_df['exit_reason'].value_counts().items():
    print(f"  {reason}: {count} ({count/len(pine_df)*100:.1f}%)")

# Total return
regular_return = regular_df['pnl_pct'].sum()
pine_return = pine_df['pnl_pct'].sum()

print(f"\nTotal Return (Simple Sum):")
print(f"  Regular: {regular_return:.2f}%")
print(f"  Pine Script: {pine_return:.2f}%")

print("\n" + "="*60)
print("KEY DIFFERENCES:")
print("-"*60)
print("1. Pine Script generates more trades (no stop loss filtering)")
print("2. Pine Script exits only on signal changes")
print("3. Regular backtesting uses stops, targets, and time exits")
print("4. Pine Script results show pure signal accuracy")
print("="*60)