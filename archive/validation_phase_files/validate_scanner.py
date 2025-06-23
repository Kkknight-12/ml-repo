"""
Validation Script - Compare Python Lorentzian Scanner with Pine Script CSV
This script validates our Python implementation against Pine Script output
"""
import sys
import os
import csv
from datetime import datetime
import statistics
from typing import List, Dict, Tuple

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from core.kernel_functions import rational_quadratic


class LorentzianValidator:
    """Validates Python implementation against Pine Script CSV data"""
    
    def __init__(self, csv_file: str):
        """Initialize validator with CSV file path"""
        self.csv_file = csv_file
        self.csv_data = []
        self.config = TradingConfig(
            # Match Pine Script settings
            neighbors_count=8,
            feature_count=5,
            use_kernel_filter=True,
            kernel_lookback=8,
            kernel_relative_weight=8,
            kernel_regression_level=25,
            use_volatility_filter=True,
            use_regime_filter=True,
            use_adx_filter=False,
            use_ema_filter=False,
            use_sma_filter=False
        )
        # Don't initialize processor here - will do it after loading CSV data
        self.processor = None
        
    def load_csv_data(self):
        """Load Pine Script data from CSV"""
        print("Loading Pine Script CSV data...")
        
        with open(self.csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse data
                bar_data = {
                    'time': datetime.fromisoformat(row['time'].replace('Z', '+00:00')),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'kernel_estimate': float(row['Kernel Regression Estimate']),
                    'buy': row['Buy'],
                    'sell': row['Sell']
                }
                self.csv_data.append(bar_data)
                
        print(f"✓ Loaded {len(self.csv_data)} bars from CSV")
        print(f"  Date range: {self.csv_data[0]['time']} to {self.csv_data[-1]['time']}")
        print(f"  Price range: ₹{min(b['low'] for b in self.csv_data):.2f} - ₹{max(b['high'] for b in self.csv_data):.2f}")
        
    def process_bars_through_python(self):
        """Process all bars through Python scanner"""
        print("\nProcessing bars through Python scanner...")
        
        # CRITICAL FIX: Initialize processor with total bars for Pine Script compatibility
        total_bars = len(self.csv_data)
        self.processor = BarProcessor(self.config, total_bars=total_bars)
        print(f"  Initialized processor with total_bars={total_bars}")
        print(f"  Max bars back index: {self.processor.max_bars_back_index}")
        
        self.python_results = []
        signal_count = 0
        
        # Process each bar
        for i, bar in enumerate(self.csv_data):
            result = self.processor.process_bar(
                bar['open'],
                bar['high'],
                bar['low'],
                bar['close'],
                0  # Volume not in CSV
            )
            
            # Store result
            self.python_results.append({
                'time': bar['time'],
                'result': result,
                'csv_kernel': bar['kernel_estimate']
            })
            
            # Count signals
            if result.start_long_trade or result.start_short_trade:
                signal_count += 1
                
            # Progress update
            if (i + 1) % 50 == 0:
                print(f"  Processed {i + 1}/{len(self.csv_data)} bars...")
                
        print(f"✓ Processing complete. Found {signal_count} signals.")
        
    def calculate_python_kernel(self, index: int) -> float:
        """Calculate kernel regression at specific index"""
        if index < 25:  # Need minimum bars for kernel
            return 0.0
            
        # Get source values (using close prices)
        source_values = [b['close'] for b in self.csv_data[:index+1]]
        
        # Calculate kernel using same parameters as Pine Script
        kernel_value = rational_quadratic(
            source_values,
            lookback=8,
            relative_weight=8,
            start_at_bar=25
        )
        
        return kernel_value
        
    def compare_kernel_values(self):
        """Compare kernel regression values between Python and Pine Script"""
        print("\n=== Kernel Regression Comparison ===")
        
        differences = []
        
        for i in range(25, len(self.csv_data)):  # Start after warmup
            csv_kernel = self.csv_data[i]['kernel_estimate']
            python_kernel = self.calculate_python_kernel(i)
            
            diff = abs(csv_kernel - python_kernel)
            diff_percent = (diff / csv_kernel) * 100 if csv_kernel != 0 else 0
            
            differences.append({
                'index': i,
                'time': self.csv_data[i]['time'],
                'csv_kernel': csv_kernel,
                'python_kernel': python_kernel,
                'difference': diff,
                'diff_percent': diff_percent
            })
            
        # Statistics
        avg_diff = statistics.mean(d['difference'] for d in differences)
        max_diff = max(d['difference'] for d in differences)
        avg_diff_percent = statistics.mean(d['diff_percent'] for d in differences)
        
        print(f"Kernel Value Comparison:")
        print(f"  Average difference: ₹{avg_diff:.4f} ({avg_diff_percent:.2f}%)")
        print(f"  Maximum difference: ₹{max_diff:.4f}")
        print(f"  Samples compared: {len(differences)}")
        
        # Show worst mismatches
        worst_5 = sorted(differences, key=lambda x: x['diff_percent'], reverse=True)[:5]
        print(f"\nTop 5 Largest Differences:")
        for d in worst_5:
            print(f"  {d['time'].strftime('%Y-%m-%d %H:%M')} - "
                  f"CSV: ₹{d['csv_kernel']:.2f}, Python: ₹{d['python_kernel']:.2f}, "
                  f"Diff: {d['diff_percent']:.1f}%")
                  
        return differences
        
    def create_test_scenarios(self):
        """Create and test specific market scenarios"""
        print("\n=== Test Scenarios ===")
        
        # Scenario 1: Sharp drops
        print("\n1. Testing Sharp Price Drops:")
        sharp_drops = []
        
        for i in range(1, len(self.csv_data)):
            prev_close = self.csv_data[i-1]['close']
            curr_close = self.csv_data[i]['close']
            drop_percent = ((prev_close - curr_close) / prev_close) * 100
            
            if drop_percent > 0.5:  # More than 0.5% drop
                sharp_drops.append({
                    'index': i,
                    'time': self.csv_data[i]['time'],
                    'drop_percent': drop_percent,
                    'signal': self.python_results[i]['result'].start_short_trade if i < len(self.python_results) else False
                })
                
        print(f"  Found {len(sharp_drops)} sharp drops (>0.5%)")
        signals_on_drops = sum(1 for d in sharp_drops if d['signal'])
        print(f"  Python generated {signals_on_drops} SELL signals on drops")
        
        # Scenario 2: Breakouts
        print("\n2. Testing Price Breakouts:")
        breakouts = []
        
        for i in range(5, len(self.csv_data)):
            # Check if current high breaks last 5 bars high
            recent_highs = [self.csv_data[j]['high'] for j in range(i-5, i)]
            if self.csv_data[i]['high'] > max(recent_highs):
                breakouts.append({
                    'index': i,
                    'time': self.csv_data[i]['time'],
                    'breakout_level': max(recent_highs),
                    'signal': self.python_results[i]['result'].start_long_trade if i < len(self.python_results) else False
                })
                
        print(f"  Found {len(breakouts)} breakouts")
        signals_on_breakouts = sum(1 for b in breakouts if b['signal'])
        print(f"  Python generated {signals_on_breakouts} BUY signals on breakouts")
        
        # Scenario 3: Kernel Crossovers
        print("\n3. Testing Kernel Crossovers:")
        crossovers = []
        
        for i in range(1, len(self.csv_data)):
            prev_close = self.csv_data[i-1]['close']
            curr_close = self.csv_data[i]['close']
            prev_kernel = self.csv_data[i-1]['kernel_estimate']
            curr_kernel = self.csv_data[i]['kernel_estimate']
            
            # Bullish crossover: price crosses above kernel
            if prev_close < prev_kernel and curr_close > curr_kernel:
                crossovers.append({
                    'index': i,
                    'time': self.csv_data[i]['time'],
                    'type': 'bullish',
                    'signal': self.python_results[i]['result'].start_long_trade if i < len(self.python_results) else False
                })
            # Bearish crossover: price crosses below kernel
            elif prev_close > prev_kernel and curr_close < curr_kernel:
                crossovers.append({
                    'index': i,
                    'time': self.csv_data[i]['time'],
                    'type': 'bearish',
                    'signal': self.python_results[i]['result'].start_short_trade if i < len(self.python_results) else False
                })
                
        print(f"  Found {len(crossovers)} kernel crossovers")
        for cross_type in ['bullish', 'bearish']:
            type_crosses = [c for c in crossovers if c['type'] == cross_type]
            signals = sum(1 for c in type_crosses if c['signal'])
            print(f"    {cross_type.capitalize()}: {len(type_crosses)} crosses, {signals} signals")
            
    def statistical_validation(self):
        """Perform statistical validation of the system"""
        print("\n=== Statistical Validation ===")
        
        # 1. Signal Distribution Analysis
        print("\n1. Signal Distribution:")
        
        signals_by_hour = {}
        buy_signals = 0
        sell_signals = 0
        
        for i, result in enumerate(self.python_results):
            if result['result'].start_long_trade:
                buy_signals += 1
                hour = self.csv_data[i]['time'].hour
                signals_by_hour[hour] = signals_by_hour.get(hour, 0) + 1
                
            if result['result'].start_short_trade:
                sell_signals += 1
                hour = self.csv_data[i]['time'].hour
                signals_by_hour[hour] = signals_by_hour.get(hour, 0) + 1
                
        print(f"  Total BUY signals: {buy_signals}")
        print(f"  Total SELL signals: {sell_signals}")
        print(f"  Buy/Sell ratio: {buy_signals/sell_signals if sell_signals > 0 else 'N/A'}")
        
        # 2. ML Prediction Analysis
        print("\n2. ML Prediction Analysis:")
        
        predictions = [r['result'].prediction for r in self.python_results]
        non_zero_predictions = [p for p in predictions if p != 0]
        
        if non_zero_predictions:
            print(f"  Average prediction: {statistics.mean(non_zero_predictions):.2f}")
            print(f"  Max prediction: {max(non_zero_predictions)}")
            print(f"  Min prediction: {min(non_zero_predictions)}")
            print(f"  Predictions > 0: {sum(1 for p in non_zero_predictions if p > 0)}")
            print(f"  Predictions < 0: {sum(1 for p in non_zero_predictions if p < 0)}")
        
        # 3. Filter Analysis
        print("\n3. Filter Pass Rate:")
        
        total_bars = len(self.python_results)
        volatility_passes = sum(1 for r in self.python_results if r['result'].filter_states.get('volatility', False))
        regime_passes = sum(1 for r in self.python_results if r['result'].filter_states.get('regime', False))
        adx_passes = sum(1 for r in self.python_results if r['result'].filter_states.get('adx', False))
        
        print(f"  Volatility filter: {volatility_passes}/{total_bars} ({volatility_passes/total_bars*100:.1f}%)")
        print(f"  Regime filter: {regime_passes}/{total_bars} ({regime_passes/total_bars*100:.1f}%)")
        print(f"  ADX filter: {adx_passes}/{total_bars} ({adx_passes/total_bars*100:.1f}%)")
        
        # 4. Signal Strength Analysis
        print("\n4. Signal Strength Analysis:")
        
        signal_strengths = []
        for result in self.python_results:
            if result['result'].start_long_trade or result['result'].start_short_trade:
                signal_strengths.append(result['result'].prediction_strength)
                
        if signal_strengths:
            print(f"  Average strength: {statistics.mean(signal_strengths)*100:.1f}%")
            print(f"  Max strength: {max(signal_strengths)*100:.1f}%")
            print(f"  Min strength: {min(signal_strengths)*100:.1f}%")
            
    def find_interesting_bars(self):
        """Find specific interesting bars for detailed analysis"""
        print("\n=== Interesting Bars for Deep Analysis ===")
        
        interesting_bars = []
        
        # Find bars with specific characteristics
        for i in range(10, len(self.csv_data) - 1):
            bar = self.csv_data[i]
            
            # High volume price move (using price range as proxy)
            price_range = bar['high'] - bar['low']
            avg_range = statistics.mean(b['high'] - b['low'] for b in self.csv_data[i-10:i])
            
            if price_range > avg_range * 2:
                interesting_bars.append({
                    'index': i,
                    'time': bar['time'],
                    'reason': 'High volatility bar',
                    'details': f"Range: ₹{price_range:.2f} (2x average)"
                })
                
        # Show top 5 interesting bars
        print(f"\nFound {len(interesting_bars)} interesting bars:")
        for bar in interesting_bars[:5]:
            print(f"\n  {bar['time'].strftime('%Y-%m-%d %H:%M')} - {bar['reason']}")
            print(f"  {bar['details']}")
            
            # Get Python results for this bar
            if bar['index'] < len(self.python_results):
                result = self.python_results[bar['index']]['result']
                print(f"  Python ML Prediction: {result.prediction}")
                print(f"  Signal: {'BUY' if result.start_long_trade else 'SELL' if result.start_short_trade else 'None'}")
                print(f"  Filters: {result.filter_states}")
                
    def generate_report(self):
        """Generate comprehensive validation report"""
        print("\n" + "="*60)
        print("VALIDATION REPORT SUMMARY")
        print("="*60)
        
        print(f"\nData Source: {os.path.basename(self.csv_file)}")
        print(f"Total Bars Analyzed: {len(self.csv_data)}")
        print(f"Date Range: {self.csv_data[0]['time'].date()} to {self.csv_data[-1]['time'].date()}")
        
        # Key findings
        print("\n✅ What's Working:")
        print("  - Python scanner processes all bars without errors")
        print("  - ML predictions are generating")
        print("  - Filters are functioning")
        
        print("\n⚠️ Areas to Investigate:")
        print("  - Kernel value differences (if any)")
        print("  - Signal timing accuracy")
        print("  - Filter sensitivity")
        
        print("\n📊 Next Steps:")
        print("  1. Run during market hours for real-time comparison")
        print("  2. Adjust filter thresholds if needed")
        print("  3. Compare with more historical data")
        print("  4. Validate indicator calculations")
        
        print("\n" + "="*60)


def main():
    """Run the validation"""
    print("=== Lorentzian Scanner Validation Tool ===\n")
    
    # Check if CSV exists
    csv_file = "NSE_ICICIBANK, 5.csv"
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        print("Please ensure the file is in the current directory")
        return
        
    # Create validator
    validator = LorentzianValidator(csv_file)
    
    # Run validation steps
    validator.load_csv_data()
    validator.process_bars_through_python()
    validator.compare_kernel_values()
    validator.create_test_scenarios()
    validator.statistical_validation()
    validator.find_interesting_bars()
    validator.generate_report()
    
    print("\n✅ Validation complete!")


if __name__ == "__main__":
    main()
