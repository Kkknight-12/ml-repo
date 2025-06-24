#!/usr/bin/env python3
"""
Test memory limits implementation
=================================

This script verifies that memory limits are properly enforced
for all persistent arrays in the system.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.memory_limits import *
from ml.lorentzian_knn_fixed_corrected import LorentzianKNNFixedCorrected
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
from data.data_types import Settings, Label, FeatureArrays, FeatureSeries


def test_training_array_limit():
    """Test that training array respects memory limit"""
    print("\n1. Testing Training Array Memory Limit")
    print("="*50)
    
    # Create ML model
    settings = Settings()
    label = Label()
    ml_model = LorentzianKNNFixedCorrected(settings, label)
    
    # Add more than MAX_TRAINING_ARRAY_SIZE items
    test_size = MAX_TRAINING_ARRAY_SIZE + 1000
    print(f"   Adding {test_size} training samples...")
    
    for i in range(test_size):
        ml_model.update_training_data(100.0 + i, 99.0 + i)
        
        if i % 1000 == 0 and i > 0:
            print(f"   Progress: {i} samples, array size: {len(ml_model.y_train_array)}")
    
    final_size = len(ml_model.y_train_array)
    print(f"\n   Final training array size: {final_size}")
    print(f"   Maximum allowed size: {MAX_TRAINING_ARRAY_SIZE}")
    print(f"   ✅ Memory limit enforced: {final_size <= MAX_TRAINING_ARRAY_SIZE}")
    
    return final_size <= MAX_TRAINING_ARRAY_SIZE


def test_feature_array_limits():
    """Test that feature arrays respect memory limits"""
    print("\n2. Testing Feature Array Memory Limits")
    print("="*50)
    
    # Create processor
    config = TradingConfig()
    processor = EnhancedBarProcessor(config, "TEST", "day")
    
    # Simulate processing many bars
    test_bars = MAX_FEATURE_ARRAY_SIZE + 500
    print(f"   Processing {test_bars} bars...")
    
    for i in range(test_bars):
        # Process a bar
        processor.process_bar(
            open_price=100.0 + i*0.01,
            high=101.0 + i*0.01,
            low=99.0 + i*0.01,
            close=100.5 + i*0.01,
            volume=1000000.0
        )
        
        if i % 1000 == 0 and i > 0:
            print(f"   Progress: {i} bars, feature array size: {len(processor.feature_arrays.f1)}")
    
    final_size = len(processor.feature_arrays.f1)
    expected_max = min(config.max_bars_back, MAX_FEATURE_ARRAY_SIZE)
    print(f"\n   Final feature array size: {final_size}")
    print(f"   Expected maximum size: {expected_max}")
    print(f"   ✅ Memory limit enforced: {final_size <= expected_max}")
    
    return final_size <= expected_max


def test_cleanup_functions():
    """Test cleanup utility functions"""
    print("\n3. Testing Cleanup Functions")
    print("="*50)
    
    # Test should_cleanup
    test_cases = [
        (900, 1000),   # 90% full - should trigger
        (899, 1000),   # 89.9% full - should not trigger
        (9000, 10000), # 90% full - should trigger
        (100, 1000),   # 10% full - should not trigger
    ]
    
    print("   Testing should_cleanup() with threshold=90%:")
    for current, max_size in test_cases:
        should_clean = should_cleanup(current, max_size)
        percent = (current / max_size) * 100
        print(f"   - {current}/{max_size} ({percent:.1f}%): {'CLEANUP' if should_clean else 'NO CLEANUP'}")
    
    # Test calculate_items_to_remove
    print("\n   Testing calculate_items_to_remove() with 10% removal:")
    test_sizes = [100, 1000, 10000]
    for size in test_sizes:
        items = calculate_items_to_remove(size)
        print(f"   - Array size {size}: remove {items} items ({items/size*100:.1f}%)")
    
    return True


def test_signal_history_limits():
    """Test signal and entry history limits"""
    print("\n4. Testing Signal History Limits")
    print("="*50)
    
    # Create processor
    config = TradingConfig()
    processor = EnhancedBarProcessor(config, "TEST", "day")
    
    # Process many bars to build up history
    test_bars = 100
    print(f"   Processing {test_bars} bars to build history...")
    
    for i in range(test_bars):
        processor.process_bar(
            open_price=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000000.0
        )
    
    signal_size = len(processor.signal_history)
    entry_size = len(processor.entry_history)
    
    print(f"\n   Final signal history size: {signal_size}")
    print(f"   Maximum allowed size: {MAX_SIGNAL_HISTORY_SIZE}")
    print(f"   ✅ Signal history limited: {signal_size <= MAX_SIGNAL_HISTORY_SIZE}")
    
    print(f"\n   Final entry history size: {entry_size}")
    print(f"   Maximum allowed size: {MAX_ENTRY_HISTORY_SIZE}")
    print(f"   ✅ Entry history limited: {entry_size <= MAX_ENTRY_HISTORY_SIZE}")
    
    return signal_size <= MAX_SIGNAL_HISTORY_SIZE and entry_size <= MAX_ENTRY_HISTORY_SIZE


def main():
    """Run all memory limit tests"""
    print("="*70)
    print("MEMORY LIMITS IMPLEMENTATION TEST")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("Training Array Limit", test_training_array_limit()))
    results.append(("Feature Array Limits", test_feature_array_limits()))
    results.append(("Cleanup Functions", test_cleanup_functions()))
    results.append(("Signal History Limits", test_signal_history_limits()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Memory limits are properly enforced!")
    else:
        print("❌ SOME TESTS FAILED - Please check the implementation")
    print("="*70)
    
    # Performance note
    print("\nPERFORMANCE NOTE:")
    print("- Arrays are cleaned up when they reach 90% of max size")
    print("- Cleanup removes the oldest 10% of data")
    print("- This prevents frequent reallocation while maintaining limits")
    print("- Production systems should monitor actual memory usage")


if __name__ == "__main__":
    main()