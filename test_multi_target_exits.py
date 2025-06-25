#!/usr/bin/env python3
"""
Test Multi-Target Exit System
=============================

Tests the effectiveness of multi-target exits vs fixed 5-bar exits.
This addresses the main issue: small wins despite high win rate.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

# Import backtesting framework
from backtest_framework import BacktestEngine, BacktestMetrics

# Import configurations
from config.settings import TradingConfig
from config.optimized_settings import OptimizedTradingConfig

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiTargetTester:
    """Test different exit strategies"""
    
    def __init__(self):
        self.engine = BacktestEngine()
        self.results = {}
    
    def test_exit_strategies(self, symbol: str, days: int = 60):
        """Compare different exit strategies"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        print(f"\n🎯 Testing Exit Strategies on {symbol}")
        print(f"Period: {start_date.date()} to {end_date.date()}")
        print("="*60)
        
        # 1. Baseline: Fixed 5-bar exit
        print("\n1️⃣ Testing BASELINE (Fixed 5-bar exit)...")
        baseline_config = TradingConfig()
        baseline_config.use_dynamic_exits = False
        baseline_config.show_exits = True
        
        baseline_metrics = self.engine.run_backtest(
            symbol, start_date, end_date, baseline_config
        )
        self.results['baseline'] = baseline_metrics
        
        # 2. Dynamic exits (signal-based)
        print("\n2️⃣ Testing DYNAMIC EXITS (Signal-based)...")
        dynamic_config = TradingConfig()
        dynamic_config.use_dynamic_exits = True
        dynamic_config.show_exits = True
        
        dynamic_metrics = self.engine.run_backtest(
            symbol, start_date, end_date, dynamic_config
        )
        self.results['dynamic'] = dynamic_metrics
        
        # 3. Multi-target exits
        print("\n3️⃣ Testing MULTI-TARGET EXITS...")
        multi_target_config = OptimizedTradingConfig()
        multi_target_config.use_dynamic_exits = True
        multi_target_config.show_exits = True
        # Uses default targets: 50% at 1.5R, 30% at 3R, 20% trailing
        
        multi_target_metrics = self.engine.run_backtest(
            symbol, start_date, end_date, multi_target_config
        )
        self.results['multi_target'] = multi_target_metrics
        
        # 4. Conservative multi-target
        print("\n4️⃣ Testing CONSERVATIVE TARGETS...")
        conservative_config = OptimizedTradingConfig()
        conservative_config.use_dynamic_exits = True
        conservative_config.target_1_ratio = 1.2  # Quicker first target
        conservative_config.target_1_percent = 0.7  # Exit 70% quickly
        conservative_config.target_2_ratio = 2.0
        conservative_config.target_2_percent = 0.3
        
        conservative_metrics = self.engine.run_backtest(
            symbol, start_date, end_date, conservative_config
        )
        self.results['conservative'] = conservative_metrics
        
        # 5. Aggressive multi-target
        print("\n5️⃣ Testing AGGRESSIVE TARGETS...")
        aggressive_config = OptimizedTradingConfig()
        aggressive_config.use_dynamic_exits = True
        aggressive_config.target_1_ratio = 2.0  # Higher first target
        aggressive_config.target_1_percent = 0.3  # Exit less initially
        aggressive_config.target_2_ratio = 4.0  # Much higher second target
        aggressive_config.target_2_percent = 0.4
        
        aggressive_metrics = self.engine.run_backtest(
            symbol, start_date, end_date, aggressive_config
        )
        self.results['aggressive'] = aggressive_metrics
        
        # Compare results
        self._print_comparison()
        
        # Return best strategy
        return self._find_best_strategy()
    
    def _print_comparison(self):
        """Print detailed comparison of results"""
        
        print("\n" + "="*80)
        print("📊 EXIT STRATEGY COMPARISON")
        print("="*80)
        
        # Create comparison table
        headers = ['Strategy', 'Trades', 'Win%', 'Avg Win%', 'Avg Loss%', 
                   'Total Return%', 'Profit Factor', 'Max DD%']
        
        rows = []
        for name, metrics in self.results.items():
            rows.append([
                name.upper(),
                metrics.total_trades,
                f"{metrics.win_rate:.1f}",
                f"{metrics.average_win:+.2f}",
                f"{metrics.average_loss:+.2f}",
                f"{metrics.total_return:+.2f}",
                f"{metrics.profit_factor:.2f}",
                f"{metrics.max_drawdown:.1f}"
            ])
        
        # Print table
        col_widths = [max(len(str(row[i])) for row in [headers] + rows) + 2 
                      for i in range(len(headers))]
        
        # Print headers
        header_line = ""
        for header, width in zip(headers, col_widths):
            header_line += header.ljust(width)
        print(header_line)
        print("-" * len(header_line))
        
        # Print rows
        for row in rows:
            row_line = ""
            for cell, width in zip(row, col_widths):
                row_line += str(cell).ljust(width)
            print(row_line)
        
        # Key insights
        print("\n🔍 Key Insights:")
        
        # Compare average wins
        baseline_avg_win = self.results['baseline'].average_win
        for name, metrics in self.results.items():
            if name != 'baseline':
                improvement = ((metrics.average_win / baseline_avg_win) - 1) * 100
                print(f"   {name}: Avg win {improvement:+.1f}% vs baseline")
        
        # Compare total returns
        print("\n💰 Total Return Ranking:")
        sorted_results = sorted(self.results.items(), 
                              key=lambda x: x[1].total_return, 
                              reverse=True)
        for i, (name, metrics) in enumerate(sorted_results, 1):
            print(f"   {i}. {name}: {metrics.total_return:+.2f}%")
    
    def _find_best_strategy(self) -> str:
        """Determine best strategy based on multiple factors"""
        
        scores = {}
        
        for name, metrics in self.results.items():
            # Score based on multiple factors
            score = 0
            
            # Total return (weight: 40%)
            score += metrics.total_return * 0.4
            
            # Average win size (weight: 30%)
            score += metrics.average_win * 0.3
            
            # Profit factor (weight: 20%)
            score += metrics.profit_factor * 10 * 0.2
            
            # Penalty for drawdown (weight: 10%)
            score -= metrics.max_drawdown * 0.1
            
            scores[name] = score
        
        best_strategy = max(scores, key=scores.get)
        
        print(f"\n🏆 RECOMMENDED STRATEGY: {best_strategy.upper()}")
        print(f"   Score: {scores[best_strategy]:.2f}")
        
        best_metrics = self.results[best_strategy]
        print(f"   Expected avg win: {best_metrics.average_win:.2f}%")
        print(f"   Expected return: {best_metrics.total_return:.2f}%")
        
        return best_strategy
    
    def plot_exit_comparison(self):
        """Visual comparison of exit strategies"""
        
        import matplotlib.pyplot as plt
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Plot 1: Average Win/Loss comparison
        strategies = list(self.results.keys())
        avg_wins = [self.results[s].average_win for s in strategies]
        avg_losses = [abs(self.results[s].average_loss) for s in strategies]
        
        x = np.arange(len(strategies))
        width = 0.35
        
        ax1.bar(x - width/2, avg_wins, width, label='Avg Win %', color='green', alpha=0.7)
        ax1.bar(x + width/2, avg_losses, width, label='Avg Loss %', color='red', alpha=0.7)
        ax1.set_xlabel('Strategy')
        ax1.set_ylabel('Percentage')
        ax1.set_title('Average Win vs Loss by Strategy')
        ax1.set_xticks(x)
        ax1.set_xticklabels(strategies)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Risk-Reward visualization
        win_rates = [self.results[s].win_rate for s in strategies]
        avg_wins = [self.results[s].average_win for s in strategies]
        total_returns = [self.results[s].total_return for s in strategies]
        
        # Size by total return
        sizes = [abs(r) * 20 for r in total_returns]
        colors = ['green' if r > 0 else 'red' for r in total_returns]
        
        ax2.scatter(win_rates, avg_wins, s=sizes, c=colors, alpha=0.6)
        
        for i, strategy in enumerate(strategies):
            ax2.annotate(strategy, (win_rates[i], avg_wins[i]))
        
        ax2.set_xlabel('Win Rate %')
        ax2.set_ylabel('Average Win %')
        ax2.set_title('Win Rate vs Average Win Size')
        ax2.grid(True, alpha=0.3)
        
        # Add ideal zone
        ax2.axhline(y=7, color='gray', linestyle='--', alpha=0.5, label='Target avg win')
        ax2.axvline(x=60, color='gray', linestyle='--', alpha=0.5, label='Target win rate')
        
        plt.tight_layout()
        plt.savefig('exit_strategy_comparison.png')
        plt.show()


