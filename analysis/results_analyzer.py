"""
Results Analyzer
===============

Analyzes trading results and generates statistics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TradingMetrics:
    """Container for trading metrics"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    avg_win: float
    avg_loss: float
    expectancy: float
    profit_factor: float
    max_drawdown: float
    car_maxdd: float
    annualized_return: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_win: Optional[float] = None
    max_loss: Optional[float] = None


class ResultsAnalyzer:
    """Analyzes trading results"""
    
    @staticmethod
    def calculate_metrics(trades: List[Dict], strategy_name: str = "") -> TradingMetrics:
        """
        Calculate comprehensive trading metrics
        
        Args:
            trades: List of trade dictionaries
            strategy_name: Name for logging/debugging
            
        Returns:
            TradingMetrics object with all calculations
        """
        if not trades:
            return ResultsAnalyzer._empty_metrics()
        
        trades_df = pd.DataFrame(trades)
        
        # Separate winners and losers
        winning_trades = trades_df[trades_df['pnl_pct'] > 0]
        losing_trades = trades_df[trades_df['pnl_pct'] <= 0]
        
        # Calculate compound return
        trade_multipliers = 1 + trades_df['pnl_pct'] / 100
        compound_multiplier = trade_multipliers.prod()
        total_return = (compound_multiplier - 1) * 100
        
        # Basic metrics
        total_trades = len(trades_df)
        num_winners = len(winning_trades)
        num_losers = len(losing_trades)
        win_rate = (num_winners / total_trades * 100) if total_trades > 0 else 0
        
        # Win/Loss statistics
        avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
        avg_loss = abs(losing_trades['pnl_pct'].mean()) if len(losing_trades) > 0 else 0
        max_win = winning_trades['pnl_pct'].max() if len(winning_trades) > 0 else 0
        max_loss = abs(losing_trades['pnl_pct'].min()) if len(losing_trades) > 0 else 0
        
        # Expectancy
        expectancy = (win_rate/100 * avg_win) - ((100-win_rate)/100 * avg_loss)
        
        # Profit Factor
        total_wins = winning_trades['pnl_pct'].sum() if len(winning_trades) > 0 else 0
        total_losses = abs(losing_trades['pnl_pct'].sum()) if len(losing_trades) > 0 else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Drawdown calculation
        cumulative_multiplier = trade_multipliers.cumprod()
        cumulative_returns_pct = (cumulative_multiplier - 1) * 100
        running_max = cumulative_returns_pct.expanding().max()
        drawdown = cumulative_returns_pct - running_max
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0
        
        # Annualized metrics
        trading_days = len(trades_df) / 3  # Rough estimate
        years = trading_days / 252 if trading_days > 0 else 1
        
        if years < 0.1:  # Less than ~25 trading days
            annualized_return = total_return
        else:
            annualized_return = ((compound_multiplier ** (1/years)) - 1) * 100 if compound_multiplier > 0 else -100
        
        car_maxdd = annualized_return / max_drawdown if max_drawdown > 0 else 0
        
        # Additional risk metrics
        returns = trades_df['pnl_pct']
        sharpe_ratio = ResultsAnalyzer._calculate_sharpe(returns, annualized_return)
        sortino_ratio = ResultsAnalyzer._calculate_sortino(returns, annualized_return)
        
        # Debug suspicious results
        if avg_win < 0.5 and win_rate > 70:
            print(f"\n⚠️  SUSPICIOUS ({strategy_name}): High win rate ({win_rate:.1f}%) but tiny avg win ({avg_win:.3f}%)")
            print(f"   Max win: {max_win:.2f}%, Max loss: {max_loss:.2f}%")
            print(f"   This suggests targets are NOT being hit!")
        
        return TradingMetrics(
            total_trades=total_trades,
            winning_trades=num_winners,
            losing_trades=num_losers,
            win_rate=win_rate,
            total_return=total_return,
            avg_win=avg_win,
            avg_loss=avg_loss,
            expectancy=expectancy,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            car_maxdd=car_maxdd,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_win=max_win,
            max_loss=max_loss
        )
    
    @staticmethod
    def analyze_exit_reasons(trades: List[Dict]) -> Dict[str, Tuple[int, float]]:
        """
        Analyze trades by exit reason
        
        Returns:
            Dict of exit reason to (count, avg_pnl)
        """
        if not trades:
            return {}
        
        trades_df = pd.DataFrame(trades)
        
        exit_stats = {}
        for reason in trades_df['exit_reason'].unique():
            reason_trades = trades_df[trades_df['exit_reason'] == reason]
            count = len(reason_trades)
            avg_pnl = reason_trades['pnl_pct'].mean()
            exit_stats[reason] = (count, avg_pnl)
        
        return exit_stats
    
    @staticmethod
    def print_exit_analysis(trades: List[Dict], symbol: str = "", 
                          strategy: str = ""):
        """Print detailed exit reason analysis"""
        if not trades:
            return
        
        exit_stats = ResultsAnalyzer.analyze_exit_reasons(trades)
        total_trades = len(trades)
        
        print(f"\nExit Analysis - {symbol} {strategy}:")
        print(f"{'Exit Reason':<15} {'Count':<8} {'%':<8} {'Avg P&L':<10}")
        print("-" * 45)
        
        for reason, (count, avg_pnl) in sorted(exit_stats.items(), 
                                              key=lambda x: x[1][0], 
                                              reverse=True):
            pct = count / total_trades * 100
            print(f"{reason:<15} {count:<8} {pct:<8.1f} {avg_pnl:<10.3f}%")
    
    @staticmethod
    def _calculate_sharpe(returns: pd.Series, annualized_return: float) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) < 2:
            return 0
        
        # Daily returns std
        daily_std = returns.std()
        if daily_std == 0:
            return 0
        
        # Annualize (assuming ~252 trading days)
        annual_std = daily_std * np.sqrt(252 / 3)  # Adjust for trade frequency
        
        # Risk-free rate (assume 2%)
        risk_free = 2.0
        
        return (annualized_return - risk_free) / annual_std if annual_std > 0 else 0
    
    @staticmethod
    def _calculate_sortino(returns: pd.Series, annualized_return: float) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        if len(returns) < 2:
            return 0
        
        # Downside returns only
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return float('inf')  # No downside
        
        downside_std = downside_returns.std()
        if downside_std == 0:
            return 0
        
        # Annualize
        annual_downside_std = downside_std * np.sqrt(252 / 3)
        
        # Risk-free rate
        risk_free = 2.0
        
        return (annualized_return - risk_free) / annual_downside_std if annual_downside_std > 0 else 0
    
    @staticmethod
    def _empty_metrics() -> TradingMetrics:
        """Return empty metrics for no trades"""
        return TradingMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0,
            total_return=0,
            avg_win=0,
            avg_loss=0,
            expectancy=0,
            profit_factor=0,
            max_drawdown=0,
            car_maxdd=0,
            annualized_return=0,
            sharpe_ratio=0,
            sortino_ratio=0,
            max_win=0,
            max_loss=0
        )