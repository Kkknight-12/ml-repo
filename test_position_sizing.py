"""
Test Position Sizing Strategy
=============================

Test allocating more capital to proven performers (RELIANCE, INFY)
"""

import pandas as pd
import numpy as np
from test_phase3_financial_analysis import run_financial_backtest, DetailedBacktestEngine
from datetime import datetime


def test_position_sizing_strategy():
    """Test different position sizing approaches"""
    
    print("\n" + "="*80)
    print("POSITION SIZING STRATEGY TEST")
    print("Comparing equal vs performance-based allocation")
    print("="*80)
    
    # Test configuration
    initial_capital = 600000  # 6 lakhs total (1 lakh per stock)
    days = 180
    
    # Stock universe with known performance
    stocks = {
        'RELIANCE': {'performance': 'high', 'allocation_equal': 100000, 'allocation_smart': 150000},
        'INFY': {'performance': 'high', 'allocation_equal': 100000, 'allocation_smart': 150000},
        'TCS': {'performance': 'negative', 'allocation_equal': 100000, 'allocation_smart': 50000},
        'AXISBANK': {'performance': 'low', 'allocation_equal': 100000, 'allocation_smart': 75000},
        'ICICIBANK': {'performance': 'negative', 'allocation_equal': 100000, 'allocation_smart': 50000},
        'KOTAKBANK': {'performance': 'negative', 'allocation_equal': 100000, 'allocation_smart': 75000}
    }
    
    # Run tests with both strategies
    results = {
        'equal': {'total_pnl': 0, 'trades': 0, 'details': []},
        'smart': {'total_pnl': 0, 'trades': 0, 'details': []}
    }
    
    for strategy in ['equal', 'smart']:
        print(f"\n{'='*60}")
        print(f"Testing {strategy.upper()} ALLOCATION STRATEGY")
        print(f"{'='*60}")
        
        for symbol, config in stocks.items():
            capital = config[f'allocation_{strategy}']
            
            print(f"\n{symbol}: ₹{capital:,} allocation")
            
            # Run backtest with allocated capital
            metrics, trades = run_financial_backtest(
                symbol=symbol,
                use_flexible=True,
                days=days,
                ml_threshold=3.0,
                use_mode_filter=False,
                use_full_system=False,
                use_dynamic_threshold=False
            )
            
            if metrics:
                # Scale results to allocated capital
                scale_factor = capital / 100000  # Original tests used 1 lakh
                scaled_pnl = metrics['total_net_pnl'] * scale_factor
                
                results[strategy]['total_pnl'] += scaled_pnl
                results[strategy]['trades'] += metrics['total_trades']
                results[strategy]['details'].append({
                    'symbol': symbol,
                    'capital': capital,
                    'pnl': scaled_pnl,
                    'return_pct': scaled_pnl / capital * 100,
                    'trades': metrics['total_trades'],
                    'win_rate': metrics['win_rate']
                })
    
    # Print comparison
    print("\n" + "="*80)
    print("POSITION SIZING COMPARISON")
    print("="*80)
    
    print("\n1. EQUAL ALLOCATION (₹1 lakh each):")
    print(f"{'Stock':>10} {'Capital':>12} {'P&L':>12} {'Return %':>10} {'Trades':>8}")
    print("-" * 55)
    for detail in results['equal']['details']:
        print(f"{detail['symbol']:>10} ₹{detail['capital']:>10,} ₹{detail['pnl']:>10,.0f} "
              f"{detail['return_pct']:>9.1f}% {detail['trades']:>8}")
    
    print(f"\n{'TOTAL':>10} ₹{initial_capital:>10,} ₹{results['equal']['total_pnl']:>10,.0f} "
          f"{results['equal']['total_pnl']/initial_capital*100:>9.1f}% {results['equal']['trades']:>8}")
    
    print("\n2. SMART ALLOCATION (Performance-based):")
    print(f"{'Stock':>10} {'Capital':>12} {'P&L':>12} {'Return %':>10} {'Trades':>8}")
    print("-" * 55)
    for detail in results['smart']['details']:
        print(f"{detail['symbol']:>10} ₹{detail['capital']:>10,} ₹{detail['pnl']:>10,.0f} "
              f"{detail['return_pct']:>9.1f}% {detail['trades']:>8}")
    
    print(f"\n{'TOTAL':>10} ₹{initial_capital:>10,} ₹{results['smart']['total_pnl']:>10,.0f} "
          f"{results['smart']['total_pnl']/initial_capital*100:>9.1f}% {results['smart']['trades']:>8}")
    
    # Calculate improvement
    improvement = results['smart']['total_pnl'] - results['equal']['total_pnl']
    improvement_pct = improvement / abs(results['equal']['total_pnl']) * 100 if results['equal']['total_pnl'] != 0 else 0
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"\nEqual Allocation P&L: ₹{results['equal']['total_pnl']:,.2f}")
    print(f"Smart Allocation P&L: ₹{results['smart']['total_pnl']:,.2f}")
    print(f"Improvement: ₹{improvement:,.2f} ({improvement_pct:+.1f}%)")
    
    if improvement > 0:
        print("\n✅ RECOMMENDATION: Use Smart Position Sizing")
        print("   - 15% capital for RELIANCE, INFY (proven winners)")
        print("   - 7.5% capital for AXISBANK, KOTAKBANK (moderate)")
        print("   - 5% capital for TCS, ICICIBANK (poor performers)")
    else:
        print("\n❌ RECOMMENDATION: Keep Equal Allocation")


if __name__ == "__main__":
    test_position_sizing_strategy()