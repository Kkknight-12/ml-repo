"""
Realistic Comparison with 300 Bars of Data
Adjusts settings to work with limited data
"""
import os
import sys
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from core.kernel_functions import calculate_kernel_values


def compare_with_realistic_settings():
    """
    Compare using settings that work with 300 bars
    """
    print("=" * 60)
    print("🎯 REALISTIC COMPARISON WITH 300 BARS")
    print("=" * 60)
    
    # Load your data
    filename = "NSE_ICICIBANK, 1D.csv"
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        return
    
    data = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'date': row.get('Date', ''),
                'open': float(row.get('Open', 0)),
                'high': float(row.get('High', 0)),
                'low': float(row.get('Low', 0)),
                'close': float(row.get('Close', 0)),
                'volume': float(row.get('Volume', 0))
            })
    
    print(f"✅ Loaded {len(data)} bars")
    
    # IMPORTANT: Use max_bars_back that makes sense for your data
    print("\n📊 Testing with different max_bars_back values:")
    print("-" * 60)
    
    test_configs = [
        (50, "Quick Test (ML starts at bar 50)"),
        (100, "Medium Test (ML starts at bar 100)"),
        (200, "Conservative (ML starts at bar 200)"),
        (250, "Very Conservative (ML starts at bar 250)"),
    ]
    
    for max_bars_back, description in test_configs:
        print(f"\n🔧 {description}")
        print(f"   max_bars_back = {max_bars_back}")
        
        # Configure with realistic settings
        config = TradingConfig(
            # ADJUSTED FOR 300 BARS
            max_bars_back=max_bars_back,
            neighbors_count=8,
            feature_count=5,
            
            # Match TradingView settings
            use_volatility_filter=True,
            use_regime_filter=True,
            use_adx_filter=False,
            
            # Kernel settings
            use_kernel_filter=True,
            kernel_lookback=8,
            kernel_relative_weight=8.0,
            kernel_regression_level=25,
            use_kernel_smoothing=True,
            kernel_lag=2,
            
            # Features
            features={
                "f1": ("RSI", 14, 1),
                "f2": ("WT", 10, 11),
                "f3": ("CCI", 20, 1),
                "f4": ("ADX", 20, 2),
                "f5": ("RSI", 9, 1)
            }
        )
        
        # Process with correct total_bars
        processor = BarProcessor(config, total_bars=len(data))
        
        print(f"   ML will start at bar: {processor.max_bars_back_index}")
        print(f"   Bars available for ML: {len(data) - processor.max_bars_back_index}")
        
        # Track signals
        signals = []
        kernel_values = []
        
        # Process all bars
        for i, bar in enumerate(data):
            result = processor.process_bar(
                bar['open'], bar['high'], bar['low'], 
                bar['close'], bar['volume']
            )
            
            if result:
                # Only track after ML starts
                if i >= processor.max_bars_back_index:
                    # Track signals
                    if result.start_long_trade or result.start_short_trade:
                        signals.append({
                            'bar': i,
                            'date': bar['date'],
                            'type': 'BUY' if result.start_long_trade else 'SELL',
                            'price': bar['close'],
                            'prediction': result.prediction
                        })
                    
                    # Track kernel values every 10 bars
                    if i % 10 == 0:
                        source_values = processor.close_values[:min(100, len(processor.close_values))]
                        if len(source_values) >= config.kernel_lookback:
                            yhat1, _, yhat2, _ = calculate_kernel_values(
                                source_values,
                                config.kernel_lookback,
                                config.kernel_relative_weight,
                                config.kernel_regression_level,
                                config.kernel_lag
                            )
                            kernel_values.append({
                                'bar': i,
                                'date': bar['date'],
                                'rq': yhat1,
                                'gauss': yhat2
                            })
        
        print(f"   Total signals: {len(signals)}")
        if signals:
            print("   First 3 signals:")
            for sig in signals[:3]:
                print(f"     Bar {sig['bar']}: {sig['type']} @ {sig['price']:.2f}")
    
    print("\n" + "=" * 60)
    print("💡 RECOMMENDATIONS FOR TRADINGVIEW COMPARISON:")
    print("=" * 60)
    print("\n1. In TradingView, set Max Bars Back = 50 or 100")
    print("   (Not 2000 - you don't have enough data!)")
    print("\n2. Compare these specific items:")
    print("   - First ML prediction bar number")
    print("   - Kernel line values on specific dates")
    print("   - Signal dates (may differ by ±1 bar)")
    print("\n3. Expected differences:")
    print("   - Small kernel value differences (±0.02)")
    print("   - Signal timing ±1 bar")
    print("   - Filter states might differ slightly")


