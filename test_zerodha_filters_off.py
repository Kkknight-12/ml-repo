#!/usr/bin/env python3
"""
Modified version of test_zerodha_comprehensive.py
Testing with filters OFF to diagnose the issue
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Tuple, Optional

# Core imports
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from data.zerodha_client import ZerodhaClient
from core.pine_functions import nz, na
from core.history_referencing import create_series
import logging

# For debugging
import warnings
warnings.filterwarnings('ignore')

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
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
        
        # MODIFIED: Testing with filters OFF
        print("\n🔧 TESTING WITH FILTERS OFF TO DIAGNOSE ISSUE")
        print("="*70)
        
        self.config = TradingConfig(
            # Core ML settings - exact Pine Script defaults
            neighbors_count=8,
            max_bars_back=2000,
            feature_count=5,
            color_compression=1,
            
            # Source
            source='close',
            
            # FILTERS OFF FOR TESTING
            use_volatility_filter=False,  # ❌ OFF (was True)
            use_regime_filter=False,      # ❌ OFF (was True)
            use_adx_filter=False,         # Already OFF (Pine default)
            regime_threshold=-0.1,
            adx_threshold=20,
            
            # Kernel settings - exact defaults
            use_kernel_filter=True,
            use_kernel_smoothing=False,
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
        
        print("\n📋 Configuration (FILTERS OFF TEST):")
        print(f"  ML: neighbors={self.config.neighbors_count}, max_bars={self.config.max_bars_back}")
        print(f"  Filters: volatility={self.config.use_volatility_filter} ❌, "
              f"regime={self.config.use_regime_filter} ❌, adx={self.config.use_adx_filter} ❌")
        print(f"  Kernel: enabled={self.config.use_kernel_filter} ✅, "
              f"smoothing={self.config.use_kernel_smoothing}")
        print("\n⚠️  If ML predictions work now, the issue is filter settings!")
        print("="*70)
    
    def initialize_zerodha(self) -> bool:
        """Initialize Zerodha connection"""
        try:
            # Check for saved session
            if os.path.exists('.kite_session.json'):
                with open('.kite_session.json', 'r') as f:
                    session_data = json.load(f)
                    access_token = session_data.get('access_token')
                
                # Set token in environment
                os.environ['KITE_ACCESS_TOKEN'] = access_token
                self.kite_client = ZerodhaClient()
                print("✅ Zerodha connection established")
                return True
            else:
                print("❌ No access token found. Run auth_helper.py first")
                return False
                
        except Exception as e:
            self.logger.error(f"Zerodha initialization error: {str(e)}")
            print(f"❌ Zerodha error: {str(e)}")
            return False
    
    def fetch_historical_data(self, symbol: str, days: int = 1825) -> Optional[pd.DataFrame]:
        """
        Fetch historical data from Zerodha
        5 years = 1825 days (including weekends/holidays)
        """
        try:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)
            
            print(f"\n📊 Fetching {symbol} from {from_date.date()} to {to_date.date()}")
            
            # Get instrument token
            self.kite_client.get_instruments("NSE")
            
            if symbol not in self.kite_client.symbol_token_map:
                print(f"❌ Symbol {symbol} not found")
                return None
            
            instrument_token = self.kite_client.symbol_token_map[symbol]
            
            # Fetch data in chunks to avoid rate limits
            all_data = []
            chunk_days = 400  # Zerodha limit per request
            
            current_to = to_date
            while current_to > from_date:
                current_from = max(current_to - timedelta(days=chunk_days), from_date)
                
                chunk_data = self.kite_client.kite.historical_data(
                    instrument_token=instrument_token,
                    from_date=current_from.strftime("%Y-%m-%d %H:%M:%S"),
                    to_date=current_to.strftime("%Y-%m-%d %H:%M:%S"),
                    interval="day"
                )
                
                if chunk_data:
                    all_data.extend(chunk_data)
                
                current_to = current_from - timedelta(days=1)
            
            if all_data:
                df = pd.DataFrame(all_data)
                df = df.sort_values('date').reset_index(drop=True)
                print(f"✅ Fetched {len(df)} days for {symbol}")
                
                # Data quality check
                self._check_data_quality(df, symbol)
                
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
        print(f"🤖 ML TEST: {symbol} (FILTERS OFF)")
        print(f"{'='*70}")
        
        # Create enhanced processor
        processor = EnhancedBarProcessor(self.config, symbol, "day")
        
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
            'warmup_bars': 0
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
                # Track warmup period
                if result.bar_index < 50:
                    results['warmup_bars'] += 1
                    continue
                
                results['bars_processed'] += 1
                
                # Track ML predictions (raw values)
                if result.prediction != 0:
                    results['ml_predictions'].append(result.prediction)
                    ml_pred_series.update(result.prediction)
                
                # Track signals
                results['signals'].append(result.signal)
                signal_series.update(result.signal)
                
                # Track filter performance
                if result.filter_states:
                    for filter_name, passed in result.filter_states.items():
                        if passed and filter_name in results['filter_states']:
                            results['filter_states'][f"{filter_name}_passes"] += 1
                    
                    # All filters pass
                    if all(result.filter_states.values()):
                        results['filter_states']['all_pass'] += 1
                
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
        
        # Calculate final metrics
        self._calculate_metrics(results, processor)
        
        return results
    
    def _calculate_metrics(self, results: Dict, processor: EnhancedBarProcessor):
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
            for filter_name in ['volatility', 'regime', 'adx', 'kernel', 'all']:
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
        if len(processor.bars) > 20:
            results['current_state'] = {
                'last_close': nz(processor.bars.close[0], 0),
                'last_prediction': nz(processor.ml_predictions[0], 0) if processor.ml_predictions[0] is not None else 0,
                'last_signal': processor.signal_history[-1] if processor.signal_history else 0,
                'bars_available': len(processor.bars)
            }
    
    def print_detailed_results(self, symbol: str, results: Dict):
        """Print detailed results for a symbol"""
        
        print(f"\n{'='*70}")
        print(f"📊 DETAILED RESULTS: {symbol} (FILTERS OFF)")
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
        
        # Filters (should show different results with filters OFF)
        print(f"\n4️⃣ Filter Performance (FILTERS OFF):")
        print(f"   ⚠️  Filters are OFF - should see 100% pass rate")
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
            print(f"   close[0] = ₹{c['last_close']:.2f}")
            print(f"   prediction[0] = {c['last_prediction']:.1f}")
            print(f"   signal[0] = {c['last_signal']}")
            print(f"   Total bars in memory: {c['bars_available']}")
    
    def run_comprehensive_test(self, symbols: List[str]):
        """Run comprehensive test on all symbols"""
        
        print("\n" + "="*70)
        print("🚀 COMPREHENSIVE LORENTZIAN CLASSIFICATION TEST (FILTERS OFF)")
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
                df = self.fetch_historical_data(symbol)
                
                if df is not None and len(df) > 100:
                    # Analyze ML labels
                    label_stats = self.analyze_ml_labels(df, symbol)
                    
                    # Run ML test
                    results = self.run_ml_test(symbol, df)
                    results['label_stats'] = label_stats
                    
                    # Print detailed results
                    self.print_detailed_results(symbol, results)
                    
                    all_results.append(results)
                else:
                    print(f"\n⚠️  Skipping {symbol} - insufficient data")
                    
            except Exception as e:
                self.logger.error(f"Error testing {symbol}: {str(e)}")
                print(f"\n❌ Error testing {symbol}: {str(e)}")
        
        # Final summary
        self.print_final_summary(all_results)
    
    def print_final_summary(self, all_results: List[Dict]):
        """Print final summary across all symbols"""
        
        print("\n" + "="*70)
        print("📊 FINAL SUMMARY - ALL SYMBOLS (FILTERS OFF)")
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
        print(f"\n💡 Key Insights (FILTERS OFF):")
        
        # Average ML prediction strength
        all_predictions = []
        for r in all_results:
            all_predictions.extend(r['ml_predictions'])
        
        if all_predictions:
            avg_pred_strength = np.mean(np.abs(all_predictions))
            print(f"   Average ML prediction strength: {avg_pred_strength:.2f}")
        
        # Filter effectiveness (should be 100% with filters OFF)
        avg_filter_pass = np.mean([r['filter_states'].get('all_pass_rate', 0) for r in all_results])
        print(f"   Average filter pass rate: {avg_filter_pass:.1f}% (should be 100% with filters OFF)")
        
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
        
        print(f"\n✅ Test Summary (FILTERS OFF):")
        print(f"   1. ML predictions working: {'YES' if total_predictions > 0 else 'NO'}")
        print(f"   2. Signal transitions occur: {'YES' if total_transitions > 0 else 'NO'}")
        print(f"   3. Entry signals generated: {'YES' if total_entries > 0 else 'NO'}")
        print(f"   4. Filter pass rates: {'100% (OFF)' if avg_filter_pass == 100 else f'{avg_filter_pass:.1f}%'}")
        
        print(f"\n📌 Conclusions:")
        if total_predictions > 0 and total_transitions > 5:
            print(f"   ✅ ML system is working correctly!")
            print(f"   ✅ The issue was filter settings being too restrictive")
            print(f"   ✅ With filters OFF, signals change naturally")
            print(f"\n   Recommendations:")
            print(f"   1. For daily data, consider keeping filters OFF")
            print(f"   2. Or use intraday data (5min, 15min) where filters work better")
            print(f"   3. Or adjust filter thresholds for daily data")
        else:
            print(f"   ❌ ML system still not generating signals")
            print(f"   ❌ Issue is deeper than just filters")
            print(f"   Need to debug ML algorithm implementation")


def main():
    """Main entry point"""
    
    # Test symbols
    symbols = ['RELIANCE', 'INFY', 'ICICIBANK']
    
    # Create and run test
    tester = ComprehensiveMarketTest()
    tester.run_comprehensive_test(symbols)
    
    print("\n✅ Comprehensive test complete!")


if __name__ == "__main__":
    main()
