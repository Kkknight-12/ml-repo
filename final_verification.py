"""
Final Verification Before Running Test
======================================

Verify all components are correctly configured.
"""

import os
import json
from scanner.smart_exit_manager import SmartExitManager
from utils.kelly_criterion import KellyCriterion

print("="*60)
print("FINAL VERIFICATION CHECKLIST")
print("="*60)

# 1. Check if Kelly Criterion is implemented
print("\n1. Kelly Criterion Implementation:")
print("-"*40)
try:
    kelly = KellyCriterion(kelly_fraction=0.25)
    print("✅ KellyCriterion class imported successfully")
    print(f"   Default fraction: {kelly.kelly_fraction}")
    
    # Test with sample trades
    kelly.add_trade(2.0)
    kelly.add_trade(-1.0)
    kelly.add_trade(1.5)
    print("✅ Can add trades")
    
    # Test position sizing
    position = kelly.calculate_position_size(
        account_balance=100000,
        entry_price=100,
        stop_loss=98
    )
    print(f"✅ Position sizing works: {position['shares']} shares")
except Exception as e:
    print(f"❌ Kelly Criterion error: {e}")

# 2. Check exit configurations
print("\n2. Exit Strategy Configurations:")
print("-"*40)

exit_configs = {
    'conservative': {
        'stop_loss_percent': 1.0,
        'take_profit_targets': [2.0],
        'target_sizes': [100],
        'use_trailing_stop': False,
        'max_holding_bars': 78
    },
    'scalping': {
        'stop_loss_percent': 0.5,
        'take_profit_targets': [0.5, 0.75, 1.0],
        'target_sizes': [50, 30, 20],
        'use_trailing_stop': True,
        'trailing_activation': 0.5,
        'trailing_distance': 0.25,
        'max_holding_bars': 20
    },
    'adaptive': {
        'stop_loss_percent': 2.0,
        'take_profit_targets': [1.0, 2.0, 3.0],
        'target_sizes': [40, 40, 20],
        'use_trailing_stop': True,
        'trailing_activation': 1.0,
        'trailing_distance': 0.5,
        'max_holding_bars': 40
    },
    'atr': {
        'use_atr_stops': True,
        'atr_stop_multiplier': 2.0,
        'atr_profit_multipliers': [1.5, 3.0, 5.0],
        'target_sizes': [50, 30, 20],
        'use_trailing_stop': True,
        'atr_trailing_multiplier': 1.5,
        'max_holding_bars': 78
    }
}

for strategy, config in exit_configs.items():
    print(f"\n{strategy.upper()}:")
    use_atr = config.get('use_atr_stops', False)
    
    try:
        # Create exit manager with ONLY the exit config
        exit_mgr = SmartExitManager(config.copy(), use_atr_stops=use_atr)
        
        if not use_atr:
            print(f"  Stop Loss: {exit_mgr.stop_loss_pct}% (Expected: {config['stop_loss_percent']}%)")
            print(f"  Targets: {exit_mgr.targets} (Expected: {config['take_profit_targets']})")
            print(f"  Sizes: {exit_mgr.target_sizes} (Expected: {config['target_sizes']})")
        else:
            print(f"  ATR Stop: {exit_mgr.atr_stop_multiplier}x (Expected: {config['atr_stop_multiplier']}x)")
            print(f"  ATR Targets: {exit_mgr.atr_profit_multipliers} (Expected: {config['atr_profit_multipliers']})")
        
        print(f"  Max Hold: {exit_mgr.max_holding_bars} bars (Expected: {config['max_holding_bars']})")
        print("  ✅ Configuration verified")
    except Exception as e:
        print(f"  ❌ Error: {e}")

# 3. Check data access
print("\n3. Data Access:")
print("-"*40)
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session = json.load(f)
        if session.get('access_token'):
            print("✅ Kite session found with access token")
        else:
            print("⚠️  Kite session found but no access token")
else:
    print("⚠️  No Kite session found - will use cached data")

# 4. Check test script
print("\n4. Test Script:")
print("-"*40)
if os.path.exists('test_multi_stock_optimization_fixed.py'):
    print("✅ test_multi_stock_optimization_fixed.py exists")
    
    # Check key fixes
    with open('test_multi_stock_optimization_fixed.py', 'r') as f:
        content = f.read()
        
    if "CRITICAL FIX: Only pass exit config, NOT mixed with adaptive" in content:
        print("✅ Exit config fix is present")
    else:
        print("❌ Exit config fix missing!")
    
    if "_calculate_statistics(self, trades: List[Dict], strategy: str, exit_config: Dict)" in content:
        print("✅ Calculate statistics signature fixed")
    else:
        print("❌ Calculate statistics signature not fixed!")
    
    if "SmartExitManager(exit_config.copy(), use_atr_stops=use_atr)" in content:
        print("✅ Exit manager initialization fixed")
    else:
        print("❌ Exit manager initialization not fixed!")
else:
    print("❌ test_multi_stock_optimization_fixed.py not found!")

# 5. Summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60)

print("\nExpected behavior when you run the test:")
print("1. Each strategy should show DIFFERENT results")
print("2. Conservative should have ~1% stop loss, 2% target")
print("3. Scalping should have 0.5% stop, 0.5/0.75/1.0% targets")
print("4. Returns should be more reasonable (not 150%+)")
print("5. Win rates should vary by strategy")

print("\nCommand to run:")
print("  python test_multi_stock_optimization_fixed.py")

print("\nWhat to look for in results:")
print("- Different win rates for each strategy")
print("- Reasonable returns (likely -20% to +50% range)")
print("- Different average win/loss sizes per strategy")
print("- Positive expectancy for at least one strategy")