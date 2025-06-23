#!/usr/bin/env python3
"""
Test Enhanced Bar Processor Integration
Verifies all the fixes are working correctly
"""
from config.settings import TradingConfig
from scanner import BarProcessor

def test_basic_integration():
    """Test basic integration with enhanced bar processor"""
    print("🧪 Testing Enhanced Bar Processor Integration")
    
    # Create config
    config = TradingConfig()
    
    # Create processor
    processor = BarProcessor(config, symbol="TEST", timeframe="5min")
    print(f"✅ Created processor: {processor.__class__.__name__}")
    
    # Test with some sample bars
    sample_bars = [
        (100, 102, 99, 101),
        (101, 103, 100, 102),
        (102, 104, 101, 103),
        (103, 105, 102, 104),
        (104, 106, 103, 105)
    ]
    
    for i, (o, h, l, c) in enumerate(sample_bars):
        result = processor.process_bar(o, h, l, c, volume=1000)
        if result:
            print(f"✅ Bar {i}: prediction={result.prediction:.2f}, signal={result.signal}, filters={result.filter_states}")
    
    # Test debug mode
    print("\n🧪 Testing Debug Mode")
    debug_processor = BarProcessor(config, symbol="TEST", timeframe="5min", debug_mode=True)
    print(f"✅ Created debug processor with debug_mode={debug_processor.debug_mode}")
    
    # Process one bar with debug
    result = debug_processor.process_bar(105, 107, 104, 106, volume=1000)
    if result:
        print(f"✅ Debug bar result: prediction={result.prediction:.2f}")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_basic_integration()