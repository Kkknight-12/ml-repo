"""
Diagnostic script to debug why signals are not generated
"""
import os
import sys
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor


def diagnose_signal_generation():
    """Deep dive into why signals are not generated"""
    print("=" * 80)
    print("🔍 DIAGNOSTIC: WHY NO SIGNALS?")
    print("=" * 80)
    
    # Load TradingView data for specific signal dates
    tv_signals = []
    with open('NSE_ICICIBANK, 1D.csv', 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if row['Buy'] != 'NaN' or row['Sell'] != 'NaN':
                tv_signals.append({
                    'bar': i,
                    'date': row['time'],
                    'type': 'BUY' if row['Buy'] != 'NaN' else 'SELL',
                    'price': float(row['Buy'] if row['Buy'] != 'NaN' else row['Sell']),
                    'close': float(row['close'])
                })
    
    print(f"✅ Found {len(tv_signals)} TradingView signals to analyze")
    
    # Test with different configurations
    configs_to_test = [
        {
            'name': 'Original (max_bars_back=50)',
            'max_bars_back': 50,
            'use_kernel_filter': True,
            'use_volatility_filter': True,
            'use_regime_filter': True
        },
        {
            'name': 'No Filters',
            'max_bars_back': 50,
            'use_kernel_filter': False,
            'use_volatility_filter': False,
            'use_regime_filter': False
        },
        {
            'name': 'Only ML (no kernel)',
            'max_bars_back': 50,
            'use_kernel_filter': False,
            'use_volatility_filter': True,
            'use_regime_filter': True
        }
    ]
    
    # Load data
    bars = []
    with open('NSE_ICICIBANK, 1D.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bars.append({
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': 0  # Not in CSV
            })
    
    for test_config in configs_to_test:
        print(f"\n{'='*60}")
        print(f"Testing: {test_config['name']}")
        print(f"{'='*60}")
        
        # Create config
        config = TradingConfig(
            max_bars_back=test_config['max_bars_back'],
            neighbors_count=8,
            feature_count=5,
            use_kernel_filter=test_config['use_kernel_filter'],
            use_volatility_filter=test_config['use_volatility_filter'],
            use_regime_filter=test_config['use_regime_filter'],
            use_adx_filter=False,
            use_ema_filter=False,
            use_sma_filter=False,
            features={
                "f1": ("RSI", 14, 1),
                "f2": ("WT", 10, 11),
                "f3": ("CCI", 20, 1),
                "f4": ("ADX", 20, 2),
                "f5": ("RSI", 9, 1)
            }
        )
        
        # Process bars
        processor = BarProcessor(config, total_bars=len(bars))
        signals_found = 0
        
        print(f"ML starts at bar: {processor.max_bars_back_index}")
        
        # Check specific TV signal bars
        for tv_signal in tv_signals[:3]:  # First 3 signals
            bar_idx = tv_signal['bar']
            
            # Process up to this bar
            for i in range(min(bar_idx + 2, len(bars))):
                result = processor.process_bar(
                    bars[i]['open'], bars[i]['high'], 
                    bars[i]['low'], bars[i]['close'], 
                    bars[i]['volume']
                )
            
            # Get result at signal bar
            if bar_idx < len(bars):
                print(f"\n📍 Bar {bar_idx} ({tv_signal['date']}) - TV: {tv_signal['type']}")
                
                if bar_idx >= processor.max_bars_back_index:
                    # Check ML prediction
                    result = processor.bar_results[-1] if processor.bar_results else None
                    if result:
                        print(f"   ML Prediction: {result.prediction}")
                        print(f"   Signal: {result.signal}")
                        print(f"   Filters: vol={result.filter_states.get('volatility', False)}, "
                              f"regime={result.filter_states.get('regime', False)}, "
                              f"kernel_bull={result.filter_states.get('kernel_bullish', False)}")
                        
                        if result.start_long_trade or result.start_short_trade:
                            signals_found += 1
                            print(f"   ✅ SIGNAL GENERATED!")
                else:
                    print(f"   ⚠️  Bar before ML start")
        
        print(f"\nTotal signals found: {signals_found}")
    
    # Deep dive into one specific case
    print("\n" + "="*80)
    print("🔬 DEEP DIVE: First TV Buy Signal")
    print("="*80)
    
    first_buy = next((s for s in tv_signals if s['type'] == 'BUY'), None)
    if first_buy:
        print(f"\nAnalyzing: {first_buy['date']} (bar {first_buy['bar']})")
        
        # Use minimal config
        config = TradingConfig(
            max_bars_back=50,
            use_kernel_filter=False,  # Disable to see raw ML
            use_volatility_filter=False,
            use_regime_filter=False,
            use_adx_filter=False
        )
        
        processor = BarProcessor(config, total_bars=len(bars))
        
        # Process up to signal bar
        for i in range(min(first_buy['bar'] + 1, len(bars))):
            result = processor.process_bar(
                bars[i]['open'], bars[i]['high'], 
                bars[i]['low'], bars[i]['close'], 
                bars[i]['volume']
            )
            
            # Print details around signal bar
            if abs(i - first_buy['bar']) <= 2 and i >= processor.max_bars_back_index:
                print(f"\nBar {i}:")
                if result:
                    print(f"  Prediction: {result.prediction}")
                    print(f"  Signal: {result.signal}")
                    print(f"  Entry: Long={result.start_long_trade}, Short={result.start_short_trade}")


def main():
    diagnose_signal_generation()


if __name__ == "__main__":
    main()
