#!/usr/bin/env python3
"""
Debug filter pass rates and signal state changes
"""

import sys
sys.path.append('/Users/knight/Desktop/projects/mcp-testing/lorentzian_classifier')

from data.zerodha_client import ZerodhaClient
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
import pandas as pd

def debug_filters_and_signals():
    # Initialize
    client = ZerodhaClient()
    config = TradingConfig()
    processor = BarProcessor(config)
    
    symbol = "ICICIBANK"
    print(f"=== FILTER AND SIGNAL STATE ANALYSIS FOR {symbol} ===\n")
    
    # Get historical data
    historical_data = client.get_historical_data(
        symbol,
        interval="day",
        days=300
    )
    
    if not historical_data:
        print(f"Failed to fetch data for {symbol}")
        return
    
    print(f"Processing {len(historical_data)} bars...\n")
    
    # Track everything
    detailed_log = []
    signal_changes = []
    last_signal = None
    
    for i, candle in enumerate(historical_data):
        # Get internal state before processing
        ml_model = processor.ml_model
        
        result = processor.process_bar(
            candle['open'],
            candle['high'],
            candle['low'], 
            candle['close'],
            candle['volume']
        )
        
        # Track signal changes
        if last_signal is not None and result.signal != last_signal:
            signal_changes.append({
                'bar': i,
                'date': candle['date'],
                'from': last_signal,
                'to': result.signal,
                'prediction': result.prediction
            })
        
        last_signal = result.signal
        
        # Log details for each bar
        detailed_log.append({
            'bar': i,
            'date': candle['date'],
            'close': candle['close'],
            'prediction': result.prediction,
            'signal': result.signal,
            'filter_all': getattr(result, 'filter_all', 'N/A'),
            'start_long': result.start_long_trade,
            'start_short': result.start_short_trade,
            # Try to get individual filter states if available
            'volatility_filter': getattr(result, 'volatility_filter', 'N/A'),
            'regime_filter': getattr(result, 'regime_filter', 'N/A'),
            'adx_filter': getattr(result, 'adx_filter', 'N/A'),
            'is_bullish': getattr(result, 'is_bullish', 'N/A'),
            'is_bearish': getattr(result, 'is_bearish', 'N/A')
        })
    
    df = pd.DataFrame(detailed_log)
    
    # Analyze filters
    print("=== FILTER ANALYSIS ===")
    
    # Check if we have filter data
    if df['filter_all'].iloc[0] != 'N/A':
        filter_pass_rate = df['filter_all'].sum() / len(df) * 100
        print(f"Filter All Pass Rate: {filter_pass_rate:.1f}%")
        print(f"Bars where filters passed: {df['filter_all'].sum()} out of {len(df)}")
    else:
        print("Filter data not available in result object")
    
    # Signal change analysis
    print(f"\n=== SIGNAL CHANGE ANALYSIS ===")
    print(f"Total signal changes: {len(signal_changes)}")
    print(f"Signal change rate: {len(signal_changes)/len(df)*100:.1f}%")
    
    if signal_changes:
        print("\nSignal changes:")
        for change in signal_changes[:10]:  # Show first 10
            print(f"  Bar {change['bar']} ({change['date']}): {change['from']} → {change['to']} (Pred={change['prediction']})")
        if len(signal_changes) > 10:
            print(f"  ... and {len(signal_changes)-10} more changes")
    
    # Signal persistence analysis
    print(f"\n=== SIGNAL PERSISTENCE ANALYSIS ===")
    
    # Calculate consecutive signal counts
    consecutive_counts = []
    current_signal = df.iloc[0]['signal']
    count = 1
    
    for i in range(1, len(df)):
        if df.iloc[i]['signal'] == current_signal:
            count += 1
        else:
            consecutive_counts.append({
                'signal': current_signal,
                'count': count,
                'start_bar': i - count,
                'end_bar': i - 1
            })
            current_signal = df.iloc[i]['signal']
            count = 1
    
    # Add last sequence
    consecutive_counts.append({
        'signal': current_signal,
        'count': count,
        'start_bar': len(df) - count,
        'end_bar': len(df) - 1
    })
    
    # Show longest sequences
    sorted_counts = sorted(consecutive_counts, key=lambda x: x['count'], reverse=True)
    print(f"\nLongest signal sequences:")
    for seq in sorted_counts[:5]:
        start_date = df.iloc[seq['start_bar']]['date']
        end_date = df.iloc[seq['end_bar']]['date']
        print(f"  Signal {seq['signal']}: {seq['count']} bars ({start_date} to {end_date})")
    
    # Check specific problem dates
    print(f"\n=== PROBLEM DATE ANALYSIS ===")
    
    # March 21 - why no sell signal when prediction is -5?
    march_21 = df[df['date'].astype(str).str.startswith('2025-03-21')]
    if not march_21.empty:
        row = march_21.iloc[0]
        bar_idx = row['bar']
        print(f"\nMarch 21, 2025 (Bar {bar_idx}):")
        print(f"  Prediction: {row['prediction']}")
        print(f"  Signal: {row['signal']}")
        
        # Check previous bars
        if bar_idx > 0:
            prev_row = df.iloc[bar_idx - 1]
            print(f"  Previous bar signal: {prev_row['signal']}")
            print(f"  Signal changed? {prev_row['signal'] != row['signal']}")
        
        print(f"  Start Short: {row['start_short']}")
        print(f"  Reason: Signal must CHANGE to generate new signal")
    
    # Save detailed log
    df.to_csv('debug_filter_signal_analysis.csv', index=False)
    print(f"\n✓ Saved detailed analysis to debug_filter_signal_analysis.csv")
    
    # Final summary
    print(f"\n=== SUMMARY ===")
    print(f"1. Signal mostly stays in one state (low change rate)")
    print(f"2. New signals only generate on state CHANGE")
    print(f"3. This explains why so few signals vs TradingView")
    print(f"4. Need to check why signal persists so long")

if __name__ == "__main__":
    debug_filters_and_signals()
