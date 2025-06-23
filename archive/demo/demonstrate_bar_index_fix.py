"""
Demonstrate the Bar Index Fix for Pine Script Compatibility

This script shows:
1. The problem with current implementation
2. How Pine Script handles bar index
3. The fix implementation
"""
import sys
sys.path.append('..')

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor


def generate_test_data(num_bars: int) -> list:
    """Generate simple test data"""
    bars = []
    for i in range(num_bars):
        # Simple uptrend
        price = 100 + i * 0.1
        bars.append((price, price + 1, price - 1, price + 0.05, 1000))
    return bars


def test_without_total_bars():
    """Test current behavior - WITHOUT total bars (old logic)"""
    print("=" * 60)
    print("TEST 1: Without Total Bars (OLD LOGIC)")
    print("=" * 60)
    
    config = TradingConfig(
        max_bars_back=2000,
        neighbors_count=8,
        feature_count=5
    )
    
    # Create processor WITHOUT total_bars
    processor = BarProcessor(config, total_bars=None)
    
    print(f"Max bars back: {config.max_bars_back}")
    print(f"Max bars back index: {processor.max_bars_back_index}")
    print("^ This is 0 because we don't know total bars!\n")
    
    # Process some bars
    test_bars = generate_test_data(300)  # Less than max_bars_back
    
    signals_generated = 0
    for i, (o, h, l, c, v) in enumerate(test_bars):
        result = processor.process_bar(o, h, l, c, v)
        
        if i < 10 or i > 290:  # Show first and last few
            print(f"Bar {i}: prediction={result.prediction:.2f}, "
                  f"signal={result.signal}, "
                  f"ML running: {i >= processor.max_bars_back_index}")
        
        if result.start_long_trade or result.start_short_trade:
            signals_generated += 1
    
    print(f"\nTotal signals generated: {signals_generated}")
    print("PROBLEM: ML starts immediately at bar 0 with no training data!")
    

def test_with_total_bars():
    """Test fixed behavior - WITH total bars (Pine Script logic)"""
    print("\n" + "=" * 60)
    print("TEST 2: With Total Bars (PINE SCRIPT LOGIC)")
    print("=" * 60)
    
    config = TradingConfig(
        max_bars_back=2000,
        neighbors_count=8,
        feature_count=5
    )
    
    # Test with 300 bars (less than max_bars_back)
    total_bars = 300
    processor = BarProcessor(config, total_bars=total_bars)
    
    print(f"Total bars in dataset: {total_bars}")
    print(f"Max bars back: {config.max_bars_back}")
    print(f"Max bars back index: {processor.max_bars_back_index}")
    print("^ This is 0 because 300 < 2000 (use all bars)\n")
    
    # Now test with 3000 bars (more than max_bars_back)
    total_bars = 3000
    processor = BarProcessor(config, total_bars=total_bars)
    
    print(f"\nTotal bars in dataset: {total_bars}")
    print(f"Max bars back: {config.max_bars_back}")
    print(f"Max bars back index: {processor.max_bars_back_index}")
    print(f"^ This is {total_bars - config.max_bars_back} because we skip early bars!")
    

def test_signal_generation_comparison():
    """Compare signal generation with and without fix"""
    print("\n" + "=" * 60)
    print("TEST 3: Signal Generation Comparison")
    print("=" * 60)
    
    config = TradingConfig(
        max_bars_back=50,  # Smaller for demo
        neighbors_count=5,
        feature_count=3,
        use_kernel_filter=False,
        use_ema_filter=False,
        use_sma_filter=False
    )
    
    # Generate test data
    test_data = generate_test_data(100)
    
    # Test WITHOUT total bars
    print("\nWithout total_bars (OLD):")
    processor_old = BarProcessor(config, total_bars=None)
    
    old_predictions = []
    for i, (o, h, l, c, v) in enumerate(test_data):
        result = processor_old.process_bar(o, h, l, c, v)
        old_predictions.append(result.prediction)
        
        if i < 5:  # Show first few
            print(f"  Bar {i}: prediction={result.prediction:.2f}")
    
    # Test WITH total bars
    print("\nWith total_bars (FIXED):")
    processor_new = BarProcessor(config, total_bars=len(test_data))
    
    new_predictions = []
    ml_started = False
    for i, (o, h, l, c, v) in enumerate(test_data):
        result = processor_new.process_bar(o, h, l, c, v)
        new_predictions.append(result.prediction)
        
        if result.prediction != 0 and not ml_started:
            ml_started = True
            print(f"  ML started at bar {i} (after {i} bars of warmup)")
        
        if i < 5 or (ml_started and i < processor_new.max_bars_back_index + 5):
            print(f"  Bar {i}: prediction={result.prediction:.2f}")
    
    # Compare results
    print("\nComparison:")
    print(f"OLD: First non-zero prediction at bar {next((i for i, p in enumerate(old_predictions) if p != 0), -1)}")
    print(f"NEW: First non-zero prediction at bar {next((i for i, p in enumerate(new_predictions) if p != 0), -1)}")
    

def demonstrate_pine_script_logic():
    """Show exact Pine Script logic"""
    print("\n" + "=" * 60)
    print("PINE SCRIPT LOGIC EXPLANATION")
    print("=" * 60)
    
    print("""
Pine Script:
    maxBarsBackIndex = last_bar_index >= settings.maxBarsBack ? 
                       last_bar_index - settings.maxBarsBack : 0

Examples:
    1. Dataset: 300 bars, max_bars_back: 2000
       last_bar_index = 299
       299 >= 2000? NO
       maxBarsBackIndex = 0 (use all bars for ML)
       
    2. Dataset: 3000 bars, max_bars_back: 2000
       last_bar_index = 2999
       2999 >= 2000? YES
       maxBarsBackIndex = 2999 - 2000 = 999
       ML starts at bar 999 (skip first 999 bars)
       
Key Points:
    - Pine Script knows TOTAL bars upfront
    - ML only starts after sufficient warmup
    - This prevents poor predictions from insufficient data
    """)


def main():
    """Run all demonstrations"""
    print("LORENTZIAN CLASSIFICATION - BAR INDEX FIX DEMONSTRATION")
    print("=" * 60)
    
    test_without_total_bars()
    test_with_total_bars()
    test_signal_generation_comparison()
    demonstrate_pine_script_logic()
    
    print("\n" + "=" * 60)
    print("CONCLUSION: Pass total_bars to BarProcessor for correct ML behavior!")
    print("=" * 60)


if __name__ == "__main__":
    main()
