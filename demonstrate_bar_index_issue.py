#!/usr/bin/env python3
"""
Demonstrate the bar_index vs last_bar_index issue
"""

import sys
sys.path.append('/Users/knight/Desktop/projects/mcp-testing/lorentzian_classifier')

from data.zerodha_client import ZerodhaClient
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
import pandas as pd

def demonstrate_issue():
    # Initialize
    client = ZerodhaClient()
    config = TradingConfig()
    processor = BarProcessor(config)
    
    symbol = "ICICIBANK"
    print(f"=== BAR INDEX ISSUE DEMONSTRATION ===\n")
    print(f"Settings:")
    print(f"  max_bars_back = {config.max_bars_back}")
    
    # Get historical data
    historical_data = client.get_historical_data(
        symbol,
        interval="day",
        days=300
    )
    
    if not historical_data:
        print(f"Failed to fetch data")
        return
    
    total_bars = len(historical_data)
    print(f"\nTotal bars fetched: {total_bars}")
    
    # Pine Script logic
    if total_bars >= config.max_bars_back:
        pine_max_bars_back_index = total_bars - config.max_bars_back
    else:
        pine_max_bars_back_index = 0
    
    print(f"\n=== PINE SCRIPT LOGIC ===")
    print(f"last_bar_index = {total_bars - 1}")
    print(f"maxBarsBackIndex = {pine_max_bars_back_index}")
    print(f"ML starts at bar: {pine_max_bars_back_index}")
    print(f"ML processes bars: {pine_max_bars_back_index} to {total_bars-1}")
    print(f"Total bars for ML: {total_bars - pine_max_bars_back_index}")
    
    # Python current logic (WRONG)
    print(f"\n=== PYTHON CURRENT LOGIC (WRONG) ===")
    for i in [0, 50, 100, 150, 200]:
        if i < total_bars:
            python_max_bars_back_index = max(0, i - config.max_bars_back)
            will_predict = i >= python_max_bars_back_index
            print(f"Bar {i}: max_bars_back_index = {python_max_bars_back_index}, will predict = {will_predict}")
    
    # The problem
    print(f"\n=== THE PROBLEM ===")
    print(f"1. Python calculates max_bars_back_index for EACH bar")
    print(f"2. Early bars (0-{config.max_bars_back}) all get max_bars_back_index = 0")
    print(f"3. So ML runs from the very beginning with insufficient data!")
    print(f"4. This causes poor predictions and stuck signals")
    
    # The solution
    print(f"\n=== THE SOLUTION ===")
    print(f"1. Calculate max_bars_back_index ONCE using total bars")
    print(f"2. If total_bars < max_bars_back: process all bars (but with caution)")
    print(f"3. If total_bars >= max_bars_back: skip early bars for ML")
    print(f"4. This ensures ML has sufficient training data")
    
    # Let's check actual predictions
    print(f"\n=== CHECKING ACTUAL BEHAVIOR ===")
    
    early_predictions = []
    late_predictions = []
    
    for i, candle in enumerate(historical_data):
        result = processor.process_bar(
            candle['open'],
            candle['high'],
            candle['low'],
            candle['close'],
            candle['volume']
        )
        
        if i < 50:  # Early bars
            early_predictions.append(result.prediction)
        if i >= total_bars - 50:  # Late bars
            late_predictions.append(result.prediction)
    
    print(f"\nFirst 50 bars predictions:")
    print(f"  Non-zero: {sum(1 for p in early_predictions if p != 0)}")
    print(f"  Average |pred|: {sum(abs(p) for p in early_predictions) / len(early_predictions):.2f}")
    
    print(f"\nLast 50 bars predictions:")
    print(f"  Non-zero: {sum(1 for p in late_predictions if p != 0)}")
    print(f"  Average |pred|: {sum(abs(p) for p in late_predictions) / len(late_predictions):.2f}")
    
    print(f"\n💡 If early bars have many predictions, that's the problem!")
    print(f"   ML shouldn't run until it has enough training data.")

if __name__ == "__main__":
    demonstrate_issue()
