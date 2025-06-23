"""
Phase 4 Test with ICICI Bank 1D Data
Compare our implementation with TradingView signals
"""
import os
import sys
import csv
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor


def load_icici_data(filename):
    """
    Load ICICI Bank 1D data from CSV
    Expected format: Date,Open,High,Low,Close,Volume
    """
    data = []
    
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        print("Please place your ICICI Bank 1D CSV file in the project directory")
        return None
    
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                data.append({
                    'date': row.get('Date', row.get('date', row.get('time', ''))),
                    'open': float(row.get('Open', row.get('open', 0))),
                    'high': float(row.get('High', row.get('high', 0))),
                    'low': float(row.get('Low', row.get('low', 0))),
                    'close': float(row.get('Close', row.get('close', 0))),
                    'volume': float(row.get('Volume', row.get('volume', 0)))
                })
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
    
    print(f"✅ Loaded {len(data)} bars from {filename}")
    return data


def test_with_tradingview_comparison():
    """
    Test Phase 4 implementation and prepare for TradingView comparison
    """
    print("=" * 60)
    print("🏦 ICICI Bank 1D - Phase 4 Test")
    print("=" * 60)
    
    # Load data
    filename = "NSE_ICICIBANK, 1D.csv"  # Update this path if needed
    data = load_icici_data(filename)
    
    if not data:
        return
    
    # Configure for testing
    config = TradingConfig(
        # Match your TradingView settings
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        
        # Kernel settings
        use_kernel_filter=True,
        kernel_lookback=8,
        kernel_relative_weight=8.0,
        kernel_regression_level=25,
        use_kernel_smoothing=True,  # Set based on your TV settings
        kernel_lag=2,
        
        # Dynamic exits
        use_dynamic_exits=True,  # Test dynamic exits
        
        # Filters - match your TV settings
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,  # Set based on your TV settings
        
        # MA filters
        use_ema_filter=False,  # Set based on your TV settings
        use_sma_filter=False,
        
        # Features - match your TV settings
        features={
            "f1": ("RSI", 14, 1),
            "f2": ("WT", 10, 11),
            "f3": ("CCI", 20, 1),
            "f4": ("ADX", 20, 2),
            "f5": ("RSI", 9, 1)
        }
    )
    
    # Initialize processor with total bars
    total_bars = len(data)
    processor = BarProcessor(config, total_bars=total_bars)
    
    print(f"\n📊 Processing {total_bars} bars...")
    print(f"ML will start predictions after bar {processor.max_bars_back_index}")
    
    # Track signals for comparison
    signals = []
    kernel_values = []
    
    # Process all bars
    for i, bar in enumerate(data):
        result = processor.process_bar(
            bar['open'], 
            bar['high'], 
            bar['low'], 
            bar['close'], 
            bar['volume']
        )
        
        if result:
            # Track kernel values
            if i >= 10:  # After some warmup
                # Get kernel estimates
                from core.kernel_functions import calculate_kernel_values
                
                # Get source values for kernel
                source_values = []
                for j in range(min(100, len(processor.close_values))):
                    source_values.append(processor.close_values[j])
                
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
                        'close': bar['close'],
                        'yhat1': yhat1,
                        'yhat2': yhat2,
                        'diff': yhat2 - yhat1
                    })
            
            # Track signals
            if result.start_long_trade or result.start_short_trade or \
               result.end_long_trade or result.end_short_trade:
                
                signal_info = {
                    'bar': i,
                    'date': bar['date'],
                    'price': bar['close'],
                    'prediction': result.prediction,
                    'signal_strength': result.prediction_strength,
                    'type': '',
                    'sl': result.stop_loss,
                    'tp': result.take_profit
                }
                
                if result.start_long_trade:
                    signal_info['type'] = 'BUY'
                elif result.start_short_trade:
                    signal_info['type'] = 'SELL'
                elif result.end_long_trade:
                    signal_info['type'] = 'EXIT_LONG'
                elif result.end_short_trade:
                    signal_info['type'] = 'EXIT_SHORT'
                
                signals.append(signal_info)
    
    # Display results
    print("\n📈 Signal Summary:")
    print("-" * 60)
    
    if not signals:
        print("No signals generated!")
        print("\nPossible reasons:")
        print("1. Check if filters are too restrictive")
        print("2. Verify feature parameters match TradingView")
        print("3. Ensure sufficient data for ML warmup")
    else:
        print(f"Total signals: {len(signals)}")
        print("\nDetailed Signals:")
        for sig in signals:
            print(f"\nBar {sig['bar']} ({sig['date']})")
            print(f"  Type: {sig['type']} @ {sig['price']:.2f}")
            print(f"  Prediction: {sig['prediction']:.2f}")
            print(f"  Strength: {sig['signal_strength']:.2%}")
            if sig['sl'] and sig['tp']:
                print(f"  SL: {sig['sl']:.2f}, TP: {sig['tp']:.2f}")
    
    # Display kernel values (last 10)
    if kernel_values:
        print("\n📊 Kernel Values (Last 10 bars):")
        print("-" * 60)
        print("Date         Close    RQ(yhat1)  Gauss(yhat2)  Diff")
        print("-" * 60)
        
        for kv in kernel_values[-10:]:
            print(f"{kv['date'][:10]}  {kv['close']:7.2f}  "
                  f"{kv['yhat1']:9.2f}  {kv['yhat2']:11.2f}  "
                  f"{kv['diff']:6.3f}")
    
    # Save results for TradingView comparison
    output_file = "icici_signals_python.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Bar', 'Date', 'Type', 'Price', 'Prediction', 'Strength', 'SL', 'TP'])
        for sig in signals:
            writer.writerow([
                sig['bar'], sig['date'], sig['type'], sig['price'],
                sig['prediction'], f"{sig['signal_strength']:.4f}",
                sig['sl'] or '', sig['tp'] or ''
            ])
    
    print(f"\n✅ Signals saved to {output_file}")
    print("\n🔍 How to Compare with TradingView:")
    print("1. Apply the same Lorentzian Classification script in TradingView")
    print("2. Use exact same settings as in config above")
    print("3. Note down signal dates and prices from TradingView")
    print("4. Compare with signals in", output_file)
    print("\n💡 Tips:")
    print("- Kernel values (yhat1, yhat2) should closely match TV")
    print("- Signal timing might differ by 1 bar due to calculation differences")
    print("- Check if all filters are configured identically")


if __name__ == "__main__":
    test_with_tradingview_comparison()
