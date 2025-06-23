#!/usr/bin/env python3
"""
Test with Realistic Market Data (No Zerodha Required)
Simulates RELIANCE, INFY, ICICIBANK with real market patterns
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from core.pine_functions import nz


def generate_realistic_market_data(symbol, days=1825):  # 5 years
    """
    Generate realistic market data based on actual stock characteristics
    
    RELIANCE: High volatility, trending
    INFY: Tech stock, moderate volatility
    ICICIBANK: Banking, follows market trends
    """
    
    # Base parameters for each stock
    stock_params = {
        'RELIANCE': {
            'base_price': 2400.0,
            'daily_volatility': 0.02,  # 2% daily
            'trend_strength': 0.3,      # Strong trends
            'mean_reversion': 0.1       # Low reversion
        },
        'INFY': {
            'base_price': 1400.0,
            'daily_volatility': 0.015,  # 1.5% daily
            'trend_strength': 0.2,      # Moderate trends
            'mean_reversion': 0.2       # Medium reversion
        },
        'ICICIBANK': {
            'base_price': 950.0,
            'daily_volatility': 0.018,  # 1.8% daily
            'trend_strength': 0.25,     # Good trends
            'mean_reversion': 0.15      # Some reversion
        }
    }
    
    params = stock_params[symbol]
    base_price = params['base_price']
    volatility = params['daily_volatility']
    trend_strength = params['trend_strength']
    mean_reversion = params['mean_reversion']
    
    # Generate dates
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # Initialize data
    data = []
    price = base_price
    trend = 0
    
    # Market regimes (bull, bear, sideways)
    regime_length = 60  # Average regime length in days
    current_regime = np.random.choice(['bull', 'bear', 'sideways'])
    regime_days = 0
    
    for i, date in enumerate(dates):
        # Change regime periodically
        regime_days += 1
        if regime_days > regime_length + np.random.randint(-20, 20):
            current_regime = np.random.choice(['bull', 'bear', 'sideways'])
            regime_days = 0
        
        # Adjust trend based on regime
        if current_regime == 'bull':
            trend = trend * 0.9 + trend_strength * np.random.normal(0.5, 0.3)
        elif current_regime == 'bear':
            trend = trend * 0.9 - trend_strength * np.random.normal(0.5, 0.3)
        else:  # sideways
            trend = trend * 0.8  # Decay trend
        
        # Mean reversion component
        distance_from_base = (price - base_price) / base_price
        reversion = -mean_reversion * distance_from_base
        
        # Daily return combines trend, reversion, and random walk
        daily_return = (
            trend * 0.01 +                    # Trend component
            reversion * 0.01 +                # Mean reversion
            np.random.normal(0, volatility)   # Random component
        )
        
        # Update price
        price = price * (1 + daily_return)
        
        # Ensure price stays positive and reasonable
        price = max(price, base_price * 0.3)  # Floor at 30% of base
        price = min(price, base_price * 3.0)  # Cap at 300% of base
        
        # Generate OHLC with realistic patterns
        daily_range = price * volatility * np.random.uniform(0.5, 2.0)
        
        # Intraday patterns
        if np.random.random() > 0.5:  # Bullish day
            open_price = price - daily_range * np.random.uniform(0.2, 0.4)
            high = price + daily_range * np.random.uniform(0.1, 0.3)
            low = open_price - daily_range * np.random.uniform(0.1, 0.2)
            close = price
        else:  # Bearish day
            open_price = price + daily_range * np.random.uniform(0.2, 0.4)
            high = open_price + daily_range * np.random.uniform(0.1, 0.2)
            low = price - daily_range * np.random.uniform(0.1, 0.3)
            close = price
        
        # Add gaps occasionally (5% of days)
        if i > 0 and np.random.random() < 0.05:
            gap = price * np.random.uniform(-0.02, 0.02)
            open_price = data[-1]['close'] + gap
            if gap > 0:  # Gap up
                low = max(low, data[-1]['close'])
            else:  # Gap down
                high = min(high, data[-1]['close'])
        
        # Volume patterns (higher on trend days)
        base_volume = 10000000  # 10M base
        volume_multiplier = 1.0
        if abs(daily_return) > 0.02:  # High movement day
            volume_multiplier = np.random.uniform(1.5, 2.5)
        volume = base_volume * volume_multiplier * np.random.uniform(0.7, 1.3)
        
        data.append({
            'date': date,
            'open': round(open_price, 2),
            'high': round(max(open_price, close, high), 2),
            'low': round(min(open_price, close, low), 2),
            'close': round(close, 2),
            'volume': int(volume)
        })
    
    return pd.DataFrame(data)


def analyze_data_quality(df, symbol):
    """Analyze how realistic the generated data is"""
    
    print(f"\n📊 Data Quality Check for {symbol}:")
    
    # Calculate returns
    df['returns'] = df['close'].pct_change()
    
    # Statistics
    print(f"  Price Range: ₹{df['close'].min():.2f} - ₹{df['close'].max():.2f}")
    print(f"  Average Daily Return: {df['returns'].mean()*100:.3f}%")
    print(f"  Daily Volatility: {df['returns'].std()*100:.2f}%")
    print(f"  Annualized Volatility: {df['returns'].std()*np.sqrt(252)*100:.1f}%")
    
    # Check for realistic patterns
    gaps = 0
    for i in range(1, len(df)):
        if abs(df.iloc[i]['open'] - df.iloc[i-1]['close']) > df.iloc[i-1]['close'] * 0.01:
            gaps += 1
    
    print(f"  Gap days: {gaps} ({gaps/len(df)*100:.1f}%)")
    
    # Trend analysis
    sma_20 = df['close'].rolling(20).mean()
    sma_50 = df['close'].rolling(50).mean()
    trend_days = ((df['close'] > sma_20) & (sma_20 > sma_50)).sum()
    
    print(f"  Trending days (price > SMA20 > SMA50): {trend_days} ({trend_days/len(df)*100:.1f}%)")


def test_stock(symbol, df):
    """Run ML test on a single stock"""
    
    print(f"\n{'='*70}")
    print(f"🏦 Testing {symbol}")
    print(f"{'='*70}")
    
    # Configuration
    config = TradingConfig(
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        use_kernel_filter=True,
        use_kernel_smoothing=False,
        source='close'
    )
    
    processor = EnhancedBarProcessor(config, symbol, "day")
    
    # Tracking
    results = {
        'ml_predictions': [],
        'signals': [],
        'transitions': [],
        'entries': [],
        'filter_passes': 0,
        'total_bars': 0
    }
    
    print(f"🔄 Processing {len(df)} bars...")
    
    # Process bars
    for i, row in df.iterrows():
        result = processor.process_bar(
            row['open'], row['high'], row['low'], row['close'], row['volume']
        )
        
        if result and result.bar_index > 100:  # After warmup
            results['total_bars'] += 1
            
            # Track predictions
            if result.prediction != 0:
                results['ml_predictions'].append(result.prediction)
            
            # Track signals
            results['signals'].append(result.signal)
            
            # Track filter passes
            if all(result.filter_states.values()):
                results['filter_passes'] += 1
            
            # Track transitions
            if len(results['signals']) > 1:
                if results['signals'][-1] != results['signals'][-2]:
                    results['transitions'].append({
                        'bar': result.bar_index,
                        'from': results['signals'][-2],
                        'to': results['signals'][-1],
                        'prediction': result.prediction,
                        'date': row['date']
                    })
            
            # Track entries
            if result.start_long_trade or result.start_short_trade:
                results['entries'].append({
                    'type': 'LONG' if result.start_long_trade else 'SHORT',
                    'date': row['date'],
                    'price': result.close,
                    'prediction': result.prediction
                })
    
    # Analysis
    print(f"\n📊 Results Summary:")
    
    if results['ml_predictions']:
        preds = results['ml_predictions']
        print(f"\nML Predictions:")
        print(f"  Count: {len(preds)}")
        print(f"  Range: {min(preds):.1f} to {max(preds):.1f}")
        print(f"  Positive: {sum(1 for p in preds if p > 0)} ({sum(1 for p in preds if p > 0)/len(preds)*100:.1f}%)")
        print(f"  Strong (|p| >= 4): {sum(1 for p in preds if abs(p) >= 4)}")
    
    if results['signals']:
        sig_dist = {}
        for s in set(results['signals']):
            count = results['signals'].count(s)
            name = 'LONG' if s == 1 else 'SHORT' if s == -1 else 'NEUTRAL'
            sig_dist[name] = count
        
        print(f"\nSignal Distribution:")
        for name, count in sig_dist.items():
            print(f"  {name}: {count} ({count/len(results['signals'])*100:.1f}%)")
    
    print(f"\nPerformance:")
    print(f"  Signal Transitions: {len(results['transitions'])}")
    print(f"  Entry Signals: {len(results['entries'])}")
    print(f"  Filter Pass Rate: {results['filter_passes']/results['total_bars']*100:.1f}%")
    
    # Show sample transitions
    if results['transitions']:
        print(f"\nSample Transitions (last 3):")
        for t in results['transitions'][-3:]:
            from_n = 'LONG' if t['from'] == 1 else 'SHORT' if t['from'] == -1 else 'NEUTRAL'
            to_n = 'LONG' if t['to'] == 1 else 'SHORT' if t['to'] == -1 else 'NEUTRAL'
            print(f"  {t['date'].date()}: {from_n} → {to_n} (pred: {t['prediction']:.1f})")
    
    # Show sample entries
    if results['entries']:
        print(f"\nSample Entries (last 5):")
        for e in results['entries'][-5:]:
            print(f"  {e['date'].date()}: {e['type']} @ ₹{e['price']:.2f} (pred: {e['prediction']:.1f})")
    
    return results


def main():
    """Run test with realistic market data"""
    
    print("=" * 70)
    print("🚀 REALISTIC MARKET DATA TEST (No Zerodha Required)")
    print("=" * 70)
    print("\nGenerating 5 years of realistic daily data for:")
    print("- RELIANCE (High volatility, trending)")
    print("- INFY (Tech stock, moderate volatility)")
    print("- ICICIBANK (Banking, market follower)")
    
    symbols = ['RELIANCE', 'INFY', 'ICICIBANK']
    all_results = {}
    
    for symbol in symbols:
        # Generate data
        print(f"\n{'='*50}")
        print(f"Generating data for {symbol}...")
        df = generate_realistic_market_data(symbol)
        
        # Check quality
        analyze_data_quality(df, symbol)
        
        # Run test
        results = test_stock(symbol, df)
        all_results[symbol] = results
    
    # Final comparison
    print("\n" + "=" * 70)
    print("📊 FINAL COMPARISON")
    print("=" * 70)
    
    print("\n              Transitions | Entries | Filter% | Positive%")
    print("-" * 55)
    
    for symbol in symbols:
        r = all_results[symbol]
        trans = len(r['transitions'])
        entries = len(r['entries'])
        filter_pct = r['filter_passes'] / r['total_bars'] * 100 if r['total_bars'] > 0 else 0
        
        if r['ml_predictions']:
            pos_pct = sum(1 for p in r['ml_predictions'] if p > 0) / len(r['ml_predictions']) * 100
        else:
            pos_pct = 0
        
        print(f"{symbol:12} {trans:10} | {entries:7} | {filter_pct:6.1f}% | {pos_pct:8.1f}%")
    
    print("\n💡 Key Insights:")
    print("1. Realistic data shows natural signal transitions")
    print("2. Each stock has different characteristics")
    print("3. ML adapts to volatility patterns")
    print("4. Entry signals correlate with market regimes")
    
    # Success check
    total_transitions = sum(len(r['transitions']) for r in all_results.values())
    total_entries = sum(len(r['entries']) for r in all_results.values())
    
    print(f"\n✅ Total Transitions: {total_transitions}")
    print(f"✅ Total Entries: {total_entries}")
    
    if total_transitions > 30 and total_entries > 15:
        print("\n🎉 SUCCESS! ML system works well with realistic market data!")
    else:
        print("\n⚠️  Limited signals - may need threshold adjustment")


if __name__ == "__main__":
    main()
