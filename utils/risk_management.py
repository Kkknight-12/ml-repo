"""
Risk Management Module
Calculates stop loss and take profit levels for trades
"""
from typing import Tuple, Optional
from core.math_helpers import pine_atr


class RiskManager:
    """
    Manages risk calculations for trading signals
    Provides SL/TP levels based on various methods
    """
    
    def __init__(self, default_risk_reward: float = 2.0):
        """
        Initialize risk manager
        
        Args:
            default_risk_reward: Default risk-reward ratio for targets
        """
        self.default_risk_reward = default_risk_reward
    
    def calculate_atr_stops(
        self, 
        entry_price: float,
        atr_value: float,
        is_long: bool,
        atr_multiplier: float = 2.0,
        risk_reward_ratio: float = None
    ) -> Tuple[float, float]:
        """
        Calculate stop loss and take profit using ATR
        
        Args:
            entry_price: Entry price for the trade
            atr_value: Current ATR value
            is_long: True for long trades, False for short
            atr_multiplier: Multiplier for ATR (default 2.0)
            risk_reward_ratio: Risk-reward ratio (default uses class default)
            
        Returns:
            (stop_loss, take_profit)
        """
        if risk_reward_ratio is None:
            risk_reward_ratio = self.default_risk_reward
        
        # Calculate stop distance
        stop_distance = atr_value * atr_multiplier
        
        if is_long:
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + (stop_distance * risk_reward_ratio)
        else:
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - (stop_distance * risk_reward_ratio)
        
        return round(stop_loss, 2), round(take_profit, 2)
    
    def calculate_percentage_stops(
        self,
        entry_price: float,
        is_long: bool,
        stop_percentage: float = 2.0,
        target_percentage: float = 4.0
    ) -> Tuple[float, float]:
        """
        Calculate stop loss and take profit using fixed percentages
        
        Args:
            entry_price: Entry price for the trade
            is_long: True for long trades, False for short
            stop_percentage: Stop loss percentage (default 2%)
            target_percentage: Take profit percentage (default 4%)
            
        Returns:
            (stop_loss, take_profit)
        """
        stop_amount = entry_price * (stop_percentage / 100)
        target_amount = entry_price * (target_percentage / 100)
        
        if is_long:
            stop_loss = entry_price - stop_amount
            take_profit = entry_price + target_amount
        else:
            stop_loss = entry_price + stop_amount
            take_profit = entry_price - target_amount
        
        return round(stop_loss, 2), round(take_profit, 2)
    
    def calculate_swing_stops(
        self,
        entry_price: float,
        recent_high: float,
        recent_low: float,
        is_long: bool,
        buffer_points: float = 0.0,
        risk_reward_ratio: float = None
    ) -> Tuple[float, float]:
        """
        Calculate stops based on recent swing highs/lows
        
        Args:
            entry_price: Entry price for the trade
            recent_high: Recent swing high
            recent_low: Recent swing low
            is_long: True for long trades, False for short
            buffer_points: Additional buffer beyond swing point
            risk_reward_ratio: Risk-reward ratio
            
        Returns:
            (stop_loss, take_profit)
        """
        if risk_reward_ratio is None:
            risk_reward_ratio = self.default_risk_reward
        
        if is_long:
            stop_loss = recent_low - buffer_points
            stop_distance = entry_price - stop_loss
            take_profit = entry_price + (stop_distance * risk_reward_ratio)
        else:
            stop_loss = recent_high + buffer_points
            stop_distance = stop_loss - entry_price
            take_profit = entry_price - (stop_distance * risk_reward_ratio)
        
        return round(stop_loss, 2), round(take_profit, 2)
    
    def calculate_position_size(
        self,
        account_balance: float,
        risk_percentage: float,
        entry_price: float,
        stop_loss: float
    ) -> int:
        """
        Calculate position size based on risk management rules
        
        Args:
            account_balance: Total account balance
            risk_percentage: Percentage of account to risk (e.g., 1.0 for 1%)
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            
        Returns:
            Number of shares/contracts to trade
        """
        # Calculate risk amount
        risk_amount = account_balance * (risk_percentage / 100)
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            return 0
        
        # Calculate position size
        position_size = int(risk_amount / risk_per_share)
        
        return max(1, position_size)  # At least 1 share
    
    def validate_risk_reward(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        min_ratio: float = 1.5
    ) -> bool:
        """
        Validate if trade meets minimum risk-reward criteria
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            min_ratio: Minimum acceptable risk-reward ratio
            
        Returns:
            True if trade meets criteria
        """
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        
        if risk == 0:
            return False
        
        ratio = reward / risk
        return ratio >= min_ratio
    
    def adjust_stops_for_volatility(
        self,
        stop_loss: float,
        take_profit: float,
        current_volatility: float,
        average_volatility: float,
        max_adjustment: float = 0.5
    ) -> Tuple[float, float]:
        """
        Adjust stops based on current market volatility
        
        Args:
            stop_loss: Original stop loss
            take_profit: Original take profit
            current_volatility: Current market volatility (e.g., VIX, ATR)
            average_volatility: Long-term average volatility
            max_adjustment: Maximum adjustment factor (0.5 = 50%)
            
        Returns:
            (adjusted_stop_loss, adjusted_take_profit)
        """
        if average_volatility == 0:
            return stop_loss, take_profit
        
        # Calculate volatility ratio
        volatility_ratio = current_volatility / average_volatility
        
        # Cap the adjustment
        adjustment_factor = min(max(volatility_ratio, 1 - max_adjustment), 1 + max_adjustment)
        
        # Adjust stops (widen in high volatility)
        if adjustment_factor > 1:
            # High volatility - widen stops
            adjusted_sl = stop_loss * adjustment_factor if stop_loss < 100 else stop_loss
            adjusted_tp = take_profit * adjustment_factor if take_profit > 100 else take_profit
        else:
            # Low volatility - tighten stops
            adjusted_sl = stop_loss * adjustment_factor if stop_loss < 100 else stop_loss
            adjusted_tp = take_profit * adjustment_factor if take_profit > 100 else take_profit
        
        return round(adjusted_sl, 2), round(adjusted_tp, 2)


