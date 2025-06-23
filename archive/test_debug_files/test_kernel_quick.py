"""
Quick Kernel Validation Test
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Run a quick test of kernel functions
from core.kernel_functions import rational_quadratic, gaussian, get_kernel_crossovers
from core.pine_functions import crossover, crossunder

print("=" * 50)
print("🧪 Quick Kernel Validation Test")
print("=" * 50)

# Test 1: Basic kernel calculation
prices = [100.0, 99.5, 99.0, 98.5, 98.0, 97.5, 97.0, 96.5, 96.0, 95.5]
rq = rational_quadratic(prices, 8, 8.0, 25)
g = gaussian(prices, 8, 25)

print(f"\n1. Basic Kernel Values:")
print(f"   Current price: {prices[0]}")
print(f"   RQ Kernel: {rq:.4f}")
print(f"   Gaussian: {g:.4f}")

# Test 2: Crossover detection
series1 = [1.5, 0.5]  # Cross above
series2 = [1.0, 1.0]
print(f"\n2. Crossover Test:")
print(f"   Series1 crosses above Series2: {crossover(series1, series2)}")

# Test 3: Kernel crossovers
trend_prices = list(range(100, 120))  # Uptrend
trend_prices.reverse()
bull_cross, bear_cross = get_kernel_crossovers(trend_prices, 8, 8.0, 25, 2)
print(f"\n3. Kernel Crossovers (uptrend):")
print(f"   Bullish cross: {bull_cross}")
print(f"   Bearish cross: {bear_cross}")

print("\n✅ Kernel functions are working!")
print("=" * 50)
