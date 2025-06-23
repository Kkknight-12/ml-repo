"""
Test indicators to ensure they work correctly
These tests validate the mathematical implementations
"""
import sys

sys.path.append('..')

from data.bar_data import BarData
from core.indicators import (
    n_rsi, n_wt, n_cci, n_adx, series_from,
    calculate_rsi, calculate_cci, calculate_adx
)
from core.ml_extensions import (
    regime_filter, filter_adx, filter_volatility
)
from core.normalization import rescale, normalizer
from core.math_helpers import pine_ema, pine_sma, pine_rma


def create_sample_data():
    """Create sample price data for testing"""
    bars = BarData()

    # Add 50 bars of sample data (sine wave + trend)
    import math
    for i in range(50):
        base_price = 100 + i * 0.5  # Upward trend
        wave = 5 * math.sin(i * 0.5)  # Oscillation

        close = base_price + wave
        high = close + abs(wave) * 0.2
        low = close - abs(wave) * 0.2
        open_price = close - wave * 0.1

        bars.add_bar(open_price, high, low, close, 1000 * (1 + 0.1 * wave))

    return bars


def test_basic_indicators():
    """Test basic indicator calculations"""
    print("Testing Basic Indicators...")

    bars = create_sample_data()

    # Prepare data lists (newest first)
    close_values = [bars.get_close(i) for i in range(len(bars))]
    high_values = [bars.get_high(i) for i in range(len(bars))]
    low_values = [bars.get_low(i) for i in range(len(bars))]
    hlc3_values = [bars.get_hlc3(i) for i in range(len(bars))]

    # Test RSI
    rsi = calculate_rsi(close_values, 14)
    print(f"RSI(14): {rsi:.2f}")
    assert 0 <= rsi <= 100, f"RSI out of range: {rsi}"

    # Test normalized RSI
    n_rsi_val = n_rsi(close_values, 14, 1)
    print(f"Normalized RSI: {n_rsi_val:.4f}")
    assert 0 <= n_rsi_val <= 1, f"Normalized RSI out of range: {n_rsi_val}"

    # Test CCI
    cci = calculate_cci(close_values, high_values, low_values, 20)
    print(f"CCI(20): {cci:.2f}")

    # Test normalized CCI
    n_cci_val = n_cci(close_values, high_values, low_values, 20, 1)
    print(f"Normalized CCI: {n_cci_val:.4f}")
    assert 0 <= n_cci_val <= 1, f"Normalized CCI out of range: {n_cci_val}"

    # Test ADX
    adx = calculate_adx(high_values, low_values, close_values, 14)
    print(f"ADX(14): {adx:.2f}")
    assert 0 <= adx <= 100, f"ADX out of range: {adx}"

    # Test normalized ADX
    n_adx_val = n_adx(high_values, low_values, close_values, 14)
    print(f"Normalized ADX: {n_adx_val:.4f}")
    assert 0 <= n_adx_val <= 1, f"Normalized ADX out of range: {n_adx_val}"

    # Test Wave Trend
    n_wt_val = n_wt(hlc3_values, 10, 11)
    print(f"Normalized WT: {n_wt_val:.4f}")
    assert 0 <= n_wt_val <= 1, f"Normalized WT out of range: {n_wt_val}"

    print("✓ Basic indicator tests passed!")


def test_series_from():
    """Test the series_from function"""
    print("\nTesting series_from()...")

    bars = create_sample_data()

    # Prepare data
    close_values = [bars.get_close(i) for i in range(len(bars))]
    high_values = [bars.get_high(i) for i in range(len(bars))]
    low_values = [bars.get_low(i) for i in range(len(bars))]
    hlc3_values = [bars.get_hlc3(i) for i in range(len(bars))]

    # Test each indicator type
    features = {
        "RSI": (14, 1),
        "WT": (10, 11),
        "CCI": (20, 1),
        "ADX": (14, 2)
    }

    for feature_name, (param_a, param_b) in features.items():
        value = series_from(
            feature_name, close_values, high_values,
            low_values, hlc3_values, param_a, param_b
        )
        print(f"{feature_name}({param_a},{param_b}): {value:.4f}")
        assert 0 <= value <= 1, f"{feature_name} out of range: {value}"

    print("✓ series_from tests passed!")


