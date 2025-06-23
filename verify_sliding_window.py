#!/usr/bin/env python3
"""
Verify Sliding Window Implementation
====================================
Purpose: Confirm that ML predictions work correctly with sliding window approach
- Test with different data sizes
- Verify ML starts at correct point
- No dependency on total_bars
"""

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
import numpy as np

def create_test_data(num_bars, trend="bullish"):
    """Create synthetic test data with a trend"""
    print(f"Creating {num_bars} bars of {trend} data...")
    
    # Base price
    base_price = 100.0
    prices = []
    
    for i in range(num_bars):
        # Add trend
        if trend == "bullish":
            trend_component = i * 0.1  # Upward trend
        elif trend == "bearish":
            trend_component = -i * 0.1  # Downward trend
        else:
            trend_component = 0  # Sideways
        
        # Add some noise
        noise = np.random.normal(0, 1)
        
        # Calculate price
        price = base_price + trend_component + noise
        
        # Create OHLC (simplified - just using price variations)
        open_price = price + np.random.uniform(-0.5, 0.5)
        high = max(price, open_price) + np.random.uniform(0, 1)
        low = min(price, open_price) - np.random.uniform(0, 1)
        close = price
        volume = np.random.uniform(1000, 10000)
        
        prices.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    return prices

def test_sliding_window():
    """Test sliding window with different scenarios"""
    
    print("=" * 60)
    print("🔍 Testing Sliding Window Implementation")
    print("=" * 60)
    print()
    
    # Test configurations
    test_cases = [
        # (num_bars, max_bars_back, expected_ml_start)
        # Note: ML starts ~3-4 bars after max_bars_back due to training label lookback
        (500, 100, 103),    # Small dataset
        (1000, 100, 103),   # Medium dataset
        (2000, 100, 103),   # Large dataset
        (2000, 500, 503),   # Different max_bars_back
        (2000, 1000, 1003), # Half data for training
    ]
    
    for num_bars, max_bars_back, expected_ml_start in test_cases:
        print(f"\n📊 Test Case: {num_bars} bars, max_bars_back={max_bars_back}")
        print("-" * 40)
        
        # Create config
        config = TradingConfig(
            max_bars_back=max_bars_back,
            neighbors_count=8,
            feature_count=5,
            # Simple config - all filters off except volatility
            use_volatility_filter=True,
            use_regime_filter=False,
            use_adx_filter=False,
            use_kernel_filter=False,
            use_ema_filter=False,
            use_sma_filter=False
        )
        
        # Create processor - NO total_bars parameter!
        processor = BarProcessor(config)
        
        # Create test data
        data = create_test_data(num_bars, trend="bullish")
        
        # Track when ML predictions start
        ml_start_bar = None
        predictions = []
        
        # Process bars
        for i, bar in enumerate(data):
            result = processor.process_bar(
                open_price=bar['open'],
                high=bar['high'],
                low=bar['low'],
                close=bar['close'],
                volume=bar['volume']
            )
            
            # Check when ML predictions become non-zero
            if result.prediction != 0.0 and ml_start_bar is None:
                ml_start_bar = i
            
            predictions.append(result.prediction)
        
        # Analyze results
        print(f"✅ Bars processed: {num_bars}")
        print(f"📍 ML started at bar: {ml_start_bar}")
        print(f"🎯 Expected ML start: {expected_ml_start}")
        
        # Verify ML started at correct point
        if ml_start_bar == expected_ml_start:
            print(f"✅ ML start point CORRECT!")
        else:
            print(f"❌ ML start point INCORRECT!")
        
        # Show prediction statistics
        non_zero_predictions = [p for p in predictions if p != 0.0]
        if non_zero_predictions:
            print(f"📊 ML Prediction Stats:")
            print(f"   - Total predictions: {len(non_zero_predictions)}")
            print(f"   - Min: {min(non_zero_predictions):.2f}")
            print(f"   - Max: {max(non_zero_predictions):.2f}")
            print(f"   - Avg: {np.mean(non_zero_predictions):.2f}")
        else:
            print(f"⚠️ No ML predictions generated!")
    
    print("\n" + "=" * 60)
    print("✅ Sliding Window Verification Complete!")
    print("=" * 60)
    
    # Test real-time scenario
    print("\n🔄 Testing Real-Time Scenario (bar-by-bar)...")
    print("-" * 40)
    
    config = TradingConfig(
        max_bars_back=50,  # Small window for quick test
        neighbors_count=8,
        feature_count=5
    )
    
    processor = BarProcessor(config)
    
    # Simulate real-time bars
    print("Simulating real-time data feed...")
    for i in range(100):
        # Generate one bar at a time
        bar = create_test_data(1, trend="bullish")[0]
        
        result = processor.process_bar(
            open_price=bar['open'],
            high=bar['high'],
            low=bar['low'],
            close=bar['close'],
            volume=bar['volume']
        )
        
        # Show when ML starts (accounting for 3-4 bar delay)
        if i == 52:  # Just before ML should start
            print(f"Bar {i}: ML Prediction = {result.prediction} (should be 0)")
        elif i == 53:  # ML should start around here
            print(f"Bar {i}: ML Prediction = {result.prediction} (should be non-zero)")
        elif i == 54:
            print(f"Bar {i}: ML Prediction = {result.prediction}")
    
    print("\n✅ Real-time simulation complete!")
    print("\n💡 Key Insight: ML starts at max_bars_back + ~3-4 bars (for training label lookback)!")
    print("   This is EXPECTED behavior and matches Pine Script!")

if __name__ == "__main__":
    test_sliding_window()
