"""
ATR-Based Stop Loss Calculator
==============================

Implements dynamic stop losses based on Average True Range (ATR).
This addresses the need for adaptive risk management.
"""

import numpy as np
from typing import List, Tuple, Optional


class ATRStopCalculator:
    """Calculate dynamic stops using ATR"""
    
    def __init__(self, period: int = 14):
        """
        Initialize ATR calculator
        
        Args:
            period: ATR calculation period (default 14)
        """
        self.period = period
        self.tr_values = []
        self.atr_values = []
    
    def calculate_true_range(
        self, 
        high: float, 
        low: float, 
        prev_close: Optional[float] = None
    ) -> float:
        """
        Calculate True Range for a single bar
        
        TR = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        """
        if prev_close is None:
            return high - low
        
        return max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
    
    def update(self, high: float, low: float, close: float) -> float:
        """
        Update ATR with new bar data
        
        Returns:
            Current ATR value
        """
        # Calculate TR
        prev_close = self.prev_close if hasattr(self, 'prev_close') else None
        tr = self.calculate_true_range(high, low, prev_close)
        self.tr_values.append(tr)
        
        # Keep only required values
        if len(self.tr_values) > self.period:
            self.tr_values.pop(0)
        
        # Calculate ATR
        if len(self.tr_values) >= self.period:
            # First ATR is simple average
            if not self.atr_values:
                atr = sum(self.tr_values) / self.period
            else:
                # Subsequent ATRs use smoothing
                prev_atr = self.atr_values[-1]
                atr = (prev_atr * (self.period - 1) + tr) / self.period
            
            self.atr_values.append(atr)
        else:
            # Not enough data yet
            atr = sum(self.tr_values) / len(self.tr_values) if self.tr_values else 0
        
        self.prev_close = close
        return atr
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        direction: int = 1,  # 1 for long, -1 for short
        multiplier: float = 2.0
    ) -> float:
        """
        Calculate stop loss price
        
        Args:
            entry_price: Entry price of the trade
            atr: Current ATR value
            direction: 1 for long, -1 for short
            multiplier: ATR multiplier (default 2.0)
        
        Returns:
            Stop loss price
        """
        stop_distance = atr * multiplier
        
        if direction == 1:  # Long
            return entry_price - stop_distance
        else:  # Short
            return entry_price + stop_distance
    
    def calculate_trailing_stop(
        self,
        current_price: float,
        atr: float,
        direction: int = 1,
        multiplier: float = 1.5,  # Tighter for trailing
        current_stop: Optional[float] = None
    ) -> float:
        """
        Calculate trailing stop that only moves in favor of the trade
        
        Args:
            current_price: Current market price
            atr: Current ATR value
            direction: 1 for long, -1 for short
            multiplier: ATR multiplier for trailing (default 1.5)
            current_stop: Current stop loss level
        
        Returns:
            New trailing stop price
        """
        stop_distance = atr * multiplier
        
        if direction == 1:  # Long
            new_stop = current_price - stop_distance
            # Only move stop up, never down
            if current_stop is None or new_stop > current_stop:
                return new_stop
            else:
                return current_stop
        else:  # Short
            new_stop = current_price + stop_distance
            # Only move stop down, never up
            if current_stop is None or new_stop < current_stop:
                return new_stop
            else:
                return current_stop
    
    def calculate_targets(
        self,
        entry_price: float,
        atr: float,
        direction: int = 1,
        risk_reward_ratios: List[float] = [1.5, 3.0, 5.0]
    ) -> List[float]:
        """
        Calculate profit targets based on ATR
        
        Args:
            entry_price: Entry price
            atr: Current ATR value
            direction: 1 for long, -1 for short
            risk_reward_ratios: List of R:R ratios for targets
        
        Returns:
            List of target prices
        """
        # Use standard 2x ATR for initial risk
        risk = atr * 2.0
        
        targets = []
        for ratio in risk_reward_ratios:
            reward = risk * ratio
            
            if direction == 1:  # Long
                target = entry_price + reward
            else:  # Short
                target = entry_price - reward
                
            targets.append(target)
        
        return targets
    
    def calculate_position_size(
        self,
        account_balance: float,
        risk_percent: float,
        entry_price: float,
        stop_loss: float
    ) -> int:
        """
        Calculate position size based on risk
        
        Args:
            account_balance: Total account value
            risk_percent: Risk per trade (e.g., 0.015 for 1.5%)
            entry_price: Entry price
            stop_loss: Stop loss price
        
        Returns:
            Number of shares to trade
        """
        # Calculate risk amount
        risk_amount = account_balance * risk_percent
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            return 0
        
        # Calculate position size
        position_size = int(risk_amount / risk_per_share)
        
        return position_size
    
    def get_volatility_regime(self, current_atr: float, lookback: int = 100) -> str:
        """
        Determine current volatility regime
        
        Args:
            current_atr: Current ATR value
            lookback: Bars to look back for percentile
        
        Returns:
            'LOW', 'NORMAL', or 'HIGH'
        """
        if len(self.atr_values) < lookback:
            return 'NORMAL'
        
        recent_atrs = self.atr_values[-lookback:]
        percentile = np.percentile(recent_atrs, 
                                  [20, 80])
        
        if current_atr < percentile[0]:
            return 'LOW'
        elif current_atr > percentile[1]:
            return 'HIGH'
        else:
            return 'NORMAL'


