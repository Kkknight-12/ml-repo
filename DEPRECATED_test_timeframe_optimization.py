#!/usr/bin/env python3
"""
Test Timeframe-Optimized Configurations
========================================

Tests the Lorentzian Classification system with different timeframe-specific
optimizations to find the best parameters for each trading horizon.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Tuple

# Import configurations
from config.timeframe_configs import (
    TimeframeTradingConfig, 
    TimeframeOptimizedConfig,
    compare_timeframe_configs
)
from config.settings import TradingConfig

# Import backtesting framework
from backtest_framework import BacktestEngine, BacktestMetrics

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TimeframeOptimizationTester:
    """Test different timeframe configurations"""
    
    def __init__(self):
        # Set up access token
        if os.path.exists('.kite_session.json'):
            with open('.kite_session.json', 'r') as f:
                session_data = json.load(f)
                access_token = session_data.get('access_token')
                os.environ['KITE_ACCESS_TOKEN'] = access_token
        
        self.engine = BacktestEngine()
        self.results = {}
    
    def test_single_timeframe(
        self, 
        symbol: str, 
        timeframe: str,
        days: int = 90
    ) -> Dict[str, BacktestMetrics]:
        """Test all configurations for a single timeframe"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        print(f"\n🎯 Testing {timeframe} configurations on {symbol}")
        print(f"Period: {start_date.date()} to {end_date.date()}")
        print("="*60)
        
        results = {}
        
        # Test 1: Baseline (default Pine Script)
        print(f"\n1️⃣ Testing BASELINE...")
        try:
            baseline_config = TradingConfig()
            baseline_metrics = self.engine.run_backtest(
                symbol, start_date, end_date, baseline_config
            )
            results['baseline'] = baseline_metrics
            print(f"   ✅ Baseline: {baseline_metrics.total_trades} trades, "
                  f"{baseline_metrics.win_rate:.1f}% win rate, "
                  f"{baseline_metrics.average_win:.2f}% avg win")
        except Exception as e:
            logger.error(f"Baseline test failed: {e}")
        
        # Test 2: Timeframe-specific base config
        print(f"\n2️⃣ Testing {timeframe.upper()} BASE CONFIG...")
        try:
            tf_config = TimeframeTradingConfig(timeframe)
            tf_metrics = self.engine.run_backtest(
                symbol, start_date, end_date, tf_config
            )
            results[f'{timeframe}_base'] = tf_metrics
            print(f"   ✅ {timeframe} Base: {tf_metrics.total_trades} trades, "
                  f"{tf_metrics.win_rate:.1f}% win rate, "
                  f"{tf_metrics.average_win:.2f}% avg win")
        except Exception as e:
            logger.error(f"{timeframe} base test failed: {e}")
        
        # Test 3: Timeframe-specific optimized config
        print(f"\n3️⃣ Testing {timeframe.upper()} OPTIMIZED CONFIG...")
        try:
            tf_opt_config = TimeframeOptimizedConfig(timeframe)
            tf_opt_metrics = self.engine.run_backtest(
                symbol, start_date, end_date, tf_opt_config
            )
            results[f'{timeframe}_optimized'] = tf_opt_metrics
            print(f"   ✅ {timeframe} Optimized: {tf_opt_metrics.total_trades} trades, "
                  f"{tf_opt_metrics.win_rate:.1f}% win rate, "
                  f"{tf_opt_metrics.average_win:.2f}% avg win")
        except Exception as e:
            logger.error(f"{timeframe} optimized test failed: {e}")
        
        return results
    
    def test_all_timeframes(
        self, 
        symbol: str,
        timeframes: List[str] = None
    ) -> Dict[str, Dict[str, BacktestMetrics]]:
        """Test all timeframes for a symbol"""
        
        if timeframes is None:
            timeframes = ["1min", "5min", "15min", "30min", "60min", "daily"]
        
        all_results = {}
        
        # Map timeframes to appropriate test periods
        timeframe_days = {
            "1min": 7,      # 1 week for 1-minute
            "5min": 30,     # 1 month for 5-minute
            "15min": 60,    # 2 months for 15-minute
            "30min": 90,    # 3 months for 30-minute
            "60min": 180,   # 6 months for hourly
            "daily": 365    # 1 year for daily
        }
        
        for timeframe in timeframes:
            days = timeframe_days.get(timeframe, 90)
            print(f"\n{'='*80}")
            print(f"TESTING {timeframe.upper()} TIMEFRAME")
            print(f"{'='*80}")
            
            results = self.test_single_timeframe(symbol, timeframe, days)
            all_results[timeframe] = results
        
        return all_results
    
    def generate_comparison_report(
        self, 
        results: Dict[str, Dict[str, BacktestMetrics]]
    ):
        """Generate comprehensive comparison report"""
        
        print("\n" + "="*80)
        print("📊 TIMEFRAME OPTIMIZATION REPORT")
        print("="*80)
        
        # Prepare data for comparison
        comparison_data = []
        
        for timeframe, tf_results in results.items():
            for config_name, metrics in tf_results.items():
                comparison_data.append({
                    'Timeframe': timeframe,
                    'Config': config_name,
                    'Trades': metrics.total_trades,
                    'Win Rate %': metrics.win_rate,
                    'Avg Win %': metrics.average_win,
                    'Avg Loss %': abs(metrics.average_loss),
                    'Profit Factor': metrics.profit_factor,
                    'Total Return %': metrics.total_return,
                    'Sharpe': metrics.sharpe_ratio,
                    'Max DD %': metrics.max_drawdown
                })
        
        df = pd.DataFrame(comparison_data)
        
        # Best config by timeframe
        print("\n🏆 BEST CONFIGURATION BY TIMEFRAME:")
        print("-"*80)
        
        for timeframe in df['Timeframe'].unique():
            tf_data = df[df['Timeframe'] == timeframe]
            if not tf_data.empty:
                # Find best by total return
                best_idx = tf_data['Total Return %'].idxmax()
                best_row = tf_data.loc[best_idx]
                
                print(f"\n{timeframe.upper()}:")
                print(f"  Best Config: {best_row['Config']}")
                print(f"  Win Rate: {best_row['Win Rate %']:.1f}%")
                print(f"  Avg Win: {best_row['Avg Win %']:.2f}%")
                print(f"  Total Return: {best_row['Total Return %']:.2f}%")
                print(f"  Profit Factor: {best_row['Profit Factor']:.2f}")
        
        # Overall best
        print("\n🌟 OVERALL BEST CONFIGURATION:")
        print("-"*80)
        best_overall_idx = df['Total Return %'].idxmax()
        best_overall = df.loc[best_overall_idx]
        print(f"Timeframe: {best_overall['Timeframe']}")
        print(f"Config: {best_overall['Config']}")
        print(f"Total Return: {best_overall['Total Return %']:.2f}%")
        print(f"Win Rate: {best_overall['Win Rate %']:.1f}%")
        print(f"Avg Win: {best_overall['Avg Win %']:.2f}%")
        print(f"Sharpe Ratio: {best_overall['Sharpe']:.2f}")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"timeframe_optimization_results_{timestamp}.csv"
        df.to_csv(filename, index=False)
        print(f"\n💾 Detailed results saved to {filename}")
        
        return df
    
    def plot_timeframe_comparison(self, df: pd.DataFrame):
        """Create visualization comparing timeframes"""
        try:
            import matplotlib.pyplot as plt
            
            # Create figure with subplots
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Timeframe Configuration Comparison', fontsize=16)
            
            # Plot 1: Win Rate by Timeframe and Config
            ax = axes[0, 0]
            for config in df['Config'].unique():
                config_data = df[df['Config'] == config]
                ax.plot(config_data['Timeframe'], config_data['Win Rate %'], 
                       marker='o', label=config)
            ax.set_xlabel('Timeframe')
            ax.set_ylabel('Win Rate %')
            ax.set_title('Win Rate by Timeframe')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Plot 2: Average Win by Timeframe
            ax = axes[0, 1]
            for config in df['Config'].unique():
                config_data = df[df['Config'] == config]
                ax.plot(config_data['Timeframe'], config_data['Avg Win %'], 
                       marker='o', label=config)
            ax.set_xlabel('Timeframe')
            ax.set_ylabel('Average Win %')
            ax.set_title('Average Win Size by Timeframe')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Plot 3: Total Return by Timeframe
            ax = axes[1, 0]
            timeframes = df['Timeframe'].unique()
            x = np.arange(len(timeframes))
            width = 0.25
            
            configs = df['Config'].unique()
            for i, config in enumerate(configs):
                config_data = df[df['Config'] == config]
                returns = [config_data[config_data['Timeframe'] == tf]['Total Return %'].values[0] 
                          if len(config_data[config_data['Timeframe'] == tf]) > 0 else 0 
                          for tf in timeframes]
                ax.bar(x + i*width, returns, width, label=config)
            
            ax.set_xlabel('Timeframe')
            ax.set_ylabel('Total Return %')
            ax.set_title('Total Return by Timeframe and Config')
            ax.set_xticks(x + width)
            ax.set_xticklabels(timeframes)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Plot 4: Sharpe Ratio
            ax = axes[1, 1]
            for config in df['Config'].unique():
                config_data = df[df['Config'] == config]
                ax.plot(config_data['Timeframe'], config_data['Sharpe'], 
                       marker='o', label=config)
            ax.set_xlabel('Timeframe')
            ax.set_ylabel('Sharpe Ratio')
            ax.set_title('Risk-Adjusted Returns by Timeframe')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig('timeframe_comparison.png')
            plt.show()
            
        except ImportError:
            print("⚠️  Matplotlib not available for plotting")


