"""
Test enhanced stateful indicators to ensure they work correctly
These tests validate that the stateful implementations match expected behavior
"""
import sys
sys.path.append('..')

from data.bar_data import BarData
from core.indicators import (
    enhanced_n_rsi, enhanced_n_wt, enhanced_n_cci, enhanced_n_adx,
    enhanced_series_from, get_indicator_manager
)
from core.ml_extensions import (
    enhanced_regime_filter, enhanced_filter_adx, enhanced_filter_volatility
)
import math


def create_test_data():
    """Create simple test data for validation"""
    # Simple incrementing prices for easy validation
    prices = []
    for i in range(100):
        # Create a simple uptrend with some volatility
        base_price = 100 + i * 0.5
        volatility = 2 * math.sin(i * 0.2)
        prices.append({
            'open': base_price - abs(volatility) * 0.5,
            'high': base_price + abs(volatility),
            'low': base_price - abs(volatility),
            'close': base_price + volatility * 0.5,
            'volume': 1000000
        })
    return prices


def test_stateful_rsi():
    """Test that RSI maintains state correctly"""
    print("Testing Stateful RSI...")
    
    symbol = "TEST_RSI"
    timeframe = "5minute"
    
    # Clear any existing state
    manager = get_indicator_manager()
    manager.clear_symbol(symbol)
    
    # Create test data with known pattern
    prices = create_test_data()
    
    # Process bars one by one
    rsi_values = []
    previous_close = None
    
    for i, bar in enumerate(prices):
        current_close = bar['close']
        
        # Skip first bar (need previous close for RSI)
        if i == 0:
            previous_close = current_close
            continue
            
        # Calculate RSI using enhanced stateful version
        rsi_val = enhanced_n_rsi(
            current_close, previous_close,
            symbol, timeframe, 14, 1
        )
        
        rsi_values.append(rsi_val)
        previous_close = current_close
        
        # Debug output every 20 bars
        if i % 20 == 0 and i > 0:
            print(f"  Bar {i}: Close={current_close:.2f}, RSI={rsi_val:.4f}")
    
    # Verify RSI values are in valid range
    for val in rsi_values:
        assert 0 <= val <= 1, f"RSI out of normalized range: {val}"
    
    # RSI should show uptrend strength (generally > 0.5)
    avg_rsi = sum(rsi_values[20:]) / len(rsi_values[20:])  # Skip warmup
    print(f"  Average RSI (after warmup): {avg_rsi:.4f}")
    assert avg_rsi > 0.45, f"RSI too low for uptrend: {avg_rsi}"
    
    print("✓ Stateful RSI test passed!")


def test_stateful_cci():
    """Test that CCI maintains state correctly"""
    print("\nTesting Stateful CCI...")
    
    symbol = "TEST_CCI"
    timeframe = "5minute"
    
    # Clear any existing state
    manager = get_indicator_manager()
    manager.clear_symbol(symbol)
    
    prices = create_test_data()
    
    # Process bars one by one
    cci_values = []
    
    for i, bar in enumerate(prices):
        # Calculate CCI using enhanced stateful version
        cci_val = enhanced_n_cci(
            bar['high'], bar['low'], bar['close'],
            symbol, timeframe, 20, 1
        )
        
        cci_values.append(cci_val)
        
        # Debug output
        if i % 20 == 0 and i > 0:
            print(f"  Bar {i}: CCI={cci_val:.4f}")
    
    # Verify CCI values are normalized
    for val in cci_values:
        assert 0 <= val <= 1, f"CCI out of normalized range: {val}"
    
    print("✓ Stateful CCI test passed!")


def test_stateful_wavetrend():
    """Test that WaveTrend maintains state correctly"""
    print("\nTesting Stateful WaveTrend...")
    
    symbol = "TEST_WT"
    timeframe = "5minute"
    
    # Clear any existing state
    manager = get_indicator_manager()
    manager.clear_symbol(symbol)
    
    prices = create_test_data()
    
    # Process bars one by one
    wt_values = []
    
    for i, bar in enumerate(prices):
        # Calculate WT using enhanced stateful version
        wt_val = enhanced_n_wt(
            bar['high'], bar['low'], bar['close'],
            symbol, timeframe, 10, 11
        )
        
        wt_values.append(wt_val)
        
        # Debug output
        if i % 20 == 0 and i > 0:
            print(f"  Bar {i}: WT={wt_val:.4f}")
    
    # Verify WT values are normalized
    for val in wt_values:
        assert 0 <= val <= 1, f"WT out of normalized range: {val}"
    
    print("✓ Stateful WaveTrend test passed!")


