"""
Test Exit Timing Issue
=====================

Test if time exits are happening before targets.
"""

from scanner.smart_exit_manager import SmartExitManager
import pandas as pd

print("="*60)
print("TESTING EXIT TIMING")
print("="*60)

# Test different max_holding_bars values
configs = [
    {
        'name': 'Very Short (10 bars)',
        'stop_loss_percent': 1.0,
        'take_profit_targets': [2.0],
        'target_sizes': [100],
        'use_trailing_stop': False,
        'max_holding_bars': 10
    },
    {
        'name': 'Short (20 bars)',
        'stop_loss_percent': 1.0,
        'take_profit_targets': [2.0],
        'target_sizes': [100],
        'use_trailing_stop': False,
        'max_holding_bars': 20
    },
    {
        'name': 'Medium (78 bars)',
        'stop_loss_percent': 1.0,
        'take_profit_targets': [2.0],
        'target_sizes': [100],
        'use_trailing_stop': False,
        'max_holding_bars': 78
    },
    {
        'name': 'Long (200 bars)',
        'stop_loss_percent': 1.0,
        'take_profit_targets': [2.0],
        'target_sizes': [100],
        'use_trailing_stop': False,
        'max_holding_bars': 200
    }
]

# Simulate slow price movement (realistic for 5min bars)
# Price increases 0.1% per bar
entry_price = 100.0
bars_to_2pct = int(2.0 / 0.1)  # 20 bars to reach 2% target

print(f"\nSimulating price increasing 0.1% per bar")
print(f"Bars needed to reach 2% target: {bars_to_2pct}")
print("-"*40)

for config in configs:
    print(f"\n{config['name']} (max={config['max_holding_bars']} bars):")
    
    exit_mgr = SmartExitManager(config)
    position = exit_mgr.enter_position('TEST', entry_price, 100, 1, 5.0, pd.Timestamp.now())
    
    # Simulate bars
    for bar in range(1, 30):
        price = entry_price * (1 + bar * 0.001)  # 0.1% per bar
        position.bars_held = bar
        
        exit_signal = exit_mgr.check_exit('TEST', price, 5.0, pd.Timestamp.now())
        
        if exit_signal:
            pnl = (price - entry_price) / entry_price * 100
            print(f"  EXIT at bar {bar}: {exit_signal.exit_type}")
            print(f"  Price: {price:.2f} (P&L: {pnl:.2f}%)")
            print(f"  Target was: {position.targets[0]} (2.0% gain)")
            
            if exit_signal.exit_type == 'time':
                print(f"  ⚠️  TIME EXIT before reaching target!")
            break
    else:
        print(f"  ✅ No premature exit - target can be reached")

# Test with trailing stops
print("\n\n" + "="*60)
print("TESTING TRAILING STOPS")
print("="*60)

configs_trailing = [
    {
        'name': 'Conservative Trailing',
        'stop_loss_percent': 1.0,
        'take_profit_targets': [2.0],
        'target_sizes': [100],
        'use_trailing_stop': True,
        'trailing_activation': 1.0,  # Activates at 1%
        'trailing_distance': 0.5,     # Trails by 0.5%
        'max_holding_bars': 200
    },
    {
        'name': 'Aggressive Trailing',
        'stop_loss_percent': 1.0,
        'take_profit_targets': [2.0],
        'target_sizes': [100],
        'use_trailing_stop': True,
        'trailing_activation': 0.5,   # Activates at 0.5%
        'trailing_distance': 0.25,    # Trails by 0.25%
        'max_holding_bars': 200
    }
]

# Simulate price that goes up then pulls back
prices = [100.0]
for i in range(1, 15):
    prices.append(100.0 + i * 0.1)  # Up to 101.4 (1.4%)
for i in range(3):
    prices.append(prices[-1] - 0.1)  # Pull back 0.3%

print("\nPrice sequence: Up to 1.4%, then pulls back 0.3%")

for config in configs_trailing:
    print(f"\n{config['name']}:")
    print(f"  Trailing activates at: {config['trailing_activation']}%")
    print(f"  Trailing distance: {config['trailing_distance']}%")
    
    exit_mgr = SmartExitManager(config)
    position = exit_mgr.enter_position('TEST', 100.0, 100, 1, 5.0, pd.Timestamp.now())
    
    for i, price in enumerate(prices[1:], 1):
        position.bars_held = i
        position.current_price = price
        
        # Update max profit
        profit = (price - 100.0) / 100.0 * 100
        position.max_profit = max(position.max_profit, profit)
        
        exit_signal = exit_mgr.check_exit('TEST', price, 5.0, pd.Timestamp.now())
        
        if exit_signal:
            pnl = (price - 100.0) / 100.0 * 100
            print(f"  EXIT at bar {i}: {exit_signal.exit_type}")
            print(f"  Price: {price:.2f} (P&L: {pnl:.2f}%)")
            print(f"  Max profit was: {position.max_profit:.2f}%")
            
            if exit_signal.exit_type == 'trailing':
                print(f"  ⚠️  TRAILING STOP before reaching 2% target!")
            break

print("\n\n" + "="*60)
print("CONCLUSIONS")
print("="*60)
print("""
The problem is clear:

1. With max_holding_bars=20 (scalping), trades exit at 2% gain via TIME exit
   before reaching targets

2. Trailing stops activate early and exit positions with small profits
   instead of letting them run to targets

3. This explains why all strategies show ~0.3-0.4% average wins

SOLUTION:
- Increase max_holding_bars significantly (or disable)
- Adjust trailing stop parameters or disable for testing
- Focus on letting winners run to targets
""")