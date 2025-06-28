"""
Test Dynamic ML Threshold Calculation
=====================================

Compare static threshold (3.0) vs dynamic threshold calculated from data
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from data.smart_data_manager import SmartDataManager
from scanner.flexible_bar_processor import FlexibleBarProcessor
from scanner.dynamic_threshold_calculator import DynamicThresholdCalculator, calculate_optimal_threshold_from_warmup
from config.settings import TradingConfig


def test_dynamic_threshold(symbol: str, days: int = 180):
    """Test dynamic threshold calculation"""
    
    print(f"\n{'='*80}")
    print(f"Testing Dynamic ML Threshold for {symbol}")
    print(f"{'='*80}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=days)
    
    if df is None or len(df) < 2500:
        print(f"Insufficient data for {symbol}")
        return None
    
    print(f"Data loaded: {len(df)} bars")
    
    # Configuration
    config = TradingConfig(
        source='close',
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        regime_threshold=-0.1
    )
    
    # Create processor
    processor = FlexibleBarProcessor(
        config=config,
        symbol=symbol,
        timeframe='5minute',
        use_flexible_ml=True,
        feature_config={
            'original_features': ['rsi', 'wt', 'cci', 'adx', 'features_4'],
            'phase3_features': ['fisher', 'vwm', 'order_flow'],
            'use_phase3': True
        }
    )
    
    # Initialize dynamic threshold calculator
    dynamic_calc = DynamicThresholdCalculator(lookback_period=500, percentile=75)
    
    # Collect predictions during warmup
    warmup_predictions = []
    all_predictions = []
    warmup_complete = False
    
    # Process bars and collect predictions
    print("\nProcessing bars and collecting ML predictions...")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'],
            row['close'], row['volume']
        )
        
        if i == 2000:
            warmup_complete = True
            print(f"Warmup complete. Collected {len(warmup_predictions)} predictions")
            
            # Calculate initial threshold from warmup
            if warmup_predictions:
                threshold_percentile = calculate_optimal_threshold_from_warmup(
                    warmup_predictions, method='percentile'
                )
                threshold_statistical = calculate_optimal_threshold_from_warmup(
                    warmup_predictions, method='statistical'
                )
                
                print(f"\nThreshold Calculations from Warmup:")
                print(f"  Percentile method (75th): {threshold_percentile:.2f}")
                print(f"  Statistical method (mean+std): {threshold_statistical:.2f}")
                print(f"  Static threshold: 3.00")
                
                # Show prediction distribution
                predictions_abs = [abs(p) for p in warmup_predictions]
                print(f"\nPrediction Distribution in Warmup:")
                print(f"  Mean: {np.mean(predictions_abs):.2f}")
                print(f"  Std: {np.std(predictions_abs):.2f}")
                print(f"  Min: {np.min(predictions_abs):.2f}")
                print(f"  Max: {np.max(predictions_abs):.2f}")
                print(f"  25th percentile: {np.percentile(predictions_abs, 25):.2f}")
                print(f"  50th percentile: {np.percentile(predictions_abs, 50):.2f}")
                print(f"  75th percentile: {np.percentile(predictions_abs, 75):.2f}")
                print(f"  90th percentile: {np.percentile(predictions_abs, 90):.2f}")
        
        if result and hasattr(result, 'flexible_prediction'):
            prediction = result.flexible_prediction
            all_predictions.append(prediction)
            
            if not warmup_complete:
                warmup_predictions.append(prediction)
            else:
                # Add to dynamic calculator
                dynamic_calc.add_prediction(prediction)
                
                # Update threshold every 100 bars
                if (i - 2000) % 100 == 0 and (i - 2000) > 0:
                    new_threshold = dynamic_calc.calculate_threshold()
                    stats = dynamic_calc.get_statistics()
                    if (i - 2000) % 500 == 0:  # Print every 500 bars
                        print(f"\nBar {i}: Dynamic threshold updated to {new_threshold:.2f}")
                        print(f"  Based on {stats['total_predictions']} predictions")
                        print(f"  Avg prediction: {stats['avg_prediction']:.2f}")
    
    # Final analysis
    print(f"\n{'='*60}")
    print("THRESHOLD COMPARISON ANALYSIS")
    print(f"{'='*60}")
    
    # Count signals at different thresholds
    predictions_abs = [abs(p) for p in all_predictions]
    thresholds_to_test = [1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
    
    print("\nSignal Count at Different Thresholds:")
    print(f"{'Threshold':>10} {'Signals':>10} {'% of Total':>12}")
    print("-" * 35)
    
    total_predictions = len(predictions_abs)
    for threshold in thresholds_to_test:
        signals = sum(1 for p in predictions_abs if p >= threshold)
        percentage = (signals / total_predictions * 100) if total_predictions > 0 else 0
        print(f"{threshold:>10.1f} {signals:>10} {percentage:>11.1f}%")
    
    # Recommend optimal threshold
    final_stats = dynamic_calc.get_statistics()
    dynamic_threshold = final_stats['current_threshold']
    percentile_threshold = np.percentile(predictions_abs, 75)
    
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print(f"{'='*60}")
    print(f"\n1. Dynamic Threshold (updates during trading): {dynamic_threshold:.2f}")
    print(f"2. Percentile Threshold (75th percentile): {percentile_threshold:.2f}")
    print(f"3. Static Threshold (current): 3.00")
    
    # Calculate expected impact
    signals_static = sum(1 for p in predictions_abs if p >= 3.0)
    signals_dynamic = sum(1 for p in predictions_abs if p >= dynamic_threshold)
    signals_percentile = sum(1 for p in predictions_abs if p >= percentile_threshold)
    
    print(f"\nExpected Signal Reduction:")
    print(f"  Static (3.0): {signals_static} signals")
    print(f"  Dynamic ({dynamic_threshold:.2f}): {signals_dynamic} signals ({(signals_dynamic/signals_static-1)*100:+.1f}%)")
    print(f"  Percentile ({percentile_threshold:.2f}): {signals_percentile} signals ({(signals_percentile/signals_static-1)*100:+.1f}%)")
    
    return {
        'symbol': symbol,
        'dynamic_threshold': dynamic_threshold,
        'percentile_threshold': percentile_threshold,
        'total_predictions': total_predictions,
        'prediction_stats': final_stats
    }


def main():
    """Test dynamic threshold on multiple stocks"""
    
    print("\n" + "="*80)
    print("DYNAMIC ML THRESHOLD ANALYSIS")
    print("Testing adaptive threshold calculation vs static 3.0")
    print("="*80)
    
    symbols = ['RELIANCE', 'INFY', 'TCS', 'AXISBANK']
    results = []
    
    for symbol in symbols:
        result = test_dynamic_threshold(symbol, days=90)
        if result:
            results.append(result)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY - RECOMMENDED THRESHOLDS BY STOCK")
    print("="*80)
    
    print(f"\n{'Stock':>10} {'Current':>10} {'Dynamic':>10} {'Percentile':>12} {'Recommendation':>15}")
    print("-" * 60)
    
    for result in results:
        symbol = result['symbol']
        dynamic = result['dynamic_threshold']
        percentile = result['percentile_threshold']
        
        # Recommendation based on volatility
        if symbol in ['RELIANCE', 'AXISBANK']:
            recommended = max(dynamic, percentile)  # Higher for volatile
            rec_type = "Higher"
        else:
            recommended = (dynamic + percentile) / 2  # Average for normal
            rec_type = "Average"
        
        print(f"{symbol:>10} {3.0:>10.1f} {dynamic:>10.2f} {percentile:>12.2f} {recommended:>15.2f} ({rec_type})")
    
    print("\n💡 Key Insights:")
    print("1. Each stock has a different optimal threshold based on its ML prediction distribution")
    print("2. Dynamic thresholds adapt to changing market conditions")
    print("3. Using stock-specific thresholds should improve signal quality")
    print("4. Volatile stocks (RELIANCE) need higher thresholds for better filtering")


if __name__ == "__main__":
    main()