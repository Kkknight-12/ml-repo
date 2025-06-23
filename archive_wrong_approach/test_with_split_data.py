"""
Test with properly split training/testing data
Training: Historical data before 2024-04-05
Testing: Same date range as TradingView
"""
import os
import sys
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor
from core.kernel_functions import calculate_kernel_values


def test_with_split_data():
    """Test using separate training and testing data"""
    print("=" * 80)
    print("📊 TESTING WITH PROPER TRAIN/TEST SPLIT")
    print("=" * 80)
    
    # Check required files
    if not os.path.exists('zerodha_training_data.csv'):
        print("❌ zerodha_training_data.csv not found!")
        print("   Run: python fetch_split_data.py first")
        return
    
    if not os.path.exists('zerodha_testing_data.csv'):
        print("❌ zerodha_testing_data.csv not found!")
        print("   Run: python fetch_split_data.py first")
        return
    
    # 1. Load Training Data
    training_bars = []
    with open('zerodha_training_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            training_bars.append({
                'date': row['time'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            })
    
    print(f"✅ Loaded {len(training_bars)} training bars")
    
    # 2. Load Testing Data
    testing_bars = []
    with open('zerodha_testing_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            testing_bars.append({
                'date': row['time'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            })
    
    print(f"✅ Loaded {len(testing_bars)} testing bars")
    
    # 3. Load TradingView signals for comparison
    tv_signals = {'buy': [], 'sell': []}
    tv_kernels = []
    
    with open('NSE_ICICIBANK, 1D.csv', 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if row['Buy'] != 'NaN':
                tv_signals['buy'].append((i, row['time'], float(row['Buy'])))
            if row['Sell'] != 'NaN':
                tv_signals['sell'].append((i, row['time'], float(row['Sell'])))
            
            if row['Kernel Regression Estimate'] != 'NaN':
                tv_kernels.append({
                    'bar': i,
                    'date': row['time'],
                    'value': float(row['Kernel Regression Estimate'])
                })
    
    print(f"\n📊 TradingView Reference:")
    print(f"   Buy signals: {len(tv_signals['buy'])}")
    print(f"   Sell signals: {len(tv_signals['sell'])}")
    
    # 4. Configure with proper settings
    config = TradingConfig(
        # Use 2000 for proper ML training
        max_bars_back=2000,
        neighbors_count=8,
        feature_count=5,
        
        # Match TradingView settings
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        use_ema_filter=False,
        use_sma_filter=False,
        
        # Kernel settings
        use_kernel_filter=True,
        show_kernel_estimate=True,
        use_kernel_smoothing=True,
        kernel_lookback=8,
        kernel_relative_weight=8.0,
        kernel_regression_level=25,
        kernel_lag=2,
        
        # Standard features
        features={
            "f1": ("RSI", 14, 1),
            "f2": ("WT", 10, 11),
            "f3": ("CCI", 20, 1),
            "f4": ("ADX", 20, 2),
            "f5": ("RSI", 9, 1)
        }
    )
    
    # Combine training + testing for processing
    all_bars = training_bars + testing_bars
    
    # Initialize processor
    processor = BarProcessor(config, total_bars=len(all_bars))
    
    print(f"\n📈 Configuration:")
    print(f"   Total bars: {len(all_bars)}")
    print(f"   Training bars: {len(training_bars)}")
    print(f"   Testing bars: {len(testing_bars)}")
    print(f"   max_bars_back: {config.max_bars_back}")
    print(f"   ML starts at bar: {processor.max_bars_back_index}")
    print(f"   Testing starts at bar: {len(training_bars)}")
    
    # 5. Process all bars
    test_signals = {'buy': [], 'sell': []}
    kernel_comparisons = []
    
    print("\n🔄 Processing bars...")
    for i, bar in enumerate(all_bars):
        result = processor.process_bar(
            bar['open'], bar['high'], bar['low'], 
            bar['close'], bar['volume']
        )
        
        # Track signals in testing range
        if i >= len(training_bars) and result:
            test_idx = i - len(training_bars)  # Index within testing data
            
            if result.start_long_trade:
                test_signals['buy'].append((test_idx, bar['date'], bar['close']))
                
            if result.start_short_trade:
                test_signals['sell'].append((test_idx, bar['date'], bar['close']))
            
            # Compare kernel values
            if i >= len(training_bars) + config.kernel_lookback:
                source_values = processor.close_values[:min(100, len(processor.close_values))]
                if len(source_values) >= config.kernel_lookback:
                    yhat1, _, _, _ = calculate_kernel_values(
                        source_values,
                        config.kernel_lookback,
                        config.kernel_relative_weight,
                        config.kernel_regression_level,
                        config.kernel_lag
                    )
                    
                    # Find matching TV kernel
                    for tv_kernel in tv_kernels:
                        if tv_kernel['date'] == bar['date']:
                            kernel_comparisons.append({
                                'date': bar['date'],
                                'tv': tv_kernel['value'],
                                'py': yhat1,
                                'diff': abs(tv_kernel['value'] - yhat1)
                            })
                            break
    
    # 6. Results
    print("\n" + "=" * 80)
    print("📊 RESULTS")
    print("=" * 80)
    
    # Kernel comparison
    if kernel_comparisons:
        avg_kernel_diff = sum(k['diff'] for k in kernel_comparisons) / len(kernel_comparisons)
        print(f"\n1️⃣ KERNEL VALUES:")
        print(f"   Samples compared: {len(kernel_comparisons)}")
        print(f"   Average difference: {avg_kernel_diff:.6f}")
        print(f"   First 3 comparisons:")
        for k in kernel_comparisons[:3]:
            print(f"   {k['date']}: TV={k['tv']:.4f}, PY={k['py']:.4f}, Diff={k['diff']:.6f}")
    
    # Signal comparison
    print(f"\n2️⃣ SIGNALS:")
    print(f"   TradingView: {len(tv_signals['buy'])} buy, {len(tv_signals['sell'])} sell")
    print(f"   Python:      {len(test_signals['buy'])} buy, {len(test_signals['sell'])} sell")
    
    # Match signals
    matched_buy = 0
    matched_sell = 0
    
    print("\n   Signal Matching (±1 bar):")
    
    # Match buy signals
    for py_idx, py_date, _ in test_signals['buy']:
        for tv_idx, tv_date, _ in tv_signals['buy']:
            if abs(py_idx - tv_idx) <= 1:
                matched_buy += 1
                print(f"   ✅ Buy match: {py_date} ≈ {tv_date}")
                break
    
    # Match sell signals  
    for py_idx, py_date, _ in test_signals['sell']:
        for tv_idx, tv_date, _ in tv_signals['sell']:
            if abs(py_idx - tv_idx) <= 1:
                matched_sell += 1
                print(f"   ✅ Sell match: {py_date} ≈ {tv_date}")
                break
    
    total_tv = len(tv_signals['buy']) + len(tv_signals['sell'])
    total_matched = matched_buy + matched_sell
    match_rate = (total_matched / total_tv * 100) if total_tv > 0 else 0
    
    print(f"\n📊 MATCH RATE: {total_matched}/{total_tv} ({match_rate:.1f}%)")
    
    # Save detailed comparison
    print("\n3️⃣ Creating detailed comparison CSV...")
    
    with open('split_data_comparison.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Test_Bar', 'Date', 'Close', 
            'ML_Prediction', 'Signal',
            'PY_Buy', 'PY_Sell', 'TV_Buy', 'TV_Sell'
        ])
        
        for i, bar in enumerate(testing_bars):
            # Find if this date has signals
            py_buy = any(date == bar['date'] for _, date, _ in test_signals['buy'])
            py_sell = any(date == bar['date'] for _, date, _ in test_signals['sell'])
            tv_buy = any(date == bar['date'] for _, date, _ in tv_signals['buy'])
            tv_sell = any(date == bar['date'] for _, date, _ in tv_signals['sell'])
            
            # Get ML prediction if available
            training_bar_idx = len(training_bars) + i
            ml_pred = ''
            signal = ''
            
            if training_bar_idx < len(processor.bar_results):
                result = processor.bar_results[training_bar_idx]
                if result and training_bar_idx >= processor.max_bars_back_index:
                    ml_pred = f"{result.prediction:.0f}"
                    signal = result.signal
            
            writer.writerow([
                i,
                bar['date'],
                f"{bar['close']:.2f}",
                ml_pred,
                signal,
                'YES' if py_buy else '',
                'YES' if py_sell else '',
                'YES' if tv_buy else '',
                'YES' if tv_sell else ''
            ])
    
    print("   ✅ Saved to: split_data_comparison.csv")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    if len(test_signals['buy']) + len(test_signals['sell']) == 0:
        print("⚠️  NO SIGNALS GENERATED!")
        print("\nPossible reasons:")
        print("1. ML needs more warmup than 2000 bars")
        print("2. Filter thresholds too strict")
        print("3. Feature calculation differences")
        print("\nNext step: Run python diagnose_split_data.py")
    else:
        print(f"✅ Signals generated successfully!")
        print(f"✅ Match rate: {match_rate:.1f}%")
        if match_rate < 50:
            print("\n⚠️  Low match rate. Check:")
            print("- Filter parameters")
            print("- Entry/exit logic")
            print("- Feature normalization")


def main():
    test_with_split_data()


if __name__ == "__main__":
    main()
