"""
Debug script to find kernel stuck issue
"""
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
problem_start = 235  # Around bar 240

print("1. CSV Data Around Problem Time:")
print("Bar# | Time  | Close  | CSV Kernel    | Note")
print("-----|-------|--------|---------------|-----")
for i in range(problem_start, min(problem_start + 20, len(csv_data))):
    row = csv_data[i]
    time = row['time'].split('T')[1][:5]
    close = float(row['close'])
    kernel = float(row['Kernel Regression Estimate'])
    note = "STUCK" if abs(kernel - 1418.01) < 0.1 else ""
    print(f"{i:4} | {time} | {close:6.1f} | {kernel:7.2f} | {note}")

# Test with full bar processor
print("\n2. Testing Full Processing Pipeline:")

config = TradingConfig()
processor = BarProcessor(config)

# Process all bars up to problem area
print("Processing bars...")
for i in range(min(250, len(csv_data))):
    row = csv_data[i]
    result = processor.process_bar(
        float(row['open']),
        float(row['high']),
        float(row['low']),
        float(row['close']),
        0  # volume
    )
    
    # Check around problem area
    if i >= problem_start and i < problem_start + 10:
        # Get kernel estimate
        source_values = []
        for j in range(len(processor.bars)):
            source_values.append(processor.bars.get_close(j))
        
        if len(source_values) > 0:
            kernel_est = rational_quadratic(source_values, 8, 8.0, 25)
            print(f"  Bar {i}: Close={float(row['close']):.1f}, "
                  f"Kernel={kernel_est:.2f}, "
                  f"CSV Kernel={float(row['Kernel Regression Estimate']):.2f}")

# Check source values length
print(f"\n3. Data Structure Check:")
print(f"Total bars processed: {len(processor.bars)}")
print(f"Feature arrays length: {len(processor.feature_arrays.f1)}")
print(f"Max bars back: {config.max_bars_back}")

# Test kernel with different data lengths
print("\n4. Testing Kernel with Different Data Sizes:")
test_sizes = [50, 100, 200, 250]
for size in test_sizes:
    if size <= len(csv_data):
        prices = [float(csv_data[i]['close']) for i in range(size)]
        prices.reverse()  # Newest first
        kernel = rational_quadratic(prices, 8, 8.0, 25)
        print(f"  {size} bars: Kernel = {kernel:.2f}")

print("\n=== Debug Complete ===")