def main():
    """Run timeframe optimization tests"""
    
    print("="*80)
    print("🕐 TIMEFRAME OPTIMIZATION TEST")
    print("="*80)
    print("\nObjective: Find optimal configurations for each trading timeframe")
    print("Method: Test baseline, timeframe-base, and timeframe-optimized configs")
    
    # First show the configuration comparison
    compare_timeframe_configs()
    
    # Initialize tester
    tester = TimeframeOptimizationTester()
    
    # Test on a single symbol for now
    symbol = "RELIANCE"
    
    # You can test specific timeframes or all
    # For demo, let's test just 5min and 15min to save time
    timeframes_to_test = ["5min", "15min"]  # Add more as needed
    
    # Run tests
    results = tester.test_all_timeframes(symbol, timeframes_to_test)
    
    # Generate report
    df = tester.generate_comparison_report(results)
    
    # Create visualization
    tester.plot_timeframe_comparison(df)
    
    # Recommendations
    print("\n" + "="*80)
    print("📋 RECOMMENDATIONS")
    print("="*80)
    print("\n1. Use timeframe-specific configurations for better performance")
    print("2. Shorter timeframes (1min, 5min) benefit from:")
    print("   - Fewer neighbors (5-6) for faster response")
    print("   - Tighter stops (0.3-0.8x ATR)")
    print("   - Lower confidence thresholds")
    print("\n3. Longer timeframes (30min, 60min, daily) benefit from:")
    print("   - More neighbors (10-15) for stability")
    print("   - Wider stops (1.2-1.5x ATR)")
    print("   - Higher confidence thresholds")
    print("   - Trailing stops to capture trends")
    
    print("\n✅ Test complete! Check the generated files for detailed results.")


if __name__ == "__main__":
    main()