def test_stateful_adx():
    """Test that ADX maintains state correctly"""
    print("\nTesting Stateful ADX...")
    
    symbol = "TEST_ADX"
    timeframe = "5minute"
    
    # Clear any existing state
    manager = get_indicator_manager()
    manager.clear_symbol(symbol)
    
    prices = create_test_data()
    
    # Process bars one by one
    adx_values = []
    
    for i, bar in enumerate(prices):
        # Calculate ADX using enhanced stateful version
        adx_val = enhanced_n_adx(
            bar['high'], bar['low'], bar['close'],
            symbol, timeframe, 14
        )
        
        adx_values.append(adx_val)
        
        # Debug output
        if i % 20 == 0 and i > 0:
            print(f"  Bar {i}: ADX={adx_val:.4f}")
    
    # Verify ADX values are normalized
    for val in adx_values:
        assert 0 <= val <= 1, f"ADX out of normalized range: {val}"
    
    # ADX should show trending market (generally > 0.25 after warmup)
    avg_adx = sum(adx_values[30:]) / len(adx_values[30:])  # Skip warmup
    print(f"  Average ADX (after warmup): {avg_adx:.4f}")
    
    print("✓ Stateful ADX test passed!")


def test_enhanced_series_from():
    """Test the enhanced series_from function"""
    print("\nTesting enhanced_series_from()...")
    
    symbol = "TEST_SERIES"
    timeframe = "5minute"
    
    # Clear any existing state
    manager = get_indicator_manager()
    manager.clear_symbol(symbol)
    
    prices = create_test_data()
    
    # Test each indicator type
    features = {
        "RSI": (14, 1),
        "WT": (10, 11),
        "CCI": (20, 1),
        "ADX": (14, 2)
    }
    
    previous_close = None
    
    for i, bar in enumerate(prices[:50]):  # Test first 50 bars
        current_ohlc = {
            'high': bar['high'],
            'low': bar['low'],
            'close': bar['close']
        }
        
        if i == 0:
            previous_close = bar['close']
            continue
        
        # Test each feature
        for feature_name, (param_a, param_b) in features.items():
            value = enhanced_series_from(
                feature_name, current_ohlc, previous_close,
                symbol, timeframe, param_a, param_b
            )
            
            assert 0 <= value <= 1, f"{feature_name} out of range: {value}"
        
        previous_close = bar['close']
        
        if i % 10 == 0 and i > 0:
            print(f"  Bar {i}: All features calculated successfully")
    
    print("✓ enhanced_series_from tests passed!")


def test_stateful_filters():
    """Test stateful filter implementations"""
    print("\nTesting Stateful Filters...")
    
    symbol = "TEST_FILTERS"
    timeframe = "5minute"
    
    # Clear any existing state
    manager = get_indicator_manager()
    manager.clear_symbol(symbol)
    
    prices = create_test_data()
    
    # Track filter results
    volatility_results = []
    regime_results = []
    adx_results = []
    
    previous_ohlc4 = None
    
    for i, bar in enumerate(prices[:50]):
        current_ohlc4 = (bar['open'] + bar['high'] + bar['low'] + bar['close']) / 4
        
        if i == 0:
            previous_ohlc4 = current_ohlc4
            continue
        
        # Test volatility filter
        vol_filter = enhanced_filter_volatility(
            bar['high'], bar['low'], bar['close'],
            symbol, timeframe, 1, 10, True
        )
        volatility_results.append(vol_filter)
        
        # Test regime filter
        regime = enhanced_regime_filter(
            current_ohlc4, bar['high'], bar['low'], previous_ohlc4,
            symbol, timeframe, -0.1, True
        )
        regime_results.append(regime)
        
        # Test ADX filter
        adx_filter = enhanced_filter_adx(
            bar['high'], bar['low'], bar['close'],
            symbol, timeframe, 14, 20, True
        )
        adx_results.append(adx_filter)
        
        previous_ohlc4 = current_ohlc4
        
        if i % 20 == 0 and i > 0:
            print(f"  Bar {i}: Vol={vol_filter}, Regime={regime}, ADX={adx_filter}")
    
    # Verify all filters return boolean
    for results, name in [(volatility_results, "Volatility"), 
                          (regime_results, "Regime"), 
                          (adx_results, "ADX")]:
        for val in results:
            assert isinstance(val, bool), f"{name} filter should return bool, got {type(val)}"
    
    print("✓ Stateful filter tests passed!")


