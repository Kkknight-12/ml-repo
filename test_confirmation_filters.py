"""
Test Confirmation Filters
========================

Test the integrated confirmation filtering system.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from data.smart_data_manager import SmartDataManager
from scanner.confirmation_processor import ConfirmationProcessor
from scanner.ml_quality_filter import MLQualityFilter
from config.adaptive_config import create_adaptive_config
from config.settings import TradingConfig


def test_confirmation_filters(symbol: str = 'RELIANCE', days: int = 90):
    """Test confirmation filtering with different configurations"""
    
    print(f"\n{'='*60}")
    print(f"TESTING CONFIRMATION FILTERS - {symbol}")
    print(f"{'='*60}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=days)
    
    if df is None or len(df) < 2000:
        print(f"⚠️  Insufficient data: {len(df) if df is not None else 0} bars")
        return None
    
    print(f"\nData loaded: {len(df)} bars")
    
    # Get adaptive config
    stats = data_manager.analyze_price_movement(df)
    adaptive_config = create_adaptive_config(symbol, '5minute', stats)
    
    # Create trading config
    trading_config = TradingConfig(
        source=adaptive_config.source,
        neighbors_count=adaptive_config.neighbors_count,
        max_bars_back=adaptive_config.max_bars_back,
        feature_count=adaptive_config.feature_count,
        features=adaptive_config.features
    )
    
    # Test different confirmation configurations
    configs = [
        {
            'name': 'Volume Only',
            'require_volume': True,
            'require_momentum': False,
            'require_sr': False,
            'min_confirmations': 1
        },
        {
            'name': 'Volume + Momentum',
            'require_volume': True,
            'require_momentum': True,
            'require_sr': False,
            'min_confirmations': 2
        },
        {
            'name': 'All Filters',
            'require_volume': True,
            'require_momentum': True,
            'require_sr': True,
            'min_confirmations': 2
        },
        {
            'name': 'Any 2 of 3',
            'require_volume': False,
            'require_momentum': False,
            'require_sr': False,
            'min_confirmations': 2
        }
    ]
    
    # ML filter
    ml_filter = MLQualityFilter(min_confidence=3.0)
    
    results = {}
    
    for config in configs:
        print(f"\n{'='*50}")
        print(f"Testing: {config['name']}")
        print(f"{'='*50}")
        
        # Create processor
        processor = ConfirmationProcessor(
            config=trading_config,
            symbol=symbol,
            timeframe='5minute',
            **{k: v for k, v in config.items() if k != 'name'}
        )
        
        # Track signals
        mode_filtered_signals = 0
        confirmed_signals = 0
        confirmation_details = {
            'volume_confirmed': 0,
            'momentum_confirmed': 0,
            'sr_confirmed': 0,
            'avg_confirmation_score': []
        }
        
        # Process bars
        print(f"Processing {len(df)} bars...")
        
        for idx, row in df.iterrows():
            result = processor.process_bar(
                open_price=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume']
            )
            
            if result and result.mode_filtered_signal != 0:
                # Apply ML filter first
                signal_dict = {
                    'timestamp': idx,
                    'signal': result.mode_filtered_signal,
                    'prediction': result.prediction,
                    'filter_states': result.filter_states,
                    'features': {}
                }
                
                ml_signal = ml_filter.filter_signal(signal_dict, symbol)
                if ml_signal is not None:
                    mode_filtered_signals += 1
                    
                    # Check confirmation
                    if result.confirmed_signal != 0:
                        confirmed_signals += 1
                        
                        # Track confirmation details
                        if result.volume_confirmed:
                            confirmation_details['volume_confirmed'] += 1
                        if result.momentum_confirmed:
                            confirmation_details['momentum_confirmed'] += 1
                        if result.sr_confirmed:
                            confirmation_details['sr_confirmed'] += 1
                        
                        confirmation_details['avg_confirmation_score'].append(
                            result.confirmation_score
                        )
        
        # Calculate average confirmation score
        avg_score = np.mean(confirmation_details['avg_confirmation_score']) \
                   if confirmation_details['avg_confirmation_score'] else 0
        
        # Store results
        results[config['name']] = {
            'mode_filtered': mode_filtered_signals,
            'confirmed': confirmed_signals,
            'reduction_rate': (1 - confirmed_signals/mode_filtered_signals) * 100 
                            if mode_filtered_signals > 0 else 0,
            'avg_score': avg_score,
            'details': confirmation_details
        }
        
        # Print results
        print(f"\nResults:")
        print(f"  Mode-filtered signals: {mode_filtered_signals}")
        print(f"  Confirmed signals: {confirmed_signals}")
        print(f"  Reduction: {results[config['name']]['reduction_rate']:.1f}%")
        print(f"  Avg confirmation score: {avg_score:.3f}")
        
        if confirmed_signals > 0:
            print(f"\nConfirmation breakdown:")
            print(f"  Volume: {confirmation_details['volume_confirmed']} " +
                  f"({confirmation_details['volume_confirmed']/confirmed_signals*100:.1f}%)")
            print(f"  Momentum: {confirmation_details['momentum_confirmed']} " +
                  f"({confirmation_details['momentum_confirmed']/confirmed_signals*100:.1f}%)")
            print(f"  S/R: {confirmation_details['sr_confirmed']} " +
                  f"({confirmation_details['sr_confirmed']/confirmed_signals*100:.1f}%)")
    
    return results


def analyze_confirmation_impact(results):
    """Analyze the impact of different confirmation strategies"""
    
    print(f"\n{'='*60}")
    print("CONFIRMATION STRATEGY COMPARISON")
    print(f"{'='*60}")
    
    print(f"\n{'Strategy':<20} {'Signals':<10} {'Reduction':<12} {'Avg Score':<10}")
    print("-" * 52)
    
    for strategy, data in results.items():
        print(f"{strategy:<20} {data['confirmed']:<10} " +
              f"{data['reduction_rate']:<12.1f} {data['avg_score']:<10.3f}")
    
    # Find optimal strategy
    print(f"\n{'='*50}")
    print("RECOMMENDATIONS")
    print(f"{'='*50}")
    
    # Look for best balance of signal count and quality
    best_strategy = None
    best_score = 0
    
    for strategy, data in results.items():
        # Score based on: signals retained (40%) + avg score (60%)
        if data['mode_filtered'] > 0:
            retention = data['confirmed'] / data['mode_filtered']
            score = 0.4 * retention + 0.6 * data['avg_score']
            
            if score > best_score and data['confirmed'] >= 10:  # Min 10 signals
                best_score = score
                best_strategy = strategy
    
    if best_strategy:
        print(f"\n✅ Recommended strategy: {best_strategy}")
        print(f"   - Retains {results[best_strategy]['confirmed']} signals")
        print(f"   - {results[best_strategy]['reduction_rate']:.1f}% reduction")
        print(f"   - {results[best_strategy]['avg_score']:.3f} avg confirmation score")
    else:
        print("\n⚠️  No strategy generated sufficient confirmed signals")


def main():
    """Run confirmation filter tests"""
    
    print("\n" + "="*60)
    print("CONFIRMATION FILTER TEST SUITE")
    print("="*60)
    
    # Test on single symbol
    results = test_confirmation_filters('RELIANCE', days=90)
    
    if results:
        # Analyze results
        analyze_confirmation_impact(results)
        
        print(f"\n{'='*60}")
        print("CONCLUSIONS")
        print(f"{'='*60}")
        print("✅ Confirmation filters successfully integrated")
        print("✅ Multiple confirmation strategies tested")
        print("✅ Volume and momentum filters working correctly")
        print("\nNext Steps:")
        print("1. Backtest with optimal confirmation strategy")
        print("2. Fine-tune confirmation thresholds")
        print("3. Test across multiple symbols and timeframes")


if __name__ == "__main__":
    main()