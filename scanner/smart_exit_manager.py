"""
Smart Exit Manager - Intelligent position exit management
=======================================================

Manages exits based on:
- Multiple profit targets with partial exits
- Trailing stops
- Time-based exits
- ML signal changes
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.atr_stops import ATRStopCalculator


@dataclass
class Position:
    """Container for active position information"""
    symbol: str
    entry_price: float
    entry_time: pd.Timestamp
    quantity: int
    direction: int  # 1 for long, -1 for short
    ml_signal: float
    stop_loss: float
    targets: List[float]
    target_sizes: List[float]  # Percentage of position for each target
    
    # Tracking
    remaining_quantity: int = None
    max_profit: float = 0.0
    current_price: float = 0.0
    bars_held: int = 0
    
    def __post_init__(self):
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity


@dataclass
class ExitSignal:
    """Exit signal with reason and details"""
    should_exit: bool
    exit_type: str  # 'target', 'stop', 'trailing', 'time', 'signal'
    exit_price: float
    quantity: int  # How many shares to exit
    reason: str
    
    @property
    def is_partial(self) -> bool:
        """Check if this is a partial exit"""
        return self.exit_type == 'target' and self.quantity > 0


class SmartExitManager:
    """
    Manages intelligent exits for positions
    """
    
    def __init__(self, config: Dict = None, use_atr_stops: bool = False):
        """
        Initialize exit manager
        
        Args:
            config: Configuration dictionary
            use_atr_stops: Whether to use ATR-based stops
        """
        self.config = config or {}
        self.use_atr_stops = use_atr_stops
        
        # Default exit parameters
        self.stop_loss_pct = self.config.get('stop_loss_percent', 0.3)
        self.targets = self.config.get('take_profit_targets', [0.15, 0.25, 0.35])
        self.target_sizes = self.config.get('target_sizes', [50, 30, 20])
        
        # Trailing stop parameters
        self.use_trailing = self.config.get('use_trailing_stop', True)
        self.trailing_activation = self.config.get('trailing_activation', 0.15)
        self.trailing_distance = self.config.get('trailing_distance', 0.1)
        
        # Time-based exit
        self.max_holding_bars = self.config.get('max_holding_bars', 15)
        
        # ATR parameters
        self.atr_stop_multiplier = self.config.get('atr_stop_multiplier', 2.0)
        self.atr_profit_multipliers = self.config.get('atr_profit_multipliers', [1.5, 3.0, 5.0])
        self.atr_trailing_multiplier = self.config.get('atr_trailing_multiplier', 1.5)
        
        # Initialize ATR calculator if needed
        if self.use_atr_stops:
            self.atr_calc = ATRStopCalculator(period=14)
            self.current_atr = None
        
        # Active positions
        self.positions: Dict[str, Position] = {}
        
        # Exit history for analysis
        self.exit_history = []
    
    def update_atr(self, high: float, low: float, close: float) -> float:
        """Update ATR calculator with new bar data"""
        if self.use_atr_stops and hasattr(self, 'atr_calc'):
            self.current_atr = self.atr_calc.update(high, low, close)
            return self.current_atr
        return None
    
    def enter_position(self, symbol: str, entry_price: float, 
                      quantity: int, direction: int, ml_signal: float,
                      timestamp: pd.Timestamp) -> Position:
        """
        Record a new position entry
        
        Args:
            symbol: Stock symbol
            entry_price: Entry price
            quantity: Number of shares
            direction: 1 for long, -1 for short
            ml_signal: ML prediction at entry
            timestamp: Entry timestamp
            
        Returns:
            Position object
        """
        # Calculate stop loss and targets
        if self.use_atr_stops and hasattr(self, 'current_atr') and self.current_atr:
            # ATR-based stops and targets
            stop_loss = self.atr_calc.calculate_stop_loss(
                entry_price, self.current_atr, direction, 
                self.atr_stop_multiplier
            )
            targets = self.atr_calc.calculate_targets(
                entry_price, self.current_atr, direction,
                self.atr_profit_multipliers
            )
        else:
            # Percentage-based stops and targets
            stop_loss = entry_price * (1 - self.stop_loss_pct / 100) if direction == 1 else \
                       entry_price * (1 + self.stop_loss_pct / 100)
            
            # Calculate targets
            if direction == 1:  # Long
                targets = [entry_price * (1 + t / 100) for t in self.targets]
            else:  # Short
                targets = [entry_price * (1 - t / 100) for t in self.targets]
        
        position = Position(
            symbol=symbol,
            entry_price=entry_price,
            entry_time=timestamp,
            quantity=quantity,
            direction=direction,
            ml_signal=ml_signal,
            stop_loss=stop_loss,
            targets=targets,
            target_sizes=self.target_sizes
        )
        
        self.positions[symbol] = position
        return position
    
    def check_exit(self, symbol: str, current_price: float, 
                   current_ml_signal: float, timestamp: pd.Timestamp,
                   high: Optional[float] = None, 
                   low: Optional[float] = None) -> Optional[ExitSignal]:
        """
        Check if position should be exited
        
        Args:
            symbol: Stock symbol
            current_price: Current price
            current_ml_signal: Current ML prediction
            timestamp: Current timestamp
            high: High price of current bar
            low: Low price of current bar
            
        Returns:
            ExitSignal if exit needed, None otherwise
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        position.current_price = current_price
        position.bars_held += 1
        
        # Update max profit for trailing stop
        if position.direction == 1:  # Long
            profit_pct = (current_price - position.entry_price) / position.entry_price * 100
            if high:
                max_profit_pct = (high - position.entry_price) / position.entry_price * 100
                position.max_profit = max(position.max_profit, max_profit_pct)
        else:  # Short
            profit_pct = (position.entry_price - current_price) / position.entry_price * 100
            if low:
                max_profit_pct = (position.entry_price - low) / position.entry_price * 100
                position.max_profit = max(position.max_profit, max_profit_pct)
        
        # 1. Check stop loss
        exit_signal = self._check_stop_loss(position, current_price, low, high)
        if exit_signal:
            return exit_signal
        
        # 2. Check profit targets
        exit_signal = self._check_targets(position, current_price, high, low)
        if exit_signal:
            return exit_signal
        
        # 3. Check trailing stop
        if self.use_trailing:
            exit_signal = self._check_trailing_stop(position, current_price)
            if exit_signal:
                return exit_signal
        
        # 4. Check time-based exit
        exit_signal = self._check_time_exit(position)
        if exit_signal:
            return exit_signal
        
        # 5. Check ML signal change
        exit_signal = self._check_signal_change(position, current_ml_signal)
        if exit_signal:
            return exit_signal
        
        return None
    
    def _check_stop_loss(self, position: Position, current_price: float,
                        low: Optional[float], high: Optional[float]) -> Optional[ExitSignal]:
        """Check if stop loss is hit"""
        if position.direction == 1:  # Long
            check_price = low if low is not None else current_price
            if check_price <= position.stop_loss:
                return ExitSignal(
                    should_exit=True,
                    exit_type='stop',
                    exit_price=max(position.stop_loss, check_price),
                    quantity=position.remaining_quantity,
                    reason=f"Stop loss hit at {position.stop_loss:.2f}"
                )
        else:  # Short
            check_price = high if high is not None else current_price
            if check_price >= position.stop_loss:
                return ExitSignal(
                    should_exit=True,
                    exit_type='stop',
                    exit_price=min(position.stop_loss, check_price),
                    quantity=position.remaining_quantity,
                    reason=f"Stop loss hit at {position.stop_loss:.2f}"
                )
        return None
    
    def _check_targets(self, position: Position, current_price: float,
                      high: Optional[float], low: Optional[float]) -> Optional[ExitSignal]:
        """Check if any profit targets are hit"""
        for i, (target, size_pct) in enumerate(zip(position.targets, position.target_sizes)):
            # Skip already hit targets
            if i < len(position.targets) - len(position.target_sizes):
                continue
            
            hit = False
            if position.direction == 1:  # Long
                check_price = high if high is not None else current_price
                hit = check_price >= target
            else:  # Short
                check_price = low if low is not None else current_price
                hit = check_price <= target
            
            if hit:
                # Calculate quantity for this target
                exit_quantity = int(position.quantity * size_pct / 100)
                exit_quantity = min(exit_quantity, position.remaining_quantity)
                
                # Update targets list (remove hit target)
                position.targets = position.targets[i+1:]
                position.target_sizes = position.target_sizes[i+1:]
                
                return ExitSignal(
                    should_exit=True,
                    exit_type='target',
                    exit_price=target,
                    quantity=exit_quantity,
                    reason=f"Target {i+1} hit at {target:.2f} ({size_pct}% exit)"
                )
        
        return None
    
    def _check_trailing_stop(self, position: Position, 
                            current_price: float) -> Optional[ExitSignal]:
        """Check trailing stop"""
        # Only activate after minimum profit reached
        if position.max_profit < self.trailing_activation:
            return None
        
        # Calculate trailing stop level
        if self.use_atr_stops and hasattr(self, 'current_atr') and self.current_atr:
            # ATR-based trailing stop
            if not hasattr(position, 'trailing_stop'):
                # Initialize trailing stop
                position.trailing_stop = self.atr_calc.calculate_trailing_stop(
                    position.entry_price, self.current_atr, position.direction,
                    self.atr_trailing_multiplier
                )
            else:
                # Update trailing stop
                position.trailing_stop = self.atr_calc.calculate_trailing_stop(
                    current_price, self.current_atr, position.direction,
                    self.atr_trailing_multiplier, position.trailing_stop
                )
            
            # Check if stop hit
            if position.direction == 1 and current_price <= position.trailing_stop:
                return ExitSignal(
                    should_exit=True,
                    exit_type='trailing',
                    exit_price=current_price,
                    quantity=position.remaining_quantity,
                    reason=f"ATR trailing stop hit at {position.trailing_stop:.2f}"
                )
            elif position.direction == -1 and current_price >= position.trailing_stop:
                return ExitSignal(
                    should_exit=True,
                    exit_type='trailing',
                    exit_price=current_price,
                    quantity=position.remaining_quantity,
                    reason=f"ATR trailing stop hit at {position.trailing_stop:.2f}"
                )
        else:
            # Percentage-based trailing stop
            if position.direction == 1:  # Long
                trailing_stop = position.entry_price * (1 + (position.max_profit - self.trailing_distance) / 100)
                if current_price <= trailing_stop:
                    return ExitSignal(
                        should_exit=True,
                        exit_type='trailing',
                        exit_price=current_price,
                        quantity=position.remaining_quantity,
                        reason=f"Trailing stop hit. Max profit: {position.max_profit:.1f}%"
                    )
            else:  # Short
                trailing_stop = position.entry_price * (1 - (position.max_profit - self.trailing_distance) / 100)
                if current_price >= trailing_stop:
                    return ExitSignal(
                        should_exit=True,
                        exit_type='trailing',
                        exit_price=current_price,
                        quantity=position.remaining_quantity,
                        reason=f"Trailing stop hit. Max profit: {position.max_profit:.1f}%"
                    )
        
        return None
    
    def _check_time_exit(self, position: Position) -> Optional[ExitSignal]:
        """Check time-based exit"""
        if position.bars_held >= self.max_holding_bars:
            return ExitSignal(
                should_exit=True,
                exit_type='time',
                exit_price=position.current_price,
                quantity=position.remaining_quantity,
                reason=f"Max holding time reached ({self.max_holding_bars} bars)"
            )
        return None
    
    def _check_signal_change(self, position: Position, 
                           current_ml_signal: float) -> Optional[ExitSignal]:
        """Check if ML signal has reversed"""
        # Exit if signal flips
        if position.direction == 1 and current_ml_signal < -2:
            return ExitSignal(
                should_exit=True,
                exit_type='signal',
                exit_price=position.current_price,
                quantity=position.remaining_quantity,
                reason=f"ML signal reversed to {current_ml_signal:.1f}"
            )
        elif position.direction == -1 and current_ml_signal > 2:
            return ExitSignal(
                should_exit=True,
                exit_type='signal',
                exit_price=position.current_price,
                quantity=position.remaining_quantity,
                reason=f"ML signal reversed to {current_ml_signal:.1f}"
            )
        
        return None
    
    def execute_exit(self, symbol: str, exit_signal: ExitSignal) -> Dict:
        """
        Execute the exit and update position
        
        Args:
            symbol: Stock symbol
            exit_signal: Exit signal to execute
            
        Returns:
            Exit details including P&L
        """
        if symbol not in self.positions:
            return {}
        
        position = self.positions[symbol]
        
        # Calculate P&L
        if position.direction == 1:  # Long
            pnl = (exit_signal.exit_price - position.entry_price) * exit_signal.quantity
            pnl_pct = (exit_signal.exit_price - position.entry_price) / position.entry_price * 100
        else:  # Short
            pnl = (position.entry_price - exit_signal.exit_price) * exit_signal.quantity
            pnl_pct = (position.entry_price - exit_signal.exit_price) / position.entry_price * 100
        
        # Update position
        position.remaining_quantity -= exit_signal.quantity
        
        # Create exit record
        exit_record = {
            'symbol': symbol,
            'exit_time': pd.Timestamp.now(),
            'exit_type': exit_signal.exit_type,
            'exit_price': exit_signal.exit_price,
            'quantity': exit_signal.quantity,
            'entry_price': position.entry_price,
            'direction': position.direction,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'bars_held': position.bars_held,
            'reason': exit_signal.reason
        }
        
        # Store in history
        self.exit_history.append(exit_record)
        
        # Remove position if fully exited
        if position.remaining_quantity <= 0:
            del self.positions[symbol]
        
        return exit_record
    
    def update_config(self, new_config: Dict):
        """Update exit parameters"""
        self.config.update(new_config)
        self.stop_loss_pct = self.config.get('stop_loss_percent', self.stop_loss_pct)
        self.targets = self.config.get('take_profit_targets', self.targets)
        self.target_sizes = self.config.get('target_sizes', self.target_sizes)
        self.use_trailing = self.config.get('use_trailing_stop', self.use_trailing)
        self.trailing_activation = self.config.get('trailing_activation', self.trailing_activation)
        self.trailing_distance = self.config.get('trailing_distance', self.trailing_distance)
        self.max_holding_bars = self.config.get('max_holding_bars', self.max_holding_bars)
    
    def get_exit_statistics(self) -> Dict:
        """Get statistics on exits"""
        if not self.exit_history:
            return {}
        
        df = pd.DataFrame(self.exit_history)
        
        stats = {
            'total_exits': len(df),
            'by_type': df['exit_type'].value_counts().to_dict(),
            'avg_pnl_pct': df['pnl_pct'].mean(),
            'win_rate': (df['pnl'] > 0).mean() * 100,
            'avg_bars_held': df['bars_held'].mean(),
            'profit_by_type': df.groupby('exit_type')['pnl_pct'].mean().to_dict()
        }
        
        return stats