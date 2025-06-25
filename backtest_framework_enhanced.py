#!/usr/bin/env python3
"""
Enhanced Backtesting Framework with Multi-Target Exit Support
=============================================================

Extends the basic backtesting framework to properly implement:
- Multi-target partial exits
- Trailing stops after targets
- Position sizing based on targets

IMPORTANT: Use this engine instead of BacktestEngine when testing
configurations with target_1_ratio, target_2_ratio, etc. The standard
BacktestEngine calculates targets but does NOT implement partial exits.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# Import base framework
from backtest_framework import BacktestEngine, BacktestMetrics, TradeResult
from config.settings import TradingConfig
from config.fixed_optimized_settings import FixedOptimizedTradingConfig

import logging
logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Enhanced position tracking with multi-target support"""
    symbol: str
    entry_bar: int
    entry_date: datetime
    entry_price: float
    direction: int  # 1 for long, -1 for short
    pattern_score: float
    stop_loss: float
    targets: List[float]
    
    # Multi-target tracking
    initial_size: float = 1.0
    remaining_size: float = 1.0
    exits_completed: int = 0
    partial_exits: List[Dict] = field(default_factory=list)
    
    # Trailing stop
    current_stop: float = None
    trailing_active: bool = False
    
    def __post_init__(self):
        if self.current_stop is None:
            self.current_stop = self.stop_loss


