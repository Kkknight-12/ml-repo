"""
Example: How to Use BarProcessor with Correct Bar Index Logic

This shows real-world usage patterns for both:
1. Historical data processing (with known total bars)
2. Real-time streaming (without total bars)
"""
import sys
sys.path.append('..')

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
import random


def example_historical_processing():
    """Example: Processing historical data where we know total bars"""
    print("=" * 60)
    print("EXAMPLE 1: Historical Data Processing")
    print("=" * 60)
    
    # Configuration
    config = TradingConfig(
        max_bars_back=2000,
        neighbors_count=8,
        feature_count=5,
        use_volatility_filter=True,
        use_regime_filter=True
    )
    
    # Load your historical data (example)
    historical_data = []
    for i in range(3000):  # 3000 bars of data
        base_price = 100 + i * 0.01 + random.uniform(-0.5, 0.5)
        historical_data.append({
            'open': base_price,
            'high': base_price + random.uniform(0, 2),
            'low': base_price - random.uniform(0, 2),
            'close': base_price + random.uniform(-0.5, 0.5),
            'volume': random.randint(1000, 5000)
        })
    
    # IMPORTANT: Pass total bars when creating processor
    total_bars = len(historical_data)
    processor = BarProcessor(config, total_bars=total_bars)
    
    print(f"Processing {total_bars} bars of historical data...")
    print(f"ML will start at bar {processor.max_bars_back_index}")
    print()
    
    # Process all bars
    signals = []
    for i, bar in enumerate(historical_data):
        result = processor.process_bar(
            bar['open'], bar['high'], bar['low'], 
            bar['close'], bar['volume']
        )
        
        # Collect signals after warmup
        if result.start_long_trade or result.start_short_trade:
            signals.append({
                'bar': i,
                'type': 'LONG' if result.start_long_trade else 'SHORT',
                'price': result.close,
                'prediction': result.prediction
            })
            
            # Show first few signals
            if len(signals) <= 3:
                print(f"Signal #{len(signals)}: {signals[-1]['type']} "
                      f"at bar {i}, price {result.close:.2f}, "
                      f"prediction {result.prediction:.2f}")
    
    print(f"\nTotal signals generated: {len(signals)}")
    

def example_realtime_streaming():
    """Example: Real-time streaming where total bars unknown"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Real-Time Streaming")
    print("=" * 60)
    
    config = TradingConfig(
        max_bars_back=2000,
        neighbors_count=8,
        feature_count=5
    )
    
    # For real-time, we don't know total bars
    processor = BarProcessor(config, total_bars=None)
    
    print("Real-time mode: ML will start after sufficient bars")
    print("This mode is for live trading where data arrives bar by bar")
    print()
    
    # Simulate real-time data
    print("Simulating real-time bars...")
    for i in range(10):
        # Get new bar from API/websocket
        price = 100 + i * 0.1 + random.uniform(-0.5, 0.5)
        
        result = processor.process_bar(
            price, price + 0.5, price - 0.5,
            price + 0.1, 1000
        )
        
        print(f"Bar {i}: Close={result.close:.2f}, "
              f"Prediction={result.prediction:.2f}, "
              f"Signal={result.signal}")
    

def example_switching_modes():
    """Example: Loading historical then switching to real-time"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Historical Warmup + Real-Time Trading")
    print("=" * 60)
    
    config = TradingConfig(
        max_bars_back=50,  # Smaller for demo
        neighbors_count=5,
        feature_count=3
    )
    
    # Step 1: Load historical data for warmup
    historical_bars = 100
    processor = BarProcessor(config, total_bars=historical_bars)
    
    print(f"Step 1: Loading {historical_bars} historical bars for warmup...")
    
    # Process historical bars
    for i in range(historical_bars):
        price = 100 + i * 0.05
        processor.process_bar(price, price + 0.5, price - 0.5, price + 0.1, 1000)
    
    print(f"Warmup complete. ML started at bar {processor.max_bars_back_index}")
    
    # Step 2: Switch to real-time mode
    print("\nStep 2: Switching to real-time mode...")
    print("(In practice, continue using same processor instance)")
    
    # Continue processing new bars as they arrive
    for i in range(5):
        price = 105 + i * 0.1
        result = processor.process_bar(
            price, price + 0.5, price - 0.5, price + 0.1, 1000
        )
        
        print(f"Real-time bar {i}: Prediction={result.prediction:.2f}")
        
        if result.start_long_trade:
            print("  ➡️ BUY SIGNAL!")
        if result.start_short_trade:
            print("  ➡️ SELL SIGNAL!")
    

def best_practices():
    """Show best practices for using BarProcessor"""
    print("\n" + "=" * 60)
    print("BEST PRACTICES")
    print("=" * 60)
    
    print("""
1. HISTORICAL DATA PROCESSING:
   - Always pass total_bars when you know dataset size
   - This ensures ML starts at correct bar
   
   processor = BarProcessor(config, total_bars=len(data))

2. REAL-TIME STREAMING:
   - Pass total_bars=None for pure streaming
   - Or warmup with historical first
   
   processor = BarProcessor(config, total_bars=None)

3. HYBRID APPROACH (RECOMMENDED):
   - Load historical data with total_bars
   - Continue using same processor for real-time
   
   # Warmup
   processor = BarProcessor(config, total_bars=historical_count)
   # ... process historical bars ...
   
   # Then continue with real-time
   # (same processor instance)

4. CHECKING ML STATUS:
   - Use processor.max_bars_back_index to know when ML starts
   - Bar index must be >= max_bars_back_index for predictions
   
5. MINIMUM DATA REQUIREMENTS:
   - Pine Script default: 2000 bars
   - Can reduce for testing (50-100 bars)
   - More data = better predictions
    """)


def main():
    """Run all examples"""
    print("LORENTZIAN CLASSIFICATION - USAGE EXAMPLES")
    print("=" * 60)
    
    example_historical_processing()
    example_realtime_streaming()
    example_switching_modes()
    best_practices()
    
    print("\n✅ Implementation follows Pine Script logic exactly!")


if __name__ == "__main__":
    main()
