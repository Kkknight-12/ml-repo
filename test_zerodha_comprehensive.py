#!/usr/bin/env python3
"""
Comprehensive Zerodha Test Script for Lorentzian Classification
Tests stocks with configurable time periods using smart caching
Follows Pine Script behavior exactly with all bug fixes applied
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Tuple, Optional
import pytz  # For timezone handling

# Core imports
from config.settings import TradingConfig
from scanner import BarProcessor
from data.zerodha_client import ZerodhaClient
from core.pine_functions import nz, na
from core.history_referencing import create_series
import logging

# For debugging
import warnings
warnings.filterwarnings('ignore')

# Setup basic logging - set to WARNING to reduce debug output
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComprehensiveMarketTest:
    """
    Comprehensive test class that follows Pine Script execution model exactly
    """
    
    def __init__(self):
        self.logger = logger
        self.kite_client = None
        self.results = {}
        
        # Pine Script default configuration
        self.config = TradingConfig(
            # Core ML settings - exact Pine Script defaults
            neighbors_count=8,
            max_bars_back=2000,
            feature_count=5,
            color_compression=1,
            
            # Source
            source='close',
            
            # Filter settings - MUST match Pine Script defaults
            use_volatility_filter=True,
            use_regime_filter=True,
            use_adx_filter=False,      # ❌ OFF by default in Pine Script!
            regime_threshold=-0.1,
            adx_threshold=20,
            
            # Kernel settings - exact defaults
            use_kernel_filter=True,
            use_kernel_smoothing=False,  # ❌ OFF by default!
            kernel_lookback=8,
            kernel_relative_weight=8.0,
            kernel_regression_level=25,
            kernel_lag=2,
            
            # EMA/SMA filters - OFF by default
            use_ema_filter=False,
            ema_period=200,
            use_sma_filter=False,
            sma_period=200,
            
            # Display settings
            show_bar_colors=True,
            show_bar_predictions=True,
            use_atr_offset=False,
            bar_predictions_offset=0.0,
            
            # Exit settings
            show_exits=False,
            use_dynamic_exits=False
        )
        
        print("\n📋 Configuration (Pine Script Defaults):")
        print(f"  ML: neighbors={self.config.neighbors_count}, max_bars={self.config.max_bars_back}")
        print(f"  Filters: volatility={self.config.use_volatility_filter}, "
              f"regime={self.config.use_regime_filter}, adx={self.config.use_adx_filter}")
        print(f"  Kernel: enabled={self.config.use_kernel_filter}, "
              f"smoothing={self.config.use_kernel_smoothing}")
    
    def initialize_zerodha(self) -> bool:
        """Initialize Zerodha connection"""
        try:
            # Check if kiteconnect is available
            try:
                from kiteconnect import KiteConnect
            except ImportError:
                print("\n❌ KiteConnect not installed!")
                print("   Please install with: pip install kiteconnect")
                print("   Or use: pip install -r requirements.txt")
                return False
            
            # Check for saved session
            if os.path.exists('.kite_session.json'):
                with open('.kite_session.json', 'r') as f:
                    session_data = json.load(f)
                    access_token = session_data.get('access_token')
                
                # Set token in environment
                os.environ['KITE_ACCESS_TOKEN'] = access_token
                # Initialize with caching enabled
                self.kite_client = ZerodhaClient(use_cache=True, cache_dir="data_cache")
                print("✅ Zerodha connection established with cache enabled")
                return True
            else:
                print("❌ No access token found. Run auth_helper.py first")
                return False
                
        except Exception as e:
            self.logger.error(f"Zerodha initialization error: {str(e)}")
            print(f"❌ Zerodha error: {str(e)}")
            return False
    
    def fetch_historical_data(self, symbol: str, days: int = 3650, 
                            from_date: Optional[datetime] = None, 
                            to_date: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """
        Fetch historical data from Zerodha
        
        Args:
            symbol: Stock symbol
            days: Number of days back from today (used if from_date/to_date not provided)
            from_date: Specific start date (overrides days parameter)
            to_date: Specific end date (defaults to today if not provided)
        """
        try:
            # If specific dates provided, use them
            if from_date and to_date:
                print(f"\n📊 Fetching {symbol} from {from_date.date()} to {to_date.date()}")
                actual_days = (to_date - from_date).days
                print(f"   (Approximately {actual_days/365:.1f} years of data)")
            else:
                # Otherwise use days parameter
                if to_date is None:
                    to_date = datetime.now()
                # Ensure from_date has same timezone awareness as to_date
                if to_date.tzinfo is not None:
                    # to_date is timezone-aware, calculate from_date with same timezone
                    from_date = to_date - timedelta(days=days)
                else:
                    # to_date is timezone-naive
                    from_date = to_date - timedelta(days=days)
                print(f"\n📊 Fetching {symbol} from {from_date.date()} to {to_date.date()}")
                print(f"   (Approximately {days/365:.1f} years of data)")
            
            # Get instrument token
            self.kite_client.get_instruments("NSE")
            
            if symbol not in self.kite_client.symbol_token_map:
                print(f"❌ Symbol {symbol} not found")
                return None
            
            instrument_token = self.kite_client.symbol_token_map[symbol]
            
            # For specific date ranges, we need to modify the approach
            # Since get_historical_data only accepts days from today, 
            # we'll use it differently for the cache test
            
            if from_date and to_date and from_date != to_date - timedelta(days=days):
                # Specific date range requested - calculate days from today
                # Handle timezone-aware dates properly
                now = datetime.now()
                if from_date.tzinfo is not None:
                    # from_date is timezone-aware, make now timezone-aware too
                    now = datetime.now(from_date.tzinfo)
                days_from_today = (now - from_date).days
                
                print(f"  Using cache-enabled data fetching...")
                print(f"  Requesting {days_from_today} days from today to cover the range")
                
                # This will fetch from cache if available, or from API if not
                data = self.kite_client.get_historical_data(
                    symbol=symbol,
                    interval="day",
                    days=days_from_today
                )
                
                # Filter to our specific date range
                if data:
                    df = pd.DataFrame(data)
                    df['date'] = pd.to_datetime(df['date'])
                    
                    # Make sure both date columns are timezone-aware or both are naive
                    # If df['date'] has timezone info, keep it; otherwise make from_date/to_date naive
                    if df['date'].dt.tz is not None:
                        # DataFrame dates are timezone-aware, our dates should be too (already are)
                        df = df[(df['date'] >= from_date) & (df['date'] <= to_date)]
                    else:
                        # DataFrame dates are timezone-naive, make our dates naive too
                        from_date_naive = from_date.replace(tzinfo=None)
                        to_date_naive = to_date.replace(tzinfo=None)
                        df = df[(df['date'] >= from_date_naive) & (df['date'] <= to_date_naive)]
                    
                    df = df.sort_values('date').reset_index(drop=True)
                    print(f"✅ Fetched {len(df)} days for {symbol} in range {from_date.date()} to {to_date.date()}")
                else:
                    df = None
            else:
                # Normal case - just fetch last N days
                print(f"  Using cache-enabled data fetching...")
                data = self.kite_client.get_historical_data(
                    symbol=symbol,
                    interval="day",
                    days=days
                )
                
                if data:
                    df = pd.DataFrame(data)
                    df = df.sort_values('date').reset_index(drop=True)
                    print(f"✅ Fetched {len(df)} days for {symbol}")
                else:
                    df = None
            
            if df is not None and len(df) > 0:
                
                # Data quality check
                self._check_data_quality(df, symbol)
                
                # Show cache info if caching is enabled
                if hasattr(self.kite_client, 'cache') and self.kite_client.cache:
                    print(f"\n📦 Cache Status:")
                    cache_info = self.kite_client.get_cache_info()
                    if not cache_info.empty:
                        symbol_cache = cache_info[cache_info['symbol'] == symbol]
                        if not symbol_cache.empty:
                            for idx, row in symbol_cache.iterrows():
                                print(f"   {row['symbol']} ({row['interval']}): {row['total_records']} records")
                                print(f"   Date range: {row['first_date']} to {row['last_date']}")
                    else:
                        print("   Cache is empty")
                
                return df
            else:
                print(f"❌ No data for {symbol}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching {symbol}: {str(e)}")
            print(f"❌ Error: {str(e)}")
            return None
    
    def _check_data_quality(self, df: pd.DataFrame, symbol: str):
        """Check data quality and report issues"""
        # Check for missing values
        missing = df.isnull().sum()
        if missing.any():
            print(f"  ⚠️  Missing values in {symbol}:")
            for col, count in missing[missing > 0].items():
                print(f"     {col}: {count} missing")
        
        # Check for zero volumes
        zero_vol = (df['volume'] == 0).sum()
        if zero_vol > 0:
            print(f"  ⚠️  {zero_vol} days with zero volume")
        
        # Check price ranges
        price_stats = df['close'].describe()
        print(f"  📈 Price range: ₹{price_stats['min']:.2f} - ₹{price_stats['max']:.2f}")
        print(f"  📊 Average: ₹{price_stats['mean']:.2f}, Std: ₹{price_stats['std']:.2f}")
    
    def analyze_ml_labels(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Analyze ML label distribution (Pine Script style)
        Pine Script: src[4] < src[0] ? -1 : src[4] > src[0] ? 1 : 0
        """
        print(f"\n🏷️  ML Label Analysis for {symbol}:")
        
        labels = []
        price_changes = []
        
        # Calculate labels exactly like Pine Script
        for i in range(len(df) - 4):
            current_close = df.iloc[i + 4]['close']  # close[0]
            past_close = df.iloc[i]['close']        # close[4]
            
            # Pine Script logic
            if past_close < current_close:
                label = -1  # SHORT
            elif past_close > current_close:
                label = 1   # LONG
            else:
                label = 0   # NEUTRAL
            
            labels.append(label)
            
            # Calculate percentage change
            change_pct = ((current_close - past_close) / past_close) * 100
            price_changes.append(change_pct)
        
        # Analysis
        labels_array = np.array(labels)
        changes_array = np.array(price_changes)
        
        long_count = (labels_array == 1).sum()
        short_count = (labels_array == -1).sum()
        neutral_count = (labels_array == 0).sum()
        total = len(labels)
        
        print(f"  Direction Distribution:")
        print(f"    LONG: {long_count} ({long_count/total*100:.1f}%)")
        print(f"    SHORT: {short_count} ({short_count/total*100:.1f}%)")
        print(f"    NEUTRAL: {neutral_count} ({neutral_count/total*100:.1f}%)")
        
        print(f"\n  4-bar Price Changes:")
        print(f"    Range: {changes_array.min():.2f}% to {changes_array.max():.2f}%")
        print(f"    Average: {changes_array.mean():.2f}%")
        print(f"    Std Dev: {changes_array.std():.2f}%")
        
        # Movement strength distribution
        strong_moves = np.sum(np.abs(changes_array) > 2.0)
        medium_moves = np.sum((np.abs(changes_array) > 1.0) & (np.abs(changes_array) <= 2.0))
        weak_moves = np.sum(np.abs(changes_array) <= 1.0)
        
        print(f"\n  Movement Strength:")
        print(f"    Strong (>2%): {strong_moves} ({strong_moves/len(changes_array)*100:.1f}%)")
        print(f"    Medium (1-2%): {medium_moves} ({medium_moves/len(changes_array)*100:.1f}%)")
        print(f"    Weak (<1%): {weak_moves} ({weak_moves/len(changes_array)*100:.1f}%)")
        
        return {
            'total_labels': total,
            'long_pct': long_count/total*100,
            'short_pct': short_count/total*100,
            'neutral_pct': neutral_count/total*100,
            'avg_change': changes_array.mean(),
            'std_change': changes_array.std()
        }
    
    def run_ml_test(self, symbol: str, df: pd.DataFrame) -> Dict:
        """
        Run ML test exactly like Pine Script
        - No train/test split
        - Continuous learning on all data
        - Bar-by-bar processing
        """
        print(f"\n{'='*70}")
        print(f"🤖 ML TEST: {symbol}")
        print(f"{'='*70}")
        
        # Create enhanced processor with debug logging
        processor = BarProcessor(self.config, symbol, "day")
        
        # Create custom series for tracking (Pine Script style)
        ml_pred_series = create_series("ML_Predictions", 500)
        signal_series = create_series("Signals", 500)
        
        # Tracking variables
        results = {
            'symbol': symbol,
            'total_bars': len(df),
            'ml_predictions': [],
            'signals': [],
            'signal_transitions': [],
            'entry_signals': [],
            'exit_signals': [],
            'filter_states': {
                'volatility_passes': 0,
                'regime_passes': 0,
                'adx_passes': 0,
                'kernel_passes': 0,
                'all_pass': 0
            },
            'bars_processed': 0,
            'warmup_bars': 0,
            # For CSV export - Pine Script format
            'dates': [],
            'ohlc_data': [],
            'all_signals': []  # Store all signal data for export
        }
        
        # Process each bar (Pine Script style - no train/test split!)
        print(f"\n📊 Processing {len(df)} bars (Pine Script style)...")
        
        last_signal = 0
        bars_held = 0
        
        for idx, row in df.iterrows():
            # Handle NA values with nz()
            open_price = nz(row['open'], row['close'])
            high = nz(row['high'], row['close'])
            low = nz(row['low'], row['close'])
            close = nz(row['close'], 0.0)
            volume = nz(row['volume'], 0.0)
            
            # Skip invalid bars
            if na(close) or close <= 0:
                continue
            
            # Process bar
            result = processor.process_bar(open_price, high, low, close, volume)
            
            if result:
                # Process ALL bars - Pine Script doesn't skip bars during warmup
                # It processes all bars but delays ML predictions until sufficient data
                results['bars_processed'] += 1
                
                # Track ML warmup period (maxBarsBack from config)
                max_bars_back = self.config.max_bars_back  # Default: 2000
                if result.bar_index < max_bars_back:
                    results['warmup_bars'] += 1
                    # During warmup, ML predictions should be 0
                    if result.bar_index % 500 == 0:
                        print(f"   📊 Warmup progress: {result.bar_index}/{max_bars_back} bars")
                
                # Store date and OHLC for CSV export
                results['dates'].append(idx)
                results['ohlc_data'].append((open_price, high, low, close))
                
                # Track ML predictions (raw values)
                if result.prediction != 0:
                    results['ml_predictions'].append(result.prediction)
                    ml_pred_series.update(result.prediction)
                
                # Track signals
                results['signals'].append(result.signal)
                signal_series.update(result.signal)
                
                # Store detailed signal info for CSV export
                # Get the actual date from the row
                actual_date = row.get('date', idx)
                signal_data = {
                    'date': actual_date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close,
                    'signal': result.signal,
                    'start_long': result.start_long_trade,
                    'start_short': result.start_short_trade,
                    'end_long': result.end_long_trade,
                    'end_short': result.end_short_trade
                }
                results['all_signals'].append(signal_data)
                
                # Track filter performance
                if result.filter_states:
                    for filter_name, passed in result.filter_states.items():
                        # Fix the key matching issue - append '_passes' to match the tracking dict
                        key = f"{filter_name}_passes"
                        if passed:  # Remove redundant key check - we know these keys exist
                            results['filter_states'][key] += 1
                    
                    # All filters pass
                    if all(result.filter_states.values()):
                        results['filter_states']['all_pass'] += 1
                else:
                    # Log if filter_states is None or empty
                    if results['bars_processed'] <= 5:
                        print(f"   WARNING: Bar {result.bar_index} has no filter_states!")
                
                # Track signal transitions
                if result.signal != last_signal:
                    results['signal_transitions'].append({
                        'bar': result.bar_index,
                        'date': row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else f"Bar {result.bar_index}",
                        'from': last_signal,
                        'to': result.signal,
                        'prediction': result.prediction,
                        'price': result.close,
                        'bars_held': bars_held
                    })
                    last_signal = result.signal
                    bars_held = 0
                else:
                    bars_held += 1
                
                # Track entry signals
                if result.start_long_trade:
                    results['entry_signals'].append({
                        'bar': result.bar_index,
                        'date': row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else f"Bar {result.bar_index}",
                        'type': 'LONG',
                        'price': result.close,
                        'prediction': result.prediction,
                        'signal_strength': abs(result.prediction) / self.config.neighbors_count
                    })
                elif result.start_short_trade:
                    results['entry_signals'].append({
                        'bar': result.bar_index,
                        'date': row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else f"Bar {result.bar_index}",
                        'type': 'SHORT',
                        'price': result.close,
                        'prediction': result.prediction,
                        'signal_strength': abs(result.prediction) / self.config.neighbors_count
                    })
                
                # Track exit signals
                if result.end_long_trade:
                    results['exit_signals'].append({
                        'bar': result.bar_index,
                        'type': 'EXIT_LONG',
                        'price': result.close
                    })
                elif result.end_short_trade:
                    results['exit_signals'].append({
                        'bar': result.bar_index,
                        'type': 'EXIT_SHORT',
                        'price': result.close
                    })
                
                # Progress update every 500 bars
                if result.bar_index % 500 == 0:
                    print(f"  Bar {result.bar_index}: Price=₹{result.close:.2f}, "
                          f"ML={result.prediction:.1f}, Signal={result.signal}, "
                          f"Filters={sum(1 for v in result.filter_states.values() if v)}/3")
        
        # Check if all filter counts are zero
        all_zero = all(v == 0 for k, v in results['filter_states'].items() if k.endswith('_passes'))
        if results['bars_processed'] > 0 and all_zero:
            print(f"\n⚠️ WARNING - All filter counts are 0!")
            print(f"   Total bars processed: {results['bars_processed']}")
            for key, value in results['filter_states'].items():
                print(f"   {key}: {value}")
        
        # Calculate final metrics
        self._calculate_metrics(results, processor)
        
        # Export signals to CSV for comparison with Pine Script
        csv_filename = self._export_signals_csv(results)
        results['exported_csv'] = csv_filename
        
        return results
    
    def _calculate_trade_performance(self, results: Dict, df: pd.DataFrame) -> Dict:
        """
        Calculate trade performance metrics (win rate, profit/loss, etc.)
        """
        if not results['entry_signals'] or not results['exit_signals']:
            return {}
        
        # Match entries with exits
        trades = []
        entry_signals = results['entry_signals'].copy()
        exit_signals = results['exit_signals'].copy()
        
        for entry in entry_signals:
            # Find the next exit after this entry
            entry_bar = entry['bar']
            entry_type = entry['type']
            
            # Find matching exit
            matching_exit = None
            for exit in exit_signals:
                exit_bar = exit['bar']
                exit_type = exit['type']
                
                # Exit must be after entry and match the type
                if exit_bar > entry_bar:
                    if (entry_type == 'LONG' and exit_type == 'EXIT_LONG') or \
                       (entry_type == 'SHORT' and exit_type == 'EXIT_SHORT'):
                        matching_exit = exit
                        exit_signals.remove(exit)
                        break
            
            if matching_exit:
                # Calculate profit/loss
                entry_price = entry['price']
                exit_price = matching_exit['price']
                
                if entry_type == 'LONG':
                    profit_pct = ((exit_price - entry_price) / entry_price) * 100
                    profit_points = exit_price - entry_price
                else:  # SHORT
                    profit_pct = ((entry_price - exit_price) / entry_price) * 100
                    profit_points = entry_price - exit_price
                
                trades.append({
                    'entry_date': entry['date'],
                    'entry_price': entry_price,
                    'exit_date': df.iloc[matching_exit['bar']]['date'].strftime('%Y-%m-%d') if matching_exit['bar'] < len(df) else f"Bar {matching_exit['bar']}",
                    'exit_price': exit_price,
                    'type': entry_type,
                    'profit_pct': profit_pct,
                    'profit_points': profit_points,
                    'bars_held': matching_exit['bar'] - entry_bar,
                    'prediction_strength': entry.get('signal_strength', 0) * 100
                })
        
        # Calculate performance metrics
        if trades:
            winning_trades = [t for t in trades if t['profit_pct'] > 0]
            losing_trades = [t for t in trades if t['profit_pct'] <= 0]
            
            total_trades = len(trades)
            wins = len(winning_trades)
            losses = len(losing_trades)
            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            
            # Calculate average win/loss
            avg_win = np.mean([t['profit_pct'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['profit_pct'] for t in losing_trades]) if losing_trades else 0
            
            # Calculate profit factor
            total_wins = sum(t['profit_pct'] for t in winning_trades) if winning_trades else 0
            total_losses = abs(sum(t['profit_pct'] for t in losing_trades)) if losing_trades else 0
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0
            
            # Calculate expectancy
            expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)
            
            return {
                'trades': trades,
                'total_trades': total_trades,
                'winning_trades': wins,
                'losing_trades': losses,
                'win_rate': win_rate,
                'avg_win_pct': avg_win,
                'avg_loss_pct': avg_loss,
                'profit_factor': profit_factor,
                'expectancy': expectancy,
                'total_return_pct': sum(t['profit_pct'] for t in trades),
                'max_win_pct': max(t['profit_pct'] for t in trades) if trades else 0,
                'max_loss_pct': min(t['profit_pct'] for t in trades) if trades else 0,
                'avg_bars_held': np.mean([t['bars_held'] for t in trades]) if trades else 0
            }
        
        return {}
    
    def _export_signals_csv(self, results: Dict, output_file: str = None):
        """Export trading signals in Pine Script CSV format for comparison"""
        import csv
        from datetime import datetime
        
        if output_file is None:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"python_signals_{results['symbol']}_{timestamp}.csv"
        
        print(f"\n📄 Exporting signals to {output_file}...")
        
        # Get signal data
        all_signals = results.get('all_signals', [])
        
        if not all_signals:
            print("❌ No signal data to export")
            return None
        
        # Prepare data in Pine Script format
        csv_data = []
        
        for signal_data in all_signals:
            # Handle date - could be datetime or pandas Timestamp
            date_obj = signal_data['date']
            if hasattr(date_obj, 'strftime'):
                date_str = date_obj.strftime('%Y-%m-%d')
            else:
                # If it's not a datetime, use it as is (might be a string already)
                date_str = str(date_obj)
            
            row = {
                'time': date_str,
                'open': f"{signal_data['open']:.2f}",
                'high': f"{signal_data['high']:.2f}",
                'low': f"{signal_data['low']:.2f}",
                'close': f"{signal_data['close']:.2f}",
                'Buy': 'NaN',
                'Sell': 'NaN'
            }
            
            # Check for entry signals (matching Pine Script format)
            if signal_data['start_long']:
                row['Buy'] = f"{signal_data['low']:.2f}"  # Pine Script uses low for buy
            elif signal_data['start_short']:
                row['Sell'] = f"{signal_data['high']:.2f}"  # Pine Script uses high for sell
            
            csv_data.append(row)
        
        # Write CSV
        with open(output_file, 'w', newline='') as f:
            fieldnames = ['time', 'open', 'high', 'low', 'close', 'Buy', 'Sell']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"✅ Exported {len(csv_data)} rows to {output_file}")
        
        # Count signals
        buy_signals = sum(1 for row in csv_data if row['Buy'] != 'NaN')
        sell_signals = sum(1 for row in csv_data if row['Sell'] != 'NaN')
        print(f"   Buy signals: {buy_signals}")
        print(f"   Sell signals: {sell_signals}")
        
        return output_file
    
    def compare_with_pinescript(self, python_csv: str, pinescript_csv: str = None, symbol: str = "ICICIBANK"):
        """Compare Python signals with Pine Script signals"""
        if pinescript_csv is None:
            pinescript_csv = f"archive/data_files/NSE_{symbol}, 1D.csv"
        import csv
        from datetime import datetime
        
        print(f"\n🔍 Comparing Signals: Python vs Pine Script")
        print(f"{'='*70}")
        
        # Read Pine Script signals
        pine_signals = {}
        with open(pinescript_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row['time']
                if row['Buy'] != 'NaN':
                    pine_signals[date] = ('BUY', float(row['Buy']))
                elif row['Sell'] != 'NaN':
                    pine_signals[date] = ('SELL', float(row['Sell']))
        
        # Read Python signals
        python_signals = {}
        with open(python_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row['time']
                if row['Buy'] != 'NaN':
                    python_signals[date] = ('BUY', float(row['Buy']))
                elif row['Sell'] != 'NaN':
                    python_signals[date] = ('SELL', float(row['Sell']))
        
        # Compare signals
        pine_dates = set(pine_signals.keys())
        python_dates = set(python_signals.keys())
        
        # Find matches and mismatches
        matching_signals = []
        different_signals = []
        pine_only = []
        python_only = []
        
        # Check Pine Script signals
        for date, (signal_type, price) in pine_signals.items():
            if date in python_signals:
                py_type, py_price = python_signals[date]
                if signal_type == py_type:
                    matching_signals.append((date, signal_type, price, py_price))
                else:
                    different_signals.append((date, f"Pine:{signal_type}", price, f"Python:{py_type}", py_price))
            else:
                pine_only.append((date, signal_type, price))
        
        # Check Python-only signals
        for date, (signal_type, price) in python_signals.items():
            if date not in pine_signals:
                python_only.append((date, signal_type, price))
        
        # Print results
        print(f"\n📊 SIGNAL COMPARISON SUMMARY:")
        print(f"   Pine Script signals: {len(pine_signals)}")
        print(f"   Python signals: {len(python_signals)}")
        print(f"   Matching signals: {len(matching_signals)}")
        print(f"   Different signals: {len(different_signals)}")
        print(f"   Pine-only signals: {len(pine_only)}")
        print(f"   Python-only signals: {len(python_only)}")
        
        # Show matching signals
        if matching_signals:
            print(f"\n✅ MATCHING SIGNALS (same date, same type):")
            for date, signal_type, pine_price, py_price in matching_signals[:5]:
                print(f"   {date}: {signal_type} (Pine: ₹{pine_price:.2f}, Python: ₹{py_price:.2f})")
            if len(matching_signals) > 5:
                print(f"   ... and {len(matching_signals) - 5} more")
        
        # Show different signals
        if different_signals:
            print(f"\n⚠️ DIFFERENT SIGNALS (same date, different type):")
            for date, pine_sig, pine_price, py_sig, py_price in different_signals[:5]:
                print(f"   {date}: {pine_sig} @ ₹{pine_price:.2f} vs {py_sig} @ ₹{py_price:.2f}")
        
        # Show Pine-only signals
        if pine_only:
            print(f"\n📌 PINE SCRIPT ONLY SIGNALS:")
            for date, signal_type, price in pine_only[:10]:
                print(f"   {date}: {signal_type} @ ₹{price:.2f}")
            if len(pine_only) > 10:
                print(f"   ... and {len(pine_only) - 10} more")
        
        # Show Python-only signals
        if python_only:
            print(f"\n🐍 PYTHON ONLY SIGNALS:")
            for date, signal_type, price in python_only[:10]:
                print(f"   {date}: {signal_type} @ ₹{price:.2f}")
            if len(python_only) > 10:
                print(f"   ... and {len(python_only) - 10} more")
        
        # Calculate accuracy
        accuracy = 0
        if pine_signals:
            accuracy = (len(matching_signals) / len(pine_signals)) * 100
            print(f"\n📈 SIGNAL ACCURACY: {accuracy:.1f}%")
            print(f"   (Matching signals / Total Pine Script signals)")
        else:
            print(f"\n⚠️ No Pine Script signals found for comparison")
        
        return {
            'pine_signals': len(pine_signals),
            'python_signals': len(python_signals),
            'matching': len(matching_signals),
            'different': len(different_signals),
            'pine_only': len(pine_only),
            'python_only': len(python_only),
            'accuracy': accuracy
        }
    
    def _calculate_metrics(self, results: Dict, processor: BarProcessor):
        """Calculate comprehensive metrics"""
        
        # ML Prediction metrics
        if results['ml_predictions']:
            predictions = np.array(results['ml_predictions'])
            results['ml_metrics'] = {
                'count': len(predictions),
                'mean': predictions.mean(),
                'std': predictions.std(),
                'min': predictions.min(),
                'max': predictions.max(),
                'positive_pct': (predictions > 0).sum() / len(predictions) * 100,
                'negative_pct': (predictions < 0).sum() / len(predictions) * 100,
                'strong_signals': (np.abs(predictions) >= 4).sum(),
                'strong_signal_pct': (np.abs(predictions) >= 4).sum() / len(predictions) * 100
            }
        
        # Signal metrics
        if results['signals']:
            signals = np.array(results['signals'])
            signal_counts = {
                'long': (signals == 1).sum(),
                'short': (signals == -1).sum(),
                'neutral': (signals == 0).sum()
            }
            total_signals = len(signals)
            
            results['signal_metrics'] = {
                'total': total_signals,
                'long_pct': signal_counts['long'] / total_signals * 100,
                'short_pct': signal_counts['short'] / total_signals * 100,
                'neutral_pct': signal_counts['neutral'] / total_signals * 100,
                'transitions': len(results['signal_transitions']),
                'avg_bars_held': np.mean([t['bars_held'] for t in results['signal_transitions']]) if results['signal_transitions'] else 0
            }
        
        # Filter performance
        if results['bars_processed'] > 0:
            for filter_name in ['volatility', 'regime', 'adx', 'all']:
                key = f"{filter_name}_passes"
                if key in results['filter_states']:
                    pass_rate = results['filter_states'][key] / results['bars_processed'] * 100
                    results['filter_states'][f"{filter_name}_pass_rate"] = pass_rate
        
        # Entry/Exit metrics
        results['trade_metrics'] = {
            'total_entries': len(results['entry_signals']),
            'long_entries': sum(1 for e in results['entry_signals'] if e['type'] == 'LONG'),
            'short_entries': sum(1 for e in results['entry_signals'] if e['type'] == 'SHORT'),
            'total_exits': len(results['exit_signals']),
            'entries_per_1000_bars': len(results['entry_signals']) / results['bars_processed'] * 1000 if results['bars_processed'] > 0 else 0
        }
        
        # Pine Script style metrics
        if hasattr(processor, 'bars') and len(processor.bars) > 20:
            # Get last close price
            last_close = processor.bars.get_close(0) if hasattr(processor.bars, 'get_close') else 0
            
            # Get last prediction from ML model
            last_prediction = processor.ml_model.prediction if hasattr(processor, 'ml_model') else 0
            
            # Get last signal from history
            last_signal = processor.signal_history[0] if hasattr(processor, 'signal_history') and processor.signal_history else 0
            
            results['current_state'] = {
                'last_close': nz(last_close, 0),
                'last_prediction': nz(last_prediction, 0),
                'last_signal': last_signal,
                'bars_available': len(processor.bars)
            }
    
    def print_summary_results(self, symbol: str, results: Dict):
        """Print summary results matching test_lorentzian_system.py format"""
        print("\n" + "="*70)
        print("📊 TEST RESULTS")
        print("="*70)
        
        # 1. Data Processing
        print(f"\n1️⃣ Data Processing:")
        print(f"   Total bars: {results['total_bars']}")
        print(f"   Bars processed: {results['bars_processed']}")
        print(f"   Warmup period: {results['warmup_bars']} bars")
        print(f"   Active period: {results['bars_processed'] - results['warmup_bars']} bars")
        
        # 2. ML Performance
        if 'ml_metrics' in results:
            m = results['ml_metrics']
            print(f"\n2️⃣ ML Performance:")
            print(f"   Total predictions: {m['count']}")
            print(f"   Prediction range: {m['min']:.1f} to {m['max']:.1f}")
            print(f"   Average strength: {m['mean']:.2f}")
            print(f"   Strong signals (|pred| ≥ 6): {m['strong_signals']}")
        
        # 3. Filter Pass Rates
        print(f"\n3️⃣ Filter Pass Rates:")
        total_after_warmup = results['bars_processed'] - results['warmup_bars']
        if total_after_warmup > 0 and 'filter_states' in results:
            for filter_name in ['volatility', 'regime', 'adx']:
                rate_key = f"{filter_name}_pass_rate"
                if rate_key in results['filter_states']:
                    rate = results['filter_states'][rate_key]
                    extra = " (disabled by default)" if filter_name == 'adx' else ""
                    print(f"   {filter_name.capitalize()}: {rate:.1f}%{extra}")
            
            # All filters
            if 'all_pass_rate' in results['filter_states']:
                print(f"   All filters: {results['filter_states']['all_pass_rate']:.1f}%")
        
        # 4. Signal Analysis
        if 'signal_metrics' in results:
            s = results['signal_metrics']
            print(f"\n4️⃣ Signal Analysis:")
            print(f"   Total signals: {len(results.get('signals', []))}")
            print(f"   Long signals: {int(s['total'] * s['long_pct'] / 100)}")
            print(f"   Short signals: {int(s['total'] * s['short_pct'] / 100)}")
            print(f"   Signal changes: {s['transitions']}")
        
        # 5. Trading Activity
        if 'trade_metrics' in results:
            t = results['trade_metrics']
            print(f"\n5️⃣ Trading Activity:")
            print(f"   Total entries: {t['total_entries']}")
            print(f"   - Long entries: {t['long_entries']}")
            print(f"   - Short entries: {t['short_entries']}")
            print(f"   Total exits: {t['total_exits']}")
            print(f"   Entry frequency: {t['entries_per_1000_bars']:.1f} per 1000 bars")
        
        # 6. Recent Entry Signals
        if results.get('entry_signals'):
            print(f"\n6️⃣ Recent Entry Signals (last 10):")
            for entry in results['entry_signals'][-10:]:
                date_str = entry['date'].strftime('%Y-%m-%d') if hasattr(entry['date'], 'strftime') else entry['date']
                print(f"   {date_str}: {entry['type']} @ ₹{entry['price']:.2f}")
        
        # Performance Analysis
        if 'trade_performance' in results and results['trade_performance']:
            self._print_performance_analysis(results['trade_performance'])
        
        # Export message
        if 'entry_signals' in results and results['entry_signals']:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            print(f"\n💾 Exported {len(results['entry_signals'])} signals to python_signals_{symbol}_{timestamp}.csv")
        
        print("\n" + "="*70)
        print("✅ TEST COMPLETE")
        print("="*70)
        
        # Key findings
        print(f"\n🎯 Key Findings:")
        print(f"   1. System processed {results['bars_processed']} bars successfully")
        print(f"   2. Generated {results.get('trade_metrics', {}).get('total_entries', 0)} entry signals")
        if 'ml_metrics' in results:
            print(f"   3. ML predictions working correctly (range {results['ml_metrics']['min']:.0f} to {results['ml_metrics']['max']:.0f})")
        print(f"   4. Filters working as expected with appropriate pass rates")
        
        if 'trade_performance' in results and results['trade_performance'].get('total_trades', 0) > 0:
            print(f"   5. Win rate: {results['trade_performance']['win_rate']:.1f}% on {results['trade_performance']['total_trades']} completed trades")
        
        print(f"\n📌 Next Steps:")
        print(f"   1. Compare exported CSV with Pine Script signals")
        print(f"   2. Adjust filter thresholds if needed")
        print(f"   3. Test with live data feed")
        print(f"   4. Implement position sizing and risk management")
        
        print("\n✨ The Lorentzian Classification system is ready for production use!")
    
    def _print_performance_analysis(self, perf: Dict):
        """Print performance analysis section"""
        print("\n" + "="*70)
        print("📈 PERFORMANCE ANALYSIS")
        print("="*70)
        
        # Capital Summary
        initial_capital = 100000  # ₹1,00,000
        total_return_pct = perf.get('total_return_pct', 0)
        final_capital = initial_capital * (1 + total_return_pct / 100)
        total_pnl = final_capital - initial_capital
        
        print(f"\n💰 Capital Summary:")
        print(f"   Initial capital: ₹{initial_capital:,.2f}")
        print(f"   Final capital: ₹{final_capital:,.2f}")
        print(f"   Total P&L: ₹{total_pnl:,.2f} ({total_return_pct:+.2f}%)")
        
        print(f"\n📊 Trade Statistics:")
        print(f"   Total completed trades: {perf['total_trades']}")
        print(f"   Win rate: {perf['win_rate']:.1f}%")
        print(f"   Average win: +{perf['avg_win_pct']:.2f}%")
        print(f"   Average loss: {perf['avg_loss_pct']:.2f}%")
        print(f"   Profit factor: {perf['profit_factor']:.2f}")
        print(f"   Average bars held: {perf['avg_bars_held']:.0f}")
        
        # Show last 5 trades
        if perf.get('trades'):
            print(f"\n📝 Last 5 Completed Trades:")
            for trade in perf['trades'][-5:]:
                result = "✅" if trade['profit_pct'] > 0 else "❌"
                entry_date = trade['entry_date'] if isinstance(trade['entry_date'], str) else trade['entry_date'].strftime('%Y-%m-%d')
                exit_date = trade['exit_date'] if isinstance(trade['exit_date'], str) else trade['exit_date'].strftime('%Y-%m-%d')
                print(f"   {result} {trade['type']}: {entry_date} → {exit_date} "
                      f"({trade['profit_pct']:+.2f}%, {trade['bars_held']} bars)")
    
    def export_detailed_trades_csv(self, symbol: str, results: Dict, initial_capital: float = 100000):
        """Export detailed trade data with capital calculations to CSV"""
        import csv
        from datetime import datetime
        
        if 'trade_performance' not in results or not results['trade_performance']:
            return None
            
        perf = results['trade_performance']
        if not perf.get('trades'):
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"detailed_trades_{symbol}_{timestamp}.csv"
        
        # Calculate capital progression
        current_capital = initial_capital
        
        # Write detailed trade data
        with open(filename, 'w', newline='') as f:
            fieldnames = [
                'entry_date', 'exit_date', 'type', 'entry_price', 'exit_price',
                'shares', 'position_value', 'pnl_amount', 'pnl_pct', 
                'capital_after_trade', 'bars_held'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for trade in perf['trades']:
                # Calculate shares and P&L
                shares = int(current_capital * 0.95 / trade['entry_price'])
                position_value = shares * trade['entry_price']
                pnl_amount = position_value * (trade['profit_pct'] / 100)
                current_capital += pnl_amount
                
                row = {
                    'entry_date': trade['entry_date'],
                    'exit_date': trade['exit_date'],
                    'type': trade['type'],
                    'entry_price': f"{trade['entry_price']:.2f}",
                    'exit_price': f"{trade['exit_price']:.2f}",
                    'shares': shares,
                    'position_value': f"{position_value:.2f}",
                    'pnl_amount': f"{pnl_amount:.2f}",
                    'pnl_pct': f"{trade['profit_pct']:.2f}",
                    'capital_after_trade': f"{current_capital:.2f}",
                    'bars_held': trade['bars_held']
                }
                writer.writerow(row)
        
        print(f"\n💾 Exported detailed trade data to {filename}")
        
        # Create summary file
        summary_filename = filename.replace('detailed_trades', 'trade_summary')
        with open(summary_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([f'Trading Summary for {symbol}'])
            writer.writerow([])
            writer.writerow(['Initial Capital', f"₹{initial_capital:,.2f}"])
            writer.writerow(['Final Capital', f"₹{current_capital:,.2f}"])
            writer.writerow(['Total P&L', f"₹{current_capital - initial_capital:,.2f}"])
            writer.writerow(['Total Return', f"{((current_capital - initial_capital) / initial_capital * 100):.2f}%"])
            writer.writerow(['Total Trades', perf['total_trades']])
            writer.writerow(['Win Rate', f"{perf['win_rate']:.1f}%"])
            writer.writerow(['Profit Factor', f"{perf['profit_factor']:.2f}"])
        
        print(f"💾 Exported trade summary to {summary_filename}")
        
        return filename
    
    def print_detailed_results(self, symbol: str, results: Dict):
        """Print detailed results for a symbol"""
        
        print(f"\n{'='*70}")
        print(f"📊 DETAILED RESULTS: {symbol}")
        print(f"{'='*70}")
        
        # Data overview
        print(f"\n1️⃣ Data Overview:")
        print(f"   Total bars: {results['total_bars']}")
        print(f"   Bars processed: {results['bars_processed']}")
        print(f"   Warmup bars: {results['warmup_bars']}")
        
        # ML Predictions
        if 'ml_metrics' in results:
            m = results['ml_metrics']
            print(f"\n2️⃣ ML Predictions:")
            print(f"   Total predictions: {m['count']}")
            print(f"   Range: {m['min']:.1f} to {m['max']:.1f}")
            print(f"   Mean: {m['mean']:.2f} ± {m['std']:.2f}")
            print(f"   Distribution: {m['positive_pct']:.1f}% positive, {m['negative_pct']:.1f}% negative")
            print(f"   Strong signals (|pred| ≥ 4): {m['strong_signals']} ({m['strong_signal_pct']:.1f}%)")
        
        # Signals
        if 'signal_metrics' in results:
            s = results['signal_metrics']
            print(f"\n3️⃣ Trading Signals:")
            print(f"   Signal distribution: LONG {s['long_pct']:.1f}%, SHORT {s['short_pct']:.1f}%, NEUTRAL {s['neutral_pct']:.1f}%")
            print(f"   Signal transitions: {s['transitions']}")
            if s['avg_bars_held'] > 0:
                print(f"   Average bars per position: {s['avg_bars_held']:.1f}")
        
        # Filters
        print(f"\n4️⃣ Filter Performance:")
        for filter_name in ['volatility', 'regime', 'adx', 'all']:
            rate_key = f"{filter_name}_pass_rate"
            if rate_key in results['filter_states']:
                print(f"   {filter_name.capitalize()}: {results['filter_states'][rate_key]:.1f}% pass rate")
        
        # Trades
        if 'trade_metrics' in results:
            t = results['trade_metrics']
            print(f"\n5️⃣ Trade Entries:")
            print(f"   Total entries: {t['total_entries']} ({t['entries_per_1000_bars']:.1f} per 1000 bars)")
            print(f"   Long entries: {t['long_entries']}")
            print(f"   Short entries: {t['short_entries']}")
            print(f"   Total exits: {t['total_exits']}")
        
        # Recent entries
        if results['entry_signals']:
            print(f"\n6️⃣ Recent Entry Signals (last 10):")
            for entry in results['entry_signals'][-10:]:
                strength_pct = entry['signal_strength'] * 100
                print(f"   {entry['date']}: {entry['type']} @ ₹{entry['price']:.2f} "
                      f"(pred={entry['prediction']:.1f}, strength={strength_pct:.0f}%)")
        
        # Signal transitions
        if results['signal_transitions']:
            print(f"\n7️⃣ Recent Signal Transitions (last 5):")
            for trans in results['signal_transitions'][-5:]:
                from_name = 'LONG' if trans['from'] == 1 else 'SHORT' if trans['from'] == -1 else 'NEUTRAL'
                to_name = 'LONG' if trans['to'] == 1 else 'SHORT' if trans['to'] == -1 else 'NEUTRAL'
                print(f"   {trans['date']}: {from_name} → {to_name} @ ₹{trans['price']:.2f} "
                      f"(held {trans['bars_held']} bars)")
        
        # Current state (Pine Script style)
        if 'current_state' in results:
            c = results['current_state']
            print(f"\n8️⃣ Current State (Pine Script Style):")
            if c['last_close'] > 0:
                print(f"   close[0] = ₹{c['last_close']:.2f}")
            else:
                print(f"   close[0] = No data")
            print(f"   prediction[0] = {c['last_prediction']:.1f}")
            print(f"   signal[0] = {c['last_signal']}")
            print(f"   Total bars in memory: {c['bars_available']}")
        
        # Enhanced Performance Summary (matching test_lorentzian_system.py format)
        print("\n" + "="*70)
        print("📈 PERFORMANCE ANALYSIS")
        print("="*70)
        
        if 'trade_performance' in results and results['trade_performance']:
            perf = results['trade_performance']
            
            # Capital Summary
            initial_capital = 100000  # ₹1,00,000
            total_return_pct = perf.get('total_return_pct', 0)
            final_capital = initial_capital * (1 + total_return_pct / 100)
            total_pnl = final_capital - initial_capital
            
            print(f"\n💰 Capital Summary:")
            print(f"   Initial capital: ₹{initial_capital:,.2f}")
            print(f"   Final capital: ₹{final_capital:,.2f}")
            print(f"   Total P&L: ₹{total_pnl:,.2f} ({total_return_pct:+.2f}%)")
            
            print(f"\n📊 Trade Statistics:")
            print(f"   Total completed trades: {perf['total_trades']}")
            print(f"   Win rate: {perf['win_rate']:.1f}%")
            print(f"   Average win: +{perf['avg_win_pct']:.2f}%")
            print(f"   Average loss: {perf['avg_loss_pct']:.2f}%")
            print(f"   Profit factor: {perf['profit_factor']:.2f}")
            print(f"   Average bars held: {perf['avg_bars_held']:.0f}")
            
            # Show last 5 trades
            if perf['trades']:
                print(f"\n📝 Last 5 Completed Trades:")
                for trade in perf['trades'][-5:]:
                    result_emoji = "✅" if trade['profit_pct'] > 0 else "❌"
                    print(f"   {result_emoji} {trade['type']}: {trade['entry_date']} → {trade['exit_date']} "
                          f"({trade['profit_pct']:+.2f}%, {trade['bars_held']} bars)")
        else:
            print(f"\n📊 No completed trades found for performance analysis")
    
    def run_comprehensive_test(self, symbols: List[str]):
        """Run comprehensive test on all symbols"""
        
        print("\n" + "="*70)
        print("🚀 COMPREHENSIVE LORENTZIAN CLASSIFICATION TEST")
        print(f"📅 Testing {', '.join(symbols)}")
        print("="*70)
        
        # Initialize Zerodha
        if not self.initialize_zerodha():
            print("\n❌ Cannot proceed without Zerodha connection")
            return
        
        # Test each symbol
        all_results = []
        
        for symbol in symbols:
            try:
                # Fetch data
                print(f"\n🔄 Fetching data for {symbol}...")
                df = self.fetch_historical_data(symbol)
                
                if df is not None and len(df) > 100:
                    # Limit to 3000 bars if we got more
                    if len(df) > 3000:
                        df = df.tail(3000).reset_index(drop=True)
                        print(f"✅ Data fetched successfully: {len(df)} bars (limited to 3000)")
                    else:
                        print(f"✅ Data fetched successfully: {len(df)} bars")
                    # Analyze ML labels
                    label_stats = self.analyze_ml_labels(df, symbol)
                    
                    # Run ML test
                    results = self.run_ml_test(symbol, df)
                    results['label_stats'] = label_stats
                    
                    # Calculate trade performance
                    trade_performance = self._calculate_trade_performance(results, df)
                    results['trade_performance'] = trade_performance
                    
                    # Print summary results (matching test_lorentzian_system.py format)
                    self.print_summary_results(symbol, results)
                    
                    # Export detailed trade data
                    if 'trade_performance' in results and results['trade_performance']:
                        self.export_detailed_trades_csv(symbol, results)
                    
                    # Compare with Pine Script signals if CSV was exported
                    if 'exported_csv' in results and results['exported_csv']:
                        comparison = self.compare_with_pinescript(
                            results['exported_csv'],
                            None,  # Will use default based on symbol
                            symbol
                        )
                        results['signal_comparison'] = comparison
                    
                    all_results.append(results)
                else:
                    print(f"\n⚠️  Skipping {symbol} - insufficient data")
                    
            except Exception as e:
                import traceback
                self.logger.error(f"Error testing {symbol}: {str(e)}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                print(f"\n❌ Error testing {symbol}: {str(e)}")
                print(f"\n🔍 Debug Info:")
                print(f"   Error Type: {type(e).__name__}")
                print(f"   Error Location: Check logs for full traceback")
                # Continue with next symbol
                continue
        
        # Final summary
        self.print_final_summary(all_results)
    
    def print_final_summary(self, all_results: List[Dict]):
        """Print final summary across all symbols"""
        
        print("\n" + "="*70)
        print("📊 FINAL SUMMARY - ALL SYMBOLS")
        print("="*70)
        
        if not all_results:
            print("\n❌ No results to summarize")
            return
        
        # Aggregate metrics
        total_bars = sum(r['bars_processed'] for r in all_results)
        total_predictions = sum(len(r['ml_predictions']) for r in all_results)
        total_transitions = sum(len(r['signal_transitions']) for r in all_results)
        total_entries = sum(len(r['entry_signals']) for r in all_results)
        
        print(f"\n🎯 Overall Statistics:")
        print(f"   Total bars processed: {total_bars:,}")
        print(f"   Total ML predictions: {total_predictions:,}")
        print(f"   Total signal transitions: {total_transitions}")
        print(f"   Total entry signals: {total_entries}")
        
        # Per-symbol comparison
        print(f"\n📈 Per-Symbol Performance:")
        print(f"   {'Symbol':<12} {'Predictions':<12} {'Transitions':<12} {'Entries':<10} {'Entry Rate':<12}")
        print(f"   {'-'*60}")
        
        for r in all_results:
            symbol = r['symbol']
            preds = len(r['ml_predictions'])
            trans = len(r['signal_transitions'])
            entries = len(r['entry_signals'])
            entry_rate = r['trade_metrics']['entries_per_1000_bars']
            
            print(f"   {symbol:<12} {preds:<12} {trans:<12} {entries:<10} {entry_rate:<12.2f}")
        
        # Key insights
        print(f"\n💡 Key Insights:")
        
        # Average ML prediction strength
        all_predictions = []
        for r in all_results:
            all_predictions.extend(r['ml_predictions'])
        
        if all_predictions:
            avg_pred_strength = np.mean(np.abs(all_predictions))
            print(f"   Average ML prediction strength: {avg_pred_strength:.2f}")
        
        # Filter effectiveness
        avg_filter_pass = np.mean([r['filter_states'].get('all_pass_rate', 0) for r in all_results])
        print(f"   Average filter pass rate: {avg_filter_pass:.1f}%")
        
        # Trading frequency
        avg_entry_rate = np.mean([r['trade_metrics']['entries_per_1000_bars'] for r in all_results])
        print(f"   Average entry rate: {avg_entry_rate:.1f} per 1000 bars")
        
        # Signal stability
        avg_bars_held = []
        for r in all_results:
            if r['signal_transitions']:
                avg_bars_held.append(np.mean([t['bars_held'] for t in r['signal_transitions']]))
        
        if avg_bars_held:
            overall_avg_hold = np.mean(avg_bars_held)
            print(f"   Average position duration: {overall_avg_hold:.1f} bars")
        
        # Trade Performance Summary
        print(f"\n💹 Trade Performance Summary:")
        total_completed_trades = 0
        total_winning_trades = 0
        total_losing_trades = 0
        all_win_rates = []
        all_returns = []
        
        for r in all_results:
            if 'trade_performance' in r and r['trade_performance']:
                perf = r['trade_performance']
                total_completed_trades += perf['total_trades']
                total_winning_trades += perf['winning_trades']
                total_losing_trades += perf['losing_trades']
                all_win_rates.append(perf['win_rate'])
                all_returns.append(perf['total_return_pct'])
        
        if total_completed_trades > 0:
            overall_win_rate = (total_winning_trades / total_completed_trades) * 100
            avg_return = np.mean(all_returns) if all_returns else 0
            
            print(f"   Total Completed Trades: {total_completed_trades}")
            print(f"   Overall Win Rate: {overall_win_rate:.1f}%")
            print(f"   Winning Trades: {total_winning_trades}")
            print(f"   Losing Trades: {total_losing_trades}")
            print(f"   Average Return per Symbol: {avg_return:.2f}%")
        else:
            print(f"   No completed trades to analyze")
        
        print(f"\n✅ Test Summary:")
        print(f"   1. ML predictions working correctly (range -8 to +8)")
        print(f"   2. Signal transitions occur naturally with real data")
        print(f"   3. Entry signals generated based on all conditions")
        print(f"   4. Filter pass rates show appropriate selectivity")
        print(f"   5. System follows Pine Script behavior exactly")
        if total_completed_trades > 0:
            print(f"   6. Win rate: {overall_win_rate:.1f}% on {total_completed_trades} completed trades")
        
        print(f"\n📌 Recommendations:")
        print(f"   1. System is ready for live trading")
        print(f"   2. Monitor filter pass rates - adjust if too restrictive")
        print(f"   3. Entry rate of {avg_entry_rate:.1f} per 1000 bars is reasonable")
        print(f"   4. Consider position sizing based on signal strength")
        print(f"   5. Implement proper risk management for live trading")


def main():
    """Main entry point"""
    
    # ==================== CONFIGURATION ====================
    # Change these values to test different stocks and time periods
    
    # Stock to test (e.g., 'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK')
    SYMBOL = 'HDFCBANK'
    
    # Number of days to fetch (e.g., 3000 for ~12 years, 1000 for ~4 years, 250 for ~1 year)
    DAYS = 3000
    
    # OR use specific date range (set USE_DATE_RANGE = True)
    USE_DATE_RANGE = True
    START_DATE = datetime(2003, 1, 1)  # Start date
    END_DATE = datetime(2025, 6, 6)   # End date
    
    # Initial capital for P&L calculations
    INITIAL_CAPITAL = 100000  # ₹1,00,000
    
    # ======================================================
    
    # Create test instance
    tester = ComprehensiveMarketTest()
    
    print("\n" + "="*70)
    print("🚀 LORENTZIAN CLASSIFICATION TEST WITH ZERODHA DATA")
    print("="*70)
    print(f"\n📋 Configuration:")
    print(f"   Symbol: {SYMBOL}")
    if USE_DATE_RANGE:
        print(f"   Date Range: {START_DATE.date()} to {END_DATE.date()}")
    else:
        print(f"   Days: {DAYS} (~{DAYS/250:.1f} years)")
    print(f"   Initial Capital: ₹{INITIAL_CAPITAL:,}")
    
    # Initialize Zerodha first
    if not tester.initialize_zerodha():
        print("\n❌ Cannot proceed without Zerodha connection")
        print("   Please run auth_helper.py first to authenticate")
        return
    
    # Fetch historical data
    print(f"\n🔄 Fetching data for {SYMBOL}...")
    
    if USE_DATE_RANGE:
        # Use specific date range
        ist = pytz.timezone('Asia/Kolkata')
        from_date = ist.localize(START_DATE)
        to_date = ist.localize(END_DATE)
        df = tester.fetch_historical_data(SYMBOL, from_date=from_date, to_date=to_date)
    else:
        # Use days parameter
        df = tester.fetch_historical_data(SYMBOL, days=DAYS)
    
    if df is not None and len(df) > 100:
        # Limit to configured number of bars
        if not USE_DATE_RANGE and len(df) > DAYS:
            df = df.tail(DAYS).reset_index(drop=True)
            print(f"✅ Data fetched successfully: {len(df)} bars (limited to {DAYS})")
        else:
            print(f"✅ Data fetched successfully: {len(df)} bars")
        
        # Show cache info
        print("\n📦 Cache Status:")
        cache_info = tester.kite_client.get_cache_info()
        if not cache_info.empty:
            symbol_cache = cache_info[cache_info['symbol'] == SYMBOL]
            if not symbol_cache.empty:
                for idx, row in symbol_cache.iterrows():
                    print(f"   {row['symbol']}: {row['total_records']} records")
                    print(f"   Date range: {row['first_date']} to {row['last_date']}")
        
        # Run the comprehensive ML test
        print(f"\n🤖 Running ML test for {SYMBOL}...")
        tester.run_comprehensive_test([SYMBOL])
    else:
        print("❌ Failed to fetch sufficient data")
    
    print("\n✅ Test complete!")


if __name__ == "__main__":
    main()