def create_detailed_comparison_file():
    """Create a comparison file with realistic settings"""
    print("\n📄 Creating detailed comparison file...")
    
    # Load data
    filename = "NSE_ICICIBANK, 1D.csv"
    data = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'date': row.get('Date', ''),
                'open': float(row.get('Open', 0)),
                'high': float(row.get('High', 0)),
                'low': float(row.get('Low', 0)),
                'close': float(row.get('Close', 0)),
                'volume': float(row.get('Volume', 0))
            })
    
    # Use max_bars_back=50 for testing
    config = TradingConfig(
        max_bars_back=50,  # Realistic for 300 bars
        neighbors_count=8,
        feature_count=5,
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        use_kernel_filter=True
    )
    
    processor = BarProcessor(config, total_bars=len(data))
    
    # Create comparison CSV
    with open('tradingview_comparison.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Bar', 'Date', 'Close', 'Prediction', 'Signal',
            'ML_Active', 'Entry', 'Kernel_RQ', 'Kernel_Gauss',
            'Notes'
        ])
        
        for i, bar in enumerate(data):
            result = processor.process_bar(
                bar['open'], bar['high'], bar['low'], 
                bar['close'], bar['volume']
            )
            
            if result and i >= max(0, processor.max_bars_back_index - 10):
                # Calculate kernel values
                kernel_rq = ''
                kernel_gauss = ''
                
                if i >= 50:  # After warmup
                    source_values = processor.close_values[:min(50, len(processor.close_values))]
                    if len(source_values) >= 8:
                        yhat1, _, yhat2, _ = calculate_kernel_values(
                            source_values, 8, 8.0, 25, 2
                        )
                        kernel_rq = f"{yhat1:.4f}"
                        kernel_gauss = f"{yhat2:.4f}"
                
                entry = ''
                if result.start_long_trade:
                    entry = 'BUY'
                elif result.start_short_trade:
                    entry = 'SELL'
                
                notes = ''
                if i == processor.max_bars_back_index:
                    notes = '*** ML STARTS HERE ***'
                
                writer.writerow([
                    i,
                    bar['date'],
                    f"{bar['close']:.2f}",
                    f"{result.prediction:.0f}" if i >= processor.max_bars_back_index else '',
                    result.signal if i >= processor.max_bars_back_index else '',
                    'YES' if i >= processor.max_bars_back_index else 'NO',
                    entry,
                    kernel_rq,
                    kernel_gauss,
                    notes
                ])
    
    print("✅ Created tradingview_comparison.csv")
    print("\n📋 How to use:")
    print("1. Open in Excel")
    print("2. In TradingView, set Max Bars Back = 50")
    print("3. Compare row by row:")
    print("   - Prediction values")
    print("   - Kernel values")
    print("   - Entry signals")


def main():
    """Run comparison with realistic settings"""
    compare_with_realistic_settings()
    create_detailed_comparison_file()
    
    print("\n" + "=" * 60)
    print("🎯 KEY TAKEAWAY:")
    print("=" * 60)
    print("With only 300 bars of data:")
    print("- max_bars_back=2000 → NO ML predictions (correct!)")
    print("- max_bars_back=50 → ML starts at bar 50 (250 bars for ML)")
    print("- max_bars_back=100 → ML starts at bar 100 (200 bars for ML)")
    print("\nUse max_bars_back=50 or 100 in BOTH TradingView and Python!")


if __name__ == "__main__":
    main()
