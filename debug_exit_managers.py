"""
Debug Exit Manager Creation
===========================

Verify exit managers are created with correct configurations.
"""

from scanner.smart_exit_manager import SmartExitManager
import pandas as pd

print("="*60)
print("DEBUG: EXIT MANAGER CREATION")
print("="*60)

# Define exit configurations (same as in test script)
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
    }
}

# Simulate adaptive config (this should NOT affect exit managers)
adaptive_config = {
    'stop_loss_percent': 0.18,  # Very small
    'take_profit_targets': [0.11, 0.2, 0.33],  # Very small
    'target_sizes': [50, 30, 20],
    'max_holding_bars': 15
}

print("\nAdaptive config values (should NOT be used):")
print(f"  Stop: {adaptive_config['stop_loss_percent']}%")
print(f"  Targets: {adaptive_config['take_profit_targets']}")

# Test 1: Create exit managers the CORRECT way (as in fixed script)
print("\n" + "-"*60)
print("TEST 1: Creating exit managers (CORRECT way)")
print("-"*60)

exit_managers_correct = {}
for strategy, exit_config in exit_configs.items():
    # CRITICAL: Only pass exit config, NOT mixed with adaptive
    use_atr = exit_config.get('use_atr_stops', False)
    exit_managers_correct[strategy] = SmartExitManager(exit_config.copy(), use_atr_stops=use_atr)

print("\nConservative Exit Manager:")
print(f"  Stop Loss: {exit_managers_correct['conservative'].stop_loss_pct}%")
print(f"  Targets: {exit_managers_correct['conservative'].targets}")
print(f"  ✅ CORRECT!" if exit_managers_correct['conservative'].stop_loss_pct == 1.0 else "  ❌ WRONG!")

print("\nScalping Exit Manager:")
print(f"  Stop Loss: {exit_managers_correct['scalping'].stop_loss_pct}%")
print(f"  Targets: {exit_managers_correct['scalping'].targets}")
print(f"  ✅ CORRECT!" if exit_managers_correct['scalping'].stop_loss_pct == 0.5 else "  ❌ WRONG!")

# Test 2: Simulate the OLD WRONG way (mixing configs)
print("\n" + "-"*60)
print("TEST 2: Creating exit managers (WRONG way - mixing configs)")
print("-"*60)

exit_managers_wrong = {}
for strategy, exit_config in exit_configs.items():
    # WRONG: Mix adaptive and exit configs
    full_config = adaptive_config.copy()
    full_config.update(exit_config)  # This should override adaptive values
    use_atr = exit_config.get('use_atr_stops', False)
    exit_managers_wrong[strategy] = SmartExitManager(full_config, use_atr_stops=use_atr)

print("\nConservative Exit Manager (with mixed config):")
print(f"  Stop Loss: {exit_managers_wrong['conservative'].stop_loss_pct}%")
print(f"  Targets: {exit_managers_wrong['conservative'].targets}")
print(f"  Result: {'✅ Override worked' if exit_managers_wrong['conservative'].stop_loss_pct == 1.0 else '❌ Override failed'}")

# Test 3: Verify position entry calculations
print("\n" + "-"*60)
print("TEST 3: Position Entry Calculations")
print("-"*60)

# Enter a test position
test_entry_price = 100.0
for strategy_name, exit_mgr in exit_managers_correct.items():
    print(f"\n{strategy_name.upper()} - Entry at {test_entry_price}:")
    
    position = exit_mgr.enter_position(
        symbol='TEST',
        entry_price=test_entry_price,
        quantity=100,
        direction=1,
        ml_signal=5.0,
        timestamp=pd.Timestamp.now()
    )
    
    expected_stop = test_entry_price * (1 - exit_mgr.stop_loss_pct / 100)
    print(f"  Stop Loss: {position.stop_loss:.2f} (expected: {expected_stop:.2f})")
    print(f"  Targets: {[f'{t:.2f}' for t in position.targets]}")
    
    # Calculate expected targets
    expected_targets = [test_entry_price * (1 + t/100) for t in exit_mgr.targets]
    print(f"  Expected: {[f'{t:.2f}' for t in expected_targets]}")
    
    targets_match = all(abs(a-b) < 0.01 for a, b in zip(position.targets, expected_targets))
    print(f"  ✅ CORRECT!" if targets_match else "  ❌ WRONG!")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print("\nThe FIXED script should:")
print("1. Create exit managers with ONLY exit config (not mixed)")
print("2. Conservative should have 1% stop, 2% target")
print("3. Scalping should have 0.5% stop, 0.5/0.75/1% targets")
print("4. Position calculations should match configured values")