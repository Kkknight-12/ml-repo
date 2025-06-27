"""
Test with FIXED Exit Configurations
===================================

Fix the exit timing issues and test again.
"""

import pandas as pd
from scanner.smart_exit_manager import SmartExitManager

print("="*60)
print("FIXED EXIT CONFIGURATIONS")
print("="*60)

# FIXED configurations with proper holding times
exit_configs = {
    'conservative': {
        'stop_loss_percent': 1.0,
        'take_profit_targets': [2.0],
        'target_sizes': [100],
        'use_trailing_stop': False,  # Disable for now
        'max_holding_bars': 200      # Increased from 78
    },
    'scalping': {
        'stop_loss_percent': 0.5,
        'take_profit_targets': [0.5, 0.75, 1.0],
        'target_sizes': [50, 30, 20],
        'use_trailing_stop': False,  # Disable for now
        'max_holding_bars': 100      # Increased from 20!
    },
    'adaptive': {
        'stop_loss_percent': 2.0,
        'take_profit_targets': [1.0, 2.0, 3.0],
        'target_sizes': [40, 40, 20],
        'use_trailing_stop': False,  # Disable for now
        'max_holding_bars': 200      # Increased from 40
    }
}

# Test each configuration
for strategy, config in exit_configs.items():
    print(f"\n{strategy.upper()} STRATEGY:")
    print("-"*40)
    print(f"Stop: {config['stop_loss_percent']}%")
    print(f"Targets: {config['take_profit_targets']}")
    print(f"Max Hold: {config['max_holding_bars']} bars")
    
    exit_mgr = SmartExitManager(config)
    position = exit_mgr.enter_position('TEST', 100.0, 100, 1, 5.0, pd.Timestamp.now())
    
    # Simulate realistic price movement
    # Average 0.05% move per 5min bar (reasonable for stocks)
    bars_tested = 0
    exit_type = None
    final_pnl = 0
    
    for bar in range(1, config['max_holding_bars']):
        # Add some randomness
        import random
        move = random.uniform(-0.1, 0.15)  # -0.1% to +0.15% per bar
        price = 100.0 + sum([random.uniform(-0.1, 0.15) for _ in range(bar)])
        
        position.bars_held = bar
        exit_signal = exit_mgr.check_exit('TEST', price, 5.0, pd.Timestamp.now())
        
        if exit_signal:
            exit_type = exit_signal.exit_type
            final_pnl = (price - 100.0) / 100.0 * 100
            bars_tested = bar
            break
    
    print(f"\nResult after {bars_tested} bars:")
    print(f"  Exit Type: {exit_type if exit_type else 'No exit'}")
    print(f"  Final P&L: {final_pnl:.2f}%")
    
    if exit_type == 'time':
        print(f"  ⚠️  Still hitting time exit!")
    elif exit_type == 'target':
        print(f"  ✅ Hit target as expected!")
    elif exit_type == 'stop':
        print(f"  ❌ Hit stop loss")

print("\n\n" + "="*60)
print("RECOMMENDATIONS FOR MAIN SCRIPT")
print("="*60)

print("""
1. INCREASE max_holding_bars:
   - Conservative: 78 → 200+ bars
   - Scalping: 20 → 100+ bars  
   - Adaptive: 40 → 200+ bars
   - ATR: 78 → 200+ bars

2. DISABLE trailing stops initially:
   - Set use_trailing_stop: False
   - Test pure target/stop exits first
   - Add trailing back later if needed

3. EXPECTED RESULTS after fix:
   - Conservative: ~2% average win
   - Scalping: ~0.7% average win
   - Adaptive: ~1.5-2% average win
   - Win rates may decrease but profits should increase

4. The high returns (155%) were from MANY small wins compounding
   With proper exits, expect more reasonable returns
""")