def test_filters():
    """Test filter functions"""
    print("\nTesting Filters...")

    bars = create_sample_data()

    # Prepare data
    close_values = [bars.get_close(i) for i in range(len(bars))]
    high_values = [bars.get_high(i) for i in range(len(bars))]
    low_values = [bars.get_low(i) for i in range(len(bars))]
    ohlc4_values = [bars.get_ohlc4(i) for i in range(len(bars))]

    # Test volatility filter
    vol_filter = filter_volatility(high_values, low_values, close_values, 1, 10, True)
    print(f"Volatility Filter: {vol_filter}")
    assert isinstance(vol_filter, bool), "Volatility filter should return bool"

    # Test regime filter
    regime = regime_filter(ohlc4_values, -0.1, True)
    print(f"Regime Filter: {regime}")
    assert isinstance(regime, bool), "Regime filter should return bool"

    # Test ADX filter
    adx_filter = filter_adx(high_values, low_values, close_values, 14, 20, True)
    print(f"ADX Filter: {adx_filter}")
    assert isinstance(adx_filter, bool), "ADX filter should return bool"

    print("✓ Filter tests passed!")


def test_normalization():
    """Test normalization functions"""
    print("\nTesting Normalization...")

    # Test rescale
    value = rescale(50, 0, 100, 0, 1)
    assert value == 0.5, f"Rescale failed: expected 0.5, got {value}"

    value = rescale(75, 0, 100, -1, 1)
    assert value == 0.5, f"Rescale failed: expected 0.5, got {value}"

    # Test normalizer (with history)
    test_normalizer = normalizer  # Use global instance

    # Add some values to build history
    series_name = "test_series"
    values = [10, 20, 30, 40, 50, 25, 35]
    normalized_values = []

    for val in values:
        norm_val = test_normalizer.normalize(val, series_name, 0, 1)
        normalized_values.append(norm_val)
        print(f"Value: {val} -> Normalized: {norm_val:.4f}")

    # Check that all normalized values are in [0, 1]
    for nv in normalized_values:
        assert 0 <= nv <= 1, f"Normalized value out of range: {nv}"

    print("✓ Normalization tests passed!")


def test_moving_averages():
    """Test moving average implementations"""
    print("\nTesting Moving Averages...")

    values = [10, 12, 11, 13, 14, 12, 15, 16, 14, 13]

    # Test SMA
    sma = pine_sma(values, 3)
    print(f"SMA(3) of last 3 values: {sma:.2f}")
    expected_sma = (10 + 12 + 11) / 3
    assert abs(sma - expected_sma) < 0.01, f"SMA mismatch: {sma} vs {expected_sma}"

    # Test EMA
    ema = pine_ema(values, 3)
    print(f"EMA(3): {ema:.2f}")
    assert 10 <= ema <= 16, f"EMA out of reasonable range: {ema}"

    # Test RMA
    rma = pine_rma(values, 3)
    print(f"RMA(3): {rma:.2f}")
    assert 10 <= rma <= 16, f"RMA out of reasonable range: {rma}"

    print("✓ Moving average tests passed!")


def run_all_tests():
    """Run all indicator tests"""
    print("=== Running Indicator Tests ===\n")

    test_moving_averages()
    test_normalization()
    test_basic_indicators()
    test_series_from()
    test_filters()

    print("\n=== All indicator tests passed! ✓ ===")
    print("\nPhase 1 Day 3-4 Complete!")
    print("Indicators are working correctly.")
    print("Ready to move to Day 5-7: ML Algorithm (Lorentzian KNN)")


if __name__ == "__main__":
    run_all_tests()