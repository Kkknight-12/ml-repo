#!/usr/bin/env python3
"""
Test ML-Optimized Configuration
================================

Verify that the ML-optimized configuration achieves:
- 50%+ win rate (from 44.7%)
- 2:1+ risk/reward (from 1.15)
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import json

from backtest_framework_enhanced import EnhancedBacktestEngine
from config.settings import TradingConfig
from config.ml_optimized_settings import MLOptimizedTradingConfig, CONSERVATIVE_ML_CONFIG, AGGRESSIVE_ML_CONFIG
from config.fixed_optimized_settings import FixedOptimizedTradingConfig

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def test_configurations():
    """Test different configurations and compare results"""
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    engine = EnhancedBacktestEngine()
    
    print("="*80)
    print("🧪 TESTING ML-OPTIMIZED CONFIGURATIONS")
    print("="*80)
    print(f"\nSymbol: {symbol}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    
    # Configurations to test
    configs = [
        ("1. BASELINE (Original)", TradingConfig()),
        ("2. BASELINE + Dynamic Exits", create_dynamic_config()),
        ("3. ML-OPTIMIZED (Balanced)", MLOptimizedTradingConfig()),
        ("4. ML-OPTIMIZED (Conservative)", CONSERVATIVE_ML_CONFIG),
        ("5. ML-OPTIMIZED (Aggressive)", AGGRESSIVE_ML_CONFIG),
        ("6. FIXED OPTIMIZED (Original)", FixedOptimizedTradingConfig())
    ]
    
    results = {}
    
    for name, config in configs:
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"{'='*60}")
        
        if hasattr(config, 'ml_prediction_threshold'):
            print(f"ML Threshold: {config.ml_prediction_threshold}")
        
        if hasattr(config, 'target_1_ratio'):
            print(f"Targets: {config.target_1_ratio}R@{int(config.target_1_percent*100)}% + "
                  f"{config.target_2_ratio}R@{int(config.target_2_percent*100)}%")
        
        try:
            metrics = engine.run_backtest(
                symbol, start_date, end_date, config
            )
            
            # Calculate risk/reward
            risk_reward = abs(metrics.average_win / metrics.average_loss) if metrics.average_loss != 0 else 0
            
            results[name] = {
                'trades': metrics.total_trades,
                'win_rate': metrics.win_rate,
                'avg_win': metrics.average_win,
                'avg_loss': metrics.average_loss,
                'risk_reward': risk_reward,
                'profit_factor': metrics.profit_factor,
                'total_return': metrics.total_return,
                'max_drawdown': metrics.max_drawdown,
                'sharpe': metrics.sharpe_ratio
            }
            
            print(f"\nResults:")
            print(f"  Trades: {metrics.total_trades}")
            print(f"  Win Rate: {metrics.win_rate:.1f}%")
            print(f"  Avg Win: {metrics.average_win:.2f}%")
            print(f"  Avg Loss: {metrics.average_loss:.2f}%")
            print(f"  Risk/Reward: {risk_reward:.2f}")
            print(f"  Total Return: {metrics.total_return:.2f}%")
            
        except Exception as e:
            print(f"  Error: {e}")
            results[name] = None
    
    # Print comparison table
    print("\n" + "="*120)
    print("📊 PERFORMANCE COMPARISON")
    print("="*120)
    
    print(f"\n{'Configuration':<30} {'Trades':<8} {'Win%':<8} {'Avg Win':<10} {'Avg Loss':<10} "
          f"{'R/R':<8} {'PF':<8} {'Return%':<10} {'Sharpe':<8}")
    print("-"*120)
    
    for name, metrics in results.items():
        if metrics:
            print(f"{name:<30} {metrics['trades']:<8} {metrics['win_rate']:<8.1f} "
                  f"{metrics['avg_win']:<10.2f} {metrics['avg_loss']:<10.2f} "
                  f"{metrics['risk_reward']:<8.2f} {metrics['profit_factor']:<8.2f} "
                  f"{metrics['total_return']:<10.2f} {metrics['sharpe']:<8.2f}")
    
    # Analyze improvements
    print("\n" + "="*80)
    print("📈 IMPROVEMENT ANALYSIS")
    print("="*80)
    
    baseline = results.get("1. BASELINE (Original)")
    ml_optimized = results.get("3. ML-OPTIMIZED (Balanced)")
    
    if baseline and ml_optimized:
        print(f"\nBaseline → ML-Optimized:")
        print(f"  Win Rate: {baseline['win_rate']:.1f}% → {ml_optimized['win_rate']:.1f}% "
              f"({'✅' if ml_optimized['win_rate'] >= 50 else '❌'})")
        print(f"  Risk/Reward: {baseline['risk_reward']:.2f} → {ml_optimized['risk_reward']:.2f} "
              f"({'✅' if ml_optimized['risk_reward'] >= 2.0 else '⚠️'})")
        print(f"  Total Return: {baseline['total_return']:.2f}% → {ml_optimized['total_return']:.2f}%")
        
        # Calculate percentage improvements
        wr_improvement = ((ml_optimized['win_rate'] / baseline['win_rate']) - 1) * 100
        rr_improvement = ((ml_optimized['risk_reward'] / baseline['risk_reward']) - 1) * 100
        
        print(f"\nImprovements:")
        print(f"  Win Rate: +{wr_improvement:.1f}%")
        print(f"  Risk/Reward: +{rr_improvement:.1f}%")
    
    # Recommendations
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS")
    print("="*80)
    
    # Find best config by different metrics
    best_wr = max(results.items(), key=lambda x: x[1]['win_rate'] if x[1] else 0)
    best_rr = max(results.items(), key=lambda x: x[1]['risk_reward'] if x[1] else 0)
    best_return = max(results.items(), key=lambda x: x[1]['total_return'] if x[1] else -999)
    
    print(f"\nBest by Win Rate: {best_wr[0]} ({best_wr[1]['win_rate']:.1f}%)")
    print(f"Best by Risk/Reward: {best_rr[0]} ({best_rr[1]['risk_reward']:.2f})")
    print(f"Best by Total Return: {best_return[0]} ({best_return[1]['total_return']:.2f}%)")
    
    # Check if goals achieved
    print("\n🎯 GOALS ACHIEVED?")
    
    goals_config = ml_optimized if ml_optimized else None
    if goals_config:
        if goals_config['win_rate'] >= 50 and goals_config['risk_reward'] >= 2.0:
            print("✅ YES! Both 50%+ win rate and 2:1+ risk/reward achieved!")
        else:
            if goals_config['win_rate'] >= 50:
                print("✅ Win rate goal (50%+) achieved")
            else:
                print(f"❌ Win rate goal not met ({goals_config['win_rate']:.1f}% < 50%)")
            
            if goals_config['risk_reward'] >= 2.0:
                print("✅ Risk/reward goal (2:1+) achieved")
            else:
                print(f"⚠️  Risk/reward close but not quite there ({goals_config['risk_reward']:.2f} < 2.0)")


def create_dynamic_config():
    """Create baseline config with dynamic exits"""
    config = TradingConfig()
    config.use_dynamic_exits = True
    return config


if __name__ == "__main__":
    test_configurations()