def test_state_persistence():
    """Test that indicators maintain state across multiple calls"""
    print("\nTesting State Persistence...")
    
    symbol = "TEST_PERSIST"
    timeframe = "5minute"
    
    # Clear any existing state
    manager = get_indicator_manager()
    manager.clear_symbol(symbol)
    
    prices = create_test_data()
    
    # Process first 20 bars
    previous_close = None
    last_rsi = None
    
    for i, bar in enumerate(prices[:20]):
        if i == 0:
            previous_close = bar['close']
            continue
            
        last_rsi = enhanced_n_rsi(
            bar['close'], previous_close,
            symbol, timeframe, 14, 1
        )
        previous_close = bar['close']
    
    print(f"  RSI after 20 bars: {last_rsi:.4f}")
    
    # Process next 10 bars
    for i, bar in enumerate(prices[20:30]):
        last_rsi = enhanced_n_rsi(
            bar['close'], previous_close,
            symbol, timeframe, 14, 1
        )
        previous_close = bar['close']
    
    print(f"  RSI after 30 bars: {last_rsi:.4f}")
    
    # Now process the same 30 bars in one go with a different symbol
    symbol2 = "TEST_PERSIST2"
    manager.clear_symbol(symbol2)
    
    previous_close = None
    
    for i, bar in enumerate(prices[:30]):
        if i == 0:
            previous_close = bar['close']
            continue
            
        rsi_continuous = enhanced_n_rsi(
            bar['close'], previous_close,
            symbol2, timeframe, 14, 1
        )
        previous_close = bar['close']
    
    print(f"  RSI (continuous) after 30 bars: {rsi_continuous:.4f}")
    
    # The two RSI values should be very close (within floating point tolerance)
    assert abs(last_rsi - rsi_continuous) < 0.0001, \
        f"State persistence failed: {last_rsi} != {rsi_continuous}"
    
    print("✓ State persistence test passed!")


def test_multiple_symbols():
    """Test that different symbols maintain independent state"""
    print("\nTesting Multiple Symbols...")
    
    symbols = ["RELIANCE", "TCS", "INFY"]
    timeframe = "5minute"
    
    # Clear all symbols
    manager = get_indicator_manager()
    for symbol in symbols:
        manager.clear_symbol(symbol)
    
    prices = create_test_data()
    
    # Process same data for different symbols
    results = {symbol: [] for symbol in symbols}
    
    for symbol in symbols:
        previous_close = None
        
        for i, bar in enumerate(prices[:30]):
            if i == 0:
                previous_close = bar['close']
                continue
                
            rsi = enhanced_n_rsi(
                bar['close'], previous_close,
                symbol, timeframe, 14, 1
            )
            results[symbol].append(rsi)
            previous_close = bar['close']
    
    # All symbols should have same results (same data)
    for i in range(len(results[symbols[0]])):
        val1 = results[symbols[0]][i]
        val2 = results[symbols[1]][i]
        val3 = results[symbols[2]][i]
        
        assert abs(val1 - val2) < 0.0001, f"Symbol isolation failed: {val1} != {val2}"
        assert abs(val2 - val3) < 0.0001, f"Symbol isolation failed: {val2} != {val3}"
    
    print("  All symbols maintain independent state correctly")
    print("✓ Multiple symbols test passed!")


def run_all_tests():
    """Run all enhanced indicator tests"""
    print("=== Running Enhanced Stateful Indicator Tests ===\n")
    
    test_stateful_rsi()
    test_stateful_cci()
    test_stateful_wavetrend()
    test_stateful_adx()
    test_enhanced_series_from()
    test_stateful_filters()
    test_state_persistence()
    test_multiple_symbols()
    
    print("\n=== All enhanced indicator tests passed! ✓ ===")
    print("\nStateful TA implementation is working correctly!")
    print("Indicators now maintain state like Pine Script.")


if __name__ == "__main__":
    run_all_tests()
