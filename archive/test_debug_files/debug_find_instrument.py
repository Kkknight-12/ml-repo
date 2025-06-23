#!/usr/bin/env python3
"""
Find correct instrument token for ICICIBANK and debug signals
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

def find_and_debug():
    """Find ICICIBANK token and debug signals"""
    
    # Initialize
    config = TradingConfig()
    processor = BarProcessor(config)
    client = ZerodhaClient()
    
    # First, let's find ICICIBANK
    print("="*70)
    print("FINDING ICICIBANK INSTRUMENT")
    print("="*70)
    
    instruments = client.get_instruments("NSE")
    icici_instruments = []
    
    for inst in instruments:
        if 'ICICI' in inst['tradingsymbol']:
            icici_instruments.append(inst)
            if inst['tradingsymbol'] == 'ICICIBANK':
                print(f"\nFound ICICIBANK:")
                print(f"  Symbol: {inst['tradingsymbol']}")
                print(f"  Name: {inst.get('name', 'N/A')}")
                print(f"  Token: {inst['instrument_token']}")
                print(f"  Exchange: {inst.get('exchange', 'N/A')}")
                instrument = inst
    
    if not icici_instruments:
        logger.error("No ICICI instruments found!")
        return
        
    print(f"\nAll ICICI related instruments found: {len(icici_instruments)}")
    for inst in icici_instruments[:5]:  # Show first 5
        print(f"  - {inst['tradingsymbol']} (Token: {inst['instrument_token']})")
    
    # Use the found instrument
    if 'instrument' not in locals():
        # Try to find exact match
        for inst in icici_instruments:
            if inst['tradingsymbol'] == 'ICICIBANK':
                instrument = inst
                break
    
    if 'instrument' not in locals():
        logger.error("Could not find ICICIBANK instrument")
        return
    
    print(f"\nUsing instrument: {instrument['tradingsymbol']} (Token: {instrument['instrument_token']})")
    
    # Now fetch historical data
    print("\n" + "="*70)
    print("FETCHING HISTORICAL DATA")
    print("="*70)
    
    try:
        # Try with found token
        historical_data = client.get_historical_data(
            instrument['instrument_token'],
            interval="day",
            days=100  # Start with 100 days for testing
        )
        
        if historical_data:
            print(f"✓ Successfully fetched {len(historical_data)} bars")
        else:
            print("✗ No data returned")
            return
            
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        return
    
    # Process bars and analyze
    print("\n" + "="*70)
    print("PROCESSING BARS")
    print("="*70)
    
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
        
        predictions_log.append({
            'date': candle['date'],
            'close': candle['close'],
            'prediction': result.prediction,
            'signal': result.signal,
            'start_long': result.start_long_trade,
            'start_short': result.start_short_trade
        })
        
        if result.start_long_trade:
            signals_log.append({'date': candle['date'], 'type': 'BUY', 'price': candle['close']})
        elif result.start_short_trade:
            signals_log.append({'date': candle['date'], 'type': 'SELL', 'price': candle['close']})
    
    df = pd.DataFrame(predictions_log)
    
    # Analysis
    print(f"\nTotal bars processed: {len(df)}")
    print(f"Total signals: {len(signals_log)}")
    
    print("\n" + "="*70)
    print("PREDICTION ANALYSIS")
    print("="*70)
    print(f"Predictions > 0: {(df['prediction'] > 0).sum()} ({(df['prediction'] > 0).mean()*100:.1f}%)")
    print(f"Predictions < 0: {(df['prediction'] < 0).sum()} ({(df['prediction'] < 0).mean()*100:.1f}%)")
    print(f"Predictions = 0: {(df['prediction'] == 0).sum()} ({(df['prediction'] == 0).mean()*100:.1f}%)")
    
    if len(signals_log) > 0:
        print("\n" + "="*70)
        print("SIGNALS FOUND")
        print("="*70)
        for sig in signals_log:
            print(f"{sig['date']}: {sig['type']} @ ₹{sig['price']:.2f}")
    else:
        print("\n⚠️  No signals found in the data!")
        
    # Check specific dates if they exist
    print("\n" + "="*70)
    print("CHECKING KEY DATES")
    print("="*70)
    
    key_dates = ['2025-03-21', '2025-05-12']
    for date_str in key_dates:
        date_rows = df[df['date'].astype(str).str.startswith(date_str)]
        if not date_rows.empty:
            row = date_rows.iloc[0]
            print(f"\n{date_str}:")
            print(f"  Prediction: {row['prediction']}")
            print(f"  Signal: {row['signal']}")
        else:
            print(f"\n{date_str}: Not in dataset")
    
    # Save for inspection
    df.to_csv('debug_icici_predictions.csv', index=False)
    print(f"\n✓ Saved predictions to debug_icici_predictions.csv")

if __name__ == "__main__":
    find_and_debug()
