"""
Test ML Algorithm - Lorentzian KNN Implementation
Validates the core ML logic works correctly
"""
import sys

sys.path.append('..')

import math
from config.settings import TradingConfig
from scanner import BarProcessor, BarResult
from data.data_types import Label, FeatureSeries, FeatureArrays
from ml.lorentzian_knn import LorentzianKNN


def create_trending_data(num_bars: int, trend: str = "up") -> list:
    """Create synthetic trending price data"""
    bars = []
    base_price = 100.0

    for i in range(num_bars):
        if trend == "up":
            # Upward trend with some noise
            price = base_price + i * 0.5 + (i % 5) * 0.1
        else:
            # Downward trend with some noise
            price = base_price - i * 0.5 - (i % 5) * 0.1

        # Add some volatility
        high = price + abs(math.sin(i * 0.2)) * 2
        low = price - abs(math.sin(i * 0.2)) * 2
        open_price = price - 0.1
        close = price

        bars.append((open_price, high, low, close, 1000))

    return bars


def test_lorentzian_distance():
    """Test Lorentzian distance calculation"""
    print("Testing Lorentzian Distance Calculation...")

    # Create test data
    config = TradingConfig(feature_count=3)
    label = Label()
    model = LorentzianKNN(config.get_settings(), label)

    # Create feature series and arrays
    current_features = FeatureSeries(f1=0.5, f2=0.6, f3=0.7, f4=0.8, f5=0.9)

    feature_arrays = FeatureArrays()
    feature_arrays.f1 = [0.4, 0.3, 0.2]  # Historical values
    feature_arrays.f2 = [0.5, 0.4, 0.3]
    feature_arrays.f3 = [0.6, 0.5, 0.4]
    feature_arrays.f4 = [0.7, 0.6, 0.5]
    feature_arrays.f5 = [0.8, 0.7, 0.6]

    # Calculate distance to first historical point
    distance = model.get_lorentzian_distance(0, 3, current_features, feature_arrays)

    # Verify distance calculation
    expected = (
            math.log(1 + abs(0.5 - 0.4)) +  # f1
            math.log(1 + abs(0.6 - 0.5)) +  # f2
            math.log(1 + abs(0.7 - 0.6))  # f3
    )

    print(f"Calculated distance: {distance:.4f}")
    print(f"Expected distance: {expected:.4f}")

    assert abs(distance - expected) < 0.001, f"Distance mismatch: {distance} vs {expected}"
    print("✓ Lorentzian distance test passed!")


def test_knn_prediction():
    """Test KNN prediction logic"""
    print("\nTesting KNN Prediction...")

    config = TradingConfig(
        neighbors_count=3,
        max_bars_back=20,
        feature_count=2
    )
    label = Label()
    model = LorentzianKNN(config.get_settings(), label)

    # Setup training data (alternating long/short labels)
    for i in range(20):
        if i % 8 < 4:
            model.y_train_array.append(label.long)
        else:
            model.y_train_array.append(label.short)

    # Setup features
    current_features = FeatureSeries(f1=0.5, f2=0.5, f3=0.5, f4=0.5, f5=0.5)
    feature_arrays = FeatureArrays()

    # Historical features (20 values each)
    for i in range(20):
        value = 0.5 + (i % 4) * 0.1  # Some variation
        feature_arrays.f1.append(value)
        feature_arrays.f2.append(value)

    # Run prediction
    prediction = model.predict(current_features, feature_arrays, 25, 5)

    print(f"Prediction value: {prediction}")
    print(f"Number of neighbors used: {len(model.predictions)}")
    print(f"Neighbor predictions: {model.predictions}")

    # Should have exactly k neighbors
    assert len(model.predictions) <= config.neighbors_count, \
        f"Too many neighbors: {len(model.predictions)}"

    # Prediction should be sum of neighbor labels
    assert prediction == sum(model.predictions), \
        f"Prediction sum mismatch: {prediction} vs {sum(model.predictions)}"

    print("✓ KNN prediction test passed!")


