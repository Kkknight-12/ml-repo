"""
Test with proper 2000 bar training data
This ensures ML has enough data to generate signals
"""
import os
import sys
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor


def test_with_proper_training():
    """Test with 2000 training bars + TV comparison data"""
    print("=" * 80)
    print("📊 TESTING WITH PROPER 2000 BAR TRAINING")
    print("=" * 80)
    
    # First check if we have the complete data
    if not os.path.exists('zerodha_complete_data.csv'):
        print("❌ zerodha_complete_data.csv not found!")
        print("   Run: python fetch_2000_bars.py first")
        return
    
    # Load complete data
    all_bars = []
    with open('zerodha_complete_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_bars.append({
                'date': row['time'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            })
    
    print(f"✅ Loaded {len(all_bars)} total bars")
    
    # Find where TV data starts
    tv_start_index = None
    for i, bar in enumerate(all_bars):
        if bar['date'] == '2024-04-05':
            tv_start_index = i
            break
    
    if tv_start_index is None:
        print("❌ Could not find TV start date in data")
        return
    
    print(f"   Training bars: {tv_start_index}")
    print(f"   TV comparison bars: {len(all_bars) - tv_start_index}")
    
    # Configure with proper max_bars_back
    config = TradingConfig(
        # Use 2000 for proper training
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
    
    # Initialize processor with correct total bars
    processor = BarProcessor(config, total_bars=len(all_bars))
    
    print(f"\n📈 ML Configuration:")
    print(f"   max_bars_back: {config.max_bars_back}")
    print(f"   ML starts at bar: {processor.max_bars_back_index}")
    print(f"   ML active from bar: {tv_start_index} (TV data start)")
    
    # Process all bars
    signals = []
    tv_range_signals = []
    
    print("\n🔄 Processing all bars...")
    for i, bar in enumerate(all_bars):
        result = processor.process_bar(
            bar['open'], bar['high'], bar['low'], 
            bar['close'], bar['volume']
        )
        
        if result:
            # Track all signals
            if result.start_long_trade:
                signals.append((i, bar['date'], 'BUY', bar['close']))
                if i >= tv_start_index:
                    tv_range_signals.append((i - tv_start_index, bar['date'], 'BUY'))
                    
            if result.start_short_trade:
                signals.append((i, bar['date'], 'SELL', bar['close']))
                if i >= tv_start_index:
                    tv_range_signals.append((i - tv_start_index, bar['date'], 'SELL'))
    
    # Results
    print("\n" + "=" * 80)
    print("📊 RESULTS WITH PROPER TRAINING")
    print("=" * 80)
    
    print(f"\n✅ Total signals generated: {len(signals)}")
    print(f"   Signals in TV date range: {len(tv_range_signals)}")
    
    if tv_range_signals:
        print("\n📈 Signals in TradingView comparison range:")
        for bar_idx, date, signal_type in tv_range_signals[:10]:  # First 10
            print(f"   Bar {bar_idx}: {date} - {signal_type}")
        
        if len(tv_range_signals) > 10:
            print(f"   ... and {len(tv_range_signals) - 10} more signals")
    
    # Compare with TradingView signals
    print("\n📊 Comparison with TradingView:")
    
    # Load TV signals
    tv_signals = {'buy': [], 'sell': []}
    with open('NSE_ICICIBANK, 1D.csv', 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if row['Buy'] != 'NaN':
                tv_signals['buy'].append((i, row['time']))
            if row['Sell'] != 'NaN':
                tv_signals['sell'].append((i, row['time']))
    
    print(f"\n   TradingView: {len(tv_signals['buy'])} buy, {len(tv_signals['sell'])} sell")
    
    # Count our signals by type
    our_buys = sum(1 for _, _, t in tv_range_signals if t == 'BUY')
    our_sells = sum(1 for _, _, t in tv_range_signals if t == 'SELL')
    print(f"   Python:      {our_buys} buy, {our_sells} sell")
    
    # Match signals
    print("\n   Signal Matching:")
    matched = 0
    for bar_idx, date, signal_type in tv_range_signals:
        tv_list = tv_signals['buy'] if signal_type == 'BUY' else tv_signals['sell']
        for tv_idx, tv_date in tv_list:
            if abs(bar_idx - tv_idx) <= 1:  # ±1 bar tolerance
                matched += 1
                print(f"   ✅ Match: {signal_type} on {date} (bar {bar_idx})")
                break
    
    total_tv_signals = len(tv_signals['buy']) + len(tv_signals['sell'])
    match_rate = (matched / total_tv_signals * 100) if total_tv_signals > 0 else 0
    
    print(f"\n📊 Match Rate: {matched}/{total_tv_signals} ({match_rate:.1f}%)")
    
    # Diagnostic info
    if len(tv_range_signals) == 0:
        print("\n⚠️  NO SIGNALS GENERATED!")
        print("   Possible issues:")
        print("   1. Filters too restrictive")
        print("   2. ML predictions not strong enough")
        print("   3. Feature calculation differences")
        
        # Check last few ML predictions
        print("\n   Last 5 ML predictions:")
        for i in range(max(0, len(all_bars) - 5), len(all_bars)):
            result = processor.process_bar(
                all_bars[i]['open'], all_bars[i]['high'], 
                all_bars[i]['low'], all_bars[i]['close'], 
                all_bars[i]['volume']
            )
            if result and i >= processor.max_bars_back_index:
                print(f"   Bar {i}: Prediction = {result.prediction}")


def main():
    test_with_proper_training()


if __name__ == "__main__":
    main()
