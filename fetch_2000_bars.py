"""
Enhanced Zerodha Data Fetcher with 2000-day limit handling
Fetches exactly 2000 bars for ML training
"""
import os
import sys
import csv
from datetime import datetime, timedelta
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.zerodha_client import ZerodhaClient


def fetch_training_data_in_chunks(client, instrument_token, end_date, total_days=2000):
    """
    Fetch historical data in chunks to respect Zerodha's 2000-day limit
    """
    all_data = []
    current_end = end_date
    days_remaining = total_days
    
    while days_remaining > 0:
        # Calculate chunk size (max 1999 days to be safe)
        chunk_days = min(days_remaining, 1999)
        current_start = current_end - timedelta(days=chunk_days)
        
        print(f"   Fetching chunk: {current_start.date()} to {current_end.date()} ({chunk_days} days)")
        
        try:
            chunk_data = client.kite.historical_data(
                instrument_token=instrument_token,
                from_date=current_start,
                to_date=current_end,
                interval="day"
            )
            
            if chunk_data:
                all_data = chunk_data + all_data  # Prepend to maintain order
                print(f"   ✓ Got {len(chunk_data)} bars")
            
            # Move to next chunk
            current_end = current_start - timedelta(days=1)
            days_remaining -= chunk_days
            
        except Exception as e:
            print(f"   ✗ Error in chunk: {e}")
            break
    
    return all_data


def fetch_zerodha_data_fixed():
    """Fixed version: Fetch exactly 2000 bars for training"""
    print("=" * 60)
    print("📊 ZERODHA DATA FETCHER - 2000 BAR TRAINING")
    print("=" * 60)
    
    # Initialize client
    client = ZerodhaClient()
    if not client.kite:
        print("❌ Not authenticated. Run auth_helper.py first")
        return
    
    print("✅ Zerodha client initialized")
    
    # Get ICICIBANK token
    symbol = "ICICIBANK"
    instrument_token = None
    
    try:
        instruments = client.kite.instruments("NSE")
        for inst in instruments:
            if inst['tradingsymbol'] == symbol:
                instrument_token = inst['instrument_token']
                break
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    if not instrument_token:
        print(f"❌ Instrument not found: {symbol}")
        return
    
    print(f"✅ Found {symbol}: {instrument_token}")
    
    # Define dates
    tv_start_date = datetime.strptime("2024-04-05", "%Y-%m-%d")
    
    # Fetch 2000 bars before TV start date for training
    print("\n📈 Fetching 2000 bars for ML training...")
    ml_data = fetch_training_data_in_chunks(
        client, 
        instrument_token, 
        tv_start_date - timedelta(days=1),
        total_days=2800  # Extra days to ensure 2000 trading days
    )
    
    # Filter to get exactly 2000 most recent bars before TV start
    ml_data_filtered = []
    for bar in reversed(ml_data):  # Start from most recent
        if bar['date'].date() < tv_start_date.date():
            ml_data_filtered.append(bar)
            if len(ml_data_filtered) >= 2000:
                break
    
    ml_data_filtered.reverse()  # Back to chronological order
    
    print(f"\n✅ Got {len(ml_data_filtered)} training bars")
    
    if ml_data_filtered:
        # Save training data
        with open('zerodha_training_2000.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['time', 'open', 'high', 'low', 'close', 'volume'])
            
            for bar in ml_data_filtered:
                writer.writerow([
                    bar['date'].strftime('%Y-%m-%d'),
                    bar['open'],
                    bar['high'],
                    bar['low'],
                    bar['close'],
                    bar['volume']
                ])
        
        print(f"✅ Saved training data: zerodha_training_2000.csv")
        print(f"   Date range: {ml_data_filtered[0]['date'].date()} to {ml_data_filtered[-1]['date'].date()}")
    
    # Now fetch TV comparison data
    print("\n📈 Fetching TV comparison data...")
    try:
        tv_data = client.kite.historical_data(
            instrument_token=instrument_token,
            from_date=tv_start_date,
            to_date=datetime.strptime("2025-06-20", "%Y-%m-%d"),
            interval="day"
        )
        
        print(f"✅ Got {len(tv_data)} TV comparison bars")
        
        # Combine training + TV data
        all_data = ml_data_filtered + tv_data
        
        # Save combined data
        with open('zerodha_complete_data.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['time', 'open', 'high', 'low', 'close', 'volume'])
            
            for bar in all_data:
                writer.writerow([
                    bar['date'].strftime('%Y-%m-%d'),
                    bar['open'],
                    bar['high'],
                    bar['low'],
                    bar['close'],
                    bar['volume']
                ])
        
        print(f"\n✅ Created complete dataset: zerodha_complete_data.csv")
        print(f"   Total bars: {len(all_data)}")
        print(f"   Training bars: {len(ml_data_filtered)}")
        print(f"   TV comparison bars: {len(tv_data)}")
        
    except Exception as e:
        print(f"❌ Error fetching TV data: {e}")
    
    print("\n📋 Next Steps:")
    print("1. Run python test_with_2000_bars.py")
    print("2. This will use proper 2000 bar training")
    print("3. Should generate signals correctly")


def main():
    fetch_zerodha_data_fixed()


if __name__ == "__main__":
    main()
