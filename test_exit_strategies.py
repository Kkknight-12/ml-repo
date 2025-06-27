#!/usr/bin/env python3
"""
Test Different Exit Strategies for Lorentzian Classifier
========================================================

This script tests various exit strategies to find the optimal approach
for improving returns on 5-minute timeframe trading.
"""

import sys
import os
sys.path.append('.')

from test_multi_stock_optimization import MultiStockOptimizer
from scanner.smart_exit_manager import SmartExitManager
import json


def test_exit_configurations():
    """Test different exit strategy configurations"""
    
    print("\n" + "="*60)
    print("TESTING MULTIPLE EXIT STRATEGY CONFIGURATIONS")
    print("="*60)
    
    # Define test stocks
    test_stocks = ['RELIANCE', 'INFY', 'AXISBANK', 'ITC', 'TCS']
    
    # Define exit configurations to test
    exit_configs = [
        {
            'name': 'Baseline (No Exits)',
            'use_smart_exits': False,
            'config': {}
        },
        {
            'name': 'Conservative (0.3% SL, 0.15-0.35% TP)',
            'use_smart_exits': True,
            'config': {
                'stop_loss_percent': 0.3,
                'take_profit_targets': [0.15, 0.25, 0.35],
                'use_trailing_stop': True,
                'trailing_activation': 0.15,
                'max_holding_bars': 15
            }
        },
        {
            'name': 'Balanced (0.5% SL, 0.3-0.7% TP)',
            'use_smart_exits': True,
            'config': {
                'stop_loss_percent': 0.5,
                'take_profit_targets': [0.3, 0.5, 0.7],
                'use_trailing_stop': True,
                'trailing_activation': 0.3,
                'max_holding_bars': 20
            }
        },
        {
            'name': 'Aggressive (0.75% SL, 0.5-1.5% TP)',
            'use_smart_exits': True,
            'config': {
                'stop_loss_percent': 0.75,
                'take_profit_targets': [0.5, 1.0, 1.5],
                'use_trailing_stop': True,
                'trailing_activation': 0.5,
                'max_holding_bars': 30
            }
        },
        {
            'name': 'Quick Scalp (0.2% SL, 0.1-0.3% TP)',
            'use_smart_exits': True,
            'config': {
                'stop_loss_percent': 0.2,
                'take_profit_targets': [0.1, 0.2, 0.3],
                'target_sizes': [60, 30, 10],  # Take most profit quickly
                'use_trailing_stop': False,
                'max_holding_bars': 10
            }
        },
        {
            'name': 'Risk 1:2 (0.5% SL, 1.0% TP)',
            'use_smart_exits': True,
            'config': {
                'stop_loss_percent': 0.5,
                'take_profit_targets': [1.0],  # Single target
                'target_sizes': [100],  # Exit full position
                'use_trailing_stop': False,
                'max_holding_bars': 25
            }
        }
    ]
    
    results = []
    
    for exit_config in exit_configs:
        print(f"\n{'='*60}")
        print(f"Testing: {exit_config['name']}")
        print(f"{'='*60}")
        
        # Initialize optimizer with custom exit config
        optimizer = MultiStockOptimizer(
            symbols=test_stocks,
            timeframe='5minute',
            lookback_days=180
        )
        
        # Update exit config if using smart exits
        if exit_config['use_smart_exits']:
            # Inject custom exit config into adaptive configs
            for symbol in test_stocks:
                if hasattr(optimizer, 'config'):
                    optimizer.config.update(exit_config['config'])
        
        # Run test
        test_results = optimizer.run_baseline_test(
            use_ml_filter=True,
            use_smart_exits=exit_config['use_smart_exits']
        )
        
        # Store results
        result_summary = {
            'strategy': exit_config['name'],
            'total_return': test_results['total_return'],
            'win_rate': test_results['overall_win_rate'],
            'total_trades': test_results['total_trades'],
            'avg_return_per_stock': test_results['avg_return_per_stock']
        }
        results.append(result_summary)
        
        # Print summary
        print(f"\nResults for {exit_config['name']}:")
        print(f"  Total Return: {test_results['total_return']:.2f}%")
        print(f"  Win Rate: {test_results['overall_win_rate']:.1f}%")
        print(f"  Total Trades: {test_results['total_trades']}")
    
    # Compare all results
    print("\n" + "="*60)
    print("EXIT STRATEGY COMPARISON SUMMARY")
    print("="*60)
    print(f"{'Strategy':<40} {'Return':<10} {'Win Rate':<10} {'Trades':<10}")
    print("-"*70)
    
    for result in results:
        print(f"{result['strategy']:<40} {result['total_return']:>8.2f}% {result['win_rate']:>8.1f}% {result['total_trades']:>8}")
    
    # Find best strategy
    best_result = max(results, key=lambda x: x['total_return'])
    print(f"\n🏆 Best Strategy: {best_result['strategy']}")
    print(f"   Return: {best_result['total_return']:.2f}%")
    print(f"   Win Rate: {best_result['win_rate']:.1f}%")
    
    # Save results
    with open('exit_strategy_comparison.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\n💾 Results saved to exit_strategy_comparison.json")


if __name__ == "__main__":
    test_exit_configurations()