def main():
    """Run exit strategy tests"""
    
    print("="*80)
    print("🎯 MULTI-TARGET EXIT SYSTEM TEST")
    print("="*80)
    print("\nObjective: Increase average win from 3.72% to 7-10%")
    print("Method: Test different exit strategies to capture larger moves")
    
    # Test on multiple symbols
    symbols = ["RELIANCE", "TCS", "INFY"]
    
    tester = MultiTargetTester()
    best_strategies = {}
    
    for symbol in symbols:
        print(f"\n{'='*80}")
        print(f"Testing {symbol}")
        print('='*80)
        
        best = tester.test_exit_strategies(symbol, days=90)
        best_strategies[symbol] = best
    
    # Summary
    print("\n" + "="*80)
    print("📋 SUMMARY RECOMMENDATIONS")
    print("="*80)
    
    for symbol, strategy in best_strategies.items():
        print(f"{symbol}: Use {strategy} exit strategy")
    
    # Overall recommendation
    strategy_counts = {}
    for strategy in best_strategies.values():
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
    
    most_common = max(strategy_counts, key=strategy_counts.get)
    print(f"\n🎯 OVERALL RECOMMENDATION: {most_common.upper()} exit strategy")
    print("This strategy performed best across multiple symbols")
    
    # Create visualization
    tester.plot_exit_comparison()


if __name__ == "__main__":
    main()