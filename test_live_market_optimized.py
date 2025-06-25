#!/usr/bin/env python3
"""
Optimized Live Market Test Script
=================================

Tests the Lorentzian system with optimized settings including:
- Multi-target exits
- ATR-based stops
- Pattern quality scoring
- Modular strategy integration

This version implements Phase 1 optimizations.
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
from config.fixed_optimized_settings import FixedOptimizedTradingConfig, get_conservative_config
from config.modular_strategies import ModularTradingSystem, StrategyModule
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from data.zerodha_client import ZerodhaClient
from utils.atr_stops import ATRStopCalculator
from utils.risk_management import calculate_trade_levels

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OptimizedLiveMarketTest:
    """
    Live market testing with optimized settings and multi-target exits
    """
    
    def __init__(self, config_type: str = "optimized", timeframe: str = "5min"):
        """
        Initialize with specified configuration
        
        Args:
            config_type: One of ["optimized", "conservative", "aggressive", "baseline"]
        """
        # Select configuration
        if config_type == "timeframe":
            from config.timeframe_configs import TimeframeOptimizedConfig
            self.config = TimeframeOptimizedConfig(timeframe)
        elif config_type == "conservative":
            self.config = get_conservative_config()
        elif config_type == "baseline":
            from config.settings import TradingConfig
            self.config = TradingConfig()
        else:
            self.config = FixedOptimizedTradingConfig()
        
        # Initialize modular system
        self.modular_system = ModularTradingSystem()
        if config_type == "optimized":
            # Enable proven modules for live trading
            self.modular_system.enable_module(StrategyModule.AI_PATTERN_QUALITY)
            self.modular_system.enable_module(StrategyModule.AI_TIME_WINDOWS)
            self.modular_system.enable_module(StrategyModule.RISK_ATR_STOPS)
            self.modular_system.enable_module(StrategyModule.RISK_MULTI_TARGET)
        
        # Initialize components
        self.kite_client = ZerodhaClient()
        self.processors = {}
        self.atr_calculators = {}
        self.active_trades = {}
        self.completed_trades = []
        
        # Performance tracking
        self.performance_stats = {
            'signals_generated': 0,
            'trades_entered': 0,
            'trades_exited': 0,
            'winning_trades': 0,
            'total_pnl': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0
        }
        
        logger.info(f"Initialized OptimizedLiveMarketTest with {config_type} configuration")
        self._print_configuration()
    
    def _print_configuration(self):
        """Print current configuration details"""
        print("\n" + "="*60)
        print("🔧 OPTIMIZED CONFIGURATION")
        print("="*60)
        print(f"Neighbors Count: {self.config.neighbors_count}")
        print(f"Dynamic Exits: {self.config.use_dynamic_exits}")
        print(f"Multi-Target System: Enabled")
        print(f"  - Target 1: {self.config.target_1_percent*100}% @ {self.config.target_1_ratio}R")
        print(f"  - Target 2: {self.config.target_2_percent*100}% @ {self.config.target_2_ratio}R")
        print(f"ATR Stop Multiplier: {self.config.stop_loss_atr_multiplier}")
        print(f"Min Pattern Score: {self.config.min_pattern_score}")
        
        print("\n📦 Enabled Modules:")
        for module in self.modular_system.get_enabled_modules():
            print(f"  - {module.value}")
    
    def run_live_test(
        self, 
        symbols: List[str], 
        duration_minutes: int = 60,
        update_interval: int = 5
    ):
        """
        Run live market test
        
        Args:
            symbols: List of stock symbols to test
            duration_minutes: How long to run the test
            update_interval: Seconds between updates
        """
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        print(f"\n🚀 Starting Optimized Live Market Test")
        print(f"Symbols: {symbols}")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Initialize processors and ATR calculators
        for symbol in symbols:
            self.processors[symbol] = EnhancedBarProcessor(
                self.config, symbol, "5minute"
            )
            self.atr_calculators[symbol] = ATRStopCalculator(period=14)
        
        # Main loop
        iteration = 0
        while datetime.now() < end_time:
            iteration += 1
            print(f"\n⏱️  Iteration {iteration} - {datetime.now().strftime('%H:%M:%S')}")
            
            # Process each symbol
            with ThreadPoolExecutor(max_workers=len(symbols)) as executor:
                futures = {
                    executor.submit(self._process_symbol, symbol): symbol 
                    for symbol in symbols
                }
                
                for future in as_completed(futures):
                    symbol = futures[future]
                    try:
                        result = future.result()
                        if result:
                            self._handle_signal(symbol, result)
                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {str(e)}")
            
            # Check active trades
            self._manage_active_trades()
            
            # Print status
            self._print_status()
            
            # Wait for next iteration
            time.sleep(update_interval)
        
        # Final summary
        self._print_final_summary()
        
        # Export results
        self._export_results()
    
    def _process_symbol(self, symbol: str) -> Optional[Dict]:
        """Process a single symbol and return signal if any"""
        try:
            # Get latest data
            df = self.kite_client.get_historical_data(
                symbol, 
                interval="5minute",
                days=1
            )
            
            if df.empty or len(df) < 5:
                return None
            
            # Get latest bar
            latest_bar = df.iloc[-1]
            
            # Update ATR
            atr = self.atr_calculators[symbol].update(
                latest_bar['high'],
                latest_bar['low'], 
                latest_bar['close']
            )
            
            # Process through ML
            result = self.processors[symbol].process_bar(
                latest_bar['open'],
                latest_bar['high'],
                latest_bar['low'],
                latest_bar['close'],
                latest_bar['volume']
            )
            
            # Skip if in warmup
            if self.processors[symbol].bars_processed < self.config.max_bars_back:
                return None
            
            # Calculate pattern quality score
            pattern_score = self._calculate_pattern_quality(result, latest_bar)
            
            # Apply modular strategies
            signal_score = result.prediction
            if self.modular_system.modules[StrategyModule.AI_TIME_WINDOWS].enabled:
                signal_score = self._apply_time_window_filter(signal_score)
            
            # Check entry conditions
            if (abs(signal_score) >= self.config.min_prediction_strength and
                pattern_score >= self.config.min_pattern_score and
                symbol not in self.active_trades):
                
                return {
                    'symbol': symbol,
                    'signal': 'LONG' if signal_score > 0 else 'SHORT',
                    'prediction': signal_score,
                    'pattern_score': pattern_score,
                    'price': latest_bar['close'],
                    'atr': atr,
                    'time': latest_bar.name,
                    'filters': result.filter_states
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {str(e)}")
            return None
    
    def _calculate_pattern_quality(self, result, bar) -> float:
        """Calculate pattern quality score (0-10)"""
        score = 5.0
        
        # ML prediction strength (0-3 points)
        pred_strength = abs(result.prediction)
        if pred_strength >= 6:
            score += 3
        elif pred_strength >= 4:
            score += 2
        elif pred_strength >= 2:
            score += 1
        
        # Filter alignment (0-2 points)
        filters_passed = sum([
            result.filter_states.get('volatility', False),
            result.filter_states.get('regime', False),
            result.filter_states.get('adx', False)
        ])
        score += filters_passed * 0.67
        
        # Volume confirmation (0-1 point)
        if 'volume' in bar and bar['volume'] > 0:
            # Placeholder for volume analysis
            score += 0.5
        
        # Price action (0-1 point)
        # Placeholder for price action scoring
        score += 0.5
        
        return min(10, score)
    
    def _apply_time_window_filter(self, signal_score: float) -> float:
        """Apply time-based trading window filter"""
        current_hour = datetime.now().hour + datetime.now().minute / 60
        
        # No trades before 10 AM or after 2:45 PM
        if current_hour < 10.0 or current_hour > 14.75:
            return 0.0
        
        # Prime window boost (11:30 AM - 1:30 PM)
        if 11.5 <= current_hour <= 13.5:
            return signal_score * 1.5
        
        return signal_score
    
    def _handle_signal(self, symbol: str, signal_data: Dict):
        """Handle a new trading signal"""
        self.performance_stats['signals_generated'] += 1
        
        print(f"\n🎯 SIGNAL: {signal_data['signal']} {symbol}")
        print(f"   Price: ₹{signal_data['price']:.2f}")
        print(f"   Prediction: {signal_data['prediction']:.2f}")
        print(f"   Pattern Score: {signal_data['pattern_score']:.1f}/10")
        print(f"   ATR: {signal_data['atr']:.2f}")
        
        # Calculate position details using ATR
        atr = signal_data['atr']
        entry_price = signal_data['price']
        
        # ATR-based stop loss
        stop_loss = self.atr_calculators[symbol].calculate_stop_loss(
            entry_price,
            atr,
            direction=1 if signal_data['signal'] == 'LONG' else -1,
            multiplier=self.config.stop_loss_atr_multiplier
        )
        
        # Multi-target calculation
        risk = abs(entry_price - stop_loss)
        targets = [
            entry_price + (risk * self.config.target_1_ratio * (1 if signal_data['signal'] == 'LONG' else -1)),
            entry_price + (risk * self.config.target_2_ratio * (1 if signal_data['signal'] == 'LONG' else -1))
        ]
        
        # Create trade entry
        trade = {
            'entry_time': datetime.now(),
            'signal': signal_data['signal'],
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'targets': targets,
            'current_stop': stop_loss,
            'atr': atr,
            'pattern_score': signal_data['pattern_score'],
            'prediction': signal_data['prediction'],
            'partial_exits': 0,
            'remaining_position': 1.0,
            'status': 'ACTIVE'
        }
        
        self.active_trades[symbol] = trade
        self.performance_stats['trades_entered'] += 1
        
        print(f"   Stop Loss: ₹{stop_loss:.2f} ({risk/entry_price*100:.1f}%)")
        print(f"   Target 1: ₹{targets[0]:.2f} ({abs(targets[0]-entry_price)/entry_price*100:.1f}%)")
        print(f"   Target 2: ₹{targets[1]:.2f} ({abs(targets[1]-entry_price)/entry_price*100:.1f}%)")
    
    def _manage_active_trades(self):
        """Check and manage active trades"""
        for symbol, trade in list(self.active_trades.items()):
            try:
                # Get current price
                ltp_data = self.kite_client.get_ltp([symbol])
                if symbol not in ltp_data:
                    continue
                
                current_price = ltp_data[symbol]['last_price']
                
                # Check stop loss
                if trade['signal'] == 'LONG':
                    if current_price <= trade['current_stop']:
                        self._exit_trade(symbol, current_price, 'STOP_LOSS')
                        continue
                    
                    # Check targets
                    if trade['partial_exits'] == 0 and current_price >= trade['targets'][0]:
                        self._partial_exit(symbol, current_price, 1)
                    elif trade['partial_exits'] == 1 and current_price >= trade['targets'][1]:
                        self._partial_exit(symbol, current_price, 2)
                    
                    # Update trailing stop
                    if trade['partial_exits'] > 0:
                        new_stop = self.atr_calculators[symbol].calculate_trailing_stop(
                            current_price,
                            trade['atr'],
                            direction=1,
                            multiplier=1.5,
                            current_stop=trade['current_stop']
                        )
                        if new_stop > trade['current_stop']:
                            trade['current_stop'] = new_stop
                            print(f"   {symbol}: Trailing stop updated to ₹{new_stop:.2f}")
                
                else:  # SHORT
                    if current_price >= trade['current_stop']:
                        self._exit_trade(symbol, current_price, 'STOP_LOSS')
                        continue
                    
                    # Check targets
                    if trade['partial_exits'] == 0 and current_price <= trade['targets'][0]:
                        self._partial_exit(symbol, current_price, 1)
                    elif trade['partial_exits'] == 1 and current_price <= trade['targets'][1]:
                        self._partial_exit(symbol, current_price, 2)
                    
                    # Update trailing stop
                    if trade['partial_exits'] > 0:
                        new_stop = self.atr_calculators[symbol].calculate_trailing_stop(
                            current_price,
                            trade['atr'],
                            direction=-1,
                            multiplier=1.5,
                            current_stop=trade['current_stop']
                        )
                        if new_stop < trade['current_stop']:
                            trade['current_stop'] = new_stop
                            print(f"   {symbol}: Trailing stop updated to ₹{new_stop:.2f}")
                
            except Exception as e:
                logger.error(f"Error managing trade for {symbol}: {str(e)}")
    
    def _partial_exit(self, symbol: str, exit_price: float, target_num: int):
        """Execute partial exit"""
        trade = self.active_trades[symbol]
        
        if target_num == 1:
            exit_percent = self.config.target_1_percent
            print(f"\n💰 TARGET 1 HIT - {symbol}")
        else:
            exit_percent = self.config.target_2_percent
            print(f"\n💰 TARGET 2 HIT - {symbol}")
        
        # Calculate partial P&L
        if trade['signal'] == 'LONG':
            pnl_percent = (exit_price - trade['entry_price']) / trade['entry_price'] * 100
        else:
            pnl_percent = (trade['entry_price'] - exit_price) / trade['entry_price'] * 100
        
        print(f"   Exit {exit_percent*100:.0f}% @ ₹{exit_price:.2f} (+{pnl_percent:.1f}%)")
        
        # Update trade
        trade['partial_exits'] = target_num
        trade['remaining_position'] -= exit_percent
        
        # Move stop to breakeven after first target
        if target_num == 1:
            trade['current_stop'] = trade['entry_price']
            print(f"   Stop moved to breakeven: ₹{trade['entry_price']:.2f}")
    
    def _exit_trade(self, symbol: str, exit_price: float, reason: str):
        """Complete exit of trade"""
        trade = self.active_trades[symbol]
        
        # Calculate final P&L
        if trade['signal'] == 'LONG':
            pnl_percent = (exit_price - trade['entry_price']) / trade['entry_price'] * 100
        else:
            pnl_percent = (trade['entry_price'] - exit_price) / trade['entry_price'] * 100
        
        # Account for partial exits
        effective_pnl = pnl_percent * trade['remaining_position']
        
        # Update stats
        self.performance_stats['trades_exited'] += 1
        self.performance_stats['total_pnl'] += effective_pnl
        
        if effective_pnl > 0:
            self.performance_stats['winning_trades'] += 1
            if effective_pnl > self.performance_stats['largest_win']:
                self.performance_stats['largest_win'] = effective_pnl
        else:
            if effective_pnl < self.performance_stats['largest_loss']:
                self.performance_stats['largest_loss'] = effective_pnl
        
        # Record completed trade
        trade['exit_time'] = datetime.now()
        trade['exit_price'] = exit_price
        trade['exit_reason'] = reason
        trade['pnl_percent'] = effective_pnl
        trade['status'] = 'COMPLETED'
        self.completed_trades.append(trade)
        
        # Remove from active
        del self.active_trades[symbol]
        
        emoji = "✅" if effective_pnl > 0 else "❌"
        print(f"\n{emoji} EXIT {trade['signal']} - {symbol}")
        print(f"   Exit Price: ₹{exit_price:.2f} ({reason})")
        print(f"   P&L: {effective_pnl:+.1f}%")
        print(f"   Hold Time: {(trade['exit_time'] - trade['entry_time']).seconds // 60} minutes")
    
    def _print_status(self):
        """Print current status"""
        win_rate = (self.performance_stats['winning_trades'] / 
                   max(1, self.performance_stats['trades_exited']) * 100)
        
        print(f"\n📊 Status: {len(self.active_trades)} active, "
              f"{self.performance_stats['trades_exited']} completed, "
              f"Win Rate: {win_rate:.1f}%, "
              f"Total P&L: {self.performance_stats['total_pnl']:+.1f}%")
    
    def _print_final_summary(self):
        """Print final test summary"""
        print("\n" + "="*60)
        print("📊 OPTIMIZED LIVE TEST SUMMARY")
        print("="*60)
        
        print(f"\n📈 Signal Statistics:")
        print(f"   Signals Generated: {self.performance_stats['signals_generated']}")
        print(f"   Trades Entered: {self.performance_stats['trades_entered']}")
        print(f"   Trades Completed: {self.performance_stats['trades_exited']}")
        print(f"   Active Trades: {len(self.active_trades)}")
        
        if self.performance_stats['trades_exited'] > 0:
            win_rate = (self.performance_stats['winning_trades'] / 
                       self.performance_stats['trades_exited'] * 100)
            avg_pnl = (self.performance_stats['total_pnl'] / 
                      self.performance_stats['trades_exited'])
            
            print(f"\n💰 Performance Metrics:")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Total P&L: {self.performance_stats['total_pnl']:+.1f}%")
            print(f"   Average P&L: {avg_pnl:+.1f}%")
            print(f"   Largest Win: {self.performance_stats['largest_win']:+.1f}%")
            print(f"   Largest Loss: {self.performance_stats['largest_loss']:+.1f}%")
        
        print(f"\n🎯 Multi-Target Performance:")
        target_hits = sum(1 for t in self.completed_trades if t['partial_exits'] > 0)
        if target_hits > 0:
            print(f"   Trades hitting Target 1: {target_hits}")
            target2_hits = sum(1 for t in self.completed_trades if t['partial_exits'] > 1)
            print(f"   Trades hitting Target 2: {target2_hits}")
    
    def _export_results(self):
        """Export test results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export completed trades
        if self.completed_trades:
            trades_df = pd.DataFrame(self.completed_trades)
            filename = f"optimized_live_results_{timestamp}.csv"
            trades_df.to_csv(filename, index=False)
            print(f"\n💾 Results exported to {filename}")
        
        # Export summary
        summary = {
            'test_time': timestamp,
            'configuration': self.config.__class__.__name__,
            'enabled_modules': [m.value for m in self.modular_system.get_enabled_modules()],
            'performance': self.performance_stats,
            'config_params': {
                'neighbors_count': self.config.neighbors_count,
                'min_prediction_strength': self.config.min_prediction_strength,
                'min_pattern_score': self.config.min_pattern_score,
                'stop_loss_multiplier': self.config.stop_loss_atr_multiplier,
                'target_1_ratio': self.config.target_1_ratio,
                'target_2_ratio': self.config.target_2_ratio
            }
        }
        
        summary_file = f"optimized_test_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"💾 Summary exported to {summary_file}")