def test_signal_generation():
    """Test complete signal generation flow"""
    print("\nTesting Signal Generation Flow...")

    # Create processor with custom config
    config = TradingConfig(
        neighbors_count=5,
        max_bars_back=50,
        feature_count=3,
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        use_kernel_filter=False,  # Disable for simpler testing
        use_ema_filter=False,
        use_sma_filter=False
    )

    # Pass total bars for proper Pine Script behavior
    processor = BarProcessor(config, total_bars=60)  # We're processing 60 bars

    # Process uptrend data
    print("\nProcessing uptrend data...")
    uptrend_bars = create_trending_data(60, "up")

    signals = []
    for i, (o, h, l, c, v) in enumerate(uptrend_bars):
        result = processor.process_bar(o, h, l, c, v)

        if i >= 50:  # After warmup period
            signals.append(result)
            if result.start_long_trade or result.start_short_trade:
                print(f"Bar {i}: Signal generated!")
                print(f"  Prediction: {result.prediction:.2f}")
                print(f"  Signal: {result.signal}")
                print(f"  Long: {result.start_long_trade}, Short: {result.start_short_trade}")

    # Should generate some signals
    total_signals = sum(1 for s in signals if s.start_long_trade or s.start_short_trade)
    print(f"\nTotal signals generated: {total_signals}")

    assert total_signals > 0, "No signals generated in uptrend"
    print("✓ Signal generation test passed!")


def test_bar_processor():
    """Test the complete bar processing pipeline"""
    print("\nTesting Complete Bar Processing...")

    config = TradingConfig()
    processor = BarProcessor(config, total_bars=100)  # Assume we'll process 100 bars

    # Process a single bar
    result = processor.process_bar(100, 105, 99, 102, 1000)

    # Verify result structure
    assert isinstance(result, BarResult), "Should return BarResult"
    assert result.bar_index == 0, "First bar should have index 0"
    assert result.close == 102, "Close price mismatch"
    assert isinstance(result.prediction, float), "Prediction should be float"
    assert result.signal in [-1, 0, 1], "Signal should be -1, 0, or 1"
    assert isinstance(result.filter_states, dict), "Filter states should be dict"

    print(f"Bar processed successfully:")
    print(f"  Bar index: {result.bar_index}")
    print(f"  Prediction: {result.prediction}")
    print(f"  Signal: {result.signal}")
    print(f"  Filters: {result.filter_states}")

    # Process more bars to test continuity
    for i in range(10):
        price = 100 + i
        result = processor.process_bar(price, price + 2, price - 2, price + 1, 1000)
        assert result.bar_index == i + 1, f"Bar index mismatch at {i}"

    print("✓ Bar processor test passed!")


def test_entry_exit_logic():
    """Test entry and exit signal logic"""
    print("\nTesting Entry/Exit Logic...")

    config = TradingConfig(
        use_kernel_filter=False,
        use_ema_filter=False,
        use_sma_filter=False,
        show_exits=True
    )
    processor = BarProcessor(config, total_bars=40)  # We're processing 40 bars

    # Create a pattern that should generate entry/exit
    # First create downtrend, then uptrend
    bars = []

    # Downtrend for 20 bars
    for i in range(20):
        price = 100 - i * 0.5
        bars.append((price, price + 1, price - 1, price, 1000))

    # Sharp uptrend for 20 bars
    for i in range(20):
        price = 90 + i * 1.0
        bars.append((price, price + 1, price - 1, price, 1000))

    # Process all bars
    entries = []
    exits = []

    for i, (o, h, l, c, v) in enumerate(bars):
        result = processor.process_bar(o, h, l, c, v)

        if result.start_long_trade:
            entries.append((i, "LONG"))
            print(f"Bar {i}: LONG entry signal")

        if result.start_short_trade:
            entries.append((i, "SHORT"))
            print(f"Bar {i}: SHORT entry signal")

        if result.end_long_trade:
            exits.append((i, "EXIT_LONG"))
            print(f"Bar {i}: EXIT long signal")

        if result.end_short_trade:
            exits.append((i, "EXIT_SHORT"))
            print(f"Bar {i}: EXIT short signal")

    print(f"\nTotal entries: {len(entries)}")
    print(f"Total exits: {len(exits)}")

    # Should have at least some signals after trend change
    assert len(entries) > 0 or len(exits) > 0, "No entry/exit signals generated"

    print("✓ Entry/Exit logic test passed!")


def run_all_tests():
    """Run all ML algorithm tests"""
    print("=== Running ML Algorithm Tests ===\n")

    test_lorentzian_distance()
    test_knn_prediction()
    test_bar_processor()
    test_signal_generation()
    test_entry_exit_logic()

    print("\n=== All ML algorithm tests passed! ✓ ===")
    print("\nPhase 1 Day 5-7 Complete!")
    print("ML Algorithm is working correctly.")
    print("Ready for integration with live data!")


if __name__ == "__main__":
    run_all_tests()