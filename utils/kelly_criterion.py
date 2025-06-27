"""
Kelly Criterion Position Sizing
===============================

Implements the Kelly Criterion for optimal position sizing based on:
- Win probability
- Average win/loss ratio
- Account for partial Kelly (fractional Kelly) for safety

Formula: f = (p*b - q) / b
Where:
- f = fraction of capital to bet
- p = probability of winning
- b = odds received on bet (avg win / avg loss)
- q = probability of losing (1-p)
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class KellyStats:
    """Statistics needed for Kelly calculation"""
    win_rate: float
    avg_win: float
    avg_loss: float
    num_trades: int
    kelly_fraction: float
    recommended_fraction: float  # Fractional Kelly for safety
    

class KellyCriterion:
    """
    Calculate optimal position size using Kelly Criterion
    
    Based on Quantitative Trading principles - never risk more than
    the mathematically optimal amount.
    """
    
    def __init__(self, kelly_fraction: float = 0.25):
        """
        Initialize Kelly calculator
        
        Args:
            kelly_fraction: Fraction of full Kelly to use (0.25 = 25% of full Kelly)
                           Most traders use 20-30% for safety
        """
        self.kelly_fraction = kelly_fraction
        self.trade_history = []
        
    def add_trade(self, pnl_pct: float):
        """
        Add a trade result to history
        
        Args:
            pnl_pct: Profit/loss percentage (e.g., 2.5 for 2.5% gain)
        """
        self.trade_history.append(pnl_pct)
    
    def calculate_kelly_percentage(self, 
                                  min_trades: int = 20,
                                  max_kelly: float = 0.25) -> KellyStats:
        """
        Calculate Kelly percentage based on trade history
        
        Args:
            min_trades: Minimum trades required for calculation
            max_kelly: Maximum Kelly percentage allowed (safety cap)
            
        Returns:
            KellyStats with calculations
        """
        if len(self.trade_history) < min_trades:
            # Not enough data - use minimum position size
            return KellyStats(
                win_rate=0.5,
                avg_win=0,
                avg_loss=0,
                num_trades=len(self.trade_history),
                kelly_fraction=0,
                recommended_fraction=0.01  # 1% default
            )
        
        # Calculate statistics
        trades = np.array(self.trade_history)
        winners = trades[trades > 0]
        losers = trades[trades <= 0]
        
        if len(winners) == 0 or len(losers) == 0:
            # All wins or all losses - can't calculate Kelly
            return KellyStats(
                win_rate=len(winners) / len(trades),
                avg_win=np.mean(winners) if len(winners) > 0 else 0,
                avg_loss=abs(np.mean(losers)) if len(losers) > 0 else 0,
                num_trades=len(trades),
                kelly_fraction=0,
                recommended_fraction=0.01
            )
        
        # Calculate parameters
        win_rate = len(winners) / len(trades)
        avg_win = np.mean(winners)
        avg_loss = abs(np.mean(losers))
        
        # Kelly formula: f = (p*b - q) / b
        p = win_rate
        q = 1 - p
        b = avg_win / avg_loss if avg_loss > 0 else 0
        
        if b > 0:
            kelly_pct = (p * b - q) / b
        else:
            kelly_pct = 0
        
        # Apply safety measures
        # 1. Cap at maximum allowed
        kelly_pct = min(kelly_pct, max_kelly)
        
        # 2. If negative, don't trade
        if kelly_pct < 0:
            kelly_pct = 0
            
        # 3. Apply fractional Kelly
        recommended_pct = kelly_pct * self.kelly_fraction
        
        return KellyStats(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            num_trades=len(trades),
            kelly_fraction=kelly_pct,
            recommended_fraction=recommended_pct
        )
    
    def calculate_position_size(self,
                               account_balance: float,
                               entry_price: float,
                               stop_loss: float,
                               kelly_stats: Optional[KellyStats] = None) -> Dict:
        """
        Calculate position size using Kelly Criterion
        
        Args:
            account_balance: Total account value
            entry_price: Entry price for trade
            stop_loss: Stop loss price
            kelly_stats: Pre-calculated Kelly stats (or will calculate)
            
        Returns:
            Dictionary with position sizing details
        """
        if kelly_stats is None:
            kelly_stats = self.calculate_kelly_percentage()
        
        # Risk per share
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share == 0:
            return {
                'shares': 0,
                'position_value': 0,
                'risk_amount': 0,
                'risk_pct': 0,
                'kelly_pct': 0,
                'reason': 'Invalid stop loss'
            }
        
        # Calculate position size based on Kelly
        if kelly_stats.recommended_fraction > 0:
            # Use Kelly-based sizing
            risk_amount = account_balance * kelly_stats.recommended_fraction
            shares = int(risk_amount / risk_per_share)
            actual_risk_pct = kelly_stats.recommended_fraction
        else:
            # Use minimum sizing (1%)
            risk_amount = account_balance * 0.01
            shares = int(risk_amount / risk_per_share)
            actual_risk_pct = 0.01
        
        # Ensure minimum position
        shares = max(shares, 1)
        
        # Calculate actual values
        position_value = shares * entry_price
        actual_risk = shares * risk_per_share
        
        return {
            'shares': shares,
            'position_value': position_value,
            'risk_amount': actual_risk,
            'risk_pct': actual_risk_pct * 100,
            'kelly_pct': kelly_stats.kelly_fraction * 100,
            'recommended_kelly_pct': kelly_stats.recommended_fraction * 100,
            'win_rate': kelly_stats.win_rate,
            'avg_win': kelly_stats.avg_win,
            'avg_loss': kelly_stats.avg_loss,
            'num_trades': kelly_stats.num_trades,
            'reason': 'Kelly Criterion' if kelly_stats.recommended_fraction > 0 else 'Minimum size'
        }
    
    def get_expectancy(self) -> float:
        """
        Calculate system expectancy
        
        Expectancy = (Win% × Avg Win) - (Loss% × Avg Loss)
        """
        if len(self.trade_history) == 0:
            return 0
        
        trades = np.array(self.trade_history)
        winners = trades[trades > 0]
        losers = trades[trades <= 0]
        
        if len(trades) == 0:
            return 0
            
        win_rate = len(winners) / len(trades)
        loss_rate = 1 - win_rate
        
        avg_win = np.mean(winners) if len(winners) > 0 else 0
        avg_loss = abs(np.mean(losers)) if len(losers) > 0 else 0
        
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        return expectancy
    
    def should_trade(self, min_expectancy: float = 0.0) -> bool:
        """
        Determine if system should trade based on expectancy
        
        Args:
            min_expectancy: Minimum required expectancy
            
        Returns:
            True if system has positive expectancy
        """
        return self.get_expectancy() > min_expectancy


def demo_kelly_criterion():
    """Demonstrate Kelly Criterion calculations"""
    
    print("="*60)
    print("📊 KELLY CRITERION POSITION SIZING DEMO")
    print("="*60)
    
    # Create calculator
    kelly = KellyCriterion(kelly_fraction=0.25)  # Use 25% of full Kelly
    
    # Add sample trade history (mix of wins and losses)
    sample_trades = [
        2.5, -1.2, 3.1, -0.8, 1.8, -1.5, 4.2, -0.9,
        2.1, -1.1, 3.5, 1.2, -0.7, 2.8, -1.3, 3.9,
        -0.6, 2.3, 1.9, -1.0, 2.7, 3.3, -0.8, 2.2
    ]
    
    print("\nAdding trade history...")
    for trade in sample_trades:
        kelly.add_trade(trade)
        print(f"Trade: {trade:+.1f}%", end="  ")
        if len(kelly.trade_history) % 4 == 0:
            print()  # New line every 4 trades
    
    # Calculate Kelly statistics
    print("\n\n" + "="*60)
    print("📈 KELLY CALCULATION RESULTS")
    print("="*60)
    
    stats = kelly.calculate_kelly_percentage()
    
    print(f"\nTrade Statistics:")
    print(f"  Total Trades: {stats.num_trades}")
    print(f"  Win Rate: {stats.win_rate:.1%}")
    print(f"  Average Win: {stats.avg_win:.2f}%")
    print(f"  Average Loss: {stats.avg_loss:.2f}%")
    print(f"  Win/Loss Ratio: {stats.avg_win/stats.avg_loss:.2f}" if stats.avg_loss > 0 else "  Win/Loss Ratio: N/A")
    
    print(f"\nKelly Calculations:")
    print(f"  Full Kelly: {stats.kelly_fraction:.1%}")
    print(f"  Fractional Kelly (25%): {stats.recommended_fraction:.1%}")
    
    expectancy = kelly.get_expectancy()
    print(f"\nSystem Expectancy: {expectancy:.3f}%")
    print(f"Should Trade: {'YES' if kelly.should_trade() else 'NO'}")
    
    # Example position sizing
    print("\n" + "="*60)
    print("💰 POSITION SIZING EXAMPLE")
    print("="*60)
    
    account_balance = 100000
    entry_price = 105
    stop_loss = 103
    
    print(f"\nAccount Balance: ₹{account_balance:,}")
    print(f"Entry Price: ₹{entry_price}")
    print(f"Stop Loss: ₹{stop_loss}")
    print(f"Risk per Share: ₹{entry_price - stop_loss}")
    
    # Calculate position size
    position = kelly.calculate_position_size(
        account_balance=account_balance,
        entry_price=entry_price,
        stop_loss=stop_loss,
        kelly_stats=stats
    )
    
    print(f"\nPosition Sizing Results:")
    print(f"  Shares to Buy: {position['shares']}")
    print(f"  Position Value: ₹{position['position_value']:,.0f}")
    print(f"  Risk Amount: ₹{position['risk_amount']:,.0f}")
    print(f"  Risk Percentage: {position['risk_pct']:.2f}%")
    print(f"  Sizing Method: {position['reason']}")
    
    # Compare with fixed sizing
    print("\n" + "="*60)
    print("📊 COMPARISON WITH FIXED SIZING")
    print("="*60)
    
    fixed_risk_pct = 0.02  # 2% fixed risk
    fixed_risk_amount = account_balance * fixed_risk_pct
    fixed_shares = int(fixed_risk_amount / (entry_price - stop_loss))
    
    print(f"\nFixed 2% Risk:")
    print(f"  Shares: {fixed_shares}")
    print(f"  Position Value: ₹{fixed_shares * entry_price:,.0f}")
    print(f"  Risk Amount: ₹{fixed_risk_amount:,.0f}")
    
    print(f"\nKelly Advantage:")
    print(f"  Position Size Difference: {position['shares'] - fixed_shares:+d} shares")
    print(f"  Risk Optimization: {position['risk_pct'] - 2:.2f}% points")
    
    # Show how Kelly adapts to different win rates
    print("\n" + "="*60)
    print("🎯 KELLY ADAPTATION TO WIN RATES")
    print("="*60)
    
    print("\nWin Rate | Avg W/L | Full Kelly | 25% Kelly | Risk/Trade")
    print("-" * 55)
    
    # Simulate different scenarios
    scenarios = [
        (0.30, 3.0, 1.0),  # Low win rate, high R:R
        (0.50, 2.0, 1.0),  # Average system
        (0.60, 1.5, 1.0),  # High win rate, lower R:R
        (0.70, 1.2, 1.0),  # Very high win rate
    ]
    
    for win_rate, avg_win, avg_loss in scenarios:
        p = win_rate
        q = 1 - p
        b = avg_win / avg_loss
        
        kelly_full = (p * b - q) / b if b > 0 else 0
        kelly_frac = kelly_full * 0.25
        
        risk_amt = account_balance * kelly_frac
        
        print(f"{win_rate:6.1%} | {b:7.2f} | {kelly_full:9.1%} | "
              f"{kelly_frac:8.1%} | ₹{risk_amt:8,.0f}")


if __name__ == "__main__":
    demo_kelly_criterion()