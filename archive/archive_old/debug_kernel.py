#!/usr/bin/env python3
"""Debug kernel calculation issue"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.kernel_functions import rational_quadratic
from data.bar_data import BarData
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
import csv

print("=== Kernel Debug Analysis ===\n")

# Load CSV data
csv_file = "NSE_ICICIBANK, 5.csv"
with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    csv_data = list(reader)

# Focus on problem area (June 19, 6:40-7:00)
problem_start = 240  # Approximate bar number

print("1. CSV Data Around Problem Time:")
print("Bar# | Time  | Close  | CSV Kernel")
print("-----|-------|--------|------------")
for i in range(235, 255):
    if i < len(csv_data):
        row = csv_data[i]
        time = row['time'].split('T')[1][:5]
        print(f"{i:4} | {time} | {float(row['close']):6.1f} | {float(row['Kernel Regression Estimate']):7.2f}")

# Test kernel calculation directly
print("\n2. Testing Kernel Calculation Directly:")

# Create test data (simple prices)
test_prices = [1406.2, 1406.2, 1407.3, 1407.6, 1408.7]  # June 19 prices
test_prices.reverse()  # Newest first for kernel function

kernel_result = rational_quadratic(test_prices, 8, 8.0, 25)
print(f"Direct kernel calc with June 19 prices: ₹{kernel_result:.2f}")

# Test with June 16 prices
june16_prices = [1418.1, 1418.5, 1416.9, 1418.4, 1420.5]
june16_prices.reverse()

kernel_result2 = rational_quadratic(june16_prices, 8, 8.0, 25)
print(f"Direct kernel calc with June 16 prices: ₹{kernel_result2:.2f}")

# Test bar processor
print("\n3. Testing Bar Processor Data Flow:")

config = TradingConfig()
processor = BarProcessor(config)

# Add some bars
for i in range(10):
    price = 1406.0 + i * 0.5
    processor.process_bar(price, price+1, price-1, price, 100)

# Check what source values the processor has
print(f"Bars in processor: {len(processor.bars)}")
print(f"Last 5 closes: {[processor.bars.get_close(i) for i in range(min(5, len(processor.bars)))]}") 

# Check if source values are being built correctly
source_values = []
for i in range(len(processor.bars)):
    if config.source == 'close':
        source_values.append(processor.bars.get_close(i))

print(f"Source values for kernel: {source_values[:5]}")

print("\n=== Debug Complete ===")
