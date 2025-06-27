#!/usr/bin/env python3
"""
Test Optimized Exit Strategy
============================

Simulate how multi-target exits would improve the relaxed configuration
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import pandas as pd
import json
import numpy as np

from scanner.enhanced_bar_processor_relaxed import EnhancedBarProcessorRelaxed
from config.relaxed_optimized_settings import RELAXED_OPTIMIZED_V1
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def simulate_optimized_exits():
    """Simulate trades with optimized exit strategy"""
    
    print("="*80)
    print("🎯 TESTING OPTIMIZED EXIT STRATEGY")
    print("="*80)
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # Get data
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return
    
    print(f"\n📊 Testing on {len(df)} bars for {symbol}")
    
    # Create processor
    config = RELAXED_OPTIMIZED_V1
    processor = EnhancedBarProcessorRelaxed(config, symbol, "5minute")
    
    # Track trades with detailed exit info
    trades = []
    current_position = None
    
    print(f"\n📋 Configuration:")
    print(f"   Stop Loss: {config.stop_loss_percent}%")
    print(f"   Target 1: {config.target_1_r_multiple * config.stop_loss_percent:.1f}% @ {config.target_1_percent}%")
    print(f"   Target 2: {config.target_2_r_multiple * config.stop_loss_percent:.1f}% @ {config.target_2_percent}%")
    print(f"   Target 3: {config.target_3_r_multiple * config.stop_loss_percent:.1f}% @ {config.target_3_percent}%")
    print(f"   Trailing: {config.trailing_stop_distance}% after {config.trailing_stop_activation}%")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        if i < config.max_bars_back:
            continue
        
        # Handle position management
        if current_position:
            bars_held = i - current_position['entry_bar']
            
            # Calculate current PnL
            if current_position['type'] == 'long':
                current_pnl = (row['close'] - current_position['entry_price']) / current_position['entry_price'] * 100
                high_pnl = (row['high'] - current_position['entry_price']) / current_position['entry_price'] * 100
                low_pnl = (row['low'] - current_position['entry_price']) / current_position['entry_price'] * 100
            else:  # short
                current_pnl = (current_position['entry_price'] - row['close']) / current_position['entry_price'] * 100
                high_pnl = (current_position['entry_price'] - row['low']) / current_position['entry_price'] * 100
                low_pnl = (current_position['entry_price'] - row['high']) / current_position['entry_price'] * 100
            
            # Update highest profit
            current_position['highest_pnl'] = max(current_position['highest_pnl'], high_pnl)
            
            exit_price = None
            exit_reason = None
            partial_exit = False
            
            # Check stop loss
            if low_pnl <= -config.stop_loss_percent:
                exit_price = current_position['stop_loss']
                exit_reason = 'stop_loss'
                
            # Check targets (if position not fully exited)
            elif current_position['position_remaining'] > 0:
                # Target 1
                if not current_position['target_1_hit'] and high_pnl >= config.target_1_r_multiple * config.stop_loss_percent:
                    current_position['target_1_hit'] = True
                    current_position['position_remaining'] -= config.target_1_percent
                    partial_exit = True
                    
                    # Move stop to breakeven
                    current_position['stop_loss'] = current_position['entry_price']
                    
                    # Record partial exit
                    partial_pnl = config.target_1_r_multiple * config.stop_loss_percent
                    current_position['partial_exits'].append({
                        'bar': i,
                        'percent_exited': config.target_1_percent,
                        'exit_price': current_position['entry_price'] * (1 + partial_pnl/100),
                        'pnl': partial_pnl
                    })
                
                # Target 2
                if current_position['target_1_hit'] and not current_position['target_2_hit'] and \
                   high_pnl >= config.target_2_r_multiple * config.stop_loss_percent:
                    current_position['target_2_hit'] = True
                    current_position['position_remaining'] -= config.target_2_percent
                    partial_exit = True
                    
                    # Move stop to target 1
                    current_position['stop_loss'] = current_position['entry_price'] * \
                        (1 + config.target_1_r_multiple * config.stop_loss_percent / 100)
                    
                    # Record partial exit
                    partial_pnl = config.target_2_r_multiple * config.stop_loss_percent
                    current_position['partial_exits'].append({
                        'bar': i,
                        'percent_exited': config.target_2_percent,
                        'exit_price': current_position['entry_price'] * (1 + partial_pnl/100),
                        'pnl': partial_pnl
                    })
                
                # Trailing stop (after target 1)
                if current_position['target_1_hit'] and high_pnl >= config.trailing_stop_activation:
                    trailing_stop = current_position['entry_price'] * \
                        (1 + (current_position['highest_pnl'] - config.trailing_stop_distance) / 100)
                    current_position['stop_loss'] = max(current_position['stop_loss'], trailing_stop)
            
            # Check time exit
            if not exit_price and bars_held >= config.fixed_exit_bars:
                exit_price = row['close']
                exit_reason = 'time_exit'
            
            # Process exit
            if exit_price:
                # Calculate weighted PnL
                total_pnl = 0
                position_exited = 0
                
                # Add partial exits
                for partial in current_position['partial_exits']:
                    total_pnl += partial['pnl'] * (partial['percent_exited'] / 100)
                    position_exited += partial['percent_exited']
                
                # Add final exit
                remaining = 100 - position_exited
                if remaining > 0:
                    if current_position['type'] == 'long':
                        final_pnl = (exit_price - current_position['entry_price']) / current_position['entry_price'] * 100
                    else:
                        final_pnl = (current_position['entry_price'] - exit_price) / current_position['entry_price'] * 100
                    
                    total_pnl += final_pnl * (remaining / 100)
                
                trade = {
                    'entry_bar': current_position['entry_bar'],
                    'exit_bar': i,
                    'bars_held': bars_held,
                    'type': current_position['type'],
                    'entry_price': current_position['entry_price'],
                    'exit_price': exit_price,
                    'pnl_pct': total_pnl,
                    'highest_pnl': current_position['highest_pnl'],
                    'exit_reason': exit_reason,
                    'targets_hit': sum([current_position['target_1_hit'], current_position['target_2_hit']]),
                    'partial_exits': len(current_position['partial_exits'])
                }
                trades.append(trade)
                current_position = None
        
        # New entries
        if not current_position:
            if result.start_long_trade:
                current_position = {
                    'type': 'long',
                    'entry_bar': i,
                    'entry_price': row['close'],
                    'stop_loss': row['close'] * (1 - config.stop_loss_percent / 100),
                    'ml_prediction': result.prediction,
                    'highest_pnl': 0,
                    'position_remaining': 100,
                    'target_1_hit': False,
                    'target_2_hit': False,
                    'partial_exits': []
                }
            elif result.start_short_trade:
                current_position = {
                    'type': 'short',
                    'entry_bar': i,
                    'entry_price': row['close'],
                    'stop_loss': row['close'] * (1 + config.stop_loss_percent / 100),
                    'ml_prediction': result.prediction,
                    'highest_pnl': 0,
                    'position_remaining': 100,
                    'target_1_hit': False,
                    'target_2_hit': False,
                    'partial_exits': []
                }
    
    # Analyze results
    if not trades:
        print("\nNo trades to analyze")
        return
    
    trades_df = pd.DataFrame(trades)
    
    print(f"\n\n📊 OPTIMIZED EXIT RESULTS ({len(trades)} trades):")
    print("="*60)
    
    # Basic stats
    winners = trades_df[trades_df['pnl_pct'] > 0]
    losers = trades_df[trades_df['pnl_pct'] <= 0]
    
    print(f"\n1. PERFORMANCE METRICS:")
    print(f"   Total trades: {len(trades)}")
    print(f"   Winners: {len(winners)} ({len(winners)/len(trades)*100:.1f}%)")
    print(f"   Avg PnL: {trades_df['pnl_pct'].mean():.2f}%")
    print(f"   Avg Win: {winners['pnl_pct'].mean():.2f}%" if len(winners) > 0 else "   Avg Win: N/A")
    print(f"   Avg Loss: {losers['pnl_pct'].mean():.2f}%" if len(losers) > 0 else "   Avg Loss: N/A")
    
    # Calculate profit factor
    if len(winners) > 0 and len(losers) > 0:
        gross_profit = winners['pnl_pct'].sum()
        gross_loss = abs(losers['pnl_pct'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit
        win_loss_ratio = winners['pnl_pct'].mean() / abs(losers['pnl_pct'].mean())
        print(f"   Profit Factor: {profit_factor:.2f}")
        print(f"   Win/Loss Ratio: {win_loss_ratio:.2f}")
    
    # Target analysis
    print(f"\n2. TARGET ACHIEVEMENT:")
    trades_with_targets = trades_df[trades_df['targets_hit'] > 0]
    print(f"   Trades hitting targets: {len(trades_with_targets)} ({len(trades_with_targets)/len(trades)*100:.1f}%)")
    if len(trades_with_targets) > 0:
        print(f"   - 1+ targets: {len(trades_df[trades_df['targets_hit'] >= 1])}")
        print(f"   - 2+ targets: {len(trades_df[trades_df['targets_hit'] >= 2])}")
        print(f"   Avg PnL (with targets): {trades_with_targets['pnl_pct'].mean():.2f}%")
    
    # Exit reason analysis
    print(f"\n3. EXIT REASONS:")
    for reason, group in trades_df.groupby('exit_reason'):
        print(f"   {reason}: {len(group)} trades ({len(group)/len(trades)*100:.1f}%), "
              f"avg PnL: {group['pnl_pct'].mean():.2f}%")
    
    # Profit capture
    print(f"\n4. PROFIT CAPTURE:")
    avg_highest = trades_df['highest_pnl'].mean()
    avg_realized = trades_df['pnl_pct'].mean()
    capture_rate = (avg_realized / avg_highest * 100) if avg_highest > 0 else 0
    print(f"   Avg highest PnL: {avg_highest:.2f}%")
    print(f"   Avg realized PnL: {avg_realized:.2f}%")
    print(f"   Capture rate: {capture_rate:.1f}%")
    
    # Compare with simple exit
    print(f"\n\n💡 COMPARISON WITH SIMPLE EXIT:")
    print("="*60)
    print(f"Simple exit (5-bar): -0.02% avg PnL, 47.5% win rate")
    print(f"Optimized exit: {trades_df['pnl_pct'].mean():.2f}% avg PnL, "
          f"{len(winners)/len(trades)*100:.1f}% win rate")
    
    improvement = trades_df['pnl_pct'].mean() - (-0.02)
    print(f"\n📈 Improvement: {improvement:+.2f}% per trade")
    
    # Save results
    trades_df.to_csv('optimized_exit_results.csv', index=False)
    print(f"\n💾 Results saved to optimized_exit_results.csv")


if __name__ == "__main__":
    simulate_optimized_exits()