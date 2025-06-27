"""
Trade Executor
=============

Handles trade execution logic for a single symbol.
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from scanner.ml_quality_filter import MLQualityFilter
from strategies.base_strategy import BaseExitStrategy
from utils.kelly_criterion import KellyCriterion
from config.settings import TradingConfig


class TradeExecutor:
    """Executes trades for a single symbol with given strategies"""
    
    def __init__(self, symbol: str, timeframe: str = "5minute",
                 ml_threshold: float = 3.0):
        self.symbol = symbol
        self.timeframe = timeframe
        self.ml_filter = MLQualityFilter(
            min_confidence=ml_threshold, 
            high_confidence=5.0
        )
        self.processor = None
        self.trades_by_strategy = {}
        self.positions_by_strategy = {}
        self.kelly_calculators = {}
    
    def initialize_processor(self, config: TradingConfig):
        """Initialize the bar processor with config"""
        self.processor = EnhancedBarProcessor(
            config=config,
            symbol=self.symbol,
            timeframe=self.timeframe
        )
    
    def process_data(self, df: pd.DataFrame, strategies: Dict[str, BaseExitStrategy],
                    start_bar: int = 2000) -> Dict[str, List[Dict]]:
        """
        Process market data with multiple strategies
        
        Args:
            df: DataFrame with OHLCV data
            strategies: Dict of strategy name to strategy instance
            start_bar: Minimum bar index before taking trades
        
        Returns:
            Dict of strategy name to list of trades
        """
        if self.processor is None:
            raise ValueError("Processor not initialized. Call initialize_processor first.")
        
        # Reset for new run
        self.trades_by_strategy = {name: [] for name in strategies}
        self.positions_by_strategy = {name: None for name in strategies}
        self.kelly_calculators = {
            name: KellyCriterion(kelly_fraction=0.25) 
            for name in strategies
        }
        
        # Process each bar
        current_date = None
        
        for idx, row in df.iterrows():
            bar_date = idx.date() if hasattr(idx, 'date') else idx
            bar_time = idx.time() if hasattr(idx, 'time') else None
            
            # Handle day transitions
            if current_date and bar_date != current_date:
                self._close_overnight_positions(row['open'], strategies)
            
            current_date = bar_date
            
            # Update ATR for strategies that need it
            self._update_atr(row, strategies)
            
            # Process the bar
            result = self.processor.process_bar(
                open_price=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume']
            )
            
            if result is None:
                continue
            
            # Get ML-filtered signal
            signal = self._get_ml_signal(result, idx)
            
            # Check trading time constraints
            can_enter = self._check_trading_hours(bar_time)
            
            # Process each strategy
            for name, strategy in strategies.items():
                self._process_strategy(
                    strategy_name=name,
                    strategy=strategy,
                    row=row,
                    idx=idx,
                    signal=signal,
                    ml_prediction=result.prediction,
                    bar_index=result.bar_index,
                    can_enter=can_enter and result.bar_index >= start_bar
                )
        
        # Close any remaining positions
        self._close_all_positions(df.iloc[-1]['close'], strategies)
        
        return self.trades_by_strategy
    
    def _process_strategy(self, strategy_name: str, strategy: BaseExitStrategy,
                         row: pd.Series, idx: pd.Timestamp, signal: int,
                         ml_prediction: float, bar_index: int, can_enter: bool):
        """Process a single strategy for current bar"""
        position = self.positions_by_strategy[strategy_name]
        exit_mgr = strategy.exit_manager
        
        # Check for exit if in position
        if position and self.symbol in exit_mgr.positions:
            exit_signal = self._check_exit(
                strategy, position, row, idx, ml_prediction
            )
            
            if exit_signal and exit_signal.should_exit:
                self._execute_exit(strategy_name, strategy, exit_signal)
        
        # Check for new entry
        elif not position and signal != 0 and can_enter:
            self._enter_position(
                strategy_name, strategy, row, idx, 
                signal, ml_prediction
            )
    
    def _check_exit(self, strategy: BaseExitStrategy, position: Dict,
                   row: pd.Series, idx: pd.Timestamp, 
                   ml_prediction: float) -> Optional:
        """Check if position should exit"""
        exit_mgr = strategy.exit_manager
        exit_pos = exit_mgr.positions[self.symbol]
        exit_pos.current_price = row['close']
        
        # Update max profit
        if exit_pos.direction == 1:
            current_profit = (row['close'] - exit_pos.entry_price) / exit_pos.entry_price * 100
        else:
            current_profit = (exit_pos.entry_price - row['close']) / exit_pos.entry_price * 100
        exit_pos.max_profit = max(exit_pos.max_profit, current_profit)
        
        # Check exit conditions
        return exit_mgr.check_exit(
            symbol=self.symbol,
            current_price=row['close'],
            current_ml_signal=ml_prediction,
            timestamp=idx,
            high=row['high'],
            low=row['low']
        )
    
    def _execute_exit(self, strategy_name: str, strategy: BaseExitStrategy,
                     exit_signal):
        """Execute an exit and record the trade"""
        exit_mgr = strategy.exit_manager
        exit_record = exit_mgr.execute_exit(self.symbol, exit_signal)
        
        self.trades_by_strategy[strategy_name].append({
            'symbol': self.symbol,
            'entry_price': exit_record.get('entry_price', 0),
            'exit_price': exit_record.get('exit_price', 0),
            'pnl_pct': exit_record.get('pnl_pct', 0),
            'bars_held': exit_record.get('bars_held', 1),
            'direction': exit_record.get('direction', 1),
            'exit_reason': exit_record.get('exit_type', 'smart_exit'),
            'quantity': exit_record.get('quantity', 100)
        })
        
        # Update Kelly calculator
        self.kelly_calculators[strategy_name].add_trade(
            exit_record.get('pnl_pct', 0)
        )
        
        # Clear position
        if self.symbol not in exit_mgr.positions:
            self.positions_by_strategy[strategy_name] = None
    
    def _enter_position(self, strategy_name: str, strategy: BaseExitStrategy,
                       row: pd.Series, idx: pd.Timestamp, 
                       signal: int, ml_prediction: float):
        """Enter a new position"""
        direction = 1 if signal > 0 else -1
        entry_price = row['close']
        
        # Calculate position size using Kelly
        quantity = self._calculate_position_size(
            strategy_name, strategy, entry_price, direction
        )
        
        # Enter position
        exit_mgr = strategy.exit_manager
        exit_mgr.enter_position(
            symbol=self.symbol,
            entry_price=entry_price,
            quantity=quantity,
            direction=direction,
            ml_signal=ml_prediction,
            timestamp=idx
        )
        
        # Record position
        self.positions_by_strategy[strategy_name] = {
            'entry_price': entry_price,
            'entry_time': idx,
            'direction': direction,
            'quantity': quantity
        }
    
    def _calculate_position_size(self, strategy_name: str, 
                                strategy: BaseExitStrategy,
                                entry_price: float, direction: int) -> int:
        """Calculate position size using Kelly criterion"""
        kelly_calc = self.kelly_calculators[strategy_name]
        exit_mgr = strategy.exit_manager
        
        if direction == 1:
            stop_loss = entry_price * (1 - exit_mgr.stop_loss_pct / 100)
        else:
            stop_loss = entry_price * (1 + exit_mgr.stop_loss_pct / 100)
        
        account_balance = 1000000  # Default account size
        kelly_position = kelly_calc.calculate_position_size(
            account_balance=account_balance,
            entry_price=entry_price,
            stop_loss=stop_loss
        )
        
        return kelly_position['shares']
    
    def _get_ml_signal(self, result, idx: pd.Timestamp) -> int:
        """Apply ML filter to signal"""
        if result.signal == 0:
            return 0
        
        signal_dict = {
            'timestamp': idx,
            'signal': result.signal,
            'prediction': result.prediction,
            'filter_states': result.filter_states,
            'features': {}
        }
        
        ml_signal = self.ml_filter.filter_signal(signal_dict, self.symbol)
        return result.signal if ml_signal is not None else 0
    
    def _check_trading_hours(self, bar_time) -> bool:
        """Check if current time allows trading"""
        if bar_time is None:
            return True
        
        # No trades in first 30 min or last 15 min
        if (bar_time.hour == 9 and bar_time.minute < 30) or \
           (bar_time.hour == 15 and bar_time.minute >= 15):
            return False
        
        return True
    
    def _update_atr(self, row: pd.Series, strategies: Dict[str, BaseExitStrategy]):
        """Update ATR for strategies that use it"""
        for strategy in strategies.values():
            if hasattr(strategy.exit_manager, 'update_atr'):
                strategy.exit_manager.update_atr(
                    row['high'], row['low'], row['close']
                )
    
    def _close_overnight_positions(self, open_price: float, 
                                  strategies: Dict[str, BaseExitStrategy]):
        """Close all positions at day end"""
        for strategy_name, strategy in strategies.items():
            position = self.positions_by_strategy[strategy_name]
            if position:
                self._force_exit(strategy_name, position, open_price, 'day_end')
    
    def _close_all_positions(self, close_price: float,
                           strategies: Dict[str, BaseExitStrategy]):
        """Close all remaining positions"""
        for strategy_name, strategy in strategies.items():
            position = self.positions_by_strategy[strategy_name]
            if position:
                self._force_exit(strategy_name, position, close_price, 'end_of_data')
    
    def _force_exit(self, strategy_name: str, position: Dict,
                   exit_price: float, reason: str):
        """Force exit a position"""
        entry_price = position['entry_price']
        direction = position['direction']
        
        if direction == 1:
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100
        
        self.trades_by_strategy[strategy_name].append({
            'symbol': self.symbol,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'bars_held': 1,
            'direction': direction,
            'exit_reason': reason,
            'quantity': position.get('quantity', 100)
        })
        
        self.positions_by_strategy[strategy_name] = None