#!/usr/bin/env python3
"""
Export bar states for debugging signal differences
Reads directly from cache to avoid kiteconnect dependency
"""
import sqlite3
import pandas as pd
import csv
from datetime import datetime
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import TradingConfig
from scanner import BarProcessor
from core.pine_functions import nz


def export_bar_states_from_cache():
    """Export detailed bar states using cached data"""
    
    # Read from cache
    db_path = os.path.join("data_cache", "market_data.db")
    if not os.path.exists(db_path):
        print(f"❌ Cache database not found at {db_path}")
        return
    
    # Load ICICIBANK data from cache
    with sqlite3.connect(db_path) as conn:
        query = """
        SELECT date, open, high, low, close, volume
        FROM market_data
        WHERE symbol = 'ICICIBANK' AND interval = 'day'
        ORDER BY date
        """
        df = pd.read_sql_query(query, conn, parse_dates=['date'])
    
    print(f"✅ Loaded {len(df)} bars from cache")
    
    # Reset index to use as bar numbers
    df = df.reset_index(drop=True)
    
    # Pine Script configuration
    config = TradingConfig(
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        color_compression=1,
        source='close',
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        regime_threshold=-0.1,
        adx_threshold=20,
        use_kernel_filter=True,
        use_kernel_smoothing=False,
        kernel_lookback=8,
        kernel_relative_weight=8.0,
        kernel_regression_level=25,
        kernel_lag=2,
        use_ema_filter=False,
        ema_period=200,
        use_sma_filter=False,
        sma_period=200
    )
    
    # Initialize processor
    processor = BarProcessor(config, "ICICIBANK", "day", debug_mode=False)
    
    # Export bars around warmup transition and first signals
    start_bar = 1990  # Before warmup ends at 2000
    end_bar = 2200    # After Pine Script's first signal
    
    output_file = f"icicibank_bar_states_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    print(f"\n📊 Exporting bars {start_bar} to {end_bar}")
    print(f"   Warmup ends at bar: {config.max_bars_back}")
    
    # Process all bars but only export the range we care about
    export_data = []
    
    for idx, row in df.iterrows():
        # Process bar
        result = processor.process_bar(
            nz(row['open'], row['close']),
            nz(row['high'], row['close']),
            nz(row['low'], row['close']),
            nz(row['close'], 0.0),
            nz(row['volume'], 0.0)
        )
        
        # Only export bars in our range
        if result and start_bar <= idx <= end_bar:
            # Get ML model state
            ml_model = processor.ml_model
            
            # Extract state
            bar_state = {
                'bar_index': result.bar_index,
                'date': row['date'].strftime('%Y-%m-%d'),
                'close': row['close'],
                
                # ML State
                'prediction': result.prediction,
                'signal': result.signal,
                'neighbors': len(ml_model.predictions),
                'training_size': len(ml_model.y_train_array),
                
                # Filters
                'filter_vol': int(result.filter_states.get('volatility', False)),
                'filter_reg': int(result.filter_states.get('regime', False)),
                'filter_adx': int(result.filter_states.get('adx', False)),
                'filter_all': int(all(result.filter_states.values())),
                
                # Entries
                'entry_long': int(result.start_long_trade),
                'entry_short': int(result.start_short_trade),
                
                # Signal history
                'signal_prev': processor.signal_history[0] if processor.signal_history else 0,
                
                # Features (last values)
                'f1_last': processor.feature_arrays.f1[-1] if processor.feature_arrays.f1 else 0,
                'f2_last': processor.feature_arrays.f2[-1] if processor.feature_arrays.f2 else 0,
                'f3_last': processor.feature_arrays.f3[-1] if processor.feature_arrays.f3 else 0,
                'f4_last': processor.feature_arrays.f4[-1] if processor.feature_arrays.f4 else 0,
                'f5_last': processor.feature_arrays.f5[-1] if processor.feature_arrays.f5 else 0,
            }
            
            export_data.append(bar_state)
            
            # Show key transitions
            if idx == config.max_bars_back:
                print(f"\n>>> BAR {idx}: WARMUP ENDS <<<")
                print(f"   Prediction: {result.prediction}")
                print(f"   Signal: {result.signal}")
                print(f"   Filters: Vol={bar_state['filter_vol']}, Reg={bar_state['filter_reg']}, All={bar_state['filter_all']}")
            
            if result.start_long_trade or result.start_short_trade:
                entry_type = "LONG" if result.start_long_trade else "SHORT"
                print(f"\n>>> BAR {idx}: {entry_type} ENTRY <<<")
                print(f"   Date: {row['date'].strftime('%Y-%m-%d')}")
                print(f"   Price: ₹{row['close']:.2f}")
                print(f"   Prediction: {result.prediction}")
                print(f"   Filters: Vol={bar_state['filter_vol']}, Reg={bar_state['filter_reg']}, All={bar_state['filter_all']}")
    
    # Export to CSV
    if export_data:
        with open(output_file, 'w', newline='') as f:
            fieldnames = export_data[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(export_data)
        
        print(f"\n✅ Exported {len(export_data)} bars to {output_file}")
        
        # Summary
        df_export = pd.DataFrame(export_data)
        entries = df_export['entry_long'].sum() + df_export['entry_short'].sum()
        
        print(f"\n📊 Summary:")
        print(f"   Total entries in range: {entries}")
        print(f"   Filter pass rates:")
        
        # Calculate pass rates after warmup
        after_warmup = df_export[df_export['bar_index'] >= config.max_bars_back]
        if len(after_warmup) > 0:
            print(f"   - Volatility: {after_warmup['filter_vol'].mean()*100:.1f}%")
            print(f"   - Regime: {after_warmup['filter_reg'].mean()*100:.1f}%")
            print(f"   - All filters: {after_warmup['filter_all'].mean()*100:.1f}%")
        
        return output_file
    
    return None


if __name__ == "__main__":
    export_bar_states_from_cache()