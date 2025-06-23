"""
Fetch ICICIBANK data from Zerodha - Proper Training/Testing Split
- Training: 2000 bars BEFORE 2024-04-05
- Testing: Same date range as TradingView CSV
"""
import os
import sys
import csv
from datetime import datetime, timedelta
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.zerodha_client import ZerodhaClient


def fetch_data_in_chunks(client, instrument_token, start_date, end_date):
    """
    Fetch data in chunks respecting Zerodha's 2000-day limit
    """
    all_data = []
    current_start = start_date
    
    while current_start < end_date:
        # Calculate chunk end (max 1999 days)
        chunk_end = min(current_start + timedelta(days=1999), end_date)
        
        print(f"   Fetching: {current_start.date()} to {chunk_end.date()}")
        
        try:
            chunk_data = client.kite.historical_data(
                instrument_token=instrument_token,
                from_date=current_start,
                to_date=chunk_end,
                interval="day"
            )
            
            if chunk_data:
                all_data.extend(chunk_data)
                print(f"   ✓ Got {len(chunk_data)} bars")
            
            # Move to next chunk
            current_start = chunk_end + timedelta(days=1)
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
            break
    
    return all_data


def fetch_training_testing_data():
    """Fetch separate training and testing data"""
    print("=" * 80)
    print("📊 ZERODHA DATA FETCHER - PROPER TRAIN/TEST SPLIT")
    print("=" * 80)
    
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
    tv_start = datetime.strptime("2024-04-05", "%Y-%m-%d")
    tv_end = datetime.strptime("2025-06-20", "%Y-%m-%d")
    
    # Training data should end 1 day before TV data starts
    training_end = tv_start - timedelta(days=1)  # 2024-04-04
    
    # For 2000 trading days, go back ~8 years (accounting for weekends/holidays)
    training_start = training_end - timedelta(days=3000)
    
    print(f"\n📅 Date Ranges:")
    print(f"   Training: {training_start.date()} to {training_end.date()}")
    print(f"   Testing:  {tv_start.date()} to {tv_end.date()}")
    print(f"   No overlap! ✅")
    
    # 1. Fetch Training Data (2000 bars before TV start)
    print("\n📈 [1/2] Fetching TRAINING data...")
    training_data = fetch_data_in_chunks(client, instrument_token, training_start, training_end)
    
    # Keep only last 2000 bars for training
    if len(training_data) > 2000:
        training_data = training_data[-2000:]
    
    print(f"\n✅ Training data: {len(training_data)} bars")
    if training_data:
        print(f"   Range: {training_data[0]['date'].date()} to {training_data[-1]['date'].date()}")
        
        # Save training data
        with open('zerodha_training_data.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['time', 'open', 'high', 'low', 'close', 'volume'])
            
            for bar in training_data:
                writer.writerow([
                    bar['date'].strftime('%Y-%m-%d'),
                    bar['open'],
                    bar['high'],
                    bar['low'],
                    bar['close'],
                    bar['volume']
                ])
        
        print("   Saved to: zerodha_training_data.csv")
    
    # 2. Fetch Testing Data (same range as TradingView)
    print("\n📈 [2/2] Fetching TESTING data (TV comparison)...")
    testing_data = client.kite.historical_data(
        instrument_token=instrument_token,
        from_date=tv_start,
        to_date=tv_end,
        interval="day"
    )
    
    print(f"\n✅ Testing data: {len(testing_data)} bars")
    if testing_data:
        print(f"   Range: {testing_data[0]['date'].date()} to {testing_data[-1]['date'].date()}")
        
        # Save testing data
        with open('zerodha_testing_data.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['time', 'open', 'high', 'low', 'close', 'volume'])
            
            for bar in testing_data:
                writer.writerow([
                    bar['date'].strftime('%Y-%m-%d'),
                    bar['open'],
                    bar['high'],
                    bar['low'],
                    bar['close'],
                    bar['volume']
                ])
        
        print("   Saved to: zerodha_testing_data.csv")
    
    # 3. Compare with TradingView data
    print("\n🔍 Comparing Testing data with TradingView...")
    
    # Load TV dates
    tv_dates = []
    with open('NSE_ICICIBANK, 1D.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tv_dates.append(row['time'])
    
    # Compare
    zerodha_dates = [bar['date'].strftime('%Y-%m-%d') for bar in testing_data]
    
    tv_set = set(tv_dates)
    zerodha_set = set(zerodha_dates)
    
    missing_in_zerodha = tv_set - zerodha_set
    missing_in_tv = zerodha_set - tv_set
    
    print(f"   Dates in TradingView: {len(tv_dates)}")
    print(f"   Dates in Zerodha: {len(zerodha_dates)}")
    print(f"   Missing in Zerodha: {len(missing_in_zerodha)}")
    print(f"   Missing in TV: {len(missing_in_tv)}")
    
    if len(missing_in_zerodha) < 5 and len(missing_in_tv) < 5:
        print("   ✅ Date ranges match well!")
    
    # 4. Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"\n✅ Training Data: {len(training_data)} bars (BEFORE TV data)")
    print(f"✅ Testing Data: {len(testing_data)} bars (SAME as TV range)")
    print(f"✅ No overlap between training and testing!")
    
    print("\n📋 Next Steps:")
    print("1. Run: python test_with_split_data.py")
    print("2. This will:")
    print("   - Train ML on historical data")
    print("   - Test on TV date range")
    print("   - Compare signals with TradingView")


def main():
    fetch_training_testing_data()


if __name__ == "__main__":
    main()
