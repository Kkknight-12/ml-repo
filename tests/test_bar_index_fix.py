"""
Test Bar Index Fix - Validate Pine Script Compatibility

This script tests that the bar index fix is working correctly.
"""
import sys
sys.path.append('..')

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor


def test_small_dataset():
    """Test with dataset smaller than max_bars_back"""
    print("=" * 60)
    print("TEST 1: Small Dataset (300 bars, max_bars_back=2000)")
    print("=" * 60)
    
    config = TradingConfig(max_bars_back=2000)
    processor = BarProcessor(config, total_bars=300)
    
    assert processor.max_bars_back_index == 0, \
        f"Expected 0, got {processor.max_bars_back_index}"
    
    print(f"✅ PASS: max_bars_back_index = {processor.max_bars_back_index}")
    print("   (Correct: Use all 300 bars)")


def test_large_dataset():
    """Test with dataset larger than max_bars_back"""
    print("\n" + "=" * 60)
    print("TEST 2: Large Dataset (3000 bars, max_bars_back=2000)")
    print("=" * 60)
    
    config = TradingConfig(max_bars_back=2000)
    processor = BarProcessor(config, total_bars=3000)
    
    expected = 3000 - 2000  # Should be 1000
    assert processor.max_bars_back_index == expected, \
        f"Expected {expected}, got {processor.max_bars_back_index}"
    
    print(f"✅ PASS: max_bars_back_index = {processor.max_bars_back_index}")
    print(f"   (Correct: Skip first {expected} bars)")


def test_ml_activation():
    """Test that ML only activates after warmup"""
    print("\n" + "=" * 60)
    print("TEST 3: ML Activation Timing")
    print("=" * 60)
    
    config = TradingConfig(max_bars_back=50, neighbors_count=3)
    processor = BarProcessor(config, total_bars=100)
    
    print(f"Setup: 100 total bars, max_bars_back=50")
    print(f"Expected: ML starts at bar 50")
    print()
    
    # Process bars and check when ML activates
    ml_started = False
    ml_start_bar = -1
    
    for i in range(60):
        result = processor.process_bar(100, 101, 99, 100.5, 1000)
        
        if result.prediction != 0 and not ml_started:
            ml_started = True
            ml_start_bar = i
            
        if i in [48, 49, 50, 51]:
            print(f"Bar {i}: prediction = {result.prediction:.2f}")
    
    assert ml_start_bar >= processor.max_bars_back_index, \
        f"ML started too early at bar {ml_start_bar}"
    
    print(f"\n✅ PASS: ML started at bar {ml_start_bar}")
    print(f"   (Correct: Started at or after bar {processor.max_bars_back_index})")


def test_no_total_bars():
    """Test behavior when total_bars not provided"""
    print("\n" + "=" * 60)
    print("TEST 4: No Total Bars (Real-time mode)")
    print("=" * 60)
    
    config = TradingConfig(max_bars_back=2000)
    processor = BarProcessor(config, total_bars=None)
    
    assert processor.max_bars_back_index == 0, \
        f"Expected 0, got {processor.max_bars_back_index}"
    
    print(f"✅ PASS: max_bars_back_index = {processor.max_bars_back_index}")
    print("   (Correct: Real-time mode, no warmup calculation)")


def test_edge_cases():
    """Test edge cases"""
    print("\n" + "=" * 60)
    print("TEST 5: Edge Cases")
    print("=" * 60)
    
    # Edge case 1: Exactly max_bars_back
    config = TradingConfig(max_bars_back=100)
    processor = BarProcessor(config, total_bars=100)
    assert processor.max_bars_back_index == 0
    print("✅ PASS: total_bars == max_bars_back → max_bars_back_index = 0")
    
    # Edge case 2: One more than max_bars_back
    processor = BarProcessor(config, total_bars=101)
    assert processor.max_bars_back_index == 1
    print("✅ PASS: total_bars = 101, max_bars_back = 100 → max_bars_back_index = 1")
    
    # Edge case 3: Very small dataset
    processor = BarProcessor(config, total_bars=10)
    assert processor.max_bars_back_index == 0
    print("✅ PASS: total_bars = 10 → max_bars_back_index = 0")


def test_set_total_bars():
    """Test dynamic total_bars update"""
    print("\n" + "=" * 60)
    print("TEST 6: Dynamic Total Bars Update")
    print("=" * 60)
    
    config = TradingConfig(max_bars_back=50)
    processor = BarProcessor(config, total_bars=None)
    
    print(f"Initial: total_bars=None, max_bars_back_index={processor.max_bars_back_index}")
    
    # Update total bars
    processor.set_total_bars(100)
    print(f"After set_total_bars(100): max_bars_back_index={processor.max_bars_back_index}")
    
    assert processor.max_bars_back_index == 50, \
        f"Expected 50, got {processor.max_bars_back_index}"
    
    print("✅ PASS: Dynamic update works correctly")


def run_all_tests():
    """Run all validation tests"""
    print("LORENTZIAN CLASSIFICATION - BAR INDEX FIX VALIDATION")
    print("=" * 60)
    print()
    
    try:
        test_small_dataset()
        test_large_dataset()
        test_ml_activation()
        test_no_total_bars()
        test_edge_cases()
        test_set_total_bars()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe bar index fix is working correctly.")
        print("Implementation matches Pine Script logic exactly.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
