"""
Analyze Position Sizing Strategy Based on Known Results
=======================================================

Using the 180-day results we already have to calculate optimal position sizing
"""

import numpy as np
import pandas as pd


def analyze_position_sizing():
    """Analyze position sizing based on known 180-day results"""
    
    # Known results from 180-day test (Flexible ML)
    stock_results = {
        'RELIANCE': {'pnl': 26719.85, 'return_pct': 26.72, 'trades': 9, 'win_rate': 77.8},
        'INFY': {'pnl': 21184.48, 'return_pct': 21.18, 'trades': 12, 'win_rate': 58.3},
        'TCS': {'pnl': -3436.84, 'return_pct': -3.44, 'trades': 15, 'win_rate': 40.0},
        'AXISBANK': {'pnl': 1292.62, 'return_pct': 1.29, 'trades': 19, 'win_rate': 52.6},
        'ICICIBANK': {'pnl': -5189.09, 'return_pct': -5.19, 'trades': 11, 'win_rate': 36.4},
        'KOTAKBANK': {'pnl': -1206.81, 'return_pct': -1.21, 'trades': 13, 'win_rate': 53.8}
    }
    
    # Total capital
    total_capital = 600000  # 6 lakhs
    
    print("\n" + "="*80)
    print("POSITION SIZING ANALYSIS")
    print("Based on 180-day performance data")
    print("="*80)
    
    # Strategy 1: Equal Allocation
    print("\n1. EQUAL ALLOCATION STRATEGY")
    print("-" * 40)
    equal_allocation = total_capital / 6  # 1 lakh each
    equal_total_pnl = 0
    
    print(f"{'Stock':>12} {'Capital':>12} {'Expected P&L':>15} {'Return %':>10}")
    print("-" * 50)
    
    for stock, results in stock_results.items():
        expected_pnl = results['pnl']  # Already based on 1 lakh
        equal_total_pnl += expected_pnl
        print(f"{stock:>12} ₹{equal_allocation:>10,.0f} ₹{expected_pnl:>13,.2f} {results['return_pct']:>9.2f}%")
    
    print(f"\n{'TOTAL':>12} ₹{total_capital:>10,.0f} ₹{equal_total_pnl:>13,.2f} {equal_total_pnl/total_capital*100:>9.2f}%")
    
    # Strategy 2: Performance-Based Allocation
    print("\n\n2. PERFORMANCE-BASED ALLOCATION STRATEGY")
    print("-" * 40)
    
    # Calculate allocation weights based on performance
    # Method: Allocate proportionally to positive returns, minimum allocation for negative
    allocations = {}
    
    # Categorize stocks
    high_performers = ['RELIANCE', 'INFY']  # > 20% return
    moderate_performers = ['AXISBANK']  # 0-5% return
    poor_performers = ['TCS', 'ICICIBANK', 'KOTAKBANK']  # < 0% return
    
    # Allocation percentages
    allocation_pcts = {
        'high': 0.25,  # 25% each for high performers (50% total)
        'moderate': 0.15,  # 15% for moderate (15% total)
        'poor': 0.1167  # ~11.67% each for poor (35% total)
    }
    
    # Assign allocations
    for stock in high_performers:
        allocations[stock] = total_capital * allocation_pcts['high']
    for stock in moderate_performers:
        allocations[stock] = total_capital * allocation_pcts['moderate']
    for stock in poor_performers:
        allocations[stock] = total_capital * allocation_pcts['poor']
    
    # Calculate expected returns
    smart_total_pnl = 0
    
    print(f"{'Stock':>12} {'Capital':>12} {'Expected P&L':>15} {'Return %':>10}")
    print("-" * 50)
    
    for stock, capital in allocations.items():
        # Scale P&L based on allocation
        scale_factor = capital / 100000  # Original results based on 1 lakh
        expected_pnl = stock_results[stock]['pnl'] * scale_factor
        smart_total_pnl += expected_pnl
        print(f"{stock:>12} ₹{capital:>10,.0f} ₹{expected_pnl:>13,.2f} {expected_pnl/capital*100:>9.2f}%")
    
    print(f"\n{'TOTAL':>12} ₹{total_capital:>10,.0f} ₹{smart_total_pnl:>13,.2f} {smart_total_pnl/total_capital*100:>9.2f}%")
    
    # Strategy 3: Kelly Criterion-Based
    print("\n\n3. KELLY CRITERION-BASED ALLOCATION")
    print("-" * 40)
    print("(Simplified Kelly: f = (p*b - q)/b where p=win_rate, q=loss_rate, b=avg_win/avg_loss)")
    
    kelly_allocations = {}
    kelly_total = 0
    
    # Calculate Kelly fraction for each stock
    for stock, results in stock_results.items():
        win_rate = results['win_rate'] / 100
        loss_rate = 1 - win_rate
        
        # Estimate avg win/loss ratio from return percentage
        if results['return_pct'] > 0:
            # Positive expectancy
            avg_win_loss_ratio = 1.5  # Conservative estimate
            kelly_fraction = (win_rate * avg_win_loss_ratio - loss_rate) / avg_win_loss_ratio
        else:
            # Negative expectancy - minimum allocation
            kelly_fraction = 0.05  # 5% minimum
        
        # Cap Kelly fraction at 25% for safety
        kelly_fraction = min(max(kelly_fraction, 0.05), 0.25)
        kelly_allocations[stock] = kelly_fraction
        kelly_total += kelly_fraction
    
    # Normalize to sum to 100%
    for stock in kelly_allocations:
        kelly_allocations[stock] = kelly_allocations[stock] / kelly_total
    
    # Calculate expected returns
    kelly_total_pnl = 0
    
    print(f"{'Stock':>12} {'Kelly %':>10} {'Capital':>12} {'Expected P&L':>15} {'Return %':>10}")
    print("-" * 65)
    
    for stock, kelly_pct in kelly_allocations.items():
        capital = total_capital * kelly_pct
        scale_factor = capital / 100000
        expected_pnl = stock_results[stock]['pnl'] * scale_factor
        kelly_total_pnl += expected_pnl
        print(f"{stock:>12} {kelly_pct*100:>9.1f}% ₹{capital:>10,.0f} ₹{expected_pnl:>13,.2f} {expected_pnl/capital*100:>9.2f}%")
    
    print(f"\n{'TOTAL':>12} {'100.0':>9}% ₹{total_capital:>10,.0f} ₹{kelly_total_pnl:>13,.2f} {kelly_total_pnl/total_capital*100:>9.2f}%")
    
    # Comparison Summary
    print("\n\n" + "="*80)
    print("STRATEGY COMPARISON SUMMARY")
    print("="*80)
    
    strategies = [
        ('Equal Allocation', equal_total_pnl),
        ('Performance-Based', smart_total_pnl),
        ('Kelly Criterion', kelly_total_pnl)
    ]
    
    strategies.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n{'Strategy':>20} {'Total P&L':>15} {'Return %':>10} {'vs Equal':>15}")
    print("-" * 60)
    
    for strategy, pnl in strategies:
        return_pct = pnl / total_capital * 100
        vs_equal = pnl - equal_total_pnl
        print(f"{strategy:>20} ₹{pnl:>13,.2f} {return_pct:>9.2f}% ₹{vs_equal:>13,.2f}")
    
    # Recommendation
    best_strategy = strategies[0]
    print(f"\n✅ RECOMMENDATION: Use {best_strategy[0]}")
    print(f"   Expected improvement: ₹{best_strategy[1] - equal_total_pnl:,.2f}")
    
    # Practical allocation table
    if best_strategy[0] == 'Performance-Based':
        print("\n📊 RECOMMENDED ALLOCATION:")
        print(f"{'Stock':>12} {'Allocation':>12} {'Amount':>12}")
        print("-" * 40)
        for stock, capital in sorted(allocations.items(), key=lambda x: x[1], reverse=True):
            print(f"{stock:>12} {capital/total_capital*100:>10.1f}% ₹{capital:>10,.0f}")


if __name__ == "__main__":
    analyze_position_sizing()