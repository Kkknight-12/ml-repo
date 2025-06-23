#!/usr/bin/env python3
"""
Example: Analyzing multiple stocks from cache
Shows how the cache handles multiple symbols efficiently
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
from data.zerodha_client import ZerodhaClient
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
import json

def analyze_multiple_stocks():
    """Demo analyzing multiple stocks from cache"""
    
    # Stocks to analyze
    stocks = ["RELIANCE", "TCS", "ICICIBANK", "INFY", "HDFCBANK"]
    
    print("=== Multi-Stock Analysis from Cache ===\n")
    
    # Check for auth
    if not os.path.exists('.kite_session.json'):
        print("❌ No access token found. Run auth_helper.py first")
        return
    
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        os.environ['KITE_ACCESS_TOKEN'] = session_data.get('access_token')
    
    # Initialize client with cache
    client = ZerodhaClient(use_cache=True, cache_dir="data_cache")
    
    # Check cache status
    print("Current cache status:")
    cache_info = client.get_cache_info()
    if not cache_info.empty:
        cached_symbols = cache_info['symbol'].unique()
        print(f"Cached symbols: {', '.join(cached_symbols)}\n")
    else:
        print("Cache is empty\n")
    
    # Configure trading strategy
    config = TradingConfig(
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        use_kernel_filter=True,
        use_kernel_smoothing=False
    )
    
    # Analyze each stock
    results = {}
    
    for symbol in stocks:
        print(f"\n{'='*50}")
        print(f"Analyzing {symbol}")
        print('='*50)
        
        # Fetch data (from cache if available)
        print(f"Fetching data...")
        start_time = datetime.now()
        data = client.get_historical_data(symbol, "day", days=500)
        fetch_time = (datetime.now() - start_time).total_seconds()
        
        if not data:
            print(f"❌ No data available for {symbol}")
            continue
        
        print(f"✅ Loaded {len(data)} bars in {fetch_time:.3f}s")
        
        # Check if it was from cache
        if fetch_time < 0.5:  # Very fast = likely from cache
            print("⚡ Data loaded from cache!")
        
        # Process with trading strategy
        processor = EnhancedBarProcessor(config, symbol=symbol, timeframe="day")
        
        # Track signals
        long_signals = 0
        short_signals = 0
        
        # Process last 200 bars
        for i, bar in enumerate(data[-200:]):
            result = processor.process_bar(
                bar['open'], bar['high'], bar['low'], 
                bar['close'], bar.get('volume', 0)
            )
            
            if result:
                if result.start_long_trade:
                    long_signals += 1
                if result.start_short_trade:
                    short_signals += 1
        
        # Calculate simple metrics
        df = pd.DataFrame(data)
        returns = df['close'].pct_change().dropna()
        
        results[symbol] = {
            'bars': len(data),
            'long_signals': long_signals,
            'short_signals': short_signals,
            'total_signals': long_signals + short_signals,
            'avg_return': returns.mean() * 100,
            'volatility': returns.std() * 100,
            'fetch_time': fetch_time
        }
        
        print(f"\nResults for {symbol}:")
        print(f"  Long signals: {long_signals}")
        print(f"  Short signals: {short_signals}")
        print(f"  Avg daily return: {results[symbol]['avg_return']:.2f}%")
        print(f"  Daily volatility: {results[symbol]['volatility']:.2f}%")
    
    # Summary comparison
    print(f"\n{'='*70}")
    print("SUMMARY COMPARISON")
    print('='*70)
    print(f"{'Symbol':<10} {'Bars':<6} {'Long':<6} {'Short':<6} {'Total':<6} {'Avg Ret':<10} {'Vol':<8} {'Load Time':<10}")
    print('-'*70)
    
    for symbol, res in results.items():
        print(f"{symbol:<10} {res['bars']:<6} {res['long_signals']:<6} "
              f"{res['short_signals']:<6} {res['total_signals']:<6} "
              f"{res['avg_return']:>7.2f}%   {res['volatility']:>6.2f}%  "
              f"{res['fetch_time']:>6.3f}s")
    
    # Cache statistics
    print(f"\n{'='*50}")
    print("CACHE STATISTICS")
    print('='*50)
    
    # Get updated cache info
    cache_info = client.get_cache_info()
    if not cache_info.empty:
        total_records = cache_info['total_records'].sum()
        total_symbols = len(cache_info['symbol'].unique())
        
        print(f"Total symbols cached: {total_symbols}")
        print(f"Total records: {total_records:,}")
        
        # Database size
        db_path = os.path.join("data_cache", "market_data.db")
        if os.path.exists(db_path):
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
            print(f"Database size: {size_mb:.2f} MB")
            print(f"Average per symbol: {size_mb/total_symbols:.2f} MB")
    
    print("\n✅ Multi-stock analysis complete!")
    print("\nKey observations:")
    print("- Cache supports unlimited stocks in single database")
    print("- Each stock's data is stored independently")
    print("- After first fetch, data loads in milliseconds")
    print("- Perfect for backtesting strategies across multiple stocks")

if __name__ == "__main__":
    analyze_multiple_stocks()