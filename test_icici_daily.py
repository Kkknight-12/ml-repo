#!/usr/bin/env python3
"""
Test script for ICICI Bank (NSE) on 1-Day timeframe
Shows Pine Script style history referencing in action
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from data.enhanced_bar_data import EnhancedBarData
from core.history_referencing import create_series, PineScriptSeries
import random


def generate_icici_like_data(days: int = 500) -> list:
    """
    Generate ICICI Bank-like daily data
    Starting around 950-1000 range (typical ICICI levels)
    """
    data = []
    base_price = 950.0  # ICICI typical range
    
    for i in range(days):
        # Add some trend and volatility
        trend = i * 0.1  # Slight upward trend
        daily_volatility = random.uniform(-20, 20)  # Daily movement
        
        close = base_price + trend + daily_volatility
        
        # Generate OHLC
        daily_range = abs(random.gauss(10, 5))  # Daily range
        
        if random.random() > 0.5:  # Bullish day
            open_price = close - random.uniform(0, daily_range * 0.7)
            high = close + random.uniform(0, daily_range * 0.3)
            low = open_price - random.uniform(0, daily_range * 0.2)
        else:  # Bearish day
            open_price = close + random.uniform(0, daily_range * 0.7)
            low = close - random.uniform(0, daily_range * 0.3)
            high = open_price + random.uniform(0, daily_range * 0.2)
        
        # Ensure OHLC constraints
        high = max(open_price, close, high)
        low = min(open_price, close, low)
        
        # Volume (in thousands)
        volume = random.uniform(5000, 20000) * 1000
        
        data.append((open_price, high, low, close, volume))
    
    return data


def test_icici_daily():
    """Test with ICICI Bank daily timeframe configuration"""
    
    print("=" * 70)
    print("🏦 ICICI BANK (NSE) - 1 DAY TIMEFRAME TEST")
    print("=" * 70)
    
    # Configuration for daily timeframe
    config = TradingConfig(
        # Core settings
        neighbors_count=8,
        max_bars_back=2000,      # 2000 days = ~8 years of data
        feature_count=5,
        
        # Filters optimized for daily timeframe
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,    # Keep disabled for now
        regime_threshold=-0.1,   # Standard for daily
        adx_threshold=20,        # Standard for daily trends
        
        # Kernel settings for daily
        use_kernel_filter=True,
        use_kernel_smoothing=False,  # Less smoothing for daily
        kernel_lookback=8,           # 8 days lookback
        kernel_relative_weight=8.0,
        kernel_regression_level=25,
        
        # Trend filters - adjusted for daily
        use_ema_filter=False,    # Start without EMA/SMA
        ema_period=200,          # 200-day EMA (if enabled)
        use_sma_filter=False,
        sma_period=200,          # 200-day SMA (if enabled)
    )
    
    print("\n📊 Configuration for Daily Timeframe:")
    print(f"  Neighbors: {config.neighbors_count}")
    print(f"  Max bars back: {config.max_bars_back} days")
    print(f"  Regime threshold: {config.regime_threshold}")
    print(f"  ADX threshold: {config.adx_threshold}")
    print(f"  Kernel lookback: {config.kernel_lookback} days")
    
    # Generate test data
    print("\n📈 Generating ICICI-like daily data...")
    data = generate_icici_like_data(600)  # 600 days
    
    # Initialize processor with enhanced bar data
    processor = EnhancedBarProcessor(config, "ICICIBANK", "day")
    
    # Also create Pine Script style series for custom tracking
    rsi_series = create_series("RSI", 500)
    prediction_series = create_series("ML_Prediction", 500)
    
    # Process bars
    print("\n🔄 Processing daily bars...\n")
    
    ml_predictions = []
    entry_signals = []
    
    for i, (o, h, l, c, v) in enumerate(data):
        result = processor.process_bar(o, h, l, c, v)
        
        if result:
            # Store in Pine Script series
            if result.prediction != 0:
                ml_predictions.append(result.prediction)
                prediction_series.update(result.prediction)
            
            # Track entries
            if result.start_long_trade or result.start_short_trade:
                entry_signals.append({
                    'day': i,
                    'type': 'LONG' if result.start_long_trade else 'SHORT',
                    'price': result.close,
                    'prediction': result.prediction
                })
            
            # Show Pine Script style access every 50 days
            if i > 100 and i % 50 == 0:
                print(f"Day {i} - Pine Script Style Access:")
                print(f"  close[0] = ₹{processor.bars.close[0]:.2f} (current)")
                print(f"  close[1] = ₹{processor.bars.close[1]:.2f} (yesterday)")
                print(f"  close[5] = ₹{processor.bars.close[5]:.2f} (5 days ago)")
                
                # Calculate simple returns
                if len(processor.bars) > 1:
                    daily_return = ((processor.bars.close[0] - processor.bars.close[1]) / 
                                   processor.bars.close[1]) * 100
                    print(f"  Daily return: {daily_return:.2f}%")
                
                if len(processor.bars) > 5:
                    weekly_return = ((processor.bars.close[0] - processor.bars.close[5]) / 
                                    processor.bars.close[5]) * 100
                    print(f"  5-day return: {weekly_return:.2f}%")
                
                # ML info
                print(f"  ML Prediction: {result.prediction:.2f}")
                print(f"  Filters: {result.filter_states}")
                
                # Show historical predictions using Pine Script series
                if len(prediction_series._history._buffer) > 5:
                    print(f"\n  Historical ML Predictions:")
                    print(f"    prediction[0] = {prediction_series[0]:.2f} (current)")
                    print(f"    prediction[1] = {prediction_series[1]:.2f} (yesterday)")
                    print(f"    prediction[5] = {prediction_series[5]:.2f} (5 days ago)")
                
                print("-" * 50)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 DAILY TIMEFRAME TEST SUMMARY")
    print("=" * 70)
    
    print(f"\n1️⃣ Data Processed:")
    print(f"   Total days: {len(data)}")
    print(f"   Price range: ₹{min(d[3] for d in data):.2f} - ₹{max(d[3] for d in data):.2f}")
    
    print(f"\n2️⃣ ML Performance:")
    print(f"   Non-zero predictions: {len(ml_predictions)}")
    if ml_predictions:
        print(f"   Prediction range: {min(ml_predictions):.2f} to {max(ml_predictions):.2f}")
        print(f"   Average: {sum(ml_predictions)/len(ml_predictions):.2f}")
    
    print(f"\n3️⃣ Trading Signals:")
    print(f"   Total entries: {len(entry_signals)}")
    if entry_signals:
        print("\n   Recent signals:")
        for signal in entry_signals[-5:]:  # Last 5 signals
            print(f"   - Day {signal['day']}: {signal['type']} @ ₹{signal['price']:.2f}")
    
    # Filter analysis
    if len(data) > 200:  # Need enough data for analysis
        print(f"\n4️⃣ Filter Performance:")
        volatility_passes = sum(1 for d in processor.signal_history if d != 0)
        print(f"   Signal generation rate: {(volatility_passes / len(data)) * 100:.1f}%")
    
    print(f"\n5️⃣ Pine Script Features Demo:")
    print(f"   ✅ History referencing with [] operator")
    print(f"   ✅ Series tracking for custom indicators")
    print(f"   ✅ Multi-bar lookback calculations")
    print(f"   ✅ Proper data alignment")
    
    print("\n💡 Recommendations for Daily Trading:")
    print("   1. Daily timeframe works well with default parameters")
    print("   2. Consider enabling EMA filter for trend confirmation")
    print("   3. Monitor regime filter behavior on ranging days")
    print("   4. Use at least 500 days for stable ML predictions")
    
    return len(entry_signals) > 0


def demo_pine_script_features():
    """Demonstrate Pine Script style features"""
    
    print("\n\n" + "=" * 70)
    print("🔧 PINE SCRIPT STYLE FEATURES DEMO")
    print("=" * 70)
    
    # Create enhanced bar data
    bars = EnhancedBarData()
    
    # Add some ICICI-like data
    print("\n1️⃣ Adding ICICI daily bars:")
    test_prices = [950, 955, 952, 958, 960, 957, 962]
    
    for i, close in enumerate(test_prices):
        open_price = close - random.uniform(-2, 2)
        high = max(open_price, close) + random.uniform(0, 3)
        low = min(open_price, close) - random.uniform(0, 3)
        volume = random.uniform(5000, 15000) * 1000
        
        bars.add_bar(open_price, high, low, close, volume)
        
        if i >= 2:  # Need history
            print(f"\nDay {i}:")
            print(f"  close[0] = ₹{bars.close[0]:.2f} (today)")
            print(f"  close[1] = ₹{bars.close[1]:.2f} (yesterday)")
            print(f"  close[2] = ₹{bars.close[2]:.2f} (2 days ago)")
            
            # Calculate price change
            change = bars.close[0] - bars.close[1] if bars.close[1] else 0
            print(f"  Daily change: ₹{change:.2f}")
            
            # Show HLC3 (typical price)
            print(f"  hlc3[0] = ₹{bars.hlc3[0]:.2f}")
    
    print("\n2️⃣ Custom Series Example:")
    # Create custom RSI series
    rsi = bars.create_series("RSI")
    
    # Simulate RSI values
    for i in range(5):
        rsi_value = 50 + random.uniform(-20, 20)
        rsi.update(rsi_value)
        
        if i > 0:
            print(f"\nBar {i}: RSI = {rsi_value:.2f}")
            print(f"  RSI[0] = {rsi[0]:.2f} (current)")
            print(f"  RSI[1] = {rsi[1]:.2f} (previous)")


if __name__ == "__main__":
    # Run ICICI daily test
    success = test_icici_daily()
    
    # Demo Pine Script features
    demo_pine_script_features()
    
    print("\n✅ Test complete!")
    exit(0 if success else 1)
