"""
Basic tests to ensure our data structures work like Pine Script
Run this to validate Phase 1 Day 1-2 implementation
"""
import sys

sys.path.append('..')  # Add parent directory to path

from data.data_types import *
from data.bar_data import BarData
from config.settings import TradingConfig


def test_bar_data():
    """Test bar data structure behaves like Pine Script"""
    print("Testing BarData...")

    # Create bar data
    bars = BarData()
    # print("bars ", bars)

    # Add some bars (oldest first, simulating chronological data)
    bars.add_bar(100, 105, 99, 102, 1000)  # First bar (will be at index 2)
    bars.add_bar(98, 101, 97, 100, 1100)  # Second bar (will be at index 1)
    bars.add_bar(96, 99, 95, 98, 1200)  # Third bar (will be at index 0 - current)

    # Test current values (index 0)
    assert bars.close == 98, f"Expected close=98, got {bars.close}"
    assert bars.high == 99, f"Expected high=99, got {bars.high}"
    assert bars.low == 95, f"Expected low=95, got {bars.low}"
    assert bars.open == 96, f"Expected open=96, got {bars.open}"

    # Test historical access (like Pine Script close[1], close[2])
    assert bars.get_close(0) == 98, "Current close wrong"
    assert bars.get_close(1) == 100, "Previous close wrong"
    assert bars.get_close(2) == 102, "2 bars ago close wrong"

    # Test calculated values
    assert bars.hlc3 == (99 + 95 + 98) / 3, "HLC3 calculation wrong"
    assert bars.ohlc4 == (96 + 99 + 95 + 98) / 4, "OHLC4 calculation wrong"

    # Test bar index
    assert bars.bar_index == 2, f"Expected bar_index=2, got {bars.bar_index}"

    print("✓ BarData tests passed!")


def test_data_types():
    """Test Pine Script type conversions"""
    print("\nTesting Data Types...")

    # Test Settings
    settings = Settings()
    assert settings.neighbors_count == 8, "Default neighbors_count wrong"
    assert settings.max_bars_back == 2000, "Default max_bars_back wrong"

    # Test Label
    label = Label()
    assert label.long == 1, "Long label wrong"
    assert label.short == -1, "Short label wrong"
    assert label.neutral == 0, "Neutral label wrong"

    # Test FeatureArrays
    features = FeatureArrays()
    assert isinstance(features.f1, list), "Feature array should be list"
    assert len(features.f1) == 0, "Feature array should start empty"

    # Test MLModel
    model = MLModel()
    assert model.last_distance == -1.0, "Initial last_distance wrong"
    assert isinstance(model.predictions_array, list), "Predictions should be list"

    print("✓ Data type tests passed!")


def test_config():
    """Test configuration system"""
    print("\nTesting Configuration...")

    # Test default config
    config = TradingConfig()
    assert config.neighbors_count == 8, "Default config wrong"
    assert config.features["f1"] == ("RSI", 14, 1), "Default feature f1 wrong"
    assert config.features["f2"] == ("WT", 10, 11), "Default feature f2 wrong"

    # Test config conversions
    settings = config.get_settings()
    assert isinstance(settings, Settings), "Should return Settings object"
    assert settings.neighbors_count == 8, "Settings conversion wrong"

    filter_settings = config.get_filter_settings()
    assert isinstance(filter_settings, FilterSettings), "Should return FilterSettings"
    assert filter_settings.use_volatility_filter == True, "Filter settings wrong"

    print("✓ Configuration tests passed!")


def test_bar_processor_initialization():
    """Test BarProcessor initialization with total_bars"""
    print("\nTesting BarProcessor Initialization...")
    
    from scanner.bar_processor import BarProcessor
    
    config = TradingConfig(max_bars_back=100)
    
    # Test without total_bars (backward compatibility)
    processor1 = BarProcessor(config)
    assert processor1.total_bars is None, "Should be None when not provided"
    assert processor1.max_bars_back_index == 0, "Should be 0 when total_bars not provided"
    
    # Test with total_bars less than max_bars_back
    processor2 = BarProcessor(config, total_bars=50)
    assert processor2.total_bars == 50, "Total bars not set correctly"
    assert processor2.max_bars_back_index == 0, "Should be 0 when total_bars < max_bars_back"
    
    # Test with total_bars greater than max_bars_back
    processor3 = BarProcessor(config, total_bars=200)
    assert processor3.total_bars == 200, "Total bars not set correctly"
    assert processor3.max_bars_back_index == 99, "Should be total_bars - 1 - max_bars_back"
    
    # Test set_total_bars method
    processor3.set_total_bars(300)
    assert processor3.total_bars == 300, "set_total_bars not working"
    assert processor3.max_bars_back_index == 199, "max_bars_back_index not updated"
    
    print("✓ BarProcessor initialization tests passed!")


def run_all_tests():
    """Run all basic tests"""
    print("=== Running Basic Tests ===\n")

    test_bar_data()
    test_data_types()
    test_config()
    test_bar_processor_initialization()

    print("\n=== All tests passed! ✓ ===")
    print("\nPhase 1 Day 1-2 Complete!")
    print("Data structures match Pine Script exactly.")
    print("Bar index fix properly tested.")
    print("Ready to move to Day 3-4: Indicators")


if __name__ == "__main__":
    run_all_tests()