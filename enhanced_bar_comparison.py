#!/usr/bin/env python3
"""
Enhanced bar-by-bar comparison tool for Pine Script vs Python debugging
Creates side-by-side comparison with Pine Script format
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pandas as pd
import csv
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from core.pine_functions import nz
from ml.lorentzian_knn_fixed_corrected import LorentzianKNNFixedCorrected
from core.kernel_functions import rational_quadratic


class EnhancedBarComparison:
    """Enhanced side-by-side comparison with Pine Script"""
    
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
        
    def export_pine_script_format(self, symbol: str = 'ICICIBANK', 
                                start_bar: int = 1995, 
                                end_bar: int = 2050) -> str:
        """
        Export data in Pine Script debugging format
        
        Args:
            symbol: Stock symbol
            start_bar: Starting bar index
            end_bar: Ending bar index
            
        Returns:
            Output filename
        """
        # Read from cache
        db_path = os.path.join("data_cache", "market_data.db")
        if not os.path.exists(db_path):
            print(f"❌ Cache database not found at {db_path}")
            return None
        
        # Load data
        with sqlite3.connect(db_path) as conn:
            query = """
            SELECT date, open, high, low, close, volume
            FROM market_data
            WHERE symbol = ? AND interval = 'day'
            ORDER BY date
            """
            df = pd.read_sql_query(query, conn, params=(symbol,), parse_dates=['date'])
        
        print(f"✅ Loaded {len(df)} bars from cache")
        df = df.reset_index(drop=True)
        
        # Initialize processor
        processor = EnhancedBarProcessor(self.config, symbol, "day", debug_mode=True)
        
        # Output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"pine_script_comparison_{symbol}_{timestamp}.csv"
        
        print(f"\n📊 Exporting Pine Script Comparison Format")
        print(f"   Symbol: {symbol}")
        print(f"   Bars: {start_bar} to {end_bar}")
        print(f"   Warmup ends at bar: {self.config.max_bars_back}")
        
        # Process all bars and collect data
        export_data = []
        
        # Track important transitions
        first_ml_prediction_bar = None
        first_entry_bar = None
        
        for idx, row in df.iterrows():
            # Process bar
            result = processor.process_bar(
                nz(row['open'], row['close']),
                nz(row['high'], row['close']),
                nz(row['low'], row['close']),
                nz(row['close'], 0.0),
                nz(row['volume'], 0.0)
            )
            
            # Skip bars before our export range
            if idx < start_bar:
                continue
            
            if idx > end_bar:
                break
            
            if result:
                # Get detailed state
                ml_model = processor.ml_model
                
                # Get feature values directly
                feature_arrays = processor.feature_arrays
                
                # Get kernel values if using kernel filter
                kernel_estimate = 0.0
                kernel_upper = 0.0
                kernel_lower = 0.0
                
                if self.config.use_kernel_filter and hasattr(processor.bars, '_close') and len(processor.bars._close) >= 2:
                    # Calculate kernel regression
                    close_series = processor.bars._close
                    lookback = min(self.config.kernel_lookback, len(close_series))
                    
                    if lookback >= 2:
                        # Simply use the kernel function with close prices
                        # rational_quadratic expects: src_values, lookback, relative_weight, start_at_bar
                        kernel_estimate = rational_quadratic(
                            close_series,  # src_values (newest first)
                            self.config.kernel_lookback,  # lookback
                            self.config.kernel_relative_weight,  # relative_weight
                            0  # start_at_bar
                        )
                
                # Get the actual neighbor predictions for debugging
                neighbor_predictions = ml_model.predictions.copy() if ml_model.predictions else []
                
                # Create row matching Pine Script debug format
                bar_data = {
                    # Bar identification
                    'bar': idx,
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'close': f"{row['close']:.2f}",
                    
                    # ML Core State
                    'pred': f"{result.prediction:.1f}",
                    'signal': result.signal,
                    'neighbors': len(ml_model.predictions),
                    'y_train_size': len(ml_model.y_train_array),
                    
                    # Neighbor details (for debugging)
                    'neighbor_preds': ','.join([str(int(p)) for p in neighbor_predictions]),
                    'pred_sum': sum(neighbor_predictions),
                    
                    # Features (rounded like Pine Script display)
                    'f1_rsi': f"{feature_arrays.f1[-1]:.1f}" if feature_arrays.f1 else "0.0",
                    'f2_wt': f"{feature_arrays.f2[-1]:.1f}" if feature_arrays.f2 else "0.0", 
                    'f3_cci': f"{feature_arrays.f3[-1]:.1f}" if feature_arrays.f3 else "0.0",
                    'f4_adx': f"{feature_arrays.f4[-1]:.1f}" if feature_arrays.f4 else "0.0",
                    'f5_rsi9': f"{feature_arrays.f5[-1]:.1f}" if feature_arrays.f5 else "0.0",
                    
                    # Filter states (1/0)
                    'filt_vol': 1 if result.filter_states.get('volatility', False) else 0,
                    'filt_reg': 1 if result.filter_states.get('regime', False) else 0,
                    'filt_adx': 1 if result.filter_states.get('adx', False) else 0,
                    'filt_all': 1 if all(result.filter_states.values()) else 0,
                    
                    # Kernel values
                    'kernel_est': f"{kernel_estimate:.2f}",
                    'kernel_bull': 1 if kernel_estimate > row['close'] else 0,
                    'kernel_bear': 1 if kernel_estimate < row['close'] else 0,
                    
                    # Entry/Exit signals
                    'start_long': 1 if result.start_long_trade else 0,
                    'start_short': 1 if result.start_short_trade else 0,
                    'end_long': 1 if result.end_long_trade else 0,
                    'end_short': 1 if result.end_short_trade else 0,
                    
                    # State flags
                    'warmup': 1 if idx < self.config.max_bars_back else 0,
                    'ml_enabled': 1 if idx >= self.config.max_bars_back else 0,
                }
                
                export_data.append(bar_data)
                
                # Track key transitions
                if first_ml_prediction_bar is None and result.prediction != 0 and idx >= self.config.max_bars_back:
                    first_ml_prediction_bar = idx
                    print(f"\n>>> First ML prediction at bar {idx} (date: {row['date'].strftime('%Y-%m-%d')})")
                    print(f"    Prediction: {result.prediction}")
                    print(f"    Neighbors: {neighbor_predictions}")
                
                if first_entry_bar is None and (result.start_long_trade or result.start_short_trade):
                    first_entry_bar = idx
                    entry_type = "LONG" if result.start_long_trade else "SHORT"
                    print(f"\n>>> First {entry_type} entry at bar {idx} (date: {row['date'].strftime('%Y-%m-%d')})")
                    print(f"    Prediction: {result.prediction}")
                    print(f"    Filters: Vol={bar_data['filt_vol']}, Reg={bar_data['filt_reg']}, All={bar_data['filt_all']}")
        
        # Export to CSV
        if export_data:
            with open(output_file, 'w', newline='') as f:
                fieldnames = export_data[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(export_data)
            
            print(f"\n✅ Exported {len(export_data)} bars to {output_file}")
            
            # Analysis summary
            df_export = pd.DataFrame(export_data)
            
            print("\n📊 Export Summary:")
            print(f"   Total bars exported: {len(df_export)}")
            print(f"   Warmup period bars: {(df_export['warmup'] == 1).sum()}")
            print(f"   ML enabled bars: {(df_export['ml_enabled'] == 1).sum()}")
            
            # Post-warmup analysis
            post_warmup = df_export[df_export['warmup'] == 0]
            if len(post_warmup) > 0:
                print(f"\n   Post-warmup statistics:")
                print(f"   - Bars with predictions: {(post_warmup['pred'] != '0.0').sum()}")
                print(f"   - Long entries: {post_warmup['start_long'].sum()}")
                print(f"   - Short entries: {post_warmup['start_short'].sum()}")
                
                print(f"\n   Filter pass rates:")
                # Convert filter columns to numeric to ensure proper calculation
                vol_pass_rate = pd.to_numeric(post_warmup['filt_vol'], errors='coerce').mean() * 100
                reg_pass_rate = pd.to_numeric(post_warmup['filt_reg'], errors='coerce').mean() * 100
                adx_pass_rate = pd.to_numeric(post_warmup['filt_adx'], errors='coerce').mean() * 100
                all_pass_rate = pd.to_numeric(post_warmup['filt_all'], errors='coerce').mean() * 100
                
                print(f"   - Volatility: {vol_pass_rate:.1f}%")
                print(f"   - Regime: {reg_pass_rate:.1f}%")
                print(f"   - ADX: {adx_pass_rate:.1f}%")
                print(f"   - All filters: {all_pass_rate:.1f}%")
            
            print(f"\n📌 Pine Script Comparison Format:")
            print(f"   This CSV matches Pine Script debug output format")
            print(f"   Key columns for comparison:")
            print(f"   - pred: ML prediction value")
            print(f"   - signal: Current signal state")
            print(f"   - neighbor_preds: Individual neighbor predictions")
            print(f"   - filt_*: Filter pass/fail states")
            print(f"   - start_long/short: Entry signals")
            
            # SUMMARY FOR QUICK REFERENCE
            print(f"\n" + "="*70)
            print("SUMMARY - BAR-BY-BAR COMPARISON EXPORT")
            print("="*70)
            print(f"Export Range: Bars {start_bar} to {end_bar}")
            print(f"Warmup Period: {(df_export['warmup'] == 1).sum()} bars")
            print(f"Post-Warmup: {(df_export['warmup'] == 0).sum()} bars")
            
            # ML Statistics
            post_warmup_data = df_export[df_export['warmup'] == 0]
            if len(post_warmup_data) > 0:
                print(f"\nML STATISTICS (Post-Warmup):")
                print(f"  Bars with predictions: {(post_warmup_data['pred'] != '0.0').sum()}")
                print(f"  Prediction range: {post_warmup_data[post_warmup_data['pred'] != '0.0']['pred'].min()} to {post_warmup_data[post_warmup_data['pred'] != '0.0']['pred'].max()}")
                print(f"  Neighbors accumulated: {post_warmup_data['neighbors'].max()}")
                
                print(f"\nFILTER PASS RATES:")
                # Convert filter columns to numeric to ensure proper calculation
                vol_rate = pd.to_numeric(post_warmup_data['filt_vol'], errors='coerce').mean() * 100
                reg_rate = pd.to_numeric(post_warmup_data['filt_reg'], errors='coerce').mean() * 100
                adx_rate = pd.to_numeric(post_warmup_data['filt_adx'], errors='coerce').mean() * 100
                all_rate = pd.to_numeric(post_warmup_data['filt_all'], errors='coerce').mean() * 100
                
                print(f"  Volatility: {vol_rate:.1f}%")
                print(f"  Regime: {reg_rate:.1f}%")
                print(f"  ADX: {adx_rate:.1f}%")
                print(f"  All Combined: {all_rate:.1f}%")
                
                print(f"\nENTRY SIGNALS:")
                print(f"  Long entries: {post_warmup_data['start_long'].sum()}")
                print(f"  Short entries: {post_warmup_data['start_short'].sum()}")
                print(f"  Total entries: {post_warmup_data['start_long'].sum() + post_warmup_data['start_short'].sum()}")
                
                # First signal info
                first_long = post_warmup_data[post_warmup_data['start_long'] == 1]
                first_short = post_warmup_data[post_warmup_data['start_short'] == 1]
                
                if not first_long.empty:
                    print(f"\n  First LONG entry:")
                    print(f"    Bar: {first_long.iloc[0]['bar']}")
                    print(f"    Date: {first_long.iloc[0]['date']}")
                    print(f"    Bars after warmup: {first_long.iloc[0]['bar'] - self.config.max_bars_back}")
                
                if not first_short.empty:
                    print(f"\n  First SHORT entry:")
                    print(f"    Bar: {first_short.iloc[0]['bar']}")
                    print(f"    Date: {first_short.iloc[0]['date']}")
                    print(f"    Bars after warmup: {first_short.iloc[0]['bar'] - self.config.max_bars_back}")
            
            print("="*70)
            
            return output_file
        
        return None
    
    def create_comparison_report(self, python_csv: str, pine_csv: str = None):
        """
        Create detailed comparison report between Python and Pine Script
        
        Args:
            python_csv: Python export CSV file
            pine_csv: Pine Script export CSV file (if available)
        """
        print(f"\n🔍 Creating Comparison Report")
        
        # Load Python data
        df_python = pd.read_csv(python_csv)
        print(f"   Loaded {len(df_python)} bars from Python export")
        
        if pine_csv and os.path.exists(pine_csv):
            # Load Pine Script data
            df_pine = pd.read_csv(pine_csv)
            print(f"   Loaded {len(df_pine)} bars from Pine Script export")
            
            # Merge on bar index
            df_merged = pd.merge(
                df_python, df_pine, 
                on='bar', 
                suffixes=('_py', '_pine'),
                how='inner'
            )
            
            print(f"\n📊 Comparison Results:")
            print(f"   Matched bars: {len(df_merged)}")
            
            # Compare key fields
            mismatches = []
            
            # ML predictions
            pred_matches = df_merged['pred_py'] == df_merged['pred_pine']
            print(f"\n   ML Predictions:")
            print(f"   - Matches: {pred_matches.sum()}/{len(df_merged)} ({pred_matches.mean()*100:.1f}%)")
            
            if not pred_matches.all():
                first_mismatch = df_merged[~pred_matches].iloc[0]
                mismatches.append(('prediction', first_mismatch['bar']))
                print(f"   - First mismatch at bar {first_mismatch['bar']}")
                print(f"     Python: {first_mismatch['pred_py']}, Pine: {first_mismatch['pred_pine']}")
            
            # Signals
            signal_matches = df_merged['signal_py'] == df_merged['signal_pine']
            print(f"\n   Signals:")
            print(f"   - Matches: {signal_matches.sum()}/{len(df_merged)} ({signal_matches.mean()*100:.1f}%)")
            
            # Filters
            for filt in ['vol', 'reg', 'adx', 'all']:
                filt_matches = df_merged[f'filt_{filt}_py'] == df_merged[f'filt_{filt}_pine']
                print(f"\n   Filter {filt.upper()}:")
                print(f"   - Matches: {filt_matches.sum()}/{len(df_merged)} ({filt_matches.mean()*100:.1f}%)")
                
                if not filt_matches.all():
                    first_mismatch = df_merged[~filt_matches].iloc[0]
                    mismatches.append((f'filter_{filt}', first_mismatch['bar']))
            
            # Entry signals
            long_matches = df_merged['start_long_py'] == df_merged['start_long_pine']
            short_matches = df_merged['start_short_py'] == df_merged['start_short_pine']
            
            print(f"\n   Entry Signals:")
            print(f"   - Long matches: {long_matches.sum()}/{len(df_merged)} ({long_matches.mean()*100:.1f}%)")
            print(f"   - Short matches: {short_matches.sum()}/{len(df_merged)} ({short_matches.mean()*100:.1f}%)")
            
            # Summary of issues
            if mismatches:
                print(f"\n⚠️  First mismatches by type:")
                for mismatch_type, bar in mismatches:
                    print(f"   - {mismatch_type}: bar {bar}")
            
            # Export detailed mismatch report
            if not pred_matches.all() or not signal_matches.all():
                mismatch_file = f"mismatches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df_mismatches = df_merged[~pred_matches | ~signal_matches]
                df_mismatches.to_csv(mismatch_file, index=False)
                print(f"\n💾 Saved detailed mismatches to: {mismatch_file}")
        
        else:
            print("\n⚠️  No Pine Script export provided for comparison")
            print("   To create Pine Script export, add this to your Pine Script:")
            print("   // Debug export code")
            print('   if barstate.islast')
            print('       str = ""')
            print('       for i = 0 to min(200, bar_index)')
            print('           str := str + tostring(bar_index[i]) + "," +')
            print('                 tostring(prediction[i]) + "," +') 
            print('                 tostring(signal[i]) + "\\n"')
            print('       label.new(bar_index, high, str)')


def main():
    """Run the enhanced bar comparison tool"""
    
    # Initialize comparison tool
    comparator = EnhancedBarComparison()
    
    # Export Python data in Pine Script format
    print("\n=== Enhanced Bar-by-Bar Comparison Tool ===")
    
    # Export bars around warmup transition
    # Default: bars 1995-2050 to capture warmup end and first signals
    output_file = comparator.export_pine_script_format(
        symbol='ICICIBANK',
        start_bar=1995,
        end_bar=2050
    )
    
    if output_file:
        print(f"\n✅ Export complete!")
        print(f"\n📌 Next steps:")
        print(f"1. Export similar data from Pine Script")
        print(f"2. Place Pine Script export in same directory")
        print(f"3. Run comparison: python enhanced_bar_comparison.py --compare")
        
        # If --compare flag is provided, run comparison
        if len(sys.argv) > 1 and sys.argv[1] == '--compare':
            pine_file = input("\nEnter Pine Script CSV filename: ")
            if pine_file:
                comparator.create_comparison_report(output_file, pine_file)
    
    else:
        print("❌ Export failed")


if __name__ == "__main__":
    main()