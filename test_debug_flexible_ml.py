"""
Debug Flexible ML Signal Generation
===================================

Quick test to understand why flexible ML isn't generating signals.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging
import warnings
warnings.filterwarnings('ignore')

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from data.smart_data_manager import SmartDataManager
from scanner.flexible_bar_processor import FlexibleBarProcessor
from config.settings import TradingConfig


def debug_flexible_ml(symbol='RELIANCE'):
    """Debug flexible ML signal generation"""
    
    print(f"\n{'='*80}")
    print(f"DEBUG FLEXIBLE ML - {symbol}")
    print(f"{'='*80}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=90)
    
    if df is None or len(df) < 2500:
        print(f"Insufficient data: {len(df) if df is not None else 0} bars")
        return
    
    print(f"Data loaded: {len(df)} bars")
    
    # Simple config with minimal filters
    config = TradingConfig(
        source='close',
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        use_volatility_filter=False,
        use_regime_filter=False,
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
    
    # Track signals
    signal_changes = []
    predictions = []
    filter_states_log = []
    
    # Process bars
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'],
            row['close'], row['volume']
        )
        
        if i >= 2000 and result:  # After warmup
            # Track predictions
            if hasattr(result, 'flexible_prediction'):
                pred = result.flexible_prediction
            else:
                pred = result.prediction
                
            predictions.append({
                'bar': i,
                'prediction': pred,
                'signal': result.signal,
                'filter_all': result.filter_states.get('filter_all', False) if result.filter_states else False,
                'start_long': result.start_long_trade,
                'start_short': result.start_short_trade
            })
            
            # Track signal changes
            if len(predictions) > 1:
                prev_signal = predictions[-2]['signal']
                curr_signal = result.signal
                if prev_signal != curr_signal and curr_signal != 0:
                    signal_changes.append({
                        'bar': i,
                        'from': prev_signal,
                        'to': curr_signal,
                        'prediction': pred,
                        'filter_all': result.filter_states.get('filter_all', False) if result.filter_states else False
                    })
            
            # Log filter states periodically
            if i % 100 == 0:
                filter_states_log.append({
                    'bar': i,
                    'states': result.filter_states if result.filter_states else {}
                })
    
    # Analysis
    print(f"\n{'='*60}")
    print("ANALYSIS")
    print(f"{'='*60}")
    
    # Prediction analysis
    if predictions:
        non_zero_preds = [p for p in predictions if p['prediction'] != 0]
        print(f"\nPredictions:")
        print(f"  Total predictions: {len(predictions)}")
        print(f"  Non-zero predictions: {len(non_zero_preds)}")
        
        if non_zero_preds:
            pred_values = [p['prediction'] for p in non_zero_preds]
            print(f"  Avg prediction: {np.mean(pred_values):.2f}")
            print(f"  Max prediction: {max(pred_values):.2f}")
            print(f"  Min prediction: {min(pred_values):.2f}")
            
            # Show samples
            print("\nSample predictions:")
            for p in non_zero_preds[:5]:
                print(f"  Bar {p['bar']}: pred={p['prediction']:.2f}, signal={p['signal']}, "
                      f"filter_all={p['filter_all']}, long={p['start_long']}, short={p['start_short']}")
    
    # Signal changes
    print(f"\nSignal changes: {len(signal_changes)}")
    if signal_changes:
        print("Sample signal changes:")
        for sc in signal_changes[:5]:
            print(f"  Bar {sc['bar']}: {sc['from']} -> {sc['to']}, "
                  f"pred={sc['prediction']:.2f}, filter_all={sc['filter_all']}")
    
    # Filter states
    print(f"\nFilter states (sample):")
    for fs in filter_states_log[:3]:
        print(f"  Bar {fs['bar']}: {fs['states']}")
    
    # Check specific attributes
    if hasattr(processor, '_prev_flexible_signal'):
        print(f"\nFinal flexible signal: {processor._prev_flexible_signal}")
    if hasattr(processor, '_last_flexible_entry_bar'):
        print(f"Last entry bar: {processor._last_flexible_entry_bar}")
    
    # Get flexible ML state
    if hasattr(processor, 'flexible_ml'):
        ml_state = processor.flexible_ml.get_state()
        print(f"\nFlexible ML state:")
        print(f"  Training size: {ml_state['training_size']}")
        print(f"  Predictions made: {ml_state['predictions_made']}")


def main():
    """Run debug test"""
    debug_flexible_ml('RELIANCE')


if __name__ == "__main__":
    main()