def main():
    """Run optimized live market test"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Optimized Live Market Test')
    parser.add_argument('--symbols', nargs='+', 
                       default=['RELIANCE', 'TCS', 'INFY'],
                       help='Symbols to test')
    parser.add_argument('--duration', type=int, default=60,
                       help='Test duration in minutes')
    parser.add_argument('--config', choices=['optimized', 'conservative', 'baseline', 'timeframe'],
                       default='optimized',
                       help='Configuration type to use')
    parser.add_argument('--timeframe', choices=['1min', '5min', '15min', '30min', '60min', 'daily'],
                       default='5min',
                       help='Timeframe to use (only applies when config=timeframe)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("🚀 OPTIMIZED LIVE MARKET TEST")
    print("="*60)
    print("\nObjective: Test multi-target exits and optimized settings")
    print("Focus: Increase average win from 3.7% to 7-10%")
    
    # Initialize and run test
    if args.config == 'timeframe':
        tester = OptimizedLiveMarketTest(config_type=args.config, timeframe=args.timeframe)
        print(f"Using {args.timeframe} timeframe configuration")
    else:
        tester = OptimizedLiveMarketTest(config_type=args.config)
    
    tester.run_live_test(
        symbols=args.symbols,
        duration_minutes=args.duration,
        update_interval=5
    )


if __name__ == "__main__":
    main()