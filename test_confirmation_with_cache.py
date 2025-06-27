"""
Test Confirmation Filters with Cached Data
=========================================

Uses all available cached data to test confirmation filters.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from data.cache_manager import MarketDataCache
from scanner.confirmation_processor import ConfirmationProcessor
from scanner.ml_quality_filter import MLQualityFilter
from config.adaptive_config import create_adaptive_config
from config.settings import TradingConfig
from data.smart_data_manager import SmartDataManager


def test_with_all_cache(symbol: str = 'RELIANCE'):
    """Test using all cached data"""
    
    print(f"\n{'='*60}")
    print(f"TESTING CONFIRMATION FILTERS - {symbol}")
    print(f"{'='*60}")
    
    # Try to get ALL cached data
    cache = MarketDataCache()
    
    # First check what we have in cache
    try:
        # Get data through smart data manager first to see total available
        data_manager = SmartDataManager()
        # Try very large number of days to get all data
        df = data_manager.get_data(symbol, interval='5minute', days=365)
        
        if df is None:
            print("No cached data found")
            return None
            
        print(f"\nTotal cached data: {len(df)} bars")
        
        if len(df) < 2000:
            print(f"⚠️  Still insufficient data for ML warmup")
            return None
            
    except Exception as e:
        print(f"Error loading cache: {e}")
        return None
    
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
    
    # Test configurations
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
        }
    ]
    
    # ML filter with lower threshold for more signals
    ml_filter = MLQualityFilter(min_confidence=2.5)
    
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
        raw_signals = 0
        bars_processed = 0
        first_signal_bar = None
        
        print(f"Processing {len(df)} bars...")
        
        for idx, row in df.iterrows():
            bars_processed += 1
            result = processor.process_bar(
                open_price=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume']
            )
            
            if result:
                # Track raw signals
                if result.signal != 0:
                    raw_signals += 1
                    if first_signal_bar is None:
                        first_signal_bar = bars_processed
                
                # Track mode-filtered signals
                if result.mode_filtered_signal != 0:
                    # Apply ML filter
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
        
        # Store results
        results[config['name']] = {
            'bars_processed': bars_processed,
            'first_signal_bar': first_signal_bar,
            'raw_signals': raw_signals,
            'mode_filtered': mode_filtered_signals,
            'confirmed': confirmed_signals
        }
        
        # Print results
        print(f"\nResults:")
        print(f"  Bars processed: {bars_processed}")
        if first_signal_bar:
            print(f"  First signal at bar: {first_signal_bar}")
        print(f"  Raw signals: {raw_signals}")
        print(f"  Mode-filtered signals: {mode_filtered_signals}")
        print(f"  Confirmed signals: {confirmed_signals}")
        
        if mode_filtered_signals > 0:
            reduction = (1 - confirmed_signals/mode_filtered_signals) * 100
            print(f"  Confirmation reduction: {reduction:.1f}%")
    
    return results


def main():
    """Run test with all cached data"""
    
    print("\n" + "="*60)
    print("CONFIRMATION FILTER TEST (CACHED DATA)")
    print("="*60)
    
    results = test_with_all_cache('RELIANCE')
    
    if results:
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        
        for config, data in results.items():
            print(f"\n{config}:")
            print(f"  Confirmed signals: {data['confirmed']}")
            if data['mode_filtered'] > 0:
                retention = data['confirmed'] / data['mode_filtered'] * 100
                print(f"  Signal retention: {retention:.1f}%")


if __name__ == "__main__":
    main()