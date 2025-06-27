"""
Debug calculation issues in the trading system
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict

def test_compound_returns():
    """Test compound return calculation with known values"""
    print("="*60)
    print("TESTING COMPOUND RETURN CALCULATION")
    print("="*60)
    
    # Test case 1: Simple trades
    trades = [
        {'pnl_pct': 2.0},    # +2%
        {'pnl_pct': -1.0},   # -1%
        {'pnl_pct': 3.0},    # +3%
        {'pnl_pct': -0.5},   # -0.5%
        {'pnl_pct': 1.5}     # +1.5%
    ]
    
    trades_df = pd.DataFrame(trades)
    
    # Method 1: WRONG - Simple sum
    simple_sum = trades_df['pnl_pct'].sum()
    print(f"\n1. Simple Sum (WRONG): {simple_sum:.2f}%")
    
    # Method 2: CORRECT - Compound
    trade_multipliers = 1 + trades_df['pnl_pct'] / 100
    compound_multiplier = trade_multipliers.prod()
    compound_return = (compound_multiplier - 1) * 100
    
    print(f"\n2. Compound Return (CORRECT): {compound_return:.2f}%")
    print(f"   Trade multipliers: {trade_multipliers.tolist()}")
    print(f"   Final multiplier: {compound_multiplier:.6f}")
    
    # Manual verification
    manual = 1.02 * 0.99 * 1.03 * 0.995 * 1.015
    manual_return = (manual - 1) * 100
    print(f"\n3. Manual Calculation: {manual_return:.2f}%")
    print(f"   1.02 × 0.99 × 1.03 × 0.995 × 1.015 = {manual:.6f}")
    
    # Test case 2: Many small wins (like 71% win rate)
    print("\n" + "="*60)
    print("TEST CASE 2: 71% Win Rate Scenario")
    print("="*60)
    
    # Simulate 100 trades with 71% win rate
    np.random.seed(42)
    num_trades = 100
    win_rate = 0.71
    avg_win = 0.3  # 0.3% average win
    avg_loss = 0.2  # 0.2% average loss
    
    trades2 = []
    for i in range(num_trades):
        if np.random.random() < win_rate:
            # Win
            pnl = np.random.normal(avg_win, 0.1)
        else:
            # Loss
            pnl = -np.random.normal(avg_loss, 0.05)
        trades2.append({'pnl_pct': pnl})
    
    trades2_df = pd.DataFrame(trades2)
    
    # Calculate returns
    simple_sum2 = trades2_df['pnl_pct'].sum()
    trade_multipliers2 = 1 + trades2_df['pnl_pct'] / 100
    compound_multiplier2 = trade_multipliers2.prod()
    compound_return2 = (compound_multiplier2 - 1) * 100
    
    print(f"\n100 trades with 71% win rate:")
    print(f"  Simple sum: {simple_sum2:.2f}%")
    print(f"  Compound return: {compound_return2:.2f}%")
    print(f"  Ratio: {simple_sum2/compound_return2:.2f}x")
    
    # Check if 2000+ trades could give 500%+ returns
    print("\n" + "="*60)
    print("TEST CASE 3: Can 2000 trades give 500% return?")
    print("="*60)
    
    # For 500% return with compound: (1 + r)^2000 = 6
    # Solving: r = 6^(1/2000) - 1
    required_avg_return_per_trade = (6 ** (1/2000) - 1) * 100
    print(f"\nRequired average return per trade for 500% total: {required_avg_return_per_trade:.4f}%")
    
    # With 71% win rate, what win/loss ratio needed?
    # Expectancy = win_rate * avg_win - loss_rate * avg_loss
    # 0.0009 = 0.71 * avg_win - 0.29 * avg_loss
    # If avg_loss = 0.2%, then avg_win = ?
    avg_loss_assumed = 0.2
    required_avg_win = (required_avg_return_per_trade + 0.29 * avg_loss_assumed) / 0.71
    print(f"\nWith 71% win rate and {avg_loss_assumed}% avg loss:")
    print(f"  Required avg win: {required_avg_win:.4f}%")
    print(f"  Win/Loss ratio: {required_avg_win/avg_loss_assumed:.2f}")
    
    # This seems too low to be true!
    # Let's check with the actual numbers from the test
    
    print("\n" + "="*60)
    print("DEBUGGING ACTUAL TEST RESULTS")
    print("="*60)
    
    # If we have 2099 trades and 491.65% return
    actual_trades = 2099
    actual_return = 491.65
    
    # What was the average return per trade?
    actual_multiplier = 1 + actual_return / 100
    avg_multiplier_per_trade = actual_multiplier ** (1/actual_trades)
    avg_return_per_trade = (avg_multiplier_per_trade - 1) * 100
    
    print(f"\nRELIANCE actual results:")
    print(f"  Total trades: {actual_trades}")
    print(f"  Total return: {actual_return:.2f}%")
    print(f"  Final multiplier: {actual_multiplier:.2f}x")
    print(f"  Avg return per trade: {avg_return_per_trade:.4f}%")
    
    # With 71.6% win rate
    win_rate_actual = 0.716
    wins = int(actual_trades * win_rate_actual)
    losses = actual_trades - wins
    
    # If expectancy = avg_return_per_trade
    # And expectancy = win_rate * avg_win - loss_rate * avg_loss
    # Let's assume avg_loss = 0.5% (reasonable stop loss)
    assumed_avg_loss = 0.5
    implied_avg_win = (avg_return_per_trade + (1-win_rate_actual) * assumed_avg_loss) / win_rate_actual
    
    print(f"\nImplied trade statistics:")
    print(f"  Wins: {wins}, Losses: {losses}")
    print(f"  If avg loss = {assumed_avg_loss}%")
    print(f"  Then avg win = {implied_avg_win:.4f}%")
    print(f"  Win/Loss ratio = {implied_avg_win/assumed_avg_loss:.2f}")
    
    # This is showing VERY small average wins/losses
    # Something is wrong with the exit logic!


def analyze_exit_configs():
    """Analyze the exit configurations"""
    print("\n" + "="*60)
    print("ANALYZING EXIT CONFIGURATIONS")
    print("="*60)
    
    configs = {
        'conservative': {
            'stop_loss_percent': 1.0,      # 1% stop loss
            'take_profit_targets': [2.0],   # 2% take profit
            'target_sizes': [100],          # Exit full position
        },
        'scalping': {
            'stop_loss_percent': 0.5,       # 0.5% stop loss
            'take_profit_targets': [0.5, 0.75, 1.0],  # Multiple small targets
            'target_sizes': [50, 30, 20],   # Partial exits
        }
    }
    
    for name, config in configs.items():
        print(f"\n{name.upper()}:")
        print(f"  Stop Loss: {config['stop_loss_percent']}%")
        print(f"  Targets: {config['take_profit_targets']}")
        print(f"  Sizes: {config.get('target_sizes', [100])}")
        
        # Calculate expected R:R
        sl = config['stop_loss_percent']
        targets = config['take_profit_targets']
        sizes = config.get('target_sizes', [100])
        
        # Weighted average target
        if len(targets) == 1:
            avg_target = targets[0]
        else:
            # Calculate weighted average based on position sizes
            total_size = sum(sizes)
            weighted_sum = sum(t * s for t, s in zip(targets, sizes))
            avg_target = weighted_sum / total_size
        
        risk_reward = avg_target / sl
        print(f"  Risk:Reward = 1:{risk_reward:.1f}")
        
        # With 71% win rate, what's the expectancy?
        win_rate = 0.71
        expectancy_pct = win_rate * avg_target - (1 - win_rate) * sl
        print(f"  Expectancy @ 71% WR: {expectancy_pct:.3f}%")
        
        # How many trades to reach 500%?
        if expectancy_pct > 0:
            # (1 + e)^n = 6
            trades_needed = np.log(6) / np.log(1 + expectancy_pct/100)
            print(f"  Trades for 500% return: {int(trades_needed)}")


if __name__ == "__main__":
    test_compound_returns()
    analyze_exit_configs()
    
    print("\n" + "="*60)
    print("CONCLUSION")
    print("="*60)
    print("\nThe 500%+ returns suggest one of these issues:")
    print("1. Exit logic is not working (stops not triggering)")
    print("2. There are many tiny winning trades compounding")
    print("3. Data issues (prices might be adjusted incorrectly)")
    print("4. Partial exit logic might be crediting wins multiple times")
    print("\nNeed to add detailed trade logging to see actual entry/exit prices!")