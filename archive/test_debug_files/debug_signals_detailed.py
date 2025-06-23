#!/usr/bin/env python3
"""
Debug script to find why Python and TradingView signals don't match
"""

import sys
sys.path.append('/Users/knight/Desktop/projects/mcp-testing/lorentzian_classifier')

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from data.zerodha_client import ZerodhaClient
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_specific_dates():
    """Debug why March 21 and May 12 show signals in Python but not TradingView"""
    
    # Initialize
    config = TradingConfig()
    processor = BarProcessor(config)
    client = ZerodhaClient()
    
    # Fetch data
    symbol = "ICICIBANK"
    
    # Get instruments and find ICICIBANK
    instruments = client.get_instruments("NSE")
    instrument = None
    for inst in instruments:
        if inst['tradingsymbol'] == symbol:
            instrument = inst
            break
    
    if not instrument:
        logger.error(f"Could not find instrument for {symbol}")
        return
    
    # Get historical data - 400 days to ensure we get 300 trading days
    historical_data = client.get_historical_data(
        instrument['instrument_token'],
        interval="day",
        days=400
    )
    
    if not historical_data:
        logger.error("No data fetched")
        return
    
    logger.info(f"Fetched {len(historical_data)} daily bars")
    
    # Take last 300 bars to match TradingView
    if len(historical_data) > 300:
        historical_data = historical_data[-300:]
        logger.info(f"Using last 300 bars for analysis")
    
    # Process each bar and track predictions
    predictions_log = []
    signals_log = []
    
    for i, candle in enumerate(historical_data):
        result = processor.process_bar(
            candle['open'],
            candle['high'], 
            candle['low'],
            candle['close'],
            candle['volume']
        )
        
        # Log every bar's prediction - using only attributes we know exist
        predictions_log.append({
            'date': candle['date'],
            'open': candle['open'],
            'high': candle['high'],
            'low': candle['low'],
            'close': candle['close'],
            'prediction': result.prediction,
            'signal': result.signal,
            'start_long': result.start_long_trade,
            'start_short': result.start_short_trade
        })
        
        # Log signals
        if result.start_long_trade:
            signals_log.append({
                'date': candle['date'],
                'type': 'BUY',
                'price': candle['close'],
                'prediction': result.prediction
            })
        elif result.start_short_trade:
            signals_log.append({
                'date': candle['date'],
                'type': 'SELL',
                'price': candle['close'],
                'prediction': result.prediction
            })
    
    # Create DataFrame for analysis
    df = pd.DataFrame(predictions_log)
    
    # Save detailed log
    df.to_csv('debug_predictions_log.csv', index=False)
    logger.info("Saved detailed predictions to debug_predictions_log.csv")
    
    # Check specific dates
    print("\n" + "="*70)
    print("SPECIFIC DATE ANALYSIS")
    print("="*70)
    
    important_dates = ['2025-03-21', '2025-05-12']
    for date in important_dates:
        date_data = df[df['date'].astype(str).str.startswith(date)]
        if not date_data.empty:
            row = date_data.iloc[0]
            print(f"\n{date}:")
            print(f"  OHLC: O:{row['open']:.2f} H:{row['high']:.2f} L:{row['low']:.2f} C:{row['close']:.2f}")
            print(f"  Prediction: {row['prediction']}")
            print(f"  Signal: {row['signal']}")
            print(f"  Start Long: {row['start_long']}")
            print(f"  Start Short: {row['start_short']}")
        else:
            print(f"\n{date}: No data found")
    
    # Signal summary
    print("\n" + "="*70)
    print("SIGNAL SUMMARY")
    print("="*70)
    print(f"Total bars processed: {len(df)}")
    print(f"Total signals: {len(signals_log)}")
    
    if signals_log:
        print("\nAll signals found:")
        for signal in signals_log[:10]:  # Show first 10 signals
            print(f"{signal['date']}: {signal['type']} @ {signal['price']:.2f} (Pred={signal['prediction']})")
        if len(signals_log) > 10:
            print(f"... and {len(signals_log) - 10} more signals")
    
    # Check prediction distribution
    print("\n" + "="*70)
    print("PREDICTION DISTRIBUTION")
    print("="*70)
    print(f"Predictions > 0: {(df['prediction'] > 0).sum()} ({(df['prediction'] > 0).mean()*100:.1f}%)")
    print(f"Predictions < 0: {(df['prediction'] < 0).sum()} ({(df['prediction'] < 0).mean()*100:.1f}%)")
    print(f"Predictions = 0: {(df['prediction'] == 0).sum()} ({(df['prediction'] == 0).mean()*100:.1f}%)")
    print(f"\nPrediction Statistics:")
    print(f"  Min: {df['prediction'].min()}")
    print(f"  Max: {df['prediction'].max()}")
    print(f"  Mean: {df['prediction'].mean():.2f}")
    print(f"  Std: {df['prediction'].std():.2f}")
    
    # Check signal distribution
    print("\n" + "="*70)
    print("SIGNAL DISTRIBUTION")
    print("="*70)
    signal_counts = df['signal'].value_counts()
    for sig, count in signal_counts.items():
        print(f"  Signal {sig}: {count} times ({count/len(df)*100:.1f}%)")
    
    # First check what attributes the result object has
    if len(predictions_log) > 0:
        print("\n" + "="*70)
        print("DEBUGGING INFO - Available Result Attributes:")
        print("="*70)
        # Process one more bar to check attributes
        test_result = processor.process_bar(
            historical_data[-1]['open'],
            historical_data[-1]['high'],
            historical_data[-1]['low'],
            historical_data[-1]['close'],
            historical_data[-1]['volume']
        )
        # List all attributes
        attrs = [attr for attr in dir(test_result) if not attr.startswith('_')]
        print(f"Result object attributes: {attrs}")

if __name__ == "__main__":
    debug_specific_dates()
