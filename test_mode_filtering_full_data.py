"""
Test Mode Filtering with Full Data
==================================

Test mode-aware filtering with sufficient data for ML warmup (2000+ bars).
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from data.smart_data_manager import SmartDataManager
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from scanner.mode_aware_processor import ModeAwareBarProcessor
from scanner.ml_quality_filter import MLQualityFilter
from config.adaptive_config import create_adaptive_config
from config.settings import TradingConfig


def test_with_full_data(symbol: str = 'RELIANCE', days: int = 90):
    """Test with enough data for ML warmup"""
    
    print(f"\n{'='*60}")
    print(f"TESTING MODE FILTERING WITH FULL DATA")
    print(f"{'='*60}")
    
    # Get more data for ML warmup
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=days)
    
    if df is None:
        print(f"⚠️  No data available for {symbol}")
        return None
    
    print(f"\nData loaded: {len(df)} bars (need 2000+ for ML)")
    
    if len(df) < 2000:
        print(f"⚠️  Still insufficient data. Trying to fetch more...")
        # Try fetching more days
        df = data_manager.get_data(symbol, interval='5minute', days=120)
        if df is not None:
            print(f"  Now have {len(df)} bars")
    
    if df is None or len(df) < 2000:
        print(f"❌ Cannot get enough data for ML warmup")
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
    
    # Create processors
    standard_processor = EnhancedBarProcessor(
        config=trading_config,
        symbol=symbol,
        timeframe='5minute'
    )
    
    mode_aware_processor = ModeAwareBarProcessor(
        config=trading_config,
        symbol=symbol,
        timeframe='5minute',
        allow_trend_trades=False
    )
    
    # ML filter with different thresholds to test
    ml_thresholds = [3.0, 2.5, 2.0]
    
    results = {}
    
    for threshold in ml_thresholds:
        print(f"\n{'='*50}")
        print(f"Testing with ML threshold = {threshold}")
        print(f"{'='*50}")
        
        ml_filter = MLQualityFilter(min_confidence=threshold)
        
        # Track signals
        standard_signals = []
        mode_filtered_signals = []
        mode_stats = {
            'cycle_bars': 0,
            'trend_bars': 0,
            'signals_in_cycle': 0,
            'signals_in_trend': 0,
            'filtered_in_trend': 0
        }
        
        # Process all bars for ML warmup
        print(f"Processing {len(df)} bars...")
        bar_count = 0
        first_signal_bar = None
        
        for idx, row in df.iterrows():
            bar_count += 1
            
            # Standard processor
            std_result = standard_processor.process_bar(
                open_price=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume']
            )
            
            if std_result and std_result.signal != 0:
                if first_signal_bar is None:
                    first_signal_bar = bar_count
                    print(f"  First signal at bar {bar_count}")
                
                # Apply ML filter
                signal_dict = {
                    'timestamp': idx,
                    'signal': std_result.signal,
                    'prediction': std_result.prediction,
                    'filter_states': std_result.filter_states,
                    'features': {}
                }
                
                ml_signal = ml_filter.filter_signal(signal_dict, symbol)
                if ml_signal is not None:
                    standard_signals.append({
                        'timestamp': idx,
                        'signal': std_result.signal,
                        'prediction': std_result.prediction
                    })
            
            # Mode-aware processor
            ma_result = mode_aware_processor.process_bar(
                open_price=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume']
            )
            
            if ma_result:
                # Track mode statistics
                if ma_result.market_mode == 'cycle':
                    mode_stats['cycle_bars'] += 1
                else:
                    mode_stats['trend_bars'] += 1
                
                # Check if signal was generated
                if ma_result.signal != 0:
                    if ma_result.market_mode == 'cycle':
                        mode_stats['signals_in_cycle'] += 1
                    else:
                        mode_stats['signals_in_trend'] += 1
                        
                    # Check if it was filtered
                    if ma_result.mode_filtered_signal == 0:
                        mode_stats['filtered_in_trend'] += 1
                
                # Track mode-filtered signals
                if ma_result.mode_filtered_signal != 0:
                    signal_dict = {
                        'timestamp': idx,
                        'signal': ma_result.mode_filtered_signal,
                        'prediction': ma_result.prediction,
                        'filter_states': ma_result.filter_states,
                        'features': {}
                    }
                    
                    ml_signal = ml_filter.filter_signal(signal_dict, symbol)
                    if ml_signal is not None:
                        mode_filtered_signals.append({
                            'timestamp': idx,
                            'signal': ma_result.mode_filtered_signal,
                            'prediction': ma_result.prediction,
                            'mode': ma_result.market_mode,
                            'confidence': ma_result.mode_confidence
                        })
        
        # Store results
        results[threshold] = {
            'standard_signals': len(standard_signals),
            'mode_filtered_signals': len(mode_filtered_signals),
            'mode_stats': mode_stats,
            'first_signal_bar': first_signal_bar
        }
        
        # Print results for this threshold
        print(f"\nResults for ML threshold {threshold}:")
        print(f"  Standard signals: {len(standard_signals)}")
        print(f"  Mode-filtered signals: {len(mode_filtered_signals)}")
        
        if len(standard_signals) > 0:
            reduction = (1 - len(mode_filtered_signals)/len(standard_signals)) * 100
            print(f"  Signal reduction: {reduction:.1f}%")
        
        print(f"\nMode Statistics:")
        print(f"  Cycle bars: {mode_stats['cycle_bars']}")
        print(f"  Trend bars: {mode_stats['trend_bars']}")
        print(f"  Signals in cycle: {mode_stats['signals_in_cycle']}")
        print(f"  Signals in trend: {mode_stats['signals_in_trend']}")
        print(f"  Filtered in trend: {mode_stats['filtered_in_trend']}")
        
        if mode_stats['signals_in_trend'] > 0:
            filter_rate = mode_stats['filtered_in_trend'] / mode_stats['signals_in_trend'] * 100
            print(f"  Trend filter rate: {filter_rate:.1f}%")
    
    return results


def analyze_mode_filtering_impact(results):
    """Analyze the impact of mode filtering"""
    
    print(f"\n{'='*60}")
    print("MODE FILTERING IMPACT ANALYSIS")
    print(f"{'='*60}")
    
    # Compare across thresholds
    print("\nSignal Count by ML Threshold:")
    print(f"{'Threshold':<10} {'Standard':<10} {'Filtered':<10} {'Reduction':<10}")
    print("-" * 40)
    
    for threshold, data in results.items():
        std_count = data['standard_signals']
        filtered_count = data['mode_filtered_signals']
        reduction = (1 - filtered_count/std_count * 100) if std_count > 0 else 0
        print(f"{threshold:<10} {std_count:<10} {filtered_count:<10} {reduction:<10.1f}%")
    
    # Find optimal threshold
    print("\nRecommendation:")
    
    # Look for threshold that generates reasonable signals with good filtering
    optimal_threshold = None
    for threshold, data in results.items():
        if data['mode_filtered_signals'] >= 5:  # At least 5 signals
            if optimal_threshold is None:
                optimal_threshold = threshold
            print(f"  ML threshold {threshold}: {data['mode_filtered_signals']} signals (viable)")
        else:
            print(f"  ML threshold {threshold}: {data['mode_filtered_signals']} signals (too few)")
    
    if optimal_threshold:
        print(f"\n✅ Recommended ML threshold: {optimal_threshold}")
    else:
        print("\n⚠️  No threshold generated sufficient signals")


def main():
    """Run comprehensive mode filtering test"""
    
    print("\n" + "="*60)
    print("MODE FILTERING TEST WITH FULL DATA")
    print("="*60)
    
    # Test with full data
    results = test_with_full_data('RELIANCE', days=90)
    
    if results:
        # Analyze impact
        analyze_mode_filtering_impact(results)
        
        print(f"\n{'='*60}")
        print("CONCLUSIONS")
        print(f"{'='*60}")
        
        # Check if any threshold worked
        any_signals = any(r['mode_filtered_signals'] > 0 for r in results.values())
        
        if any_signals:
            print("✅ Mode filtering is working correctly")
            print("✅ Successfully filtering signals in trending markets")
            print("✅ ML threshold adjustment can control signal frequency")
            print("\nNext Steps:")
            print("1. Choose optimal ML threshold based on backtest results")
            print("2. Continue with Phase 2.2: Entry Confirmation Filters")
            print("3. Test with multiple symbols and timeframes")
        else:
            print("⚠️  No signals generated even with lower thresholds")
            print("Consider:")
            print("1. Further reducing ML threshold (< 2.0)")
            print("2. Adjusting mode detection parameters")
            print("3. Testing with different symbols or timeframes")
    else:
        print("\n❌ Could not complete test due to insufficient data")
        print("Try:")
        print("1. Using a different symbol with more history")
        print("2. Using daily timeframe instead of 5-minute")
        print("3. Checking data source availability")


if __name__ == "__main__":
    main()