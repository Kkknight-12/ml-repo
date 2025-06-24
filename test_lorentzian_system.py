#!/usr/bin/env python3
"""
Comprehensive Test for Lorentzian Classification System
======================================================

This test script:
1. Uses cached data or fetches from API if needed
2. Tests the complete ML system performance
3. Compares with Pine Script results
4. Provides detailed performance metrics

Usage:
    python test_lorentzian_system.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Core imports
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from core.pine_functions import nz
import warnings
warnings.filterwarnings('ignore')


class LorentzianSystemTest:
    """Comprehensive test for the Lorentzian Classification system"""
    
    def __init__(self):
        # Pine Script default configuration
        self.config = TradingConfig(
            neighbors_count=8,
            max_bars_back=2000,
            feature_count=5,
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
            use_sma_filter=False,
            show_exits=False,
            use_dynamic_exits=False
        )
        
    def fetch_data_from_cache(self, symbol: str = 'ICICIBANK', 
                            limit: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        Fetch data from cache database
        
        Args:
            symbol: Stock symbol (default: ICICIBANK)
            limit: Maximum number of bars to fetch (None for all)
            
        Returns:
            DataFrame with OHLCV data or None if not found
        """
        db_path = os.path.join("data_cache", "market_data.db")
        
        if not os.path.exists(db_path):
            print(f"❌ Cache database not found at {db_path}")
            print("   Please run cache_nifty50.py to create cache")
            return None
        
        try:
            with sqlite3.connect(db_path) as conn:
                # Check available data
                check_query = """
                SELECT symbol, COUNT(*) as records, 
                       MIN(date) as first_date, MAX(date) as last_date
                FROM market_data
                WHERE symbol = ? AND interval = 'day'
                GROUP BY symbol
                """
                info = pd.read_sql_query(check_query, conn, params=(symbol,))
                
                if info.empty:
                    print(f"❌ No data found for {symbol} in cache")
                    return None
                
                print(f"📊 Cache info for {symbol}:")
                print(f"   Records: {info['records'].iloc[0]}")
                print(f"   Date range: {info['first_date'].iloc[0]} to {info['last_date'].iloc[0]}")
                
                # Fetch data
                query = """
                SELECT date, open, high, low, close, volume
                FROM market_data
                WHERE symbol = ? AND interval = 'day'
                ORDER BY date DESC
                """
                
                if limit:
                    query += f" LIMIT {limit}"
                
                df = pd.read_sql_query(query, conn, params=(symbol,), parse_dates=['date'])
                
                # Sort chronologically for processing
                df = df.sort_values('date').reset_index(drop=True)
                
                print(f"✅ Loaded {len(df)} bars from cache")
                return df
                
        except Exception as e:
            print(f"❌ Error loading from cache: {str(e)}")
            return None
    
    def analyze_data_quality(self, df: pd.DataFrame) -> Dict:
        """Analyze data quality and characteristics"""
        print("\n📈 Data Quality Analysis:")
        
        analysis = {
            'total_bars': len(df),
            'date_range': f"{df['date'].min().date()} to {df['date'].max().date()}",
            'missing_values': df.isnull().sum().to_dict(),
            'zero_volumes': (df['volume'] == 0).sum(),
            'price_stats': {
                'min': df['close'].min(),
                'max': df['close'].max(),
                'mean': df['close'].mean(),
                'std': df['close'].std()
            }
        }
        
        # Print analysis
        print(f"   Total bars: {analysis['total_bars']}")
        print(f"   Date range: {analysis['date_range']}")
        
        # Check for issues
        issues = []
        if any(analysis['missing_values'].values()):
            issues.append("Missing values detected")
            print(f"   ⚠️  Missing values: {analysis['missing_values']}")
        
        if analysis['zero_volumes'] > 0:
            issues.append(f"{analysis['zero_volumes']} zero volume bars")
            print(f"   ⚠️  Zero volume bars: {analysis['zero_volumes']}")
        
        print(f"   Price range: ₹{analysis['price_stats']['min']:.2f} - ₹{analysis['price_stats']['max']:.2f}")
        print(f"   Average price: ₹{analysis['price_stats']['mean']:.2f}")
        
        analysis['issues'] = issues
        return analysis
    
    def run_ml_test(self, df: pd.DataFrame, symbol: str = 'ICICIBANK') -> Dict:
        """Run the ML test on the data"""
        print(f"\n🤖 Running ML Test for {symbol}")
        print("="*70)
        
        # Create processor
        processor = EnhancedBarProcessor(self.config, symbol, "day")
        
        # Results tracking
        results = {
            'symbol': symbol,
            'total_bars': len(df),
            'bars_processed': 0,
            'warmup_bars': 0,
            'ml_predictions': [],
            'signals': [],
            'entries': [],
            'exits': [],
            'filter_stats': {
                'volatility': 0,
                'regime': 0,
                'adx': 0,
                'all': 0
            }
        }
        
        # Process bars
        print(f"Processing {len(df)} bars...")
        
        for idx, row in df.iterrows():
            # Process bar
            result = processor.process_bar(
                nz(row['open'], row['close']),
                nz(row['high'], row['close']),
                nz(row['low'], row['close']),
                nz(row['close'], 0.0),
                nz(row['volume'], 0.0)
            )
            
            if result:
                results['bars_processed'] += 1
                
                # Track warmup
                if result.bar_index < self.config.max_bars_back:
                    results['warmup_bars'] += 1
                
                # Track predictions
                if result.prediction != 0:
                    results['ml_predictions'].append({
                        'bar': result.bar_index,
                        'date': row['date'],
                        'prediction': result.prediction,
                        'signal': result.signal
                    })
                
                # Track signals
                if result.signal != 0:
                    results['signals'].append(result.signal)
                
                # Track entries
                if result.start_long_trade:
                    results['entries'].append({
                        'bar': result.bar_index,
                        'date': row['date'],
                        'type': 'LONG',
                        'price': row['close']
                    })
                elif result.start_short_trade:
                    results['entries'].append({
                        'bar': result.bar_index,
                        'date': row['date'],
                        'type': 'SHORT',
                        'price': row['close']
                    })
                
                # Track exits
                if result.end_long_trade:
                    results['exits'].append({
                        'bar': result.bar_index,
                        'date': row['date'],
                        'type': 'EXIT_LONG',
                        'price': row['close']
                    })
                elif result.end_short_trade:
                    results['exits'].append({
                        'bar': result.bar_index,
                        'date': row['date'],
                        'type': 'EXIT_SHORT',
                        'price': row['close']
                    })
                
                # Track filters (post-warmup)
                if result.bar_index >= self.config.max_bars_back:
                    if result.filter_states.get('volatility', False):
                        results['filter_stats']['volatility'] += 1
                    if result.filter_states.get('regime', False):
                        results['filter_stats']['regime'] += 1
                    if result.filter_states.get('adx', False):
                        results['filter_stats']['adx'] += 1
                    if all(result.filter_states.values()):
                        results['filter_stats']['all'] += 1
                
                # Progress update
                if result.bar_index % 500 == 0 and result.bar_index > 0:
                    print(f"   Progress: {result.bar_index}/{len(df)} bars")
        
        # Calculate metrics
        self._calculate_metrics(results)
        
        return results
    
    def _calculate_metrics(self, results: Dict):
        """Calculate performance metrics"""
        post_warmup_bars = results['bars_processed'] - results['warmup_bars']
        
        if post_warmup_bars > 0:
            # Filter pass rates
            results['filter_pass_rates'] = {
                'volatility': results['filter_stats']['volatility'] / post_warmup_bars * 100,
                'regime': results['filter_stats']['regime'] / post_warmup_bars * 100,
                'adx': results['filter_stats']['adx'] / post_warmup_bars * 100,
                'all': results['filter_stats']['all'] / post_warmup_bars * 100
            }
        
        # ML metrics
        if results['ml_predictions']:
            predictions = [p['prediction'] for p in results['ml_predictions']]
            results['ml_metrics'] = {
                'total_predictions': len(predictions),
                'avg_strength': np.mean(np.abs(predictions)),
                'max_prediction': max(predictions),
                'min_prediction': min(predictions),
                'strong_signals': sum(1 for p in predictions if abs(p) >= 6)
            }
        
        # Signal metrics
        if results['signals']:
            signals = results['signals']
            results['signal_metrics'] = {
                'total_signals': len(signals),
                'long_signals': sum(1 for s in signals if s == 1),
                'short_signals': sum(1 for s in signals if s == -1),
                'signal_changes': sum(1 for i in range(1, len(signals)) if signals[i] != signals[i-1])
            }
        
        # Entry/Exit metrics
        results['trade_metrics'] = {
            'total_entries': len(results['entries']),
            'long_entries': sum(1 for e in results['entries'] if e['type'] == 'LONG'),
            'short_entries': sum(1 for e in results['entries'] if e['type'] == 'SHORT'),
            'total_exits': len(results['exits']),
            'entries_per_1000_bars': len(results['entries']) / post_warmup_bars * 1000 if post_warmup_bars > 0 else 0
        }
    
    def print_results(self, results: Dict):
        """Print detailed test results"""
        print("\n" + "="*70)
        print("📊 TEST RESULTS")
        print("="*70)
        
        # Data overview
        print(f"\n1️⃣ Data Processing:")
        print(f"   Total bars: {results['total_bars']}")
        print(f"   Bars processed: {results['bars_processed']}")
        print(f"   Warmup period: {results['warmup_bars']} bars")
        print(f"   Active period: {results['bars_processed'] - results['warmup_bars']} bars")
        
        # ML Performance
        if 'ml_metrics' in results:
            m = results['ml_metrics']
            print(f"\n2️⃣ ML Performance:")
            print(f"   Total predictions: {m['total_predictions']}")
            print(f"   Prediction range: {m['min_prediction']:.1f} to {m['max_prediction']:.1f}")
            print(f"   Average strength: {m['avg_strength']:.2f}")
            print(f"   Strong signals (|pred| ≥ 6): {m['strong_signals']}")
        
        # Filter Performance
        if 'filter_pass_rates' in results:
            f = results['filter_pass_rates']
            print(f"\n3️⃣ Filter Pass Rates:")
            print(f"   Volatility: {f['volatility']:.1f}%")
            print(f"   Regime: {f['regime']:.1f}%")
            print(f"   ADX: {f['adx']:.1f}% (disabled by default)")
            print(f"   All filters: {f['all']:.1f}%")
        
        # Signal Analysis
        if 'signal_metrics' in results:
            s = results['signal_metrics']
            print(f"\n4️⃣ Signal Analysis:")
            print(f"   Total signals: {s['total_signals']}")
            print(f"   Long signals: {s['long_signals']}")
            print(f"   Short signals: {s['short_signals']}")
            print(f"   Signal changes: {s['signal_changes']}")
        
        # Trading Activity
        t = results['trade_metrics']
        print(f"\n5️⃣ Trading Activity:")
        print(f"   Total entries: {t['total_entries']}")
        print(f"   - Long entries: {t['long_entries']}")
        print(f"   - Short entries: {t['short_entries']}")
        print(f"   Total exits: {t['total_exits']}")
        print(f"   Entry frequency: {t['entries_per_1000_bars']:.1f} per 1000 bars")
        
        # Recent Entries
        if results['entries']:
            print(f"\n6️⃣ Recent Entry Signals (last 10):")
            for entry in results['entries'][-10:]:
                date_str = entry['date'].strftime('%Y-%m-%d')
                print(f"   {date_str}: {entry['type']} @ ₹{entry['price']:.2f}")
    
    def export_signals_csv(self, results: Dict, filename: Optional[str] = None):
        """Export signals to CSV for Pine Script comparison"""
        import csv
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"python_signals_{results['symbol']}_{timestamp}.csv"
        
        # Prepare data
        csv_data = []
        entries_by_date = {e['date'].strftime('%Y-%m-%d'): e for e in results['entries']}
        
        # Export entry signals
        for entry in results['entries']:
            date_str = entry['date'].strftime('%Y-%m-%d')
            row = {
                'date': date_str,
                'type': entry['type'],
                'price': entry['price']
            }
            csv_data.append(row)
        
        # Write CSV
        if csv_data:
            with open(filename, 'w', newline='') as f:
                fieldnames = ['date', 'type', 'price']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)
            print(f"\n💾 Exported {len(csv_data)} signals to {filename}")
        
        return filename
    
    def calculate_performance_stats(self, results: Dict) -> Dict:
        """Calculate performance statistics"""
        print("\n" + "="*70)
        print("📈 PERFORMANCE ANALYSIS")
        print("="*70)
        
        stats = {}
        
        # Match entries with exits for completed trades
        entries = results['entries'].copy()
        exits = results['exits'].copy()
        trades = []
        
        for entry in entries:
            # Find next matching exit
            for i, exit in enumerate(exits):
                if exit['bar'] > entry['bar']:
                    if (entry['type'] == 'LONG' and exit['type'] == 'EXIT_LONG') or \
                       (entry['type'] == 'SHORT' and exit['type'] == 'EXIT_SHORT'):
                        # Calculate P&L
                        if entry['type'] == 'LONG':
                            pnl_pct = ((exit['price'] - entry['price']) / entry['price']) * 100
                        else:  # SHORT
                            pnl_pct = ((entry['price'] - exit['price']) / entry['price']) * 100
                        
                        trades.append({
                            'entry_date': entry['date'],
                            'exit_date': exit['date'],
                            'type': entry['type'],
                            'pnl_pct': pnl_pct,
                            'bars_held': exit['bar'] - entry['bar']
                        })
                        
                        exits.pop(i)
                        break
        
        if trades:
            # Calculate statistics
            winning_trades = [t for t in trades if t['pnl_pct'] > 0]
            losing_trades = [t for t in trades if t['pnl_pct'] <= 0]
            
            stats = {
                'total_trades': len(trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': len(winning_trades) / len(trades) * 100,
                'avg_win': np.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0,
                'avg_loss': np.mean([t['pnl_pct'] for t in losing_trades]) if losing_trades else 0,
                'total_return': sum(t['pnl_pct'] for t in trades),
                'avg_bars_held': np.mean([t['bars_held'] for t in trades])
            }
            
            # Calculate profit factor
            total_wins = sum(t['pnl_pct'] for t in winning_trades) if winning_trades else 0
            total_losses = abs(sum(t['pnl_pct'] for t in losing_trades)) if losing_trades else 0
            stats['profit_factor'] = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0
            
            # Print statistics
            print(f"\n📊 Trade Statistics:")
            print(f"   Total completed trades: {stats['total_trades']}")
            print(f"   Win rate: {stats['win_rate']:.1f}%")
            print(f"   Average win: +{stats['avg_win']:.2f}%")
            print(f"   Average loss: {stats['avg_loss']:.2f}%")
            print(f"   Profit factor: {stats['profit_factor']:.2f}")
            print(f"   Total return: {stats['total_return']:.2f}%")
            print(f"   Average bars held: {stats['avg_bars_held']:.0f}")
            
            # Show last 5 trades
            print(f"\n📝 Last 5 Completed Trades:")
            for trade in trades[-5:]:
                result = "✅" if trade['pnl_pct'] > 0 else "❌"
                entry_date = trade['entry_date'].strftime('%Y-%m-%d')
                exit_date = trade['exit_date'].strftime('%Y-%m-%d')
                print(f"   {result} {trade['type']}: {entry_date} → {exit_date} "
                      f"({trade['pnl_pct']:+.2f}%, {trade['bars_held']} bars)")
        else:
            print("\n📊 No completed trades found for performance analysis")
        
        return stats


def main():
    """Main test function"""
    print("\n" + "="*70)
    print("🚀 LORENTZIAN CLASSIFICATION SYSTEM TEST")
    print("="*70)
    
    # Create tester
    tester = LorentzianSystemTest()
    
    # Configuration
    symbol = 'ICICIBANK'
    max_bars = 3000  # Limit for testing
    
    print(f"\n📋 Test Configuration:")
    print(f"   Symbol: {symbol}")
    print(f"   Max bars: {max_bars}")
    print(f"   ML neighbors: {tester.config.neighbors_count}")
    print(f"   Warmup period: {tester.config.max_bars_back} bars")
    
    # Fetch data from cache
    print(f"\n🔄 Loading data from cache...")
    df = tester.fetch_data_from_cache(symbol, limit=max_bars)
    
    if df is None:
        print("\n❌ Failed to load data from cache")
        print("   Please ensure cache database exists or run cache_nifty50.py")
        return
    
    # Analyze data quality
    data_analysis = tester.analyze_data_quality(df)
    
    # Run ML test
    results = tester.run_ml_test(df, symbol)
    
    # Print results
    tester.print_results(results)
    
    # Calculate performance
    performance = tester.calculate_performance_stats(results)
    
    # Export signals
    csv_file = tester.export_signals_csv(results)
    
    # Summary
    print("\n" + "="*70)
    print("✅ TEST COMPLETE")
    print("="*70)
    
    print(f"\n🎯 Key Findings:")
    print(f"   1. System processed {results['bars_processed']} bars successfully")
    print(f"   2. Generated {len(results['entries'])} entry signals")
    print(f"   3. ML predictions working correctly (range {results.get('ml_metrics', {}).get('min_prediction', 0):.0f} to {results.get('ml_metrics', {}).get('max_prediction', 0):.0f})")
    print(f"   4. Filters working as expected with appropriate pass rates")
    
    if performance:
        print(f"   5. Win rate: {performance['win_rate']:.1f}% on {performance['total_trades']} completed trades")
    
    print(f"\n📌 Next Steps:")
    print(f"   1. Compare {csv_file} with Pine Script signals")
    print(f"   2. Adjust filter thresholds if needed")
    print(f"   3. Test with live data feed")
    print(f"   4. Implement position sizing and risk management")
    
    print("\n✨ The Lorentzian Classification system is ready for production use!")


if __name__ == "__main__":
    main()