"""
Test Signal Generation
=====================

Debug why no signals are being generated.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from data.smart_data_manager import SmartDataManager
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from scanner.ml_quality_filter import MLQualityFilter
from config.adaptive_config import create_adaptive_config
from config.settings import TradingConfig


def test_signal_generation():
    """Test basic signal generation"""
    
    print("="*60)
    print("SIGNAL GENERATION TEST")
    print("="*60)
    
    # Get data
    data_manager = SmartDataManager()
    symbol = 'RELIANCE'
    df = data_manager.get_data(symbol, interval='5minute', days=30)
    
    if df is None or len(df) < 500:
        print(f"⚠️  Insufficient data for {symbol}")
        return
    
    print(f"\nTesting on {symbol} with {len(df)} bars")
    
    # Get adaptive config
    stats = data_manager.analyze_price_movement(df)
    adaptive_config = create_adaptive_config(symbol, '5minute', stats)
    
    print(f"\nAdaptive Config:")
    print(f"  Neighbors: {adaptive_config.neighbors_count}")
    print(f"  Max bars back: {adaptive_config.max_bars_back}")
    print(f"  Features: {adaptive_config.features}")
    print(f"  Use volatility filter: {adaptive_config.use_volatility_filter}")
    print(f"  Use regime filter: {adaptive_config.use_regime_filter}")
    
    # Create trading config
    trading_config = TradingConfig(
        source=adaptive_config.source,
        neighbors_count=adaptive_config.neighbors_count,
        max_bars_back=adaptive_config.max_bars_back,
        feature_count=adaptive_config.feature_count,
        features=adaptive_config.features,
        use_volatility_filter=adaptive_config.use_volatility_filter,
        use_regime_filter=adaptive_config.use_regime_filter,
        use_adx_filter=adaptive_config.use_adx_filter,
        regime_threshold=adaptive_config.regime_threshold,
        adx_threshold=adaptive_config.adx_threshold
    )
    
    # Create processor
    processor = EnhancedBarProcessor(
        config=trading_config,
        symbol=symbol,
        timeframe='5minute'
    )
    
    # ML filter with different thresholds
    ml_filters = {
        'high': MLQualityFilter(min_confidence=3.0),
        'medium': MLQualityFilter(min_confidence=2.0),
        'low': MLQualityFilter(min_confidence=1.0)
    }
    
    # Track signals at different stages
    signal_stats = {
        'raw_signals': 0,
        'ml_predictions': 0,
        'start_long': 0,
        'start_short': 0,
        'ml_filtered': {'high': 0, 'medium': 0, 'low': 0}
    }
    
    # Process only last 500 bars
    df_subset = df.iloc[-500:] if len(df) > 500 else df
    print(f"\nProcessing last {len(df_subset)} bars...")
    
    for idx, row in df_subset.iterrows():
        result = processor.process_bar(
            open_price=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume']
        )
        
        if result:
            # Track ML predictions
            if result.prediction != 0:
                signal_stats['ml_predictions'] += 1
            
            # Track raw signals
            if result.signal != 0:
                signal_stats['raw_signals'] += 1
                
                # Track entry signals
                if result.start_long_trade:
                    signal_stats['start_long'] += 1
                if result.start_short_trade:
                    signal_stats['start_short'] += 1
                
                # Test ML filters
                signal_dict = {
                    'timestamp': idx,
                    'signal': result.signal,
                    'prediction': result.prediction,
                    'filter_states': result.filter_states,
                    'features': {}
                }
                
                for threshold, ml_filter in ml_filters.items():
                    ml_signal = ml_filter.filter_signal(signal_dict, symbol)
                    if ml_signal is not None:
                        signal_stats['ml_filtered'][threshold] += 1
    
    # Print results
    print(f"\n{'='*50}")
    print("SIGNAL GENERATION RESULTS")
    print(f"{'='*50}")
    
    print(f"\nML Predictions (non-zero): {signal_stats['ml_predictions']}")
    print(f"Raw signals generated: {signal_stats['raw_signals']}")
    print(f"  Long entries: {signal_stats['start_long']}")
    print(f"  Short entries: {signal_stats['start_short']}")
    
    print(f"\nML Filter Results:")
    for threshold, count in signal_stats['ml_filtered'].items():
        print(f"  {threshold} (threshold={ml_filters[threshold].min_confidence}): {count} signals")
    
    # Analyze why no signals
    if signal_stats['raw_signals'] == 0:
        print(f"\n⚠️  NO RAW SIGNALS GENERATED!")
        print(f"\nPossible reasons:")
        print(f"1. Filters too restrictive")
        print(f"2. Not enough bars for ML warmup")
        print(f"3. Market conditions not favorable")
        print(f"4. Configuration issues")
        
        # Check filter states
        if result:
            print(f"\nLast bar filter states:")
            for filter_name, state in result.filter_states.items():
                print(f"  {filter_name}: {state}")
    
    return signal_stats


def test_with_relaxed_config():
    """Test with more relaxed configuration"""
    
    print(f"\n{'='*60}")
    print("TESTING WITH RELAXED CONFIG")
    print(f"{'='*60}")
    
    # Get data
    data_manager = SmartDataManager()
    symbol = 'RELIANCE'
    df = data_manager.get_data(symbol, interval='5minute', days=30)
    
    if df is None:
        return
    
    # Create minimal config
    config = TradingConfig(
        features=['rsi', 'cci'],  # Just 2 features
        neighbors_count=8,
        max_bars_back=600,
        use_volatility_filter=False,  # Disable filters
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=False,
        use_ema_filter=False,
        use_sma_filter=False
    )
    
    print(f"\nRelaxed Config:")
    print(f"  Features: {config.features}")
    print(f"  All filters disabled")
    
    # Create processor
    processor = EnhancedBarProcessor(
        config=config,
        symbol=symbol,
        timeframe='5minute'
    )
    
    # Count signals
    signal_count = 0
    ml_predictions = 0
    
    # Process last 200 bars only
    df_subset = df.iloc[-200:]
    
    for idx, row in df_subset.iterrows():
        result = processor.process_bar(
            open_price=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume']
        )
        
        if result:
            if result.prediction != 0:
                ml_predictions += 1
            if result.signal != 0:
                signal_count += 1
    
    print(f"\nResults with relaxed config:")
    print(f"  ML predictions: {ml_predictions}")
    print(f"  Signals generated: {signal_count}")
    
    return signal_count > 0


def main():
    """Run all tests"""
    
    # Test 1: Standard signal generation
    stats = test_signal_generation()
    
    # Test 2: Relaxed config
    success = test_with_relaxed_config()
    
    print(f"\n{'='*60}")
    print("CONCLUSIONS")
    print(f"{'='*60}")
    
    if stats['raw_signals'] == 0:
        print("\n❌ No signals generated with adaptive config")
        print("The issue is with base signal generation, not mode filtering")
        
        if success:
            print("\n✅ Signals generated with relaxed config")
            print("The adaptive config may be too restrictive")
        else:
            print("\n❌ No signals even with relaxed config")
            print("There may be a deeper issue with the ML model")
    else:
        print(f"\n✅ Signals generated: {stats['raw_signals']}")
        print("Mode filtering can be tested properly")


if __name__ == "__main__":
    main()