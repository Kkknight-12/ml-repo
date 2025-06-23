#!/usr/bin/env python3
"""
Test with DAILY data for easier comparison
Daily data has fewer bars and is more consistent across platforms
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.zerodha_client import ZerodhaClient
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from datetime import datetime, timedelta
import pandas as pd

print("=== DAILY DATA VALIDATION ===\n")

# Initialize
client = ZerodhaClient()
if not client.access_token:
    print("❌ Not logged in! Run: python auth_helper.py")
    exit(1)

# Test parameters for DAILY
SYMBOL = "ICICIBANK"
INTERVAL = "day"  # Daily timeframe
DAYS = 100  # Last 100 days

print(f"Testing {SYMBOL} with DAILY data")
print(f"Period: Last {DAYS} days\n")

# Configuration - same as 5-minute
config = TradingConfig(
    neighbors_count=8,
    max_bars_back=2000,
    feature_count=5,
    use_volatility_filter=True,
    use_regime_filter=True,
    use_adx_filter=False,
    regime_threshold=-0.1,
    adx_threshold=20,
    use_kernel_filter=True,
    kernel_lookback=8,
    kernel_relative_weight=8.0,
    kernel_regression_level=25,
    use_kernel_smoothing=False,
    use_ema_filter=False,
    use_sma_filter=False,
)

try:
    # Get DAILY data
    historical_data = client.get_historical_data(SYMBOL, INTERVAL, days=DAYS)
    
    if not historical_data:
        print("No data received!")
        exit(1)
        
    print(f"✓ Fetched {len(historical_data)} daily bars\n")
    
    # Show sample data
    print("=== SAMPLE DAILY DATA (First 5 and Last 5 bars) ===")
    df = pd.DataFrame(historical_data)
    
    # First 5 bars
    print("\nFirst 5 bars:")
    for i in range(min(5, len(df))):
        row = df.iloc[i]
        print(f"Bar {i+1}: {row['date'].strftime('%Y-%m-%d')} - "
              f"O:{row['open']:.2f} H:{row['high']:.2f} "
              f"L:{row['low']:.2f} C:{row['close']:.2f}")
    
    # Last 5 bars
    print("\nLast 5 bars:")
    for i in range(max(0, len(df)-5), len(df)):
        row = df.iloc[i]
        print(f"Bar {i+1}: {row['date'].strftime('%Y-%m-%d')} - "
              f"O:{row['open']:.2f} H:{row['high']:.2f} "
              f"L:{row['low']:.2f} C:{row['close']:.2f}")
    
    # Process through scanner
    # Initialize processor with total bars count (Pine Script compatibility)
    processor = BarProcessor(config, total_bars=len(df))
    signals = []
    
    print(f"\n\nProcessing {len(df)} daily bars...")
    print(f"Max bars back index: {processor.max_bars_back_index}")
    print(f"ML will start at bar: {processor.max_bars_back_index + 1}\n")
    
    for idx, row in df.iterrows():
        result = processor.process_bar(
            float(row['open']),
            float(row['high']),
            float(row['low']),
            float(row['close']),
            float(row['volume'])
        )
        
        # Track signals
        if result.start_long_trade:
            signals.append({
                'bar': idx + 1,
                'type': 'BUY',
                'date': row['date'].strftime('%Y-%m-%d'),
                'price': row['close'],
                'prediction': result.prediction
            })
        elif result.start_short_trade:
            signals.append({
                'bar': idx + 1,
                'type': 'SELL',
                'date': row['date'].strftime('%Y-%m-%d'),
                'price': row['close'],
                'prediction': result.prediction
            })
    
    print(f"\n✓ Processing complete. Found {len(signals)} signals\n")
    
    # Display signals
    if signals:
        print("=== SIGNALS FOUND ===")
        for sig in signals:
            print(f"Bar {sig['bar']:3}: {sig['type']} @ ₹{sig['price']:.2f} "
                  f"on {sig['date']} (Pred={sig['prediction']:2.0f})")
    else:
        print("No signals generated!")
    
    # Summary statistics
    print(f"\n=== DAILY DATA SUMMARY ===")
    print(f"Total bars: {len(df)}")
    print(f"Total signals: {len(signals)}")
    print(f"Signal rate: {len(signals)/len(df)*100:.1f}%")
    print(f"Date range: {df['date'].min().strftime('%Y-%m-%d')} to "
          f"{df['date'].max().strftime('%Y-%m-%d')}")
    
    # Save for Pine Script comparison
    print("\n=== NEXT STEPS ===")
    print("1. Run same date range in Pine Script with DAILY timeframe")
    print("2. Export Pine Script signals")
    print("3. Compare signal dates and prices")
    print("\nDaily data should have:")
    print("- Exact same OHLC values across platforms")
    print("- No missing bars")
    print("- Clear signal dates for comparison")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== DONE ===")
