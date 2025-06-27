"""
MINIMAL TEST: Single Position with Full Logging
===============================================

Test ONE position with DETAILED logging of every exit decision.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scanner.smart_exit_manager import SmartExitManager
from data.smart_data_manager import SmartDataManager

# Track exit decisions
exit_log = []

def log_exit_check(bar_num, price, check_type, result, details=""):
    """Log every exit check"""
    exit_log.append({
        'bar': bar_num,
        'price': price,
        'check': check_type,
        'triggered': result,
        'details': details
    })
    print(f"  Bar {bar_num}: {check_type} → {'EXIT' if result else 'Hold'} {details}")


def test_single_position_conservative():
    """Test conservative strategy with ONE position"""
    print("="*60)
    print("TEST: Conservative Strategy - Single Position")
    print("="*60)
    
    # Clear log
    global exit_log
    exit_log = []
    
    # Conservative config - SIMPLE AND CLEAR
    config = {
        'stop_loss_percent': 1.0,      # 1% stop loss
        'take_profit_targets': [2.0],   # 2% profit target
        'target_sizes': [100],          # Exit full position
        'use_trailing_stop': False,     # No trailing
        'max_holding_bars': 78          # Exit after 78 bars
    }
    
    print(f"\nConfiguration:")
    print(f"  Stop Loss: {config['stop_loss_percent']}%")
    print(f"  Target: {config['take_profit_targets']}%")
    print(f"  Max Hold: {config['max_holding_bars']} bars")
    
    # Create exit manager
    exit_mgr = SmartExitManager(config)
    
    # Enter position at 100
    entry_price = 100.0
    position = exit_mgr.enter_position(
        symbol='TEST',
        entry_price=entry_price,
        quantity=100,
        direction=1,  # Long
        ml_signal=5.0,
        timestamp=pd.Timestamp.now()
    )
    
    print(f"\nPosition Entered:")
    print(f"  Entry Price: {entry_price}")
    print(f"  Stop Loss: {position.stop_loss}")
    print(f"  Target: {position.targets[0]}")
    print(f"  Expected Stop: {entry_price * 0.99} (1% below)")
    print(f"  Expected Target: {entry_price * 1.02} (2% above)")
    
    # Simulate price movement
    prices = [
        100.0,  # Entry
        100.2,  # +0.2%
        100.5,  # +0.5%
        100.8,  # +0.8%
        101.0,  # +1.0%
        101.5,  # +1.5%
        101.8,  # +1.8%
        102.0,  # +2.0% - Should hit target!
        102.5,  # +2.5%
    ]
    
    print(f"\nProcessing Price Movement:")
    print("-"*40)
    
    for bar, price in enumerate(prices[1:], 1):
        # Update position tracking
        position.bars_held = bar
        position.current_price = price
        
        # Calculate current P&L
        pnl_pct = (price - entry_price) / entry_price * 100
        
        print(f"\nBar {bar}: Price={price} (P&L: {pnl_pct:+.2f}%)")
        
        # Check each exit condition manually
        # 1. Stop Loss Check
        if price <= position.stop_loss:
            log_exit_check(bar, price, "Stop Loss", True, f"Price {price} <= Stop {position.stop_loss}")
        else:
            log_exit_check(bar, price, "Stop Loss", False, f"Price {price} > Stop {position.stop_loss}")
        
        # 2. Target Check
        if price >= position.targets[0]:
            log_exit_check(bar, price, "Target", True, f"Price {price} >= Target {position.targets[0]}")
        else:
            log_exit_check(bar, price, "Target", False, f"Price {price} < Target {position.targets[0]}")
        
        # 3. Time Check
        if bar >= config['max_holding_bars']:
            log_exit_check(bar, price, "Time", True, f"Held {bar} >= Max {config['max_holding_bars']}")
        else:
            log_exit_check(bar, price, "Time", False, f"Held {bar} < Max {config['max_holding_bars']}")
        
        # Now check with actual exit manager
        exit_signal = exit_mgr.check_exit(
            symbol='TEST',
            current_price=price,
            current_ml_signal=5.0,
            timestamp=pd.Timestamp.now(),
            high=price,
            low=price
        )
        
        if exit_signal:
            print(f"\n🚪 EXIT TRIGGERED!")
            print(f"   Type: {exit_signal.exit_type}")
            print(f"   Reason: {exit_signal.reason}")
            print(f"   Exit Price: {exit_signal.exit_price}")
            
            # Execute exit
            result = exit_mgr.execute_exit('TEST', exit_signal)
            print(f"   P&L: {result['pnl_pct']:.2f}%")
            break
        else:
            print(f"   Decision: HOLD")
    
    # Summary
    print("\n" + "="*40)
    print("EXIT LOG SUMMARY:")
    print("="*40)
    
    # Count exit types
    from collections import Counter
    exit_counts = Counter()
    for log in exit_log:
        if log['triggered']:
            exit_counts[log['check']] += 1
    
    print(f"\nExit checks that triggered:")
    for check_type, count in exit_counts.items():
        print(f"  {check_type}: {count} times")
    
    print(f"\nTotal bars processed: {len(prices)-1}")
    print(f"Exit triggered at bar: {bar if exit_signal else 'Never'}")


def test_single_position_scalping():
    """Test scalping strategy with ONE position"""
    print("\n\n" + "="*60)
    print("TEST: Scalping Strategy - Single Position")
    print("="*60)
    
    # Clear log
    global exit_log
    exit_log = []
    
    # Scalping config
    config = {
        'stop_loss_percent': 0.5,
        'take_profit_targets': [0.5, 0.75, 1.0],
        'target_sizes': [50, 30, 20],
        'use_trailing_stop': False,  # Disable for now
        'max_holding_bars': 20
    }
    
    print(f"\nConfiguration:")
    print(f"  Stop Loss: {config['stop_loss_percent']}%")
    print(f"  Targets: {config['take_profit_targets']}%")
    print(f"  Sizes: {config['target_sizes']}%")
    print(f"  Max Hold: {config['max_holding_bars']} bars")
    
    # Create exit manager
    exit_mgr = SmartExitManager(config)
    
    # Enter position
    entry_price = 100.0
    position = exit_mgr.enter_position('TEST', entry_price, 100, 1, 5.0, pd.Timestamp.now())
    
    print(f"\nPosition Entered:")
    print(f"  Entry: {entry_price}")
    print(f"  Stop: {position.stop_loss}")
    print(f"  Targets: {position.targets}")
    
    # Simulate smaller price movements
    prices = [
        100.0,   # Entry
        100.1,   # +0.1%
        100.2,   # +0.2%
        100.3,   # +0.3%
        100.4,   # +0.4%
        100.5,   # +0.5% - Should hit first target!
        100.6,   # +0.6%
        100.75,  # +0.75% - Should hit second target!
        100.9,   # +0.9%
        101.0,   # +1.0% - Should hit third target!
    ]
    
    print(f"\nProcessing Price Movement:")
    print("-"*40)
    
    total_exits = 0
    remaining_qty = 100
    
    for bar, price in enumerate(prices[1:], 1):
        pnl_pct = (price - entry_price) / entry_price * 100
        
        print(f"\nBar {bar}: Price={price} (P&L: {pnl_pct:+.2f}%)")
        print(f"  Remaining Quantity: {remaining_qty}")
        
        # Check exits
        exit_signal = exit_mgr.check_exit('TEST', price, 5.0, pd.Timestamp.now(), high=price, low=price)
        
        if exit_signal:
            print(f"\n🚪 EXIT TRIGGERED!")
            print(f"   Type: {exit_signal.exit_type}")
            print(f"   Quantity: {exit_signal.quantity}")
            
            result = exit_mgr.execute_exit('TEST', exit_signal)
            total_exits += 1
            remaining_qty -= result['quantity']
            
            print(f"   P&L: {result['pnl_pct']:.2f}%")
            print(f"   Remaining after exit: {remaining_qty}")
            
            if remaining_qty <= 0:
                print(f"\n✅ Position fully closed after {total_exits} exits")
                break


def test_with_real_data():
    """Test with actual market data"""
    print("\n\n" + "="*60)
    print("TEST: With Real Market Data (RELIANCE)")
    print("="*60)
    
    # Get real data
    data_mgr = SmartDataManager()
    df = data_mgr.get_data('RELIANCE', '5minute', days=5)
    
    if df is None or len(df) < 100:
        print("❌ Could not get sufficient data")
        return
    
    # Take a small sample
    sample = df.iloc[50:70]  # 20 bars
    
    # Conservative config
    config = {
        'stop_loss_percent': 1.0,
        'take_profit_targets': [2.0],
        'target_sizes': [100],
        'use_trailing_stop': False,
        'max_holding_bars': 78
    }
    
    exit_mgr = SmartExitManager(config)
    
    # Enter at first bar
    entry_price = sample.iloc[0]['close']
    position = exit_mgr.enter_position('RELIANCE', entry_price, 100, 1, 5.0, sample.index[0])
    
    print(f"\nEntered at: {entry_price}")
    print(f"Stop: {position.stop_loss}")
    print(f"Target: {position.targets[0]}")
    
    # Process each bar
    for i, (idx, row) in enumerate(sample.iloc[1:].iterrows(), 1):
        price = row['close']
        pnl_pct = (price - entry_price) / entry_price * 100
        
        print(f"\nBar {i}: {idx.strftime('%H:%M')} Price={price:.2f} (P&L: {pnl_pct:+.2f}%)")
        
        exit_signal = exit_mgr.check_exit(
            'RELIANCE', price, 5.0, idx,
            high=row['high'], low=row['low']
        )
        
        if exit_signal:
            print(f"🚪 EXIT: {exit_signal.exit_type} - {exit_signal.reason}")
            result = exit_mgr.execute_exit('RELIANCE', exit_signal)
            print(f"Final P&L: {result['pnl_pct']:.2f}%")
            break


if __name__ == "__main__":
    # Run tests
    test_single_position_conservative()
    test_single_position_scalping()
    test_with_real_data()
    
    print("\n\n" + "="*60)
    print("INSIGHTS FROM TESTS")
    print("="*60)
    print("""
Look for:
1. Which exit type triggers most often?
2. Are targets being hit at the right prices?
3. Is the exit logic checking in the right order?
4. Are positions exiting too early?
""")