"""
Test Phase 3 Flexible ML Training Fix
=====================================

Verify that the flexible ML system is properly receiving training data
and generating predictions after the warmup period.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging
import warnings
warnings.filterwarnings('ignore')

# Enable info logging to see training progress
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from data.smart_data_manager import SmartDataManager
from scanner.flexible_bar_processor import FlexibleBarProcessor
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
from config.constants import PREDICTION_LENGTH


def test_flexible_ml_training(symbol='RELIANCE'):
    """Test flexible ML training integration"""
    
    print(f"\n{'='*80}")
    print(f"TESTING FLEXIBLE ML TRAINING - {symbol}")
    print(f"{'='*80}")
    
    # Get sufficient data for ML warmup
    data_manager = SmartDataManager()
    days_needed = 90  # Ensure we get 2000+ bars
    
    print(f"\nFetching {days_needed} days of data to ensure 2000+ bars...")
    df = data_manager.get_data(symbol, interval='5minute', days=days_needed)
    
    if df is None:
        print("❌ Failed to fetch data")
        return
    
    print(f"✅ Data loaded: {len(df)} bars")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    
    # Check if we have enough data
    min_bars_needed = 2000 + PREDICTION_LENGTH + 100  # Warmup + training buffer + test period
    if len(df) < min_bars_needed:
        print(f"\n❌ Insufficient data: Have {len(df)}, need {min_bars_needed} bars")
        print("The flexible ML requires:")
        print(f"  - 2000 bars for warmup")
        print(f"  - {PREDICTION_LENGTH} bars for training buffer")
        print(f"  - Additional bars for testing")
        return
    
    # Create configuration
    config = TradingConfig(
        source='close',
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        use_volatility_filter=False,
        use_regime_filter=False,  # Disable filters for more signals
        use_adx_filter=False
    )
    
    # Create flexible processor
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
    
    print(f"\n{'='*60}")
    print("PROCESSING BARS")
    print(f"{'='*60}")
    
    # Track ML state
    ml_states = []
    predictions = []
    first_prediction_bar = None
    
    # Process all bars
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'],
            row['close'], row['volume']
        )
        
        # Log progress every 500 bars
        if i > 0 and i % 500 == 0:
            print(f"Processed {i} bars...")
        
        # Track ML state periodically
        if i % 100 == 0 and hasattr(processor, 'flexible_ml'):
            state = processor.flexible_ml.get_state()
            ml_states.append({
                'bar': i,
                'training_size': state['training_size'],
                'predictions_made': state['predictions_made']
            })
        
        # Track predictions after warmup
        if i >= 2000 and result:
            if hasattr(result, 'flexible_prediction'):
                pred = result.flexible_prediction
            else:
                pred = result.prediction
                
            if pred != 0:
                predictions.append({
                    'bar': i,
                    'prediction': pred
                })
                
                if first_prediction_bar is None:
                    first_prediction_bar = i
                    print(f"\n✅ First non-zero prediction at bar {i}: {pred:.2f}")
    
    # Display results
    print(f"\n{'='*60}")
    print("FLEXIBLE ML TRAINING RESULTS")
    print(f"{'='*60}")
    
    # Show ML state progression
    print("\nML State Progression:")
    for state in ml_states[::5]:  # Show every 5th state
        print(f"  Bar {state['bar']:4d}: Training size = {state['training_size']:4d}, "
              f"Predictions = {state['predictions_made']:4d}")
    
    # Final state
    if hasattr(processor, 'flexible_ml'):
        final_state = processor.flexible_ml.get_state()
        print(f"\nFinal ML State:")
        print(f"  Training size: {final_state['training_size']}")
        print(f"  Predictions made: {final_state['predictions_made']}")
        print(f"  Features used: {final_state['n_features']}")
    
    # Prediction analysis
    if predictions:
        print(f"\nPrediction Analysis:")
        print(f"  Total non-zero predictions: {len(predictions)}")
        print(f"  First prediction at bar: {first_prediction_bar}")
        print(f"  Prediction rate: {len(predictions) / (len(df) - 2000) * 100:.1f}%")
        
        pred_values = [p['prediction'] for p in predictions]
        print(f"  Average strength: {np.mean([abs(p) for p in pred_values]):.2f}")
        print(f"  Max prediction: {max(pred_values):.2f}")
        print(f"  Min prediction: {min(pred_values):.2f}")
        
        # Show sample predictions
        print("\nSample Predictions:")
        for p in predictions[:5]:
            print(f"  Bar {p['bar']}: {p['prediction']:.2f}")
    else:
        print("\n❌ No predictions generated!")
        print("\nPossible issues:")
        print("1. Not enough training data accumulated")
        print("2. Training integration not working properly")
        print("3. Feature values might be invalid")
    
    # Check training buffer
    if hasattr(processor, 'training_buffer'):
        print(f"\nTraining buffer size: {len(processor.training_buffer)}")
        print(f"Expected size: {PREDICTION_LENGTH + 1}")
    
    return len(predictions) > 0


def main():
    """Run training fix verification"""
    
    print("\n" + "="*80)
    print("PHASE 3 FLEXIBLE ML - TRAINING FIX VERIFICATION")
    print("="*80)
    
    # Test on single symbol first
    success = test_flexible_ml_training('RELIANCE')
    
    if success:
        print("\n✅ Flexible ML training integration is working!")
        
        # Quick test on other symbols
        print("\nTesting other symbols...")
        for symbol in ['INFY', 'TCS']:
            try:
                df = SmartDataManager().get_data(symbol, interval='5minute', days=90)
                if df is not None and len(df) > 2100:
                    print(f"  {symbol}: {len(df)} bars available ✅")
                else:
                    print(f"  {symbol}: Insufficient data ❌")
            except Exception as e:
                print(f"  {symbol}: Error - {str(e)}")
    else:
        print("\n❌ Flexible ML training integration needs debugging")
        print("\nNext steps:")
        print("1. Check if training_buffer is being populated")
        print("2. Verify label generation logic")
        print("3. Ensure flexible_ml.add_training_data() is called")
        print("4. Check feature values are valid")


if __name__ == "__main__":
    main()