def calculate_trade_levels(
    entry_price: float,
    high_values: list,
    low_values: list,
    close_values: list,
    is_long: bool,
    method: str = "atr",
    **kwargs
) -> Tuple[float, float]:
    """
    Convenience function to calculate SL/TP levels
    
    Args:
        entry_price: Entry price
        high_values: Historical high prices
        low_values: Historical low prices
        close_values: Historical close prices
        is_long: Trade direction
        method: Method to use ("atr", "percentage", "swing")
        **kwargs: Additional parameters for specific methods
        
    Returns:
        (stop_loss, take_profit)
    """
    risk_manager = RiskManager()
    
    if method == "atr":
        # Calculate ATR
        atr_length = kwargs.get("atr_length", 14)
        atr = pine_atr(high_values, low_values, close_values, atr_length)
        
        return risk_manager.calculate_atr_stops(
            entry_price, atr, is_long,
            atr_multiplier=kwargs.get("atr_multiplier", 2.0),
            risk_reward_ratio=kwargs.get("risk_reward_ratio", 2.0)
        )
    
    elif method == "percentage":
        return risk_manager.calculate_percentage_stops(
            entry_price, is_long,
            stop_percentage=kwargs.get("stop_percentage", 2.0),
            target_percentage=kwargs.get("target_percentage", 4.0)
        )
    
    elif method == "swing":
        # Find recent swing points
        lookback = kwargs.get("lookback", 20)
        recent_high = max(high_values[:lookback]) if len(high_values) >= lookback else high_values[0]
        recent_low = min(low_values[:lookback]) if len(low_values) >= lookback else low_values[0]
        
        return risk_manager.calculate_swing_stops(
            entry_price, recent_high, recent_low, is_long,
            buffer_points=kwargs.get("buffer_points", 0.0),
            risk_reward_ratio=kwargs.get("risk_reward_ratio", 2.0)
        )
    
    else:
        # Default to percentage method
        return risk_manager.calculate_percentage_stops(entry_price, is_long)
