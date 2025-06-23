#!/usr/bin/env python3
"""
Debug signals using same approach as test_daily_data.py
"""

import sys
sys.path.append('/Users/knight/Desktop/projects/mcp-testing/lorentzian_classifier')

from data.zerodha_client import ZerodhaClient
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
import pandas as pd

def debug_signals():
    # Initialize exactly like test_daily_data.py
    client = ZerodhaClient()
    config = TradingConfig()
    
    symbol = "ICICIBANK"
    print(f"=== DEBUGGING {symbol} SIGNALS ===")
    
    # Get historical data - using same method as test_daily_data.py
    historical_data = client.get_historical_data(
        symbol,
        interval="day",
        days=300  # Get more data for better analysis
    )
    
    if not historical_data:
        print(f"Failed to fetch data for {symbol}")
        return
    
    print(f"✓ Fetched {len(historical_data)} daily bars")
    print(f"Date range: {historical_data[0]['date']} to {historical_data[-1]['date']}")
    
    # Initialize processor with total bars (Pine Script compatibility fix)
    processor = BarProcessor(config, total_bars=len(historical_data))
    print(f"\nPine Script Logic Applied:")
    print(f"  Total bars: {len(historical_data)}")
    print(f"  Max bars back: {config.max_bars_back}")
    print(f"  Max bars back index: {processor.max_bars_back_index}")
    print(f"  ML starts at bar: {processor.max_bars_back_index + 1}")
    
    # Process bars and collect detailed info
    all_predictions = []
    all_signals = []
    
    for i, candle in enumerate(historical_data):
        result = processor.process_bar(
            candle['open'],
            candle['high'],
            candle['low'], 
            candle['close'],
            candle['volume']
        )
        
        # Collect prediction info
        all_predictions.append({
            'date': candle['date'],
            'close': candle['close'],
            'prediction': result.prediction,
            'signal': result.signal,
            'is_buy': result.start_long_trade,
            'is_sell': result.start_short_trade
        })
        
        # Collect actual signals
        if result.start_long_trade:
            all_signals.append({
                'date': candle['date'],
                'type': 'BUY',
                'price': candle['close'],
                'prediction': result.prediction
            })
            
        if result.start_short_trade:
            all_signals.append({
                'date': candle['date'],
                'type': 'SELL', 
                'price': candle['close'],
                'prediction': result.prediction
            })
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(all_predictions)
    
    print("\n=== PREDICTION SUMMARY ===")
    print(f"Total bars: {len(df)}")
    print(f"Predictions > 0: {(df['prediction'] > 0).sum()} ({(df['prediction'] > 0).mean()*100:.1f}%)")
    print(f"Predictions < 0: {(df['prediction'] < 0).sum()} ({(df['prediction'] < 0).mean()*100:.1f}%)")
    print(f"Predictions = 0: {(df['prediction'] == 0).sum()} ({(df['prediction'] == 0).mean()*100:.1f}%)")
    
    print(f"\nPrediction value range: {df['prediction'].min()} to {df['prediction'].max()}")
    print(f"Average prediction: {df['prediction'].mean():.2f}")
    
    print(f"\n=== SIGNAL SUMMARY ===")
    print(f"Total signals: {len(all_signals)}")
    print(f"Signal rate: {len(all_signals)/len(df)*100:.1f}%")
    
    # Show all signals
    if all_signals:
        print("\nAll signals found:")
        for sig in all_signals:
            print(f"  {sig['date']}: {sig['type']} @ ₹{sig['price']:.2f} (Pred={sig['prediction']})")
    
    # Check specific dates
    print("\n=== SPECIFIC DATE CHECK ===")
    dates_to_check = ['2025-03-21', '2025-05-12']
    
    for date_str in dates_to_check:
        matching = df[df['date'].astype(str).str.startswith(date_str)]
        if not matching.empty:
            row = matching.iloc[0]
            print(f"\n{date_str}:")
            print(f"  Close: ₹{row['close']:.2f}")
            print(f"  Prediction: {row['prediction']}")
            print(f"  Signal: {row['signal']}")
            print(f"  Buy Signal: {row['is_buy']}")
            print(f"  Sell Signal: {row['is_sell']}")
        else:
            print(f"\n{date_str}: Not found in data")
    
    # Save detailed log
    df.to_csv('debug_daily_predictions.csv', index=False)
    print("\n✓ Saved detailed predictions to debug_daily_predictions.csv")
    
    # Signal value distribution
    print("\n=== SIGNAL VALUE DISTRIBUTION ===")
    signal_counts = df['signal'].value_counts()
    for signal_val, count in signal_counts.items():
        print(f"Signal {signal_val}: {count} times ({count/len(df)*100:.1f}%)")

if __name__ == "__main__":
    debug_signals()
