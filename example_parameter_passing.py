#!/usr/bin/env python3
"""
Example: How to write test scripts with proper parameter passing
Shows the recommended way to pass symbol, timeframe, and other parameters
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import TradingConfig
from utils.compatibility import create_processor, setup_test_environment
from utils.sample_data import generate_trending_data


def example_basic_test(symbol: str, timeframe: str):
    """
    Basic example of parameter passing
    
    Args:
        symbol: Stock symbol (e.g., "ICICIBANK")
        timeframe: Timeframe (e.g., "day", "5minute")
    """
    print(f"\n📊 Testing {symbol} on {timeframe} timeframe")
    
    # Create configuration based on timeframe
    if timeframe == "day":
        config = TradingConfig(
            neighbors_count=8,
            max_bars_back=2000,
            regime_threshold=-0.1
        )
    elif timeframe == "5minute":
        config = TradingConfig(
            neighbors_count=5,
            max_bars_back=1000,
            regime_threshold=0.0
        )
    else:
        config = TradingConfig()  # Default
    
    # Create processor with parameters
    processor = create_processor(
        config=config,
        symbol=symbol,        # Pass symbol
        timeframe=timeframe,  # Pass timeframe
        use_enhanced=True     # Use new features
    )
    
    # Generate test data
    data = generate_trending_data(100)
    
    # Process bars
    results = []
    for i, (o, h, l, c, v) in enumerate(data):
        result = processor.process_bar(o, h, l, c, v)
        if result:
            results.append(result)
    
    print(f"✅ Processed {len(results)} bars successfully")
    return results


def example_advanced_test():
    """
    Advanced example with full parameter control
    """
    print("\n🎯 Advanced Parameter Passing Example")
    
    # Define test parameters (as if from web interface)
    test_params = {
        "symbol": "RELIANCE",
        "exchange": "NSE", 
        "timeframe": "15minute",
        "lookback_days": 30,
        "filters": {
            "volatility": True,
            "regime": True,
            "adx": False,
            "kernel": True
        },
        "custom_features": {
            "f1": ("RSI", 20, 2),
            "f2": ("WT", 15, 16),
            "f3": ("CCI", 25, 1),
            "f4": ("ADX", 30, 2),
            "f5": ("RSI", 10, 1)
        }
    }
    
    # Create configuration from parameters
    config = TradingConfig(
        # Timeframe-specific settings
        neighbors_count=6,  # Custom for 15min
        max_bars_back=1200,
        regime_threshold=-0.05,
        
        # Apply filter settings
        use_volatility_filter=test_params["filters"]["volatility"],
        use_regime_filter=test_params["filters"]["regime"],
        use_adx_filter=test_params["filters"]["adx"],
        use_kernel_filter=test_params["filters"]["kernel"],
        
        # Custom features
        features=test_params["custom_features"]
    )
    
    # Create processor
    processor = create_processor(
        config=config,
        symbol=test_params["symbol"],
        timeframe=test_params["timeframe"],
        use_enhanced=True
    )
    
    print(f"\nConfiguration applied:")
    print(f"  Symbol: {processor.symbol}")
    print(f"  Timeframe: {processor.timeframe}")
    print(f"  Neighbors: {config.neighbors_count}")
    print(f"  Features: {list(config.features.keys())}")
    print(f"  Filters: {[k for k, v in test_params['filters'].items() if v]}")
    
    return processor


def example_using_setup_helper():
    """
    Simplest approach using setup helper
    """
    print("\n🚀 Using Setup Helper (Recommended)")
    
    # One-line setup for common scenarios
    env = setup_test_environment(
        symbol="TATASTEEL",
        timeframe="hour",
        use_enhanced=True
    )
    
    # Extract components
    processor = env["processor"]
    config = env["config"]
    
    print(f"\nEnvironment ready:")
    print(f"  Symbol: {env['symbol']}")
    print(f"  Timeframe: {env['timeframe']}")
    print(f"  Enhanced features: {env['use_enhanced']}")
    print(f"  Config: Optimized for {env['timeframe']}")
    
    return env


def example_batch_testing():
    """
    Example of testing multiple symbols/timeframes
    """
    print("\n📦 Batch Testing Example")
    
    # Define test matrix
    test_matrix = [
        ("ICICIBANK", "day"),
        ("RELIANCE", "5minute"),
        ("INFY", "hour"),
        ("TCS", "15minute")
    ]
    
    results = {}
    
    for symbol, timeframe in test_matrix:
        print(f"\nTesting {symbol} - {timeframe}:")
        
        # Setup environment for each combination
        env = setup_test_environment(symbol, timeframe, True)
        processor = env["processor"]
        
        # Generate and process data
        data = generate_trending_data(50)
        
        signals = 0
        for o, h, l, c, v in data:
            result = processor.process_bar(o, h, l, c, v)
            if result and (result.start_long_trade or result.start_short_trade):
                signals += 1
        
        results[f"{symbol}_{timeframe}"] = signals
        print(f"  Signals generated: {signals}")
    
    return results


def main():
    """
    Run all examples
    """
    print("=" * 70)
    print("📚 PARAMETER PASSING EXAMPLES")
    print("=" * 70)
    
    # Example 1: Basic parameter passing
    example_basic_test("ICICIBANK", "day")
    example_basic_test("HDFC", "5minute")
    
    # Example 2: Advanced configuration
    processor = example_advanced_test()
    
    # Example 3: Using setup helper
    env = example_using_setup_helper()
    
    # Example 4: Batch testing
    results = example_batch_testing()
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ KEY TAKEAWAYS")
    print("=" * 70)
    
    print("\n1. Always pass parameters explicitly:")
    print("   processor = create_processor(config, symbol, timeframe)")
    
    print("\n2. Configure based on timeframe:")
    print("   if timeframe == 'day': config.neighbors_count = 8")
    
    print("\n3. Use setup helper for quick tests:")
    print("   env = setup_test_environment('ICICIBANK', 'day')")
    
    print("\n4. Never hardcode values in functions:")
    print("   ❌ symbol = 'ICICIBANK'  # Don't do this")
    print("   ✅ def test(symbol='ICICIBANK'):  # Do this")
    
    print("\n5. Pass all user inputs as parameters:")
    print("   - Symbol, Exchange, Timeframe")
    print("   - Date ranges, Filter settings")
    print("   - Custom parameters")


if __name__ == "__main__":
    main()
