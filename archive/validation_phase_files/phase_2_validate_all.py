"""
Phase 2: Comprehensive Multi-Stock Validation
Tests all available CSV files and generates comparison report
"""
import sys
import os
import csv
from datetime import datetime
import statistics
from typing import List, Dict, Tuple
import json

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from core.kernel_functions import rational_quadratic


class MultiStockValidator:
    """Validates multiple stocks and generates comprehensive report"""
    
    def __init__(self):
        """Initialize multi-stock validator"""
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
        
        # Results storage
        self.results = {}
        
    def find_csv_files(self) -> List[str]:
        """Find all CSV files in current directory"""
        csv_files = []
        for file in os.listdir('.'):
            if file.endswith('.csv') and file.startswith('NSE_'):
                csv_files.append(file)
        return sorted(csv_files)
        
    def validate_single_stock(self, csv_file: str) -> Dict:
        """Validate a single stock CSV file"""
        print(f"\n{'='*60}")
        print(f"Validating: {csv_file}")
        print('='*60)
        
        result = {
            'file': csv_file,
            'bars_count': 0,
            'date_range': '',
            'price_range': '',
            'signals': {'total': 0, 'buy': 0, 'sell': 0},
            'predictions': {'positive': 0, 'negative': 0, 'zero': 0, 'avg': 0},
            'filters': {'volatility': 0, 'regime': 0, 'adx': 0},
            'kernel_accuracy': 0,
            'ml_start_bar': None,
            'errors': []
        }
        
        try:
            # Load CSV data
            csv_data = []
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bar_data = {
                        'time': datetime.fromisoformat(row['time'].replace('Z', '+00:00')),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'kernel_estimate': float(row.get('Kernel Regression Estimate', 0)),
                        'buy': row.get('Buy', ''),
                        'sell': row.get('Sell', '')
                    }
                    csv_data.append(bar_data)
            
            result['bars_count'] = len(csv_data)
            
            if csv_data:
                result['date_range'] = f"{csv_data[0]['time'].date()} to {csv_data[-1]['time'].date()}"
                result['price_range'] = f"₹{min(b['low'] for b in csv_data):.2f} - ₹{max(b['high'] for b in csv_data):.2f}"
                
                print(f"✓ Loaded {len(csv_data)} bars")
                print(f"  Date range: {result['date_range']}")
                print(f"  Price range: {result['price_range']}")
                
                # Process through Python scanner
                total_bars = len(csv_data)
                processor = BarProcessor(self.config, total_bars=total_bars)
                
                print(f"\nProcessing bars...")
                print(f"  Max bars back index: {processor.max_bars_back_index}")
                
                # Track when ML starts
                ml_started = False
                predictions = []
                
                for i, bar in enumerate(csv_data):
                    bar_result = processor.process_bar(
                        bar['open'],
                        bar['high'],
                        bar['low'],
                        bar['close'],
                        0  # Volume not in CSV
                    )
                    
                    # Track ML start
                    if not ml_started and bar_result.prediction != 0:
                        ml_started = True
                        result['ml_start_bar'] = i
                        print(f"  ML started at bar {i}")
                    
                    # Count signals
                    if bar_result.start_long_trade:
                        result['signals']['buy'] += 1
                        result['signals']['total'] += 1
                    if bar_result.start_short_trade:
                        result['signals']['sell'] += 1
                        result['signals']['total'] += 1
                    
                    # Track predictions
                    if bar_result.prediction != 0:
                        predictions.append(bar_result.prediction)
                        if bar_result.prediction > 0:
                            result['predictions']['positive'] += 1
                        else:
                            result['predictions']['negative'] += 1
                    else:
                        result['predictions']['zero'] += 1
                    
                    # Track filters
                    if bar_result.filter_states.get('volatility', False):
                        result['filters']['volatility'] += 1
                    if bar_result.filter_states.get('regime', False):
                        result['filters']['regime'] += 1
                    if bar_result.filter_states.get('adx', False):
                        result['filters']['adx'] += 1
                    
                    # Progress
                    if (i + 1) % 100 == 0:
                        print(f"  Processed {i + 1}/{total_bars} bars...")
                
                # Calculate averages
                if predictions:
                    result['predictions']['avg'] = statistics.mean(predictions)
                
                # Calculate filter pass rates
                result['filters']['volatility'] = (result['filters']['volatility'] / total_bars) * 100
                result['filters']['regime'] = (result['filters']['regime'] / total_bars) * 100
                result['filters']['adx'] = (result['filters']['adx'] / total_bars) * 100
                
                print(f"\n✓ Processing complete!")
                print(f"  Signals: {result['signals']['total']} (Buy: {result['signals']['buy']}, Sell: {result['signals']['sell']})")
                
        except Exception as e:
            result['errors'].append(str(e))
            print(f"❌ Error: {str(e)}")
            
        return result
    
    def validate_all_stocks(self):
        """Validate all available stock CSV files"""
        csv_files = self.find_csv_files()
        
        print(f"\n=== Phase 2: Multi-Stock Validation ===")
        print(f"Found {len(csv_files)} CSV files to validate\n")
        
        for csv_file in csv_files:
            result = self.validate_single_stock(csv_file)
            stock_symbol = csv_file.split(',')[0].replace('NSE_', '')
            self.results[stock_symbol] = result
            
    def generate_comparison_matrix(self):
        """Generate comparison matrix of all stocks"""
        print("\n\n=== COMPARISON MATRIX ===")
        print("-" * 100)
        print(f"{'Stock':<10} {'Bars':<8} {'Signals':<12} {'Buy/Sell':<10} {'Avg Pred':<10} {'Vol%':<8} {'Regime%':<8} {'ML Start':<10}")
        print("-" * 100)
        
        for stock, data in self.results.items():
            signals = f"{data['signals']['total']}"
            buy_sell = f"{data['signals']['buy']}/{data['signals']['sell']}"
            avg_pred = f"{data['predictions']['avg']:.2f}" if data['predictions']['avg'] else "N/A"
            vol_pct = f"{data['filters']['volatility']:.1f}%"
            regime_pct = f"{data['filters']['regime']:.1f}%"
            ml_start = str(data['ml_start_bar']) if data['ml_start_bar'] is not None else "N/A"
            
            print(f"{stock:<10} {data['bars_count']:<8} {signals:<12} {buy_sell:<10} {avg_pred:<10} {vol_pct:<8} {regime_pct:<8} {ml_start:<10}")
        
        print("-" * 100)
        
    def generate_summary_report(self):
        """Generate summary statistics across all stocks"""
        print("\n\n=== SUMMARY STATISTICS ===")
        
        # Aggregate statistics
        total_bars = sum(r['bars_count'] for r in self.results.values())
        total_signals = sum(r['signals']['total'] for r in self.results.values())
        total_buy = sum(r['signals']['buy'] for r in self.results.values())
        total_sell = sum(r['signals']['sell'] for r in self.results.values())
        
        print(f"\nTotal bars processed: {total_bars}")
        print(f"Total signals generated: {total_signals}")
        print(f"  Buy signals: {total_buy}")
        print(f"  Sell signals: {total_sell}")
        print(f"  Buy/Sell ratio: {total_buy/total_sell:.2f}" if total_sell > 0 else "  Buy/Sell ratio: N/A")
        
        # Average filter performance
        avg_vol = statistics.mean(r['filters']['volatility'] for r in self.results.values())
        avg_regime = statistics.mean(r['filters']['regime'] for r in self.results.values())
        
        print(f"\nAverage filter pass rates:")
        print(f"  Volatility: {avg_vol:.1f}%")
        print(f"  Regime: {avg_regime:.1f}%")
        
        # Signal distribution
        print(f"\nSignal frequency:")
        for stock, data in self.results.items():
            if data['bars_count'] > 0:
                signal_freq = (data['signals']['total'] / data['bars_count']) * 100
                print(f"  {stock}: {signal_freq:.1f}% of bars have signals")
                
    def identify_issues(self):
        """Identify potential issues across stocks"""
        print("\n\n=== POTENTIAL ISSUES ===")
        
        issues_found = False
        
        for stock, data in self.results.items():
            issues = []
            
            # Check for errors
            if data['errors']:
                issues.append(f"Errors: {', '.join(data['errors'])}")
            
            # Check for no signals
            if data['signals']['total'] == 0 and data['bars_count'] > 50:
                issues.append("No signals generated")
            
            # Check for unbalanced signals
            if data['signals']['total'] > 0:
                if data['signals']['buy'] == 0:
                    issues.append("No buy signals")
                elif data['signals']['sell'] == 0:
                    issues.append("No sell signals")
                elif data['signals']['buy'] / data['signals']['sell'] > 5 or data['signals']['sell'] / data['signals']['buy'] > 5:
                    issues.append("Highly unbalanced buy/sell ratio")
            
            # Check for too many signals
            if data['bars_count'] > 0:
                signal_freq = (data['signals']['total'] / data['bars_count']) * 100
                if signal_freq > 10:
                    issues.append(f"Too many signals ({signal_freq:.1f}% of bars)")
            
            # Check filter performance
            if data['filters']['volatility'] < 10:
                issues.append("Very low volatility filter pass rate")
            if data['filters']['regime'] < 20:
                issues.append("Very low regime filter pass rate")
            
            if issues:
                issues_found = True
                print(f"\n{stock}:")
                for issue in issues:
                    print(f"  ⚠️ {issue}")
        
        if not issues_found:
            print("\n✅ No major issues identified!")
            
    def save_results(self):
        """Save results to files"""
        # Save detailed results as JSON
        with open('phase_2_validation_results.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print("\n✓ Saved detailed results to phase_2_validation_results.json")
        
        # Save summary as markdown
        with open('PHASE_2_VALIDATION_REPORT.md', 'w') as f:
            f.write("# Phase 2: Validation Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary\n\n")
            total_bars = sum(r['bars_count'] for r in self.results.values())
            total_signals = sum(r['signals']['total'] for r in self.results.values())
            f.write(f"- Stocks tested: {len(self.results)}\n")
            f.write(f"- Total bars: {total_bars}\n")
            f.write(f"- Total signals: {total_signals}\n\n")
            
            f.write("## Results by Stock\n\n")
            for stock, data in self.results.items():
                f.write(f"### {stock}\n")
                f.write(f"- Bars: {data['bars_count']}\n")
                f.write(f"- Signals: {data['signals']['total']} (Buy: {data['signals']['buy']}, Sell: {data['signals']['sell']})\n")
                f.write(f"- ML Start Bar: {data['ml_start_bar']}\n")
                f.write(f"- Avg Prediction: {data['predictions']['avg']:.2f}\n" if data['predictions']['avg'] else "- Avg Prediction: N/A\n")
                f.write("\n")
                
        print("✓ Saved summary report to PHASE_2_VALIDATION_REPORT.md")


def main():
    """Run Phase 2 validation"""
    validator = MultiStockValidator()
    
    # Run validation
    validator.validate_all_stocks()
    
    # Generate reports
    validator.generate_comparison_matrix()
    validator.generate_summary_report()
    validator.identify_issues()
    
    # Save results
    validator.save_results()
    
    print("\n\n✅ Phase 2 Validation Complete!")
    print("\nNext steps:")
    print("1. Review PHASE_2_VALIDATION_REPORT.md")
    print("2. Check phase_2_validation_results.json for detailed data")
    print("3. Address any identified issues in Phase 3/4")


if __name__ == "__main__":
    main()
