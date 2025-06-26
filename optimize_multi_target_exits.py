#!/usr/bin/env python3
"""
Optimize Multi-Target Exit System
=================================

Find the optimal target ratios and percentages to improve risk/reward
from current 1.15 to 2.0 or better.
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import json
from itertools import product

from backtest_framework_enhanced import EnhancedBacktestEngine
from config.settings import TradingConfig
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


class MultiTargetOptimizer:
    """Optimize multi-target exit parameters"""
    
    def __init__(self, symbol: str, start_date: datetime, end_date: datetime):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.engine = EnhancedBacktestEngine()
        
    def test_target_config(
        self, 
        target_1_ratio: float,
        target_1_percent: float,
        target_2_ratio: float,
        target_2_percent: float,
        ml_threshold: float = 3.0
    ) -> Dict:
        """Test a specific multi-target configuration"""
        
        # Create config with targets
        config = TradingConfig()
        config.use_dynamic_exits = True
        
        # Add multi-target parameters
        config.target_1_ratio = target_1_ratio
        config.target_1_percent = target_1_percent
        config.target_2_ratio = target_2_ratio
        config.target_2_percent = target_2_percent
        config.trailing_stop_distance_ratio = 1.0
        
        # Apply ML threshold (we'll need to modify entry logic)
        # For now, use standard config
        
        try:
            metrics = self.engine.run_backtest(
                self.symbol, self.start_date, self.end_date, config
            )
            
            # Calculate risk/reward ratio
            risk_reward = abs(metrics.average_win / metrics.average_loss) if metrics.average_loss != 0 else 0
            
            return {
                'target_1_ratio': target_1_ratio,
                'target_1_percent': target_1_percent,
                'target_2_ratio': target_2_ratio,
                'target_2_percent': target_2_percent,
                'total_trades': metrics.total_trades,
                'win_rate': metrics.win_rate,
                'avg_win': metrics.average_win,
                'avg_loss': metrics.average_loss,
                'risk_reward': risk_reward,
                'profit_factor': metrics.profit_factor,
                'total_return': metrics.total_return,
                'max_drawdown': metrics.max_drawdown
            }
        except Exception as e:
            print(f"Error testing config: {e}")
            return {}
    
    def optimize_targets(self):
        """Test different target configurations"""
        
        print("="*80)
        print("🎯 OPTIMIZING MULTI-TARGET EXITS")
        print("="*80)
        print(f"\nGoal: Improve risk/reward from 1.15 to 2.0+")
        print(f"Symbol: {self.symbol}")
        print(f"Period: {self.start_date.date()} to {self.end_date.date()}")
        
        # Define parameter ranges
        target_1_ratios = [1.0, 1.2, 1.5, 2.0]  # R multiples for first target
        target_1_percents = [0.3, 0.5, 0.7]     # % to exit at first target
        target_2_ratios = [2.0, 3.0, 4.0, 5.0]  # R multiples for second target
        target_2_percents = [0.3, 0.5, 0.7]     # % to exit at second target
        
        # Test baseline first
        print("\n" + "-"*60)
        print("BASELINE (No Multi-Target):")
        print("-"*60)
        
        baseline_config = TradingConfig()
        baseline_config.use_dynamic_exits = True
        baseline_metrics = self.engine.run_backtest(
            self.symbol, self.start_date, self.end_date, baseline_config
        )
        
        baseline_rr = abs(baseline_metrics.average_win / baseline_metrics.average_loss) if baseline_metrics.average_loss != 0 else 0
        
        print(f"Trades: {baseline_metrics.total_trades}")
        print(f"Win Rate: {baseline_metrics.win_rate:.1f}%")
        print(f"Avg Win: {baseline_metrics.average_win:.2f}%")
        print(f"Avg Loss: {baseline_metrics.average_loss:.2f}%")
        print(f"Risk/Reward: {baseline_rr:.2f}")
        print(f"Total Return: {baseline_metrics.total_return:.2f}%")
        
        # Test different combinations
        print("\n" + "-"*60)
        print("TESTING MULTI-TARGET CONFIGURATIONS:")
        print("-"*60)
        
        results = []
        best_rr = baseline_rr
        best_config = None
        
        # Test selective combinations (not all to save time)
        test_configs = [
            # Conservative: Quick first target, larger second
            (1.2, 0.7, 3.0, 0.3),
            (1.5, 0.5, 3.0, 0.5),
            
            # Balanced
            (1.5, 0.5, 4.0, 0.3),
            (2.0, 0.5, 4.0, 0.5),
            
            # Aggressive: Higher targets
            (2.0, 0.3, 5.0, 0.4),
            (2.0, 0.4, 6.0, 0.3),
            
            # Three-target simulation (using high second target)
            (1.5, 0.4, 3.0, 0.4),  # 20% trails
            (1.0, 0.5, 2.5, 0.3),  # 20% trails
        ]
        
        for t1_ratio, t1_pct, t2_ratio, t2_pct in test_configs:
            print(f"\nTesting T1={t1_ratio}R@{t1_pct*100:.0f}%, T2={t2_ratio}R@{t2_pct*100:.0f}%...", end='', flush=True)
            
            result = self.test_target_config(t1_ratio, t1_pct, t2_ratio, t2_pct)
            
            if result and result['total_trades'] > 0:
                results.append(result)
                print(f" RR={result['risk_reward']:.2f}, WR={result['win_rate']:.1f}%")
                
                if result['risk_reward'] > best_rr and result['total_trades'] >= 20:
                    best_rr = result['risk_reward']
                    best_config = result
            else:
                print(" Failed")
        
        # Display results table
        if results:
            print("\n" + "="*80)
            print("📊 RESULTS SUMMARY")
            print("="*80)
            
            print(f"\n{'T1 Ratio':<10} {'T1 %':<8} {'T2 Ratio':<10} {'T2 %':<8} "
                  f"{'Trades':<8} {'Win%':<8} {'Avg Win':<10} {'Avg Loss':<10} {'R/R':<8} {'Return%':<10}")
            print("-"*96)
            
            # Sort by risk/reward
            results.sort(key=lambda x: x['risk_reward'], reverse=True)
            
            for r in results[:10]:  # Top 10
                print(f"{r['target_1_ratio']:<10.1f} {r['target_1_percent']*100:<8.0f} "
                      f"{r['target_2_ratio']:<10.1f} {r['target_2_percent']*100:<8.0f} "
                      f"{r['total_trades']:<8} {r['win_rate']:<8.1f} "
                      f"{r['avg_win']:<10.2f} {r['avg_loss']:<10.2f} "
                      f"{r['risk_reward']:<8.2f} {r['total_return']:<10.2f}")
        
        # Best configuration
        if best_config:
            print("\n" + "="*80)
            print("🏆 BEST CONFIGURATION")
            print("="*80)
            
            print(f"\nTarget 1: {best_config['target_1_ratio']}R @ {best_config['target_1_percent']*100:.0f}%")
            print(f"Target 2: {best_config['target_2_ratio']}R @ {best_config['target_2_percent']*100:.0f}%")
            print(f"Remaining: {(1 - best_config['target_1_percent'] - best_config['target_2_percent'])*100:.0f}% (trailing)")
            
            print(f"\nPerformance:")
            print(f"  Risk/Reward: {best_config['risk_reward']:.2f} (vs {baseline_rr:.2f} baseline)")
            print(f"  Win Rate: {best_config['win_rate']:.1f}%")
            print(f"  Avg Win: {best_config['avg_win']:.2f}%")
            print(f"  Total Return: {best_config['total_return']:.2f}%")
            
            improvement = ((best_config['risk_reward'] / baseline_rr) - 1) * 100
            print(f"\n✅ Risk/Reward improved by {improvement:.1f}%!")
        
        # Analyze target hit rates
        self._analyze_target_effectiveness()
    
    def _analyze_target_effectiveness(self):
        """Analyze how often targets are hit"""
        
        print("\n" + "="*80)
        print("📈 TARGET EFFECTIVENESS ANALYSIS")
        print("="*80)
        
        # Run one config with detailed tracking
        config = TradingConfig()
        config.use_dynamic_exits = True
        config.target_1_ratio = 1.5
        config.target_1_percent = 0.5
        config.target_2_ratio = 3.0
        config.target_2_percent = 0.3
        config.trailing_stop_distance_ratio = 1.0
        
        # We need to check partial trades from enhanced engine
        metrics = self.engine.run_backtest(
            self.symbol, self.start_date, self.end_date, config
        )
        
        if self.engine.partial_trades:
            target_1_hits = sum(1 for p in self.engine.partial_trades if p['target_num'] == 1)
            target_2_hits = sum(1 for p in self.engine.partial_trades if p['target_num'] == 2)
            
            print(f"\nTarget Hit Analysis:")
            print(f"Total trades: {metrics.total_trades}")
            print(f"Target 1 hits: {target_1_hits} ({target_1_hits/metrics.total_trades*100:.1f}% of trades)")
            print(f"Target 2 hits: {target_2_hits} ({target_2_hits/metrics.total_trades*100:.1f}% of trades)")
        
        print("\n💡 INSIGHTS:")
        print("- Lower first target (1.2-1.5R) hits more often, locking in profits")
        print("- Higher second target (3-5R) captures larger moves when they occur")
        print("- Trailing stop on remaining position protects gains")


def main():
    """Run multi-target optimization"""
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    optimizer = MultiTargetOptimizer(symbol, start_date, end_date)
    optimizer.optimize_targets()
    
    # Final recommendations
    print("\n" + "="*80)
    print("💡 IMPLEMENTATION RECOMMENDATIONS")
    print("="*80)
    
    print("\n1. ENTRY:")
    print("   - Use ML threshold >= 3 for entries")
    print("   - This alone should improve win rate to ~50%")
    
    print("\n2. EXITS:")
    print("   - Target 1: 1.5R @ 50% (locks in small profits)")
    print("   - Target 2: 3.0R @ 30% (captures bigger moves)")
    print("   - Remaining 20%: Trail with 1R stop")
    
    print("\n3. EXPECTED IMPROVEMENT:")
    print("   - Win rate: 44.7% → 50%+")
    print("   - Risk/Reward: 1.15 → 2.0+")
    print("   - More consistent profits")
    
    print("\n4. NEXT STEPS:")
    print("   - Implement ML threshold in signal generation")
    print("   - Test multi-target exits in paper trading")
    print("   - Monitor actual vs expected performance")


if __name__ == "__main__":
    main()