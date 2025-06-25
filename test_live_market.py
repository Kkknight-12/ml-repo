#!/usr/bin/env python3
"""
Live Market Test Script for Lorentzian Classification System
===========================================================

This script tests the Lorentzian system with live market data from Zerodha.
It processes real-time market bars and generates trading signals.

Features:
- Connects to Zerodha for live data
- Processes multiple stocks in real-time
- Shows ML predictions and filter states
- Tracks signal generation and performance
- Exports results for analysis

Usage:
    python test_live_market.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time
import json
from typing import Dict, List, Tuple, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Core imports
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from data.zerodha_client import ZerodhaClient
from utils.risk_management import calculate_trade_levels

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiveMarketTest:
    """
    Live market testing for the Lorentzian Classification system
    """
    
    def __init__(self, test_symbols: List[str] = None):
        """
        Initialize with optional list of symbols to test
        
        Args:
            test_symbols: List of stock symbols to test (default: top Nifty 50 stocks)
        """
        self.logger = logger
        self.kite_client = None
        self.results = {}
        self.active_signals = {}
        self.trade_history = []
        
        # Default test symbols if none provided
        self.test_symbols = test_symbols or [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
            'HDFC', 'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK',
            'BAJFINANCE', 'LT', 'HINDUNILVR', 'ASIANPAINT', 'AXISBANK'
        ]
        
        # Pine Script default configuration
        self.config = TradingConfig(
            # Core ML settings
            neighbors_count=8,
            max_bars_back=2000,
            feature_count=5,
            source='close',
            
            # Filter settings
            use_volatility_filter=True,
            use_regime_filter=True,
            use_adx_filter=False,
            regime_threshold=-0.1,
            adx_threshold=20,
            
            # Kernel settings
            use_kernel_filter=True,
            use_kernel_smoothing=False,
            kernel_lookback=8,
            kernel_relative_weight=8.0,
            kernel_regression_level=25,
            kernel_lag=2,
            
            # EMA/SMA filters
            use_ema_filter=False,
            use_sma_filter=False,
            
            # Exit settings
            show_exits=False,
            use_dynamic_exits=False
        )
        
        # Initialize processors for each symbol
        self.processors = {
            symbol: EnhancedBarProcessor(self.config, symbol, "5min")
            for symbol in self.test_symbols
        }
        
        print("\n🚀 Live Market Test Configuration:")
        print(f"   Testing {len(self.test_symbols)} stocks: {', '.join(self.test_symbols[:5])}...")
        print(f"   ML Settings: neighbors={self.config.neighbors_count}, features={self.config.feature_count}")
        print(f"   Active Filters: volatility={self.config.use_volatility_filter}, "
              f"regime={self.config.use_regime_filter}, kernel={self.config.use_kernel_filter}")
    
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
                
                # Test connection
                profile = self.kite_client.kite.profile()
                print(f"\n📡 Zerodha connected: {profile.get('user_name', 'Unknown')}")
                return True
            else:
                print("❌ No access token found. Run auth_helper.py first")
                return False
                
        except Exception as e:
            print(f"❌ Failed to initialize Zerodha: {e}")
            return False
    
    def fetch_historical_data(self, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for warmup
        
        Args:
            symbol: Stock symbol
            days: Number of days of historical data
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Fetch 5-minute data
            data = self.kite_client.get_historical_data(
                symbol=symbol,
                interval='5minute',
                days=days
            )
            
            if data:
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                return df
            else:
                self.logger.warning(f"No historical data found for {symbol}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None
    
    def warmup_processor(self, symbol: str) -> bool:
        """
        Warmup processor with historical data
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if warmup successful
        """
        try:
            print(f"\n⏳ Warming up {symbol}...")
            
            # Fetch historical data
            hist_data = self.fetch_historical_data(symbol, days=30)
            if hist_data is None or hist_data.empty:
                print(f"❌ No historical data for {symbol}")
                return False
            
            processor = self.processors[symbol]
            bars_processed = 0
            
            # Process historical bars
            for idx, row in hist_data.iterrows():
                result = processor.process_bar(
                    open_price=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume']
                )
                bars_processed += 1
            
            print(f"✅ {symbol}: Processed {bars_processed} historical bars")
            print(f"   Current bar index: {processor.bar_index}")
            print(f"   ML predictions started: {processor.ml_model.has_enough_data}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error warming up {symbol}: {e}")
            return False
    
    def process_live_bar(self, symbol: str, bar_data: Dict) -> Dict:
        """
        Process a single live bar
        
        Args:
            symbol: Stock symbol
            bar_data: Dict with OHLCV data
            
        Returns:
            Dict with processing results
        """
        try:
            processor = self.processors[symbol]
            
            # Process the bar
            result = processor.process_bar(
                open_price=bar_data['open'],
                high=bar_data['high'],
                low=bar_data['low'],
                close=bar_data['close'],
                volume=bar_data['volume']
            )
            
            # Prepare result summary
            summary = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'close': bar_data['close'],
                'prediction': result.prediction,
                'signal': result.signal,
                'ml_accuracy': processor.ml_model.calculate_accuracy() if hasattr(processor.ml_model, 'calculate_accuracy') else None,
                'start_long': result.start_long_trade,
                'start_short': result.start_short_trade,
                'filters': result.filter_states,
                'bar_index': result.bar_index
            }
            
            # Check for new signals
            if result.start_long_trade:
                stop_loss, take_profit = calculate_trade_levels(
                    entry_price=bar_data['close'],
                    is_long=True,
                    atr_value=processor.feature_series.f5 if hasattr(processor, 'feature_series') else None,
                    use_dynamic_exits=self.config.use_dynamic_exits
                )
                
                signal_info = {
                    'type': 'LONG',
                    'entry_price': bar_data['close'],
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_time': datetime.now(),
                    'prediction': result.prediction
                }
                
                self.active_signals[symbol] = signal_info
                print(f"\n🟢 LONG SIGNAL - {symbol}")
                print(f"   Entry: {bar_data['close']:.2f}")
                print(f"   SL: {stop_loss:.2f} | TP: {take_profit:.2f}")
                print(f"   ML Prediction: {result.prediction:.2f}")
                
            elif result.start_short_trade:
                stop_loss, take_profit = calculate_trade_levels(
                    entry_price=bar_data['close'],
                    is_long=False,
                    atr_value=processor.feature_series.f5 if hasattr(processor, 'feature_series') else None,
                    use_dynamic_exits=self.config.use_dynamic_exits
                )
                
                signal_info = {
                    'type': 'SHORT',
                    'entry_price': bar_data['close'],
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_time': datetime.now(),
                    'prediction': result.prediction
                }
                
                self.active_signals[symbol] = signal_info
                print(f"\n🔴 SHORT SIGNAL - {symbol}")
                print(f"   Entry: {bar_data['close']:.2f}")
                print(f"   SL: {stop_loss:.2f} | TP: {take_profit:.2f}")
                print(f"   ML Prediction: {result.prediction:.2f}")
            
            # Check for exits
            elif symbol in self.active_signals:
                active_signal = self.active_signals[symbol]
                
                # Check stop loss or take profit
                if active_signal['type'] == 'LONG':
                    if bar_data['close'] <= active_signal['stop_loss']:
                        self._close_position(symbol, bar_data['close'], 'STOP_LOSS')
                    elif bar_data['close'] >= active_signal['take_profit']:
                        self._close_position(symbol, bar_data['close'], 'TAKE_PROFIT')
                    elif result.end_long_trade:
                        self._close_position(symbol, bar_data['close'], 'SIGNAL_EXIT')
                else:  # SHORT
                    if bar_data['close'] >= active_signal['stop_loss']:
                        self._close_position(symbol, bar_data['close'], 'STOP_LOSS')
                    elif bar_data['close'] <= active_signal['take_profit']:
                        self._close_position(symbol, bar_data['close'], 'TAKE_PROFIT')
                    elif result.end_short_trade:
                        self._close_position(symbol, bar_data['close'], 'SIGNAL_EXIT')
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error processing bar for {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def _close_position(self, symbol: str, exit_price: float, exit_reason: str):
        """Close an active position"""
        if symbol not in self.active_signals:
            return
            
        signal = self.active_signals[symbol]
        pnl = exit_price - signal['entry_price'] if signal['type'] == 'LONG' else signal['entry_price'] - exit_price
        pnl_percent = (pnl / signal['entry_price']) * 100
        
        trade_record = {
            'symbol': symbol,
            'type': signal['type'],
            'entry_price': signal['entry_price'],
            'exit_price': exit_price,
            'entry_time': signal['entry_time'],
            'exit_time': datetime.now(),
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'exit_reason': exit_reason
        }
        
        self.trade_history.append(trade_record)
        del self.active_signals[symbol]
        
        emoji = "✅" if pnl > 0 else "❌"
        print(f"\n{emoji} CLOSED {signal['type']} - {symbol}")
        print(f"   Exit: {exit_price:.2f} ({exit_reason})")
        print(f"   P&L: {pnl:.2f} ({pnl_percent:+.2f}%)")
    
    def fetch_live_data(self) -> Dict[str, Dict]:
        """
        Fetch live data for all symbols
        
        Returns:
            Dict mapping symbol to latest bar data
        """
        live_data = {}
        
        try:
            # Get LTP for all symbols
            instruments = [f"NSE:{symbol}" for symbol in self.test_symbols]
            quotes = self.kite_client.kite.quote(instruments)
            
            for symbol in self.test_symbols:
                instrument = f"NSE:{symbol}"
                if instrument in quotes:
                    quote = quotes[instrument]
                    live_data[symbol] = {
                        'open': quote['ohlc']['open'],
                        'high': quote['ohlc']['high'],
                        'low': quote['ohlc']['low'],
                        'close': quote['last_price'],
                        'volume': quote['volume']
                    }
                    
        except Exception as e:
            self.logger.error(f"Error fetching live data: {e}")
            
        return live_data
    
    def run_continuous_test(self, duration_minutes: int = 60):
        """
        Run continuous live market test
        
        Args:
            duration_minutes: How long to run the test
        """
        print(f"\n🏃 Starting continuous test for {duration_minutes} minutes...")
        
        # First warmup all processors
        print("\n📊 Warming up processors with historical data...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self.warmup_processor, symbol): symbol 
                      for symbol in self.test_symbols}
            
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    success = future.result()
                    if not success:
                        print(f"⚠️  Failed to warmup {symbol}")
                except Exception as e:
                    print(f"❌ Error warming up {symbol}: {e}")
        
        # Run live test
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        update_interval = 5  # seconds
        
        print(f"\n📈 Live testing started at {start_time.strftime('%H:%M:%S')}")
        print(f"   Will run until {end_time.strftime('%H:%M:%S')}")
        print("\n" + "="*60)
        
        try:
            while datetime.now() < end_time:
                # Check if market is open
                now = datetime.now()
                if now.hour < 9 or (now.hour == 9 and now.minute < 15) or now.hour >= 15 or (now.hour == 15 and now.minute > 30):
                    print(f"\r⏸️  Market closed. Waiting... (Current time: {now.strftime('%H:%M:%S')})", end='')
                    time.sleep(30)
                    continue
                
                # Fetch and process live data
                live_data = self.fetch_live_data()
                
                if live_data:
                    # Process each symbol
                    for symbol, bar_data in live_data.items():
                        result = self.process_live_bar(symbol, bar_data)
                        
                        # Store result
                        if symbol not in self.results:
                            self.results[symbol] = []
                        self.results[symbol].append(result)
                    
                    # Display status
                    active_count = len(self.active_signals)
                    total_trades = len(self.trade_history)
                    profitable_trades = sum(1 for t in self.trade_history if t['pnl'] > 0)
                    
                    print(f"\r📊 Active: {active_count} | Completed: {total_trades} | "
                          f"Win Rate: {(profitable_trades/total_trades*100) if total_trades > 0 else 0:.1f}% | "
                          f"Time: {datetime.now().strftime('%H:%M:%S')}", end='')
                
                # Wait before next update
                time.sleep(update_interval)
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted by user")
        except Exception as e:
            print(f"\n\n❌ Error during test: {e}")
        
        # Print final summary
        self._print_summary()
    
    def _print_summary(self):
        """Print test summary"""
        print("\n\n" + "="*60)
        print("📊 LIVE MARKET TEST SUMMARY")
        print("="*60)
        
        # Overall stats
        total_signals = sum(len(v) for v in self.results.values())
        total_trades = len(self.trade_history)
        
        print(f"\n📈 Overall Statistics:")
        print(f"   Total bars processed: {total_signals}")
        print(f"   Total trades: {total_trades}")
        
        if total_trades > 0:
            profitable = sum(1 for t in self.trade_history if t['pnl'] > 0)
            total_pnl = sum(t['pnl'] for t in self.trade_history)
            avg_pnl = total_pnl / total_trades
            
            print(f"   Profitable trades: {profitable}/{total_trades} ({profitable/total_trades*100:.1f}%)")
            print(f"   Total P&L: {total_pnl:.2f}")
            print(f"   Average P&L per trade: {avg_pnl:.2f}")
        
        # Active positions
        if self.active_signals:
            print(f"\n📍 Active Positions ({len(self.active_signals)}):")
            for symbol, signal in self.active_signals.items():
                print(f"   {symbol}: {signal['type']} @ ₹{signal['entry_price']:.2f}")
        
        # Recent trades
        if self.trade_history:
            print(f"\n📜 Recent Trades (last 5):")
            for trade in self.trade_history[-5:]:
                emoji = "✅" if trade['pnl'] > 0 else "❌"
                print(f"   {emoji} {trade['symbol']}: {trade['type']} "
                      f"{trade['pnl_percent']:+.2f}% ({trade['exit_reason']})")
        
        # Export results
        self._export_results()
    
    def _export_results(self):
        """Export test results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export trade history
        if self.trade_history:
            trades_df = pd.DataFrame(self.trade_history)
            trades_file = f"live_trades_{timestamp}.csv"
            trades_df.to_csv(trades_file, index=False)
            print(f"\n💾 Trade history exported to: {trades_file}")
        
        # Export detailed results
        results_file = f"live_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'config': self.config.__dict__,
                'test_duration': str(datetime.now() - self.trade_history[0]['entry_time']) if self.trade_history else "0",
                'symbols_tested': self.test_symbols,
                'total_trades': len(self.trade_history),
                'active_signals': self.active_signals,
                'summary_stats': self._calculate_summary_stats()
            }, f, indent=2, default=str)
        print(f"💾 Detailed results exported to: {results_file}")
    
    def _calculate_summary_stats(self) -> Dict:
        """Calculate summary statistics"""
        if not self.trade_history:
            return {}
            
        trades_df = pd.DataFrame(self.trade_history)
        
        return {
            'total_trades': len(trades_df),
            'win_rate': (trades_df['pnl'] > 0).mean() * 100,
            'avg_pnl': trades_df['pnl'].mean(),
            'total_pnl': trades_df['pnl'].sum(),
            'best_trade': trades_df['pnl'].max(),
            'worst_trade': trades_df['pnl'].min(),
            'avg_trade_duration': str(trades_df['exit_time'] - trades_df['entry_time']).mean() if 'exit_time' in trades_df else None
        }


def main():
    """Main execution function"""
    print("="*60)
    print("🚀 LORENTZIAN CLASSIFIER - LIVE MARKET TEST")
    print("="*60)
    
    # Optional: Specify custom symbols to test
    # test_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICIBANK']
    test_symbols = None  # Use default list
    
    # Create tester
    tester = LiveMarketTest(test_symbols)
    
    # Initialize Zerodha
    if not tester.initialize_zerodha():
        print("\n❌ Failed to initialize Zerodha. Exiting.")
        return
    
    # Run test
    try:
        # Run for specified duration (in minutes)
        test_duration = 60  # 1 hour
        tester.run_continuous_test(duration_minutes=test_duration)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()