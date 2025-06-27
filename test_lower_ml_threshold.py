"""
Test with Lower ML Threshold
============================

Test if lowering ML threshold generates signals.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from data.smart_data_manager import SmartDataManager
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from scanner.ml_quality_filter import MLQualityFilter
from config.settings import TradingConfig


def test_ml_thresholds():
    """Test different ML thresholds to find working configuration"""
    
    print("="*60)
    print("TESTING ML THRESHOLDS")
    print("="*60)
    
    # Get data
    data_manager = SmartDataManager()
    symbol = 'RELIANCE'
    df = data_manager.get_data(symbol, interval='5minute', days=90)
    
    if df is None or len(df) < 2000:
        print(f"⚠️  Insufficient data: {len(df) if df is not None else 0} bars")
        return
    
    print(f"\nData: {len(df)} bars")
    
    # Use minimal config to reduce filtering
    config = TradingConfig(
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        use_volatility_filter=False,
        use_regime_filter=False,
        use_adx_filter=False,
        use_kernel_filter=True,  # Keep kernel for ML
        use_ema_filter=False,
        use_sma_filter=False
    )
    
    # Create processor
    processor = EnhancedBarProcessor(
        config=config,
        symbol=symbol,
        timeframe='5minute'
    )
    
    # Test different ML thresholds
    thresholds = [3.0, 2.5, 2.0, 1.5, 1.0, 0.5]
    results = {}
    
    print("\nProcessing bars...")
    
    # Collect all raw signals first
    raw_signals = []
    ml_predictions = []
    
    for idx, row in df.iterrows():
        result = processor.process_bar(
            open_price=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume']
        )
        
        if result:
            if result.prediction != 0:
                ml_predictions.append({
                    'timestamp': idx,
                    'prediction': result.prediction,
                    'bar_index': len(ml_predictions) + 1
                })
            
            if result.signal != 0:
                raw_signals.append({
                    'timestamp': idx,
                    'signal': result.signal,
                    'prediction': result.prediction,
                    'filter_states': result.filter_states,
                    'bar_index': len(raw_signals) + 1
                })
    
    print(f"\nML Predictions (non-zero): {len(ml_predictions)}")
    if ml_predictions:
        print(f"  First prediction at bar: {ml_predictions[0]['bar_index']}")
        print(f"  Prediction values: {[p['prediction'] for p in ml_predictions[:5]]}")
    
    print(f"\nRaw signals: {len(raw_signals)}")
    if raw_signals:
        print(f"  First signal at bar: {raw_signals[0]['bar_index']}")
    
    # Test each threshold
    for threshold in thresholds:
        ml_filter = MLQualityFilter(min_confidence=threshold)
        filtered_count = 0
        
        for signal in raw_signals:
            signal_dict = {
                'timestamp': signal['timestamp'],
                'signal': signal['signal'],
                'prediction': signal['prediction'],
                'filter_states': signal['filter_states'],
                'features': {}
            }
            
            ml_signal = ml_filter.filter_signal(signal_dict, symbol)
            if ml_signal is not None:
                filtered_count += 1
        
        results[threshold] = filtered_count
        print(f"\nML Threshold {threshold}: {filtered_count} signals pass")
    
    # Recommendations
    print(f"\n{'='*50}")
    print("RECOMMENDATIONS")
    print(f"{'='*50}")
    
    optimal_found = False
    for threshold in thresholds:
        if results[threshold] >= 10:  # At least 10 signals
            print(f"\n✅ ML threshold {threshold} generates {results[threshold]} signals")
            print("   This is a viable threshold for testing")
            optimal_found = True
            break
    
    if not optimal_found:
        print("\n⚠️  No threshold generated sufficient signals")
        print("   Consider checking the ML model implementation")
        
        # Debug info
        if raw_signals:
            print(f"\n   Debug: First raw signal prediction = {raw_signals[0]['prediction']}")
            print(f"   Debug: Signal filter states = {raw_signals[0]['filter_states']}")


def main():
    """Run ML threshold test"""
    test_ml_thresholds()


if __name__ == "__main__":
    main()