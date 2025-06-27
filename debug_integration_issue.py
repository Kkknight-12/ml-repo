"""
Debug Integration Issue
======================

The exit logic works in isolation. 
Let's find why it doesn't work in the main script.
"""

import pandas as pd
import numpy as np
from scanner.smart_exit_manager import SmartExitManager

def compare_exit_behaviors():
    """Compare exit behavior in different scenarios"""
    print("="*60)
    print("COMPARING EXIT BEHAVIORS")
    print("="*60)
    
    # Test 1: Direct exit manager (working)
    print("\n1. DIRECT EXIT MANAGER TEST:")
    print("-"*40)
    
    config = {
        'stop_loss_percent': 1.0,
        'take_profit_targets': [2.0],
        'target_sizes': [100],
        'use_trailing_stop': False,
        'max_holding_bars': 78
    }
    
    exit_mgr = SmartExitManager(config)
    position = exit_mgr.enter_position('TEST', 100.0, 100, 1, 5.0, pd.Timestamp.now())
    
    # Test at 2% profit
    exit_signal = exit_mgr.check_exit('TEST', 102.0, 5.0, pd.Timestamp.now(), high=102.0, low=102.0)
    print(f"At 102 (2% profit): Exit = {exit_signal is not None}")
    if exit_signal:
        print(f"  Exit type: {exit_signal.exit_type}")
    
    # Test 2: With mixed config (potential issue)
    print("\n2. MIXED CONFIG TEST:")
    print("-"*40)
    
    # Simulate what might happen in main script
    adaptive_config = {
        'stop_loss_percent': 0.18,  # Very small
        'take_profit_targets': [0.11, 0.2, 0.33],  # Very small
        'max_holding_bars': 15
    }
    
    # Mix configs (WRONG way)
    mixed_config = adaptive_config.copy()
    mixed_config.update(config)  # Should override
    
    print(f"Mixed config stop: {mixed_config['stop_loss_percent']}%")
    print(f"Mixed config targets: {mixed_config['take_profit_targets']}")
    
    exit_mgr2 = SmartExitManager(mixed_config)
    position2 = exit_mgr2.enter_position('TEST', 100.0, 100, 1, 5.0, pd.Timestamp.now())
    
    print(f"\nActual stop in exit manager: {exit_mgr2.stop_loss_pct}%")
    print(f"Actual targets: {exit_mgr2.targets}")
    print(f"Position stop: {position2.stop_loss}")
    print(f"Position targets: {position2.targets}")


def analyze_early_exits():
    """Analyze why exits might happen early"""
    print("\n\n" + "="*60)
    print("ANALYZING EARLY EXIT CAUSES")
    print("="*60)
    
    config = {
        'stop_loss_percent': 1.0,
        'take_profit_targets': [2.0],
        'target_sizes': [100],
        'use_trailing_stop': True,  # Enable trailing
        'trailing_activation': 0.5,  # Activates at 0.5% profit
        'trailing_distance': 0.25,   # Trails by 0.25%
        'max_holding_bars': 20
    }
    
    exit_mgr = SmartExitManager(config)
    position = exit_mgr.enter_position('TEST', 100.0, 100, 1, 5.0, pd.Timestamp.now())
    
    print("\nTesting price sequence with trailing stop:")
    print(f"Trailing activates at: {config['trailing_activation']}% profit")
    print(f"Trailing distance: {config['trailing_distance']}%")
    
    prices = [100.0, 100.6, 100.8, 100.7, 100.5, 100.4]  # Goes up then pulls back
    
    for i, price in enumerate(prices[1:], 1):
        position.bars_held = i
        position.current_price = price
        
        # Update max profit
        profit = (price - 100.0) / 100.0 * 100
        position.max_profit = max(position.max_profit, profit)
        
        print(f"\nBar {i}: Price={price}, Max profit={position.max_profit:.2f}%")
        
        # Check all exit types
        exit_signal = exit_mgr.check_exit('TEST', price, 5.0, pd.Timestamp.now())
        
        if exit_signal:
            print(f"  🚪 EXIT: {exit_signal.exit_type} - {exit_signal.reason}")
            break
        else:
            print(f"  Hold")


def check_exit_order():
    """Check the order of exit checks"""
    print("\n\n" + "="*60)
    print("CHECKING EXIT CHECK ORDER")
    print("="*60)
    
    print("\nFrom SmartExitManager.check_exit(), the order is:")
    print("1. Stop Loss")
    print("2. Profit Targets")
    print("3. Trailing Stop")
    print("4. Time Exit")
    print("5. Signal Change")
    
    print("\nThis means:")
    print("- Stop loss is checked FIRST (good)")
    print("- Targets are checked BEFORE trailing (good)")
    print("- Time exit could trigger before targets if max_holding_bars is too small")
    
    # Test time exit
    config = {
        'stop_loss_percent': 1.0,
        'take_profit_targets': [2.0],
        'target_sizes': [100],
        'use_trailing_stop': False,
        'max_holding_bars': 5  # Very short!
    }
    
    exit_mgr = SmartExitManager(config)
    position = exit_mgr.enter_position('TEST', 100.0, 100, 1, 5.0, pd.Timestamp.now())
    
    print(f"\nTesting with max_holding_bars = {config['max_holding_bars']}:")
    
    for bar in range(1, 7):
        position.bars_held = bar
        price = 100.0 + bar * 0.3  # Slowly going up
        
        exit_signal = exit_mgr.check_exit('TEST', price, 5.0, pd.Timestamp.now())
        
        if exit_signal:
            print(f"Bar {bar}: Price={price:.1f} → EXIT ({exit_signal.exit_type})")
            print(f"  P&L would be: {(price-100)/100*100:.2f}%")
            break
        else:
            print(f"Bar {bar}: Price={price:.1f} → Hold")


if __name__ == "__main__":
    compare_exit_behaviors()
    analyze_early_exits()
    check_exit_order()
    
    print("\n\n" + "="*60)
    print("CONCLUSIONS")
    print("="*60)
    print("""
Based on these tests:

1. Exit logic works correctly in isolation
2. Potential issues in main script:
   - Time exits happening before targets (max_holding_bars too small?)
   - Trailing stops activating and exiting early
   - Mixed configurations not properly isolated
   
Next steps:
1. Check actual exit reasons in main test results
2. Verify max_holding_bars values
3. Check if trailing stops are causing early exits
""")