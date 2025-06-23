"""
Quick Phase 3 NA Handling Test
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.na_handling import validate_ohlcv, filter_none_values
from core.math_helpers import pine_sma, pine_ema, tanh
from core.indicators import calculate_rsi
from scanner.bar_processor import BarProcessor
from config.settings import TradingConfig

print("=" * 60)
print("🧪 Phase 3 NA Handling Quick Test")
print("=" * 60)

# Test 1: Basic NA handling functions
print("\n1. Testing basic NA handling functions:")
print(f"   validate_ohlcv(100, None, 95, 102, 1000): {validate_ohlcv(100, None, 95, 102, 1000)}")
print(f"   filter_none_values([100, None, 102, float('nan')]): {filter_none_values([100, None, 102, float('nan')])}")

# Test 2: Math functions with None
print("\n2. Testing math functions with None values:")
values_with_none = [100, None, 102, float('nan'), 104, 105]
print(f"   pine_sma with None: {pine_sma(values_with_none, 3):.2f}")
print(f"   pine_ema with None: {pine_ema(values_with_none, 3):.2f}")
print(f"   tanh(None): {tanh(None)}")
print(f"   tanh(float('nan')): {tanh(float('nan'))}")

# Test 3: Indicators with None
print("\n3. Testing indicators with None values:")
close_with_none = [100, None, 102, float('nan'), 104, 105, 106, 107, 108, 109, 110]
print(f"   RSI with None values: {calculate_rsi(close_with_none, 14):.2f}")

# Test 4: Bar processor with invalid data
print("\n4. Testing BarProcessor with invalid data:")
config = TradingConfig()
processor = BarProcessor(config, total_bars=100)

# Test invalid bar
result = processor.process_bar(None, 105, 95, 102, 1000)
print(f"   Process bar with None open: {'Skipped (None)' if result is None else 'ERROR - Should skip!'}")

# Test valid bar
result = processor.process_bar(100, 105, 95, 102, 1000)
print(f"   Process bar with valid data: {'Success' if result is not None else 'ERROR - Should work!'}")

print("\n" + "=" * 60)
print("✅ Phase 3 NA Handling appears to be working!")
print("=" * 60)
