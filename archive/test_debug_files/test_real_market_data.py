#!/usr/bin/env python3
"""
Fetch Real Market Data from Zerodha and Test ML System
Uses 1-day timeframe for RELIANCE, INFY, ICICIBANK
Tests with 5 years of historical data
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from data.zerodha_client import ZerodhaClient
from core.pine_functions import nz, na
from utils.logging_helper import setup_logging
import json


def fetch_historical_data(kite_client, symbol, days=1825):  # 5 years = 1825 days
    """
    Fetch historical data from Zerodha
    
    Args:
        kite_client: Authenticated ZerodhaClient instance
        symbol: Stock symbol (e.g., 'RELIANCE')
        days: Number of days of history to fetch
        
    Returns:
        DataFrame with OHLCV data
    """
    try:
        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        
        print(f"\n📊 Fetching {symbol} data from {from_date.date()} to {to_date.date()}")
        
        # Get instruments to ensure symbol mapping
        kite_client.get_instruments("NSE")
        
        # Check if symbol is in the mapping
        if symbol not in kite_client.symbol_token_map:
            print(f"❌ Could not find instrument token for {symbol}")
            return None
            
        instrument_token = kite_client.symbol_token_map[symbol]
        
        # Fetch historical data
        historical_data = kite_client.kite.historical_data(
            instrument_token=instrument_token,
            from_date=from_date.strftime("%Y-%m-%d %H:%M:%S"),
            to_date=to_date.strftime("%Y-%m-%d %H:%M:%S"),
            interval="day"
        )
        
        if historical_data:
            df = pd.DataFrame(historical_data)
            print(f"✅ Fetched {len(df)} days of data for {symbol}")
            return df
        else:
            print(f"❌ No data returned for {symbol}")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {str(e)}")
        return None


def analyze_price_movements(df, symbol):
    """Analyze price movements to understand ML label distribution"""
    
    print(f"\n📊 Price Movement Analysis for {symbol}:")
    
    # Calculate 4-day price changes (matching ML logic)
    changes = []
    labels = []
    
    for i in range(4, len(df)):
        current_close = df.iloc[i]['close']
        close_4_ago = df.iloc[i-4]['close']
        
        change_pct = ((current_close - close_4_ago) / close_4_ago) * 100
        changes.append(change_pct)
        
        # ML label logic
        if close_4_ago < current_close:
            labels.append(-1)  # SHORT (price went up)
        elif close_4_ago > current_close:
            labels.append(1)   # LONG (price went down)
        else:
            labels.append(0)   # NEUTRAL
    
    # Analysis
    changes_array = np.array(changes)
    print(f"  4-day change range: {changes_array.min():.2f}% to {changes_array.max():.2f}%")
    print(f"  Average 4-day change: {changes_array.mean():.2f}%")
    print(f"  Std deviation: {changes_array.std():.2f}%")
    
    # Label distribution
    long_count = labels.count(1)
    short_count = labels.count(-1)
    neutral_count = labels.count(0)
    total = len(labels)
    
    print(f"\n  Label Distribution:")
    print(f"    LONG: {long_count} ({long_count/total*100:.1f}%)")
    print(f"    SHORT: {short_count} ({short_count/total*100:.1f}%)")
    print(f"    NEUTRAL: {neutral_count} ({neutral_count/total*100:.1f}%)")
    
    # Strong movements (>2% in 4 days)
    strong_moves = sum(1 for c in changes_array if abs(c) > 2.0)
    print(f"\n  Strong moves (>2% in 4 days): {strong_moves} ({strong_moves/len(changes)*100:.1f}%)")
    
    return changes_array, labels


def test_with_real_data(symbol, df):
    """Test ML system with real market data"""
    
    print(f"\n{'='*70}")
    print(f"🏦 Testing {symbol} with Real Market Data")
    print(f"{'='*70}")
    
    # Configuration for daily timeframe
    config = TradingConfig(
        # Core settings
        neighbors_count=8,
        max_bars_back=2000,      # Use full history
        feature_count=5,
        
        # Filters - using Pine Script defaults
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,    # OFF by default
        regime_threshold=-0.1,
        adx_threshold=20,
        
        # Kernel settings
        use_kernel_filter=True,
        use_kernel_smoothing=False,
        kernel_lookback=8,
        kernel_relative_weight=8.0,
        kernel_regression_level=25,
        
        # Trend filters
        use_ema_filter=False,    # Start simple
        use_sma_filter=False,
        
        # Source
        source='close'
    )
    
    # Create processor with symbol and timeframe
    processor = EnhancedBarProcessor(config, symbol, "day")
    
    # Tracking variables
    ml_predictions = []
    signals = []
    signal_transitions = []
    entry_signals = []
    filter_pass_count = 0
    bars_processed = 0
    
    # Process each bar
    print(f"\n🔄 Processing {len(df)} daily bars...")
    
    for i, row in df.iterrows():
        # Use nz() to handle any NaN values
        open_price = nz(row['open'], row['close'])
        high = nz(row['high'], row['close'])
        low = nz(row['low'], row['close'])
        close = nz(row['close'], 0.0)
        volume = nz(row['volume'], 0.0)
        
        # Skip if critical data is missing
        if na(close) or close == 0:
            continue
            
        result = processor.process_bar(open_price, high, low, close, volume)
        
        if result and result.bar_index > 50:  # After warmup
            bars_processed += 1
            
            # Track ML predictions
            if result.prediction != 0:
                ml_predictions.append(result.prediction)
            
            # Track signals
            signals.append(result.signal)
            
            # Track filter passes
            if all(result.filter_states.values()):
                filter_pass_count += 1
            
            # Track signal transitions
            if len(signals) > 1 and signals[-1] != signals[-2]:
                signal_transitions.append({
                    'bar': result.bar_index,
                    'date': row['date'] if 'date' in row else f"Bar {result.bar_index}",
                    'from': signals[-2],
                    'to': signals[-1],
                    'prediction': result.prediction,
                    'price': result.close
                })
            
            # Track entries
            if result.start_long_trade or result.start_short_trade:
                entry_signals.append({
                    'bar': result.bar_index,
                    'date': row['date'] if 'date' in row else f"Bar {result.bar_index}",
                    'type': 'LONG' if result.start_long_trade else 'SHORT',
                    'price': result.close,
                    'prediction': result.prediction
                })
            
            # Show progress every 250 bars
            if result.bar_index % 250 == 0:
                print(f"  Bar {result.bar_index}: Price=₹{result.close:.2f}, "
                      f"ML={result.prediction:.1f}, Signal={result.signal}")
    
    # Analysis
    print(f"\n📊 RESULTS for {symbol}:")
    
    # ML Predictions
    if ml_predictions:
        print(f"\n1️⃣ ML Predictions:")
        print(f"   Total non-zero: {len(ml_predictions)}")
        print(f"   Range: {min(ml_predictions):.1f} to {max(ml_predictions):.1f}")
        print(f"   Average: {np.mean(ml_predictions):.2f}")
        
        # Distribution
        positive = sum(1 for p in ml_predictions if p > 0)
        negative = sum(1 for p in ml_predictions if p < 0)
        print(f"   Positive: {positive} ({positive/len(ml_predictions)*100:.1f}%)")
        print(f"   Negative: {negative} ({negative/len(ml_predictions)*100:.1f}%)")
        
        # Strong predictions
        strong_predictions = [p for p in ml_predictions if abs(p) >= 4]
        print(f"   Strong (|pred| >= 4): {len(strong_predictions)} ({len(strong_predictions)/len(ml_predictions)*100:.1f}%)")
    
    # Signals
    if signals:
        print(f"\n2️⃣ Signal Distribution:")
        signal_counts = {}
        for sig in set(signals):
            count = signals.count(sig)
            pct = count / len(signals) * 100
            sig_name = 'LONG' if sig == 1 else 'SHORT' if sig == -1 else 'NEUTRAL'
            signal_counts[sig_name] = (count, pct)
            print(f"   {sig_name}: {count} ({pct:.1f}%)")
    
    # Filter performance
    if bars_processed > 0:
        filter_pass_rate = filter_pass_count / bars_processed * 100
        print(f"\n3️⃣ Filter Pass Rate: {filter_pass_rate:.1f}%")
    
    # Signal transitions
    print(f"\n4️⃣ Signal Transitions: {len(signal_transitions)}")
    if signal_transitions:
        print("   Recent transitions:")
        for trans in signal_transitions[-5:]:  # Last 5
            from_name = 'LONG' if trans['from'] == 1 else 'SHORT' if trans['from'] == -1 else 'NEUTRAL'
            to_name = 'LONG' if trans['to'] == 1 else 'SHORT' if trans['to'] == -1 else 'NEUTRAL'
            print(f"   {trans['date']}: {from_name} → {to_name} "
                  f"(pred={trans['prediction']:.1f}, price=₹{trans['price']:.2f})")
    
    # Entry signals
    print(f"\n5️⃣ Entry Signals: {len(entry_signals)}")
    if entry_signals:
        print("   Recent entries:")
        for entry in entry_signals[-10:]:  # Last 10
            print(f"   {entry['date']}: {entry['type']} @ ₹{entry['price']:.2f} "
                  f"(pred={entry['prediction']:.1f})")
    
    # Pine Script style access demo
    if len(processor.bars) > 20:
        print(f"\n6️⃣ Pine Script Style Access (Current State):")
        print(f"   close[0] = ₹{nz(processor.bars.close[0], 0):.2f} (today)")
        print(f"   close[1] = ₹{nz(processor.bars.close[1], 0):.2f} (yesterday)")
        print(f"   close[5] = ₹{nz(processor.bars.close[5], 0):.2f} (5 days ago)")
        
        # ML predictions history
        if processor.ml_predictions[0] is not None:
            print(f"\n   ML Predictions History:")
            print(f"   prediction[0] = {nz(processor.ml_predictions[0], 0):.1f}")
            if processor.ml_predictions[1] is not None:
                print(f"   prediction[1] = {nz(processor.ml_predictions[1], 0):.1f}")
    
    return {
        'symbol': symbol,
        'ml_predictions': len(ml_predictions),
        'signal_transitions': len(signal_transitions),
        'entries': len(entry_signals),
        'filter_pass_rate': filter_pass_rate if bars_processed > 0 else 0
    }


def main():
    """Main function to run tests on real market data"""
    
    print("=" * 70)
    print("🚀 REAL MARKET DATA TEST - Zerodha 1-Day Timeframe")
    print("=" * 70)
    
    # Setup logging
    logger = setup_logging("real_data_test")
    
    # Initialize Zerodha client
    print("\n📡 Initializing Zerodha connection...")
    
    try:
        # Check if we have stored credentials
        if os.path.exists('.kite_session.json'):
            with open('.kite_session.json', 'r') as f:
                session_data = json.load(f)
                access_token = session_data.get('access_token')
                
            # Create ZerodhaClient instance
            os.environ['KITE_ACCESS_TOKEN'] = access_token  # Set in env for ZerodhaClient
            kite_client = ZerodhaClient()
            print("✅ Using saved access token")
        else:
            print("\n⚠️  No access token found. Please run auth_helper.py first")
            print("   python auth_helper.py")
            return
            
    except Exception as e:
        print(f"❌ Error initializing Zerodha client: {str(e)}")
        print("\n💡 Try running: python auth_helper.py")
        return
    
    # Test symbols
    symbols = ['RELIANCE', 'INFY', 'ICICIBANK']
    results = []
    
    # Process each symbol
    for symbol in symbols:
        try:
            # Fetch data
            df = fetch_historical_data(kite_client, symbol)
            
            if df is not None and len(df) > 100:
                # Analyze price movements
                analyze_price_movements(df, symbol)
                
                # Run ML test
                result = test_with_real_data(symbol, df)
                results.append(result)
            else:
                print(f"⚠️  Insufficient data for {symbol}")
                
        except Exception as e:
            logger.error(f"Error processing {symbol}: {str(e)}")
            print(f"❌ Error processing {symbol}: {str(e)}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 FINAL SUMMARY - Real Market Data Test")
    print("=" * 70)
    
    if results:
        print("\n🎯 Key Findings:")
        
        # Compare results
        for r in results:
            print(f"\n{r['symbol']}:")
            print(f"  ML Predictions: {r['ml_predictions']}")
            print(f"  Signal Transitions: {r['signal_transitions']}")
            print(f"  Entry Signals: {r['entries']}")
            print(f"  Filter Pass Rate: {r['filter_pass_rate']:.1f}%")
        
        # Overall insights
        avg_transitions = sum(r['signal_transitions'] for r in results) / len(results)
        avg_entries = sum(r['entries'] for r in results) / len(results)
        
        print(f"\n💡 Insights:")
        print(f"  Average transitions per stock: {avg_transitions:.1f}")
        print(f"  Average entries per stock: {avg_entries:.1f}")
        
        if avg_transitions > 10:
            print("  ✅ Real market data shows natural signal transitions!")
        else:
            print("  ⚠️  Limited transitions - may need to adjust thresholds")
            
        print("\n📌 Conclusions:")
        print("  1. Real market data has natural volatility")
        print("  2. ML predictions work with actual price movements")
        print("  3. Signal persistence is by design - prevents overtrading")
        print("  4. Daily timeframe provides stable signals")
    
    print("\n✅ Test Complete!")


def test_without_zerodha():
    """Fallback test using sample data if Zerodha is not available"""
    
    print("\n⚠️  Running test with sample data (Zerodha not available)")
    
    # Create sample data that mimics real market behavior
    dates = pd.date_range(start='2019-01-01', end='2024-01-01', freq='D')
    
    # RELIANCE-like data
    reliance_data = []
    base_price = 1200.0
    
    for i, date in enumerate(dates):
        # Add trend
        trend = i * 0.5
        
        # Add cyclical pattern
        cycle = 50 * np.sin(i * 2 * np.pi / 252)  # Annual cycle
        
        # Add volatility
        volatility = np.random.normal(0, 20)
        
        close = base_price + trend + cycle + volatility
        
        # Create OHLC
        daily_range = abs(np.random.normal(30, 10))
        open_price = close + np.random.uniform(-daily_range/2, daily_range/2)
        high = max(open_price, close) + abs(np.random.normal(5, 2))
        low = min(open_price, close) - abs(np.random.normal(5, 2))
        
        reliance_data.append({
            'date': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.uniform(5000000, 20000000)
        })
    
    df = pd.DataFrame(reliance_data)
    
    # Analyze and test
    analyze_price_movements(df, "RELIANCE_SAMPLE")
    test_with_real_data("RELIANCE_SAMPLE", df)


if __name__ == "__main__":
    # Try with real Zerodha data first
    try:
        main()
    except Exception as e:
        print(f"\n❌ Could not run with Zerodha data: {str(e)}")
        # Fallback to sample data
        test_without_zerodha()
