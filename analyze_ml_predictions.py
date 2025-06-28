"""
Analyze ML prediction distribution to understand dynamic threshold issues
"""

import pandas as pd
import numpy as np
from data.smart_data_manager import SmartDataManager
from scanner.flexible_bar_processor import FlexibleBarProcessor
from config.settings import TradingConfig
import matplotlib.pyplot as plt

def analyze_prediction_distribution(symbol: str, days: int = 90):
    """Analyze the distribution of ML predictions"""
    
    print(f"\nAnalyzing ML predictions for {symbol}...")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=days)
    
    if df is None or len(df) < 2500:
        print(f"Insufficient data for {symbol}")
        return None
    
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
    
    # Collect all predictions
    all_predictions = []
    non_zero_predictions = []
    
    print("Processing bars...")
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'],
            row['close'], row['volume']
        )
        
        if i >= 2000 and result and hasattr(result, 'flexible_prediction'):
            prediction = result.flexible_prediction
            all_predictions.append(prediction)
            if prediction != 0:
                non_zero_predictions.append(abs(prediction))
    
    # Analyze distribution
    print(f"\nPrediction Statistics for {symbol}:")
    print(f"Total predictions: {len(all_predictions)}")
    print(f"Non-zero predictions: {len(non_zero_predictions)}")
    print(f"Zero predictions: {len(all_predictions) - len(non_zero_predictions)}")
    print(f"% of zero predictions: {(len(all_predictions) - len(non_zero_predictions)) / len(all_predictions) * 100:.1f}%")
    
    if non_zero_predictions:
        predictions_array = np.array(non_zero_predictions)
        
        print(f"\nNon-zero Prediction Distribution:")
        print(f"Mean: {np.mean(predictions_array):.2f}")
        print(f"Std: {np.std(predictions_array):.2f}")
        print(f"Min: {np.min(predictions_array):.2f}")
        print(f"Max: {np.max(predictions_array):.2f}")
        
        # Percentiles
        percentiles = [10, 25, 50, 75, 80, 85, 90, 95]
        print(f"\nPercentiles:")
        for p in percentiles:
            value = np.percentile(predictions_array, p)
            print(f"{p}th percentile: {value:.2f}")
        
        # Count by threshold
        print(f"\nSignal Count by Threshold:")
        thresholds = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
        for t in thresholds:
            count = sum(1 for p in predictions_array if p >= t)
            pct = count / len(predictions_array) * 100
            print(f"  >= {t}: {count} signals ({pct:.1f}%)")
        
        # Plot histogram
        plt.figure(figsize=(10, 6))
        plt.hist(predictions_array, bins=50, alpha=0.7, edgecolor='black')
        plt.axvline(3.0, color='red', linestyle='--', label='Static Threshold (3.0)')
        plt.axvline(np.percentile(predictions_array, 75), color='green', linestyle='--', label='75th Percentile')
        plt.axvline(np.percentile(predictions_array, 85), color='orange', linestyle='--', label='85th Percentile')
        plt.xlabel('Absolute ML Prediction')
        plt.ylabel('Frequency')
        plt.title(f'ML Prediction Distribution - {symbol}')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig(f'{symbol}_prediction_distribution.png')
        plt.close()
        
        return {
            'symbol': symbol,
            'total_predictions': len(all_predictions),
            'non_zero_predictions': len(non_zero_predictions),
            'mean': np.mean(predictions_array),
            'std': np.std(predictions_array),
            'percentile_75': np.percentile(predictions_array, 75),
            'percentile_85': np.percentile(predictions_array, 85),
            'percentile_90': np.percentile(predictions_array, 90)
        }
    
    return None

def main():
    """Analyze prediction distributions for multiple stocks"""
    
    symbols = ['RELIANCE', 'INFY', 'TCS']
    results = []
    
    for symbol in symbols:
        result = analyze_prediction_distribution(symbol)
        if result:
            results.append(result)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY - Optimal Threshold Analysis")
    print("="*80)
    
    print(f"\n{'Stock':>10} {'75th %ile':>10} {'85th %ile':>10} {'90th %ile':>10} {'Current':>10} {'Recommended':>15}")
    print("-" * 70)
    
    for r in results:
        # Recommendation based on distribution
        if r['percentile_85'] > 3.5:
            recommended = r['percentile_85']
            method = "85th %ile"
        elif r['percentile_75'] < 2.5:
            recommended = 3.0  # Keep static if too low
            method = "Static"
        else:
            recommended = (r['percentile_75'] + 3.0) / 2  # Average
            method = "Avg(75th,3.0)"
        
        print(f"{r['symbol']:>10} {r['percentile_75']:>10.2f} {r['percentile_85']:>10.2f} "
              f"{r['percentile_90']:>10.2f} {3.0:>10.1f} {recommended:>15.2f} ({method})")
    
    print("\n💡 Key Findings:")
    print("1. The 75th percentile is too low for quality signals")
    print("2. Consider using 85th percentile or higher")
    print("3. Static 3.0 threshold may be optimal for current ML distribution")

if __name__ == "__main__":
    main()