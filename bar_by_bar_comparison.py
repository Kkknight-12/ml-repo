#!/usr/bin/env python3
"""
Bar-by-bar comparison tool for Pine Script vs Python debugging
Exports detailed state at each bar for comparison
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import json
import csv
from typing import Dict, List, Optional
import pytz

from config.settings import TradingConfig
from scanner import BarProcessor
from data.zerodha_client import ZerodhaClient
from core.pine_functions import nz, na


class BarByBarComparison:
    """Export detailed state at each bar for Pine Script comparison"""
    
    def __init__(self):
        # Pine Script default configuration
        self.config = TradingConfig(
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
            sma_period=200,
            show_bar_colors=True,
            show_bar_predictions=True,
            use_atr_offset=False,
            bar_predictions_offset=0.0,
            show_exits=False,
            use_dynamic_exits=False
        )
        
    def export_detailed_state(self, symbol: str, df: pd.DataFrame, 
                            output_file: str = None, 
                            start_bar: int = 1990, 
                            end_bar: int = 2200):
        """
        Export detailed state for each bar
        
        Args:
            symbol: Stock symbol
            df: DataFrame with OHLCV data
            output_file: Output CSV filename
            start_bar: Starting bar index (default: before warmup end)
            end_bar: Ending bar index (default: after first Pine signal)
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"bar_by_bar_{symbol}_{timestamp}.csv"
        
        print(f"\n📊 Exporting Bar-by-Bar Comparison for {symbol}")
        print(f"   Bars {start_bar} to {end_bar}")
        print(f"   Output: {output_file}")
        
        # Initialize processor
        processor = BarProcessor(self.config, symbol, "day", debug_mode=True)
        
        # Track detailed state
        detailed_data = []
        
        # Process each bar
        for idx, row in df.iterrows():
            if idx < start_bar:
                # Still need to process for state building
                result = processor.process_bar(
                    nz(row['open'], row['close']),
                    nz(row['high'], row['close']),
                    nz(row['low'], row['close']),
                    nz(row['close'], 0.0),
                    nz(row['volume'], 0.0)
                )
                continue
            
            if idx > end_bar:
                break
            
            # Process bar
            open_price = nz(row['open'], row['close'])
            high = nz(row['high'], row['close'])
            low = nz(row['low'], row['close'])
            close = nz(row['close'], 0.0)
            volume = nz(row['volume'], 0.0)
            
            result = processor.process_bar(open_price, high, low, close, volume)
            
            if result:
                # Get additional state from processor
                ml_model = processor.ml_model
                
                # Get feature values
                feature_arrays = processor.feature_arrays
                f1_current = feature_arrays.f1[-1] if feature_arrays.f1 else 0.0
                f2_current = feature_arrays.f2[-1] if feature_arrays.f2 else 0.0
                f3_current = feature_arrays.f3[-1] if feature_arrays.f3 else 0.0
                f4_current = feature_arrays.f4[-1] if feature_arrays.f4 else 0.0
                f5_current = feature_arrays.f5[-1] if feature_arrays.f5 else 0.0
                
                # Get filter details
                filter_states = result.filter_states
                
                # Get ML state
                neighbor_count = len(ml_model.predictions)
                y_train_size = len(ml_model.y_train_array)
                
                # Get signal history
                signal_history = processor.signal_history[:5] if hasattr(processor, 'signal_history') else []
                
                # Get kernel state if available
                kernel_estimate = 0.0  # Would need to extract from kernel calculation
                
                # Create detailed row
                row_data = {
                    # Basic data
                    'bar_index': result.bar_index,
                    'date': row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else f"Bar_{idx}",
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close,
                    'volume': volume,
                    
                    # ML State
                    'ml_prediction': result.prediction,
                    'signal': result.signal,
                    'neighbor_count': neighbor_count,
                    'y_train_size': y_train_size,
                    'is_warmup': result.bar_index < self.config.max_bars_back,
                    
                    # Features
                    'f1_rsi': f1_current,
                    'f2_wt': f2_current,
                    'f3_cci': f3_current,
                    'f4_adx': f4_current,
                    'f5_rsi9': f5_current,
                    
                    # Filters
                    'filter_volatility': filter_states.get('volatility', False),
                    'filter_regime': filter_states.get('regime', False),
                    'filter_adx': filter_states.get('adx', False),
                    'filter_all': all(filter_states.values()),
                    
                    # Signals
                    'start_long': result.start_long_trade,
                    'start_short': result.start_short_trade,
                    'end_long': result.end_long_trade,
                    'end_short': result.end_short_trade,
                    
                    # Signal history
                    'signal_history': ','.join(map(str, signal_history)),
                    
                    # Additional context
                    'prediction_strength': result.prediction_strength,
                    'is_early_flip': result.is_early_signal_flip
                }
                
                detailed_data.append(row_data)
                
                # Progress update
                if idx % 50 == 0:
                    print(f"   Processed bar {idx}: ML={result.prediction:.1f}, "
                          f"Signal={result.signal}, Filters={sum(filter_states.values())}/3")
        
        # Export to CSV
        if detailed_data:
            with open(output_file, 'w', newline='') as f:
                fieldnames = detailed_data[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(detailed_data)
            
            print(f"\n✅ Exported {len(detailed_data)} bars to {output_file}")
            
            # Summary statistics
            df_export = pd.DataFrame(detailed_data)
            
            print("\n📊 Export Summary:")
            print(f"   Total bars: {len(df_export)}")
            print(f"   Warmup bars: {(df_export['is_warmup'] == True).sum()}")
            print(f"   Bars with predictions: {(df_export['ml_prediction'] != 0).sum()}")
            print(f"   Long entries: {df_export['start_long'].sum()}")
            print(f"   Short entries: {df_export['start_short'].sum()}")
            
            # Filter pass rates
            total_after_warmup = (df_export['is_warmup'] == False).sum()
            if total_after_warmup > 0:
                vol_pass = df_export[~df_export['is_warmup']]['filter_volatility'].sum()
                reg_pass = df_export[~df_export['is_warmup']]['filter_regime'].sum()
                all_pass = df_export[~df_export['is_warmup']]['filter_all'].sum()
                
                print(f"\n   Filter Pass Rates (after warmup):")
                print(f"   Volatility: {vol_pass}/{total_after_warmup} ({vol_pass/total_after_warmup*100:.1f}%)")
                print(f"   Regime: {reg_pass}/{total_after_warmup} ({reg_pass/total_after_warmup*100:.1f}%)")
                print(f"   All: {all_pass}/{total_after_warmup} ({all_pass/total_after_warmup*100:.1f}%)")
            
            return output_file
        
        return None
    
    def compare_with_pine_export(self, python_csv: str, pine_csv: str):
        """
        Compare Python export with Pine Script export
        Assumes Pine Script exports similar fields
        """
        print(f"\n🔍 Comparing Detailed Exports")
        print(f"   Python: {python_csv}")
        print(f"   Pine Script: {pine_csv}")
        
        # This would require Pine Script to export similar data
        # For now, we'll focus on key fields that Pine Script typically exports
        
        print("\n⚠️  Note: Pine Script needs to export matching fields for comparison")
        print("   Key fields to compare:")
        print("   - ml_prediction")
        print("   - signal")
        print("   - filter states")
        print("   - entry/exit signals")


def main():
    """Test the bar-by-bar comparison tool"""
    
    # Initialize comparison tool
    comparator = BarByBarComparison()
    
    # Check for saved session
    if not os.path.exists('.kite_session.json'):
        print("❌ No access token found. Run auth_helper.py first")
        return
    
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
    
    os.environ['KITE_ACCESS_TOKEN'] = access_token
    
    # Initialize Zerodha client
    client = ZerodhaClient(use_cache=True, cache_dir="data_cache")
    
    # Fetch data
    symbol = 'ICICIBANK'
    print(f"\n📊 Fetching data for {symbol}...")
    
    # Get data from cache
    ist = pytz.timezone('Asia/Kolkata')
    to_date = datetime.now(ist) - timedelta(days=1)
    from_date = ist.localize(datetime(2000, 1, 26))
    
    days_from_today = (datetime.now() - from_date.replace(tzinfo=None)).days
    data = client.get_historical_data(symbol=symbol, interval="day", days=days_from_today)
    
    if data:
        df = pd.DataFrame(data)
        df = df.sort_values('date').reset_index(drop=True)
        print(f"✅ Loaded {len(df)} bars")
        
        # Export detailed state around warmup transition
        # Bars 1990-2200 cover warmup end and first signals
        output_file = comparator.export_detailed_state(
            symbol, df, 
            start_bar=1990,  # Before warmup end
            end_bar=2200     # After Pine Script's first signal
        )
        
        print(f"\n📌 Next Steps:")
        print(f"1. Create similar export in Pine Script")
        print(f"2. Compare ml_prediction, signal, and filter states")
        print(f"3. Identify where behavior diverges")
        print(f"4. Focus debugging on specific bars where differences occur")
    else:
        print("❌ Failed to fetch data")


if __name__ == "__main__":
    main()