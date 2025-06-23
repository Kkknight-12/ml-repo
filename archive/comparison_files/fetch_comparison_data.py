"""
Fetch ICICIBANK data from Zerodha for comparison testing
- Fetch 2000+ bars for ML training
- Fetch exact date range as TradingView CSV
"""
import os
import sys
import csv
from datetime import datetime, timedelta
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.zerodha_client import ZerodhaClient


def fetch_zerodha_data():
    """Fetch ICICIBANK data from Zerodha"""
    print("=" * 60)
    print("📊 ZERODHA DATA FETCHER FOR COMPARISON")
    print("=" * 60)
    
    # Initialize Zerodha client
    client = ZerodhaClient()
    
    # Check if authenticated
    if not client.kite:
        print("❌ Not authenticated. Run auth_helper.py first")
        return
    
    print("✅ Zerodha client initialized")
    
    # Define date ranges
    # For TradingView comparison: 2024-04-05 to 2025-06-20
    tv_start_date = "2024-04-05"
    tv_end_date = "2025-06-20"
    
    # For ML training: 2000 bars before TV start date
    # Assuming ~250 trading days per year, 2000 bars = ~8 years
    ml_end_date = datetime.strptime(tv_start_date, "%Y-%m-%d") - timedelta(days=1)
    ml_start_date = ml_end_date - timedelta(days=3000)  # Extra days for holidays
    
    print(f"\n📅 Date Ranges:")
    print(f"   ML Training: {ml_start_date.date()} to {ml_end_date.date()}")
    print(f"   TV Comparison: {tv_start_date} to {tv_end_date}")
    
    # Fetch data
    symbol = "ICICIBANK"
    instrument_token = None
    
    # Get instrument token
    try:
        instruments = client.kite.instruments("NSE")
        for inst in instruments:
            if inst['tradingsymbol'] == symbol:
                instrument_token = inst['instrument_token']
                break
                
        if not instrument_token:
            print(f"❌ Could not find instrument token for {symbol}")
            return
            
        print(f"\n✅ Found instrument token: {instrument_token}")
        
    except Exception as e:
        print(f"❌ Error fetching instruments: {e}")
        return
    
    # Fetch ML training data (2000+ bars)
    print("\n📈 Fetching ML training data...")
    try:
        ml_data = client.kite.historical_data(
            instrument_token=instrument_token,
            from_date=ml_start_date,
            to_date=ml_end_date,
            interval="day"
        )
        print(f"   Fetched {len(ml_data)} bars for ML training")
        
        # Save ML training data
        ml_df = pd.DataFrame(ml_data)
        ml_df.to_csv('zerodha_ml_training_data.csv', index=False)
        print("   Saved to: zerodha_ml_training_data.csv")
        
    except Exception as e:
        print(f"❌ Error fetching ML data: {e}")
        ml_data = []
    
    # Fetch TV comparison data
    print("\n📈 Fetching TV comparison data...")
    try:
        tv_data = client.kite.historical_data(
            instrument_token=instrument_token,
            from_date=datetime.strptime(tv_start_date, "%Y-%m-%d"),
            to_date=datetime.strptime(tv_end_date, "%Y-%m-%d"),
            interval="day"
        )
        print(f"   Fetched {len(tv_data)} bars for TV comparison")
        
        # Save TV comparison data in same format as TradingView CSV
        with open('zerodha_tv_comparison_data.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['time', 'open', 'high', 'low', 'close', 'volume'])
            
            for bar in tv_data:
                writer.writerow([
                    bar['date'].strftime('%Y-%m-%d'),
                    bar['open'],
                    bar['high'],
                    bar['low'],
                    bar['close'],
                    bar['volume']
                ])
        
        print("   Saved to: zerodha_tv_comparison_data.csv")
        
    except Exception as e:
        print(f"❌ Error fetching TV comparison data: {e}")
        tv_data = []
    
    # Create combined dataset
    if ml_data and tv_data:
        print("\n📊 Creating combined dataset...")
        all_data = ml_data + tv_data
        
        # Remove duplicates based on date
        seen_dates = set()
        unique_data = []
        for bar in all_data:
            date_str = bar['date'].strftime('%Y-%m-%d')
            if date_str not in seen_dates:
                seen_dates.add(date_str)
                unique_data.append(bar)
        
        # Sort by date
        unique_data.sort(key=lambda x: x['date'])
        
        # Save combined data
        with open('zerodha_combined_data.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['time', 'open', 'high', 'low', 'close', 'volume'])
            
            for bar in unique_data:
                writer.writerow([
                    bar['date'].strftime('%Y-%m-%d'),
                    bar['open'],
                    bar['high'],
                    bar['low'],
                    bar['close'],
                    bar['volume']
                ])
        
        print(f"   Total unique bars: {len(unique_data)}")
        print("   Saved to: zerodha_combined_data.csv")
        
        # Data quality check
        print("\n🔍 Data Quality Check:")
        
        # Check if dates match with TradingView
        tv_csv_dates = []
        with open('NSE_ICICIBANK, 1D.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tv_csv_dates.append(row['time'])
        
        zerodha_tv_dates = [bar['date'].strftime('%Y-%m-%d') for bar in tv_data]
        
        # Find missing dates
        tv_set = set(tv_csv_dates)
        zerodha_set = set(zerodha_tv_dates)
        
        missing_in_zerodha = tv_set - zerodha_set
        missing_in_tv = zerodha_set - tv_set
        
        print(f"   Dates in TradingView CSV: {len(tv_csv_dates)}")
        print(f"   Dates in Zerodha TV range: {len(zerodha_tv_dates)}")
        print(f"   Missing in Zerodha: {len(missing_in_zerodha)}")
        print(f"   Missing in TradingView: {len(missing_in_tv)}")
        
        if missing_in_zerodha:
            print(f"   First 5 missing in Zerodha: {list(missing_in_zerodha)[:5]}")
        if missing_in_tv:
            print(f"   First 5 missing in TV: {list(missing_in_tv)[:5]}")
    
    print("\n✅ Data fetching complete!")
    print("\n📋 Next Steps:")
    print("1. Run component-wise comparison")
    print("2. Check indicator values")
    print("3. Validate ML predictions")
    print("4. Compare signal generation")


def main():
    """Main entry point"""
    fetch_zerodha_data()


if __name__ == "__main__":
    main()