class ChandelierStop:
    """
    Chandelier Exit - ATR-based trailing stop
    Developed by Chuck LeBeau
    """
    
    def __init__(self, period: int = 22, multiplier: float = 3.0):
        """
        Initialize Chandelier Stop
        
        Args:
            period: Lookback period for highest/lowest
            multiplier: ATR multiplier
        """
        self.period = period
        self.multiplier = multiplier
        self.atr_calc = ATRStopCalculator(14)
        self.highs = []
        self.lows = []
    
    def update(
        self, 
        high: float, 
        low: float, 
        close: float
    ) -> Tuple[float, float]:
        """
        Update and calculate Chandelier stops
        
        Returns:
            (long_stop, short_stop)
        """
        # Update ATR
        atr = self.atr_calc.update(high, low, close)
        
        # Track highs and lows
        self.highs.append(high)
        self.lows.append(low)
        
        # Keep only required period
        if len(self.highs) > self.period:
            self.highs.pop(0)
            self.lows.pop(0)
        
        if len(self.highs) < self.period:
            # Not enough data
            return close - atr * self.multiplier, close + atr * self.multiplier
        
        # Calculate stops
        highest_high = max(self.highs)
        lowest_low = min(self.lows)
        
        long_stop = highest_high - atr * self.multiplier
        short_stop = lowest_low + atr * self.multiplier
        
        return long_stop, short_stop


def demo_atr_stops():
    """Demonstrate ATR stop calculations"""
    
    print("="*60)
    print("🛡️ ATR-BASED STOP LOSS DEMO")
    print("="*60)
    
    # Sample data (high, low, close)
    bars = [
        (102, 98, 100),
        (103, 99, 102),
        (105, 101, 104),
        (104, 102, 103),
        (106, 103, 105),
        (107, 104, 106),
        (106, 103, 104),
        (105, 102, 103),
        (104, 101, 102),
        (103, 100, 101),
        (104, 101, 103),
        (105, 102, 104),
        (106, 103, 105),
        (107, 104, 106),
        (108, 105, 107)
    ]
    
    # Initialize calculator
    atr_calc = ATRStopCalculator(period=14)
    
    print("\nProcessing bars and calculating ATR...")
    print("-" * 50)
    print("Bar | High | Low | Close | ATR   | Vol Regime")
    print("-" * 50)
    
    for i, (high, low, close) in enumerate(bars):
        atr = atr_calc.update(high, low, close)
        regime = atr_calc.get_volatility_regime(atr)
        
        print(f"{i+1:3d} | {high:4.0f} | {low:3.0f} | {close:5.0f} | "
              f"{atr:5.2f} | {regime}")
    
    # Example trade
    print("\n" + "="*60)
    print("📊 EXAMPLE TRADE CALCULATIONS")
    print("="*60)
    
    entry_price = 105.0
    current_atr = atr
    account_balance = 100000
    risk_percent = 0.015  # 1.5%
    
    print(f"\nEntry Price: ₹{entry_price}")
    print(f"Current ATR: {current_atr:.2f}")
    print(f"Account Balance: ₹{account_balance:,}")
    print(f"Risk per Trade: {risk_percent*100}%")
    
    # Calculate stops
    stop_loss = atr_calc.calculate_stop_loss(entry_price, current_atr, 
                                            direction=1, multiplier=2.0)
    
    print(f"\n🛡️ Stop Loss Calculations:")
    print(f"   Initial Stop (2x ATR): ₹{stop_loss:.2f}")
    print(f"   Risk per Share: ₹{entry_price - stop_loss:.2f}")
    
    # Position sizing
    position_size = atr_calc.calculate_position_size(
        account_balance, risk_percent, entry_price, stop_loss
    )
    
    print(f"\n💰 Position Sizing:")
    print(f"   Risk Amount: ₹{account_balance * risk_percent:,.0f}")
    print(f"   Position Size: {position_size} shares")
    print(f"   Total Investment: ₹{position_size * entry_price:,.0f}")
    
    # Profit targets
    targets = atr_calc.calculate_targets(entry_price, current_atr, 
                                       direction=1, 
                                       risk_reward_ratios=[1.5, 3.0, 5.0])
    
    print(f"\n🎯 Profit Targets:")
    for i, (target, ratio) in enumerate(zip(targets, [1.5, 3.0, 5.0]), 1):
        profit = target - entry_price
        print(f"   Target {i} ({ratio}R): ₹{target:.2f} "
              f"(+₹{profit:.2f} or +{profit/entry_price*100:.1f}%)")
    
    # Trailing stop example
    print(f"\n📈 Trailing Stop Example:")
    current_prices = [106, 107, 108, 107, 109, 108]
    trailing_stop = stop_loss
    
    for price in current_prices:
        trailing_stop = atr_calc.calculate_trailing_stop(
            price, current_atr, direction=1, 
            multiplier=1.5, current_stop=trailing_stop
        )
        print(f"   Price: ₹{price} → Trailing Stop: ₹{trailing_stop:.2f}")
    
    # Chandelier stop demo
    print(f"\n🏮 Chandelier Stop Example:")
    chandelier = ChandelierStop(period=10, multiplier=3.0)
    
    for i, (high, low, close) in enumerate(bars[-5:]):
        long_stop, short_stop = chandelier.update(high, low, close)
        print(f"   Bar {i+1}: Long Stop: ₹{long_stop:.2f}, "
              f"Short Stop: ₹{short_stop:.2f}")


if __name__ == "__main__":
    demo_atr_stops()