#!/usr/bin/env python3
"""
Test Script for Optimized Lorentzian Classification System
=========================================================

This script demonstrates how to use the optimized parameters
to improve trading performance.

Key improvements implemented:
1. Dynamic exits instead of fixed 5-bar exit
2. More responsive ML parameters
3. Stronger trend filters
4. Multi-target profit booking
5. Time-based trading windows
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

# Import optimized configuration
from config.fixed_optimized_settings import (
    FixedOptimizedTradingConfig, 
    get_conservative_config,
    get_aggressive_config,
    get_scalping_config,
    get_swing_trading_config
)

# Core imports
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from data.zerodha_client import ZerodhaClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OptimizedTradingSystem:
    """Trading system with optimized parameters"""
    
    def __init__(self, config_type: str = "optimized"):
        """
        Initialize with specified configuration
        
        Args:
            config_type: One of ["optimized", "conservative", "aggressive", "scalping", "swing"]
        """
        # Select configuration
        if config_type == "conservative":
            self.config = get_conservative_config()
        elif config_type == "aggressive":
            self.config = get_aggressive_config()
        elif config_type == "scalping":
            self.config = get_scalping_config()
        elif config_type == "swing":
            self.config = get_swing_trading_config()
        else:
            self.config = FixedOptimizedTradingConfig()
        
        self.processors = {}
        self.active_trades = {}
        self.trade_history = []
        self.daily_stats = {
            'trades': 0,
            'pnl': 0.0,
            'wins': 0,
            'losses': 0
        }
        
        print(f"\n🚀 Initialized {config_type.upper()} Trading System")
        self._print_key_parameters()
    
    def _print_key_parameters(self):
        """Print key optimized parameters"""
        print("\n📊 Key Parameters (Optimized vs Default):")
        print(f"   ML Neighbors: {self.config.neighbors_count} (was 8)")
        print(f"   Dynamic Exits: {self.config.use_dynamic_exits} (was False)")
        print(f"   ADX Filter: {self.config.use_adx_filter} @ {self.config.adx_threshold} (was disabled)")
        print(f"   Regime Threshold: {self.config.regime_threshold} (was -0.1)")
        print(f"   EMA Filter: {self.config.use_ema_filter} @ {self.config.ema_period} (was disabled)")
        print(f"   Kernel Smoothing: {self.config.use_kernel_smoothing} (was False)")
        print(f"   Risk per Trade: {self.config.risk_per_trade*100:.1f}%")
        print(f"   Profit Targets: {self.config.target_1_ratio}R & {self.config.target_2_ratio}R")
    
    def process_bar(self, symbol: str, bar_data: Dict) -> Dict:
        """
        Process a bar with optimized logic
        """
        # Initialize processor if needed
        if symbol not in self.processors:
            self.processors[symbol] = EnhancedBarProcessor(
                self.config, symbol, "5min"
            )
        
        processor = self.processors[symbol]
        
        # Check if ML is ready
        if processor.bars_processed < self.config.max_bars_back:
            return {'status': 'warming_up', 'bars_needed': self.config.max_bars_back - processor.bars_processed}
        
        # Process the bar
        result = processor.process_bar(
            bar_data['open'], bar_data['high'], 
            bar_data['low'], bar_data['close'], bar_data['volume']
        )
        
        # Check market conditions and time windows
        current_hour = datetime.now().hour + datetime.now().minute / 60
        in_prime_window = self.config.prime_window_start <= current_hour <= self.config.prime_window_end
        can_trade = self.config.no_trade_before_hour <= current_hour <= self.config.no_trade_after_hour
        
        # Calculate pattern quality score
        pattern_score = self._calculate_pattern_score(result, in_prime_window)
        
        # Check entry conditions with optimized thresholds
        if (can_trade and 
            pattern_score >= self.config.min_pattern_score and
            abs(result.prediction) >= self.config.min_prediction_strength and
            self.daily_stats['trades'] < self.config.max_trades_per_day):
            
            if result.start_long_trade and symbol not in self.active_trades:
                self._enter_long_trade(symbol, bar_data, result, pattern_score)
            elif result.start_short_trade and symbol not in self.active_trades:
                self._enter_short_trade(symbol, bar_data, result, pattern_score)
        
        # Check exit conditions for active trades
        if symbol in self.active_trades:
            self._check_exit_conditions(symbol, bar_data, result)
        
        return {
            'symbol': symbol,
            'prediction': result.prediction,
            'signal': result.signal,
            'pattern_score': pattern_score,
            'in_prime_window': in_prime_window,
            'filters': result.filter_states
        }
    
    def _calculate_pattern_score(self, result, in_prime_window: bool) -> float:
        """Calculate pattern quality score with optimized logic"""
        score = 5.0
        
        # ML prediction strength (0-3 points)
        pred_strength = abs(result.prediction)
        if pred_strength >= 6:
            score += 3
        elif pred_strength >= 4:
            score += 2
        elif pred_strength >= self.config.min_prediction_strength:
            score += 1
        
        # Filter alignment (0-3 points) - More weight on filters
        filters_passed = sum([
            result.filter_states.get('volatility', False),
            result.filter_states.get('regime', False),
            result.filter_states.get('adx', False),
            result.filter_states.get('kernel', False)
        ])
        score += filters_passed * 0.75
        
        # Time window bonus
        if in_prime_window:
            score += 1.5
        
        return min(10, score)
    
    def _enter_long_trade(self, symbol: str, bar_data: Dict, result, pattern_score: float):
        """Enter long with optimized parameters"""
        entry_price = bar_data['close']
        
        # Calculate ATR for stops
        atr = self._calculate_atr(symbol)
        stop_loss = entry_price - (atr * self.config.stop_loss_atr_multiplier)
        
        # Multi-target calculation
        risk = entry_price - stop_loss
        target_1 = entry_price + (risk * self.config.target_1_ratio)
        target_2 = entry_price + (risk * self.config.target_2_ratio)
        
        # Position sizing with pattern quality adjustment
        position_size_multiplier = self.config.get_position_size_multiplier(pattern_score)
        
        trade = {
            'type': 'LONG',
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'position_size_multiplier': position_size_multiplier,
            'pattern_score': pattern_score,
            'prediction': result.prediction,
            'partial_exits': 0,
            'trailing_stop_active': False
        }
        
        self.active_trades[symbol] = trade
        self.daily_stats['trades'] += 1
        
        print(f"\n🟢 LONG ENTRY - {symbol}")
        print(f"   Entry: {entry_price:.2f}")
        print(f"   Stop: {stop_loss:.2f} (-{(entry_price-stop_loss)/entry_price*100:.1f}%)")
        print(f"   Target 1: {target_1:.2f} (+{(target_1-entry_price)/entry_price*100:.1f}%) @ {self.config.target_1_percent*100}% exit")
        print(f"   Target 2: {target_2:.2f} (+{(target_2-entry_price)/entry_price*100:.1f}%) @ {self.config.target_2_percent*100}% exit")
        print(f"   Pattern Score: {pattern_score:.1f}/10")
        print(f"   Position Multiplier: {position_size_multiplier}x")
    
    def _enter_short_trade(self, symbol: str, bar_data: Dict, result, pattern_score: float):
        """Enter short with optimized parameters"""
        entry_price = bar_data['close']
        
        # Calculate ATR for stops
        atr = self._calculate_atr(symbol)
        stop_loss = entry_price + (atr * self.config.stop_loss_atr_multiplier)
        
        # Multi-target calculation
        risk = stop_loss - entry_price
        target_1 = entry_price - (risk * self.config.target_1_ratio)
        target_2 = entry_price - (risk * self.config.target_2_ratio)
        
        # Position sizing with pattern quality adjustment
        position_size_multiplier = self.config.get_position_size_multiplier(pattern_score)
        
        trade = {
            'type': 'SHORT',
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'position_size_multiplier': position_size_multiplier,
            'pattern_score': pattern_score,
            'prediction': result.prediction,
            'partial_exits': 0,
            'trailing_stop_active': False
        }
        
        self.active_trades[symbol] = trade
        self.daily_stats['trades'] += 1
        
        print(f"\n🔴 SHORT ENTRY - {symbol}")
        print(f"   Entry: {entry_price:.2f}")
        print(f"   Stop: {stop_loss:.2f} (+{(stop_loss-entry_price)/entry_price*100:.1f}%)")
        print(f"   Target 1: {target_1:.2f} (-{(entry_price-target_1)/entry_price*100:.1f}%) @ {self.config.target_1_percent*100}% exit")
        print(f"   Target 2: {target_2:.2f} (-{(entry_price-target_2)/entry_price*100:.1f}%) @ {self.config.target_2_percent*100}% exit")
        print(f"   Pattern Score: {pattern_score:.1f}/10")
        print(f"   Position Multiplier: {position_size_multiplier}x")
    
    def _check_exit_conditions(self, symbol: str, bar_data: Dict, result):
        """Check exits with optimized multi-target system"""
        trade = self.active_trades[symbol]
        current_price = bar_data['close']
        
        if trade['type'] == 'LONG':
            # Stop loss
            if current_price <= trade['stop_loss']:
                self._exit_trade(symbol, current_price, 'STOP_LOSS')
                return
            
            # Target 1 (partial exit)
            if trade['partial_exits'] == 0 and current_price >= trade['target_1']:
                self._partial_exit(symbol, current_price, 1)
                # Move stop to breakeven
                trade['stop_loss'] = trade['entry_price']
                trade['trailing_stop_active'] = True
            
            # Target 2 (partial exit)
            elif trade['partial_exits'] == 1 and current_price >= trade['target_2']:
                self._partial_exit(symbol, current_price, 2)
                # Activate trailing stop for remaining position
                atr = self._calculate_atr(symbol)
                trade['stop_loss'] = current_price - atr
            
            # Trailing stop update
            elif trade['trailing_stop_active']:
                atr = self._calculate_atr(symbol)
                new_stop = current_price - atr
                if new_stop > trade['stop_loss']:
                    trade['stop_loss'] = new_stop
            
            # Dynamic exit signal
            if self.config.use_dynamic_exits and result.end_long_trade:
                self._exit_trade(symbol, current_price, 'DYNAMIC_EXIT')
                
        else:  # SHORT
            # Stop loss
            if current_price >= trade['stop_loss']:
                self._exit_trade(symbol, current_price, 'STOP_LOSS')
                return
            
            # Target 1 (partial exit)
            if trade['partial_exits'] == 0 and current_price <= trade['target_1']:
                self._partial_exit(symbol, current_price, 1)
                # Move stop to breakeven
                trade['stop_loss'] = trade['entry_price']
                trade['trailing_stop_active'] = True
            
            # Target 2 (partial exit)
            elif trade['partial_exits'] == 1 and current_price <= trade['target_2']:
                self._partial_exit(symbol, current_price, 2)
                # Activate trailing stop
                atr = self._calculate_atr(symbol)
                trade['stop_loss'] = current_price + atr
            
            # Trailing stop update
            elif trade['trailing_stop_active']:
                atr = self._calculate_atr(symbol)
                new_stop = current_price + atr
                if new_stop < trade['stop_loss']:
                    trade['stop_loss'] = new_stop
            
            # Dynamic exit signal
            if self.config.use_dynamic_exits and result.end_short_trade:
                self._exit_trade(symbol, current_price, 'DYNAMIC_EXIT')
    
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
        if trade['type'] == 'LONG':
            pnl_percent = (exit_price - trade['entry_price']) / trade['entry_price'] * 100
        else:
            pnl_percent = (trade['entry_price'] - exit_price) / trade['entry_price'] * 100
        
        print(f"   Exit {exit_percent*100:.0f}% @ {exit_price:.2f} (+{pnl_percent:.1f}%)")
        print(f"   Stop moved to: {trade['stop_loss']:.2f}")
        
        trade['partial_exits'] = target_num
    
    def _exit_trade(self, symbol: str, exit_price: float, reason: str):
        """Complete exit"""
        trade = self.active_trades[symbol]
        
        # Calculate final P&L
        if trade['type'] == 'LONG':
            pnl_percent = (exit_price - trade['entry_price']) / trade['entry_price'] * 100
        else:
            pnl_percent = (trade['entry_price'] - exit_price) / trade['entry_price'] * 100
        
        # Account for partial exits
        if trade['partial_exits'] > 0:
            # Weighted average based on exits
            remaining_percent = 1.0 - self.config.target_1_percent
            if trade['partial_exits'] > 1:
                remaining_percent -= self.config.target_2_percent
            
            # This is simplified - in reality would track each exit price
            effective_pnl = pnl_percent  # Placeholder
        else:
            effective_pnl = pnl_percent
        
        # Update stats
        if effective_pnl > 0:
            self.daily_stats['wins'] += 1
        else:
            self.daily_stats['losses'] += 1
        self.daily_stats['pnl'] += effective_pnl
        
        # Record trade
        self.trade_history.append({
            'symbol': symbol,
            'type': trade['type'],
            'entry_price': trade['entry_price'],
            'exit_price': exit_price,
            'pnl_percent': effective_pnl,
            'exit_reason': reason,
            'pattern_score': trade['pattern_score'],
            'partial_exits': trade['partial_exits'],
            'hold_time': (datetime.now() - trade['entry_time']).seconds / 60
        })
        
        del self.active_trades[symbol]
        
        emoji = "✅" if effective_pnl > 0 else "❌"
        print(f"\n{emoji} EXIT {trade['type']} - {symbol}")
        print(f"   Exit: {exit_price:.2f} ({reason})")
        print(f"   P&L: {effective_pnl:+.1f}%")
        print(f"   Daily Stats: {self.daily_stats['wins']}W/{self.daily_stats['losses']}L, {self.daily_stats['pnl']:+.1f}%")
    
    def _calculate_atr(self, symbol: str, period: int = 14) -> float:
        """Calculate ATR for the symbol"""
        processor = self.processors[symbol]
        
        if hasattr(processor, 'bars') and len(processor.bars) >= period:
            # Simplified ATR calculation
            tr_values = []
            for i in range(period):
                high = processor.bars.get_high(i)
                low = processor.bars.get_low(i)
                close_prev = processor.bars.get_close(i+1) if i+1 < len(processor.bars) else low
                
                tr = max(
                    high - low,
                    abs(high - close_prev),
                    abs(low - close_prev)
                )
                tr_values.append(tr)
            
            return sum(tr_values) / len(tr_values)
        else:
            # Fallback to 2% of price
            return processor.bars.get_close(0) * 0.02 if len(processor.bars) > 0 else 0
    
    def print_performance_summary(self):
        """Print performance metrics"""
        print("\n" + "="*60)
        print("📊 OPTIMIZED SYSTEM PERFORMANCE SUMMARY")
        print("="*60)
        
        total_trades = len(self.trade_history)
        if total_trades > 0:
            win_rate = self.daily_stats['wins'] / total_trades * 100
            avg_win = sum(t['pnl_percent'] for t in self.trade_history if t['pnl_percent'] > 0) / max(1, self.daily_stats['wins'])
            avg_loss = sum(t['pnl_percent'] for t in self.trade_history if t['pnl_percent'] < 0) / max(1, self.daily_stats['losses'])
            
            print(f"\n📈 Trade Statistics:")
            print(f"   Total Trades: {total_trades}")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Average Win: {avg_win:+.1f}%")
            print(f"   Average Loss: {avg_loss:+.1f}%")
            print(f"   Total P&L: {self.daily_stats['pnl']:+.1f}%")
            
            # Compare with baseline
            print(f"\n📊 Improvements vs Baseline:")
            print(f"   Win Rate: {win_rate:.1f}% (baseline: 75%)")
            print(f"   Avg Win: {avg_win:.1f}% (baseline: 3.7%)")
            print(f"   Trade Frequency: Higher with dynamic exits")
            print(f"   Risk Management: Multi-target exits implemented")


def main():
    """Demo optimized system"""
    print("="*60)
    print("🚀 OPTIMIZED LORENTZIAN CLASSIFICATION SYSTEM")
    print("="*60)
    
    # Let user choose configuration
    print("\nSelect configuration:")
    print("1. Optimized (Balanced)")
    print("2. Conservative")
    print("3. Aggressive")
    print("4. Scalping")
    print("5. Swing Trading")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    config_map = {
        "1": "optimized",
        "2": "conservative", 
        "3": "aggressive",
        "4": "scalping",
        "5": "swing"
    }
    
    config_type = config_map.get(choice, "optimized")
    
    # Create system
    system = OptimizedTradingSystem(config_type)
    
    # Simulate some bars (in real usage, this would be live data)
    print("\n📊 Simulating market data...")
    
    # Example: Process some dummy bars
    for i in range(10):
        bar_data = {
            'open': 100 + i * 0.1,
            'high': 100.5 + i * 0.1,
            'low': 99.5 + i * 0.1,
            'close': 100.2 + i * 0.1,
            'volume': 10000
        }
        
        result = system.process_bar('TEST', bar_data)
        
        if i % 3 == 0:
            print(f"\nBar {i}: {result}")
    
    # Show performance
    system.print_performance_summary()


if __name__ == "__main__":
    main()