class EnhancedBacktestEngine(BacktestEngine):
    """Enhanced backtesting engine with multi-target support"""
    
    def run_backtest(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        config: TradingConfig,
        modular_system = None,
        commission: float = 0.001
    ) -> BacktestMetrics:
        """Run backtest with multi-target exit support"""
        
        logger.info(f"Starting enhanced backtest for {symbol}")
        
        # Get historical data
        df = self._get_historical_data(symbol, start_date, end_date)
        if df.empty:
            raise ValueError("No data available for backtesting")
        
        # Initialize processor
        from scanner.enhanced_bar_processor import EnhancedBarProcessor
        processor = EnhancedBarProcessor(config, symbol, "5minute")
        
        # Initialize tracking
        self.trades = []
        self.partial_trades = []  # Track partial exits
        equity_curve = [self.initial_capital]
        current_position = None
        bars_processed = 0
        
        # Log data info
        logger.info(f"Total bars in dataset: {len(df)}")
        logger.info(f"Warmup period: {config.max_bars_back} bars")
        logger.info(f"Bars available for trading: {max(0, len(df) - config.max_bars_back)}")
        
        # Check if this is a multi-target config
        is_multi_target = hasattr(config, 'target_1_ratio')
        
        for idx, row in df.iterrows():
            bars_processed += 1
            
            # Process bar through ML
            result = processor.process_bar(
                row['open'], row['high'], row['low'], 
                row['close'], row['volume']
            )
            
            # Skip warmup period
            if bars_processed < config.max_bars_back:
                equity_curve.append(equity_curve[-1])
                continue
            
            # Apply modular strategies if provided
            signal_score = result.prediction
            pattern_score = 5.0  # Default
            
            if modular_system:
                signal_score, pattern_score = self._apply_modular_strategies(
                    result, row, modular_system
                )
            
            # Check for exit
            if current_position:
                if is_multi_target:
                    exit_info = self._check_multi_target_exit(
                        current_position, row, result, config
                    )
                else:
                    exit_info = self._check_standard_exit(
                        current_position, row, result, config
                    )
                
                if exit_info:
                    if exit_info['type'] == 'PARTIAL':
                        # Handle partial exit
                        partial_pnl = self._execute_partial_exit(
                            current_position, row, exit_info, config
                        )
                        equity_curve.append(equity_curve[-1] + partial_pnl - commission)
                        
                        # Check if position is fully closed
                        if current_position.remaining_size <= 0.01:  # Essentially zero
                            self._finalize_position(current_position, row, bars_processed)
                            current_position = None
                    else:
                        # Complete exit
                        trade = self._close_enhanced_position(
                            current_position, row, exit_info['reason'], bars_processed
                        )
                        self.trades.append(trade)
                        
                        # Update equity
                        pnl = self.initial_capital * (trade.pnl_percent / 100)
                        equity_curve.append(equity_curve[-1] + pnl - commission * 2)
                        current_position = None
                else:
                    equity_curve.append(equity_curve[-1])
            
            # Check for entry
            elif not current_position:
                # Use proper entry signals that respect filters
                if result.start_long_trade:
                    current_position = self._create_enhanced_position(
                        symbol, bars_processed, idx, row, 
                        abs(result.prediction), pattern_score, config
                    )
                    equity_curve.append(equity_curve[-1])
                elif result.start_short_trade:
                    current_position = self._create_enhanced_position(
                        symbol, bars_processed, idx, row, 
                        -abs(result.prediction), pattern_score, config
                    )
                    equity_curve.append(equity_curve[-1])
                else:
                    equity_curve.append(equity_curve[-1])
            else:
                equity_curve.append(equity_curve[-1])
        
        # Close any open position at end
        if current_position:
            self._finalize_position(current_position, df.iloc[-1], bars_processed)
        
        # Calculate metrics including partial trades
        metrics = self._calculate_enhanced_metrics(
            self.trades, self.partial_trades, equity_curve, bars_processed
        )
        
        return metrics
    
    def _create_enhanced_position(
        self, symbol: str, bar_num: int, date: datetime, 
        bar: pd.Series, signal: float, pattern_score: float, config
    ) -> Position:
        """Create position with multi-target support"""
        
        entry_price = bar['close']
        direction = 1 if signal > 0 else -1
        
        # Calculate stop loss
        stop_loss = self._calculate_stop_loss(bar, config)
        if direction == -1:
            stop_loss = 2 * entry_price - stop_loss  # Mirror for short
        
        # Calculate targets
        targets = []
        if hasattr(config, 'target_1_ratio'):
            risk = abs(entry_price - stop_loss)
            targets.append(entry_price + risk * config.target_1_ratio * direction)
            
            if hasattr(config, 'target_2_ratio'):
                targets.append(entry_price + risk * config.target_2_ratio * direction)
                
            if hasattr(config, 'target_3_ratio'):
                targets.append(entry_price + risk * config.target_3_ratio * direction)
        
        return Position(
            symbol=symbol,
            entry_bar=bar_num,
            entry_date=date,
            entry_price=entry_price,
            direction=direction,
            pattern_score=pattern_score,
            stop_loss=stop_loss,
            targets=targets
        )
    
    def _check_multi_target_exit(
        self, position: Position, bar: pd.Series, ml_result, config
    ) -> Optional[Dict]:
        """Check for multi-target exits"""
        
        current_price = bar['close']
        
        # Check stop loss first
        if position.direction == 1:  # Long
            if current_price <= position.current_stop:
                return {'type': 'COMPLETE', 'reason': 'STOP_LOSS'}
        else:  # Short
            if current_price >= position.current_stop:
                return {'type': 'COMPLETE', 'reason': 'STOP_LOSS'}
        
        # Check targets
        if position.targets and position.exits_completed < len(position.targets):
            target_idx = position.exits_completed
            target_price = position.targets[target_idx]
            
            if position.direction == 1:  # Long
                if current_price >= target_price:
                    return {
                        'type': 'PARTIAL',
                        'target_num': target_idx + 1,
                        'price': current_price
                    }
            else:  # Short
                if current_price <= target_price:
                    return {
                        'type': 'PARTIAL',
                        'target_num': target_idx + 1,
                        'price': current_price
                    }
        
        # Check for signal exit if all targets hit
        if config.use_dynamic_exits and position.exits_completed >= 1:
            if position.direction == 1 and ml_result.end_long_trade:
                return {'type': 'COMPLETE', 'reason': 'SIGNAL_EXIT'}
            elif position.direction == -1 and ml_result.end_short_trade:
                return {'type': 'COMPLETE', 'reason': 'SIGNAL_EXIT'}
        
        # Update trailing stop if needed
        if position.trailing_active:
            self._update_trailing_stop(position, bar, config)
        
        return None
    
    def _check_standard_exit(
        self, position: Position, bar: pd.Series, ml_result, config
    ) -> Optional[Dict]:
        """Standard exit checking (compatibility)"""
        
        bars_held = bar.name - position.entry_date
        bars_held = bars_held.total_seconds() / 300  # Convert to 5-min bars
        
        # Fixed bar exit
        if not config.use_dynamic_exits and bars_held >= 5:
            return {'type': 'COMPLETE', 'reason': 'FIXED_5_BAR'}
        
        # Stop loss
        if position.direction == 1:  # Long
            if bar['close'] <= position.stop_loss:
                return {'type': 'COMPLETE', 'reason': 'STOP_LOSS'}
        else:  # Short
            if bar['close'] >= position.stop_loss:
                return {'type': 'COMPLETE', 'reason': 'STOP_LOSS'}
        
        # Dynamic exit
        if config.use_dynamic_exits:
            if position.direction == 1 and ml_result.end_long_trade:
                return {'type': 'COMPLETE', 'reason': 'SIGNAL_EXIT'}
            elif position.direction == -1 and ml_result.end_short_trade:
                return {'type': 'COMPLETE', 'reason': 'SIGNAL_EXIT'}
        
        return None
    
    def _execute_partial_exit(
        self, position: Position, bar: pd.Series, 
        exit_info: Dict, config
    ) -> float:
        """Execute partial exit and return P&L"""
        
        target_num = exit_info['target_num']
        exit_price = bar['close']
        
        # Determine exit percentage
        if target_num == 1:
            exit_percent = config.target_1_percent if hasattr(config, 'target_1_percent') else 0.5
        elif target_num == 2:
            exit_percent = config.target_2_percent if hasattr(config, 'target_2_percent') else 0.3
        else:
            exit_percent = position.remaining_size  # Exit all remaining
        
        # Calculate P&L for this portion
        if position.direction == 1:  # Long
            pnl_percent = (exit_price - position.entry_price) / position.entry_price * 100
        else:  # Short
            pnl_percent = (position.entry_price - exit_price) / position.entry_price * 100
        
        portion_pnl = self.initial_capital * (pnl_percent / 100) * exit_percent
        
        # Record partial exit
        position.partial_exits.append({
            'target_num': target_num,
            'exit_date': bar.name,
            'exit_price': exit_price,
            'exit_percent': exit_percent,
            'pnl_percent': pnl_percent,
            'portion_pnl': portion_pnl
        })
        
        # Update position
        position.remaining_size -= exit_percent
        position.exits_completed += 1
        
        # Move stop to breakeven after first target
        if target_num == 1:
            position.current_stop = position.entry_price
            position.trailing_active = True
        
        logger.info(f"Partial exit {target_num}: {exit_percent*100:.0f}% @ "
                   f"{exit_price:.2f} for {pnl_percent:.2f}% gain")
        
        return portion_pnl
    
    def _update_trailing_stop(self, position: Position, bar: pd.Series, config):
        """Update trailing stop after targets hit"""
        
        if not hasattr(config, 'trailing_stop_distance_ratio'):
            return
        
        current_price = bar['close']
        risk = abs(position.entry_price - position.stop_loss)
        trail_distance = risk * config.trailing_stop_distance_ratio
        
        if position.direction == 1:  # Long
            new_stop = current_price - trail_distance
            if new_stop > position.current_stop:
                position.current_stop = new_stop
        else:  # Short
            new_stop = current_price + trail_distance
            if new_stop < position.current_stop:
                position.current_stop = new_stop
    
    def _close_enhanced_position(
        self, position: Position, bar: pd.Series, 
        exit_reason: str, current_bar: int
    ) -> TradeResult:
        """Close position with multi-target accounting"""
        
        exit_price = bar['close']
        
        # Calculate final P&L including partials
        total_pnl_percent = 0
        
        # Add P&L from partial exits
        for partial in position.partial_exits:
            total_pnl_percent += partial['pnl_percent'] * partial['exit_percent']
        
        # Add P&L from remaining position
        if position.remaining_size > 0:
            if position.direction == 1:  # Long
                final_pnl = (exit_price - position.entry_price) / position.entry_price * 100
            else:  # Short
                final_pnl = (position.entry_price - exit_price) / position.entry_price * 100
            
            total_pnl_percent += final_pnl * position.remaining_size
        
        pnl_amount = self.initial_capital * (total_pnl_percent / 100)
        hold_time = current_bar - position.entry_bar
        
        return TradeResult(
            symbol=position.symbol,
            entry_date=position.entry_date,
            exit_date=bar.name,
            entry_price=position.entry_price,
            exit_price=exit_price,
            direction=position.direction,
            pnl_percent=total_pnl_percent,
            pnl_amount=pnl_amount,
            hold_time_bars=hold_time,
            exit_reason=exit_reason,
            pattern_score=position.pattern_score
        )
    
    def _finalize_position(self, position: Position, last_bar: pd.Series, bars_processed: int):
        """Finalize a position and add to trades"""
        
        if position.remaining_size > 0.01:
            # Close remaining position
            trade = self._close_enhanced_position(
                position, last_bar, "FINAL_EXIT", bars_processed
            )
            self.trades.append(trade)
        else:
            # Create synthetic trade from partials
            total_pnl_percent = sum(p['pnl_percent'] * p['exit_percent'] 
                                  for p in position.partial_exits)
            
            avg_exit_price = sum(p['exit_price'] * p['exit_percent'] 
                               for p in position.partial_exits)
            
            trade = TradeResult(
                symbol=position.symbol,
                entry_date=position.entry_date,
                exit_date=position.partial_exits[-1]['exit_date'],
                entry_price=position.entry_price,
                exit_price=avg_exit_price,
                direction=position.direction,
                pnl_percent=total_pnl_percent,
                pnl_amount=self.initial_capital * (total_pnl_percent / 100),
                hold_time_bars=bars_processed - position.entry_bar,
                exit_reason="MULTI_TARGET_COMPLETE",
                pattern_score=position.pattern_score
            )
            self.trades.append(trade)
        
        # Record all partial trades
        for partial in position.partial_exits:
            self.partial_trades.append({
                'symbol': position.symbol,
                'target_num': partial['target_num'],
                'exit_date': partial['exit_date'],
                'pnl_percent': partial['pnl_percent'],
                'exit_percent': partial['exit_percent']
            })
    
    def _calculate_enhanced_metrics(
        self, trades: List[TradeResult], partial_trades: List[Dict],
        equity_curve: List[float], total_bars: int
    ) -> BacktestMetrics:
        """Calculate metrics including multi-target performance"""
        
        # Use base calculation
        metrics = self._calculate_metrics(trades, equity_curve, total_bars)
        
        # Add multi-target specific info
        if partial_trades:
            logger.info(f"Multi-target exits: {len(partial_trades)} partial exits executed")
            target_1_hits = sum(1 for p in partial_trades if p['target_num'] == 1)
            target_2_hits = sum(1 for p in partial_trades if p['target_num'] == 2)
            logger.info(f"Target 1 hits: {target_1_hits}, Target 2 hits: {target_2_hits}")
        
        return metrics


def compare_exit_strategies_enhanced(symbol: str, days: int = 180):
    """Compare exit strategies using enhanced backtest engine"""
    
    from config.settings import TradingConfig
    from config.fixed_optimized_settings import FixedOptimizedTradingConfig
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    print(f"\n🎯 Enhanced Exit Strategy Testing on {symbol}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print("="*60)
    
    # Initialize engines
    standard_engine = BacktestEngine()
    enhanced_engine = EnhancedBacktestEngine()
    
    results = {}
    
    # 1. Baseline with standard engine
    print("\n1️⃣ Testing BASELINE (Fixed 5-bar exit)...")
    baseline_config = TradingConfig()
    baseline_config.use_dynamic_exits = False
    results['baseline'] = standard_engine.run_backtest(
        symbol, start_date, end_date, baseline_config
    )
    
    # 2. Dynamic with standard engine
    print("\n2️⃣ Testing DYNAMIC EXITS...")
    dynamic_config = TradingConfig()
    dynamic_config.use_dynamic_exits = True
    results['dynamic'] = standard_engine.run_backtest(
        symbol, start_date, end_date, dynamic_config
    )
    
    # 3. Multi-target with enhanced engine
    print("\n3️⃣ Testing MULTI-TARGET (Enhanced)...")
    multi_config = FixedOptimizedTradingConfig()
    results['multi_target'] = enhanced_engine.run_backtest(
        symbol, start_date, end_date, multi_config
    )
    
    # 4. Conservative multi-target
    print("\n4️⃣ Testing CONSERVATIVE MULTI-TARGET...")
    conservative_config = FixedOptimizedTradingConfig()
    conservative_config.target_1_ratio = 1.2
    conservative_config.target_1_percent = 0.7
    conservative_config.target_2_ratio = 2.0
    conservative_config.target_2_percent = 0.3
    results['conservative'] = enhanced_engine.run_backtest(
        symbol, start_date, end_date, conservative_config
    )
    
    # 5. Aggressive multi-target
    print("\n5️⃣ Testing AGGRESSIVE MULTI-TARGET...")
    aggressive_config = FixedOptimizedTradingConfig()
    aggressive_config.target_1_ratio = 2.0
    aggressive_config.target_1_percent = 0.3
    aggressive_config.target_2_ratio = 4.0
    aggressive_config.target_2_percent = 0.4
    aggressive_config.target_3_ratio = 6.0
    aggressive_config.target_3_percent = 0.3
    results['aggressive'] = enhanced_engine.run_backtest(
        symbol, start_date, end_date, aggressive_config
    )
    
    # Print comparison
    print("\n" + "="*80)
    print("📊 ENHANCED EXIT STRATEGY COMPARISON")
    print("="*80)
    
    headers = ['Strategy', 'Trades', 'Win%', 'Avg Win%', 'Avg Loss%', 
               'Total Return%', 'Profit Factor']
    
    print(f"{headers[0]:<15} {headers[1]:<8} {headers[2]:<8} {headers[3]:<10} "
          f"{headers[4]:<10} {headers[5]:<15} {headers[6]:<15}")
    print("-"*80)
    
    for name, metrics in results.items():
        print(f"{name:<15} {metrics.total_trades:<8} {metrics.win_rate:<8.1f} "
              f"{metrics.average_win:<10.2f} {abs(metrics.average_loss):<10.2f} "
              f"{metrics.total_return:<15.2f} {metrics.profit_factor:<15.2f}")
    
    return results


if __name__ == "__main__":
    print("="*80)
    print("🎯 ENHANCED MULTI-TARGET EXIT TESTING")
    print("="*80)
    
    # Test with enhanced engine
    results = compare_exit_strategies_enhanced("RELIANCE", days=180)
    
    # Find best strategy
    best_return = max(results.items(), key=lambda x: x[1].total_return)
    best_avg_win = max(results.items(), key=lambda x: x[1].average_win)
    
    print(f"\n🏆 Best by Total Return: {best_return[0]} ({best_return[1].total_return:.2f}%)")
    print(f"🏆 Best by Avg Win: {best_avg_win[0]} ({best_avg_win[1].average_win:.2f}%)")