#!/usr/bin/env python3
"""
Verify Final 5-Minute Configuration
===================================

Test the optimized 5-minute settings with proper backtesting
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import pandas as pd
import json
import numpy as np

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.fivemin_exact_settings import FIVEMIN_EXACT
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def backtest_5min_config(config, config_name: str, use_pine_logic: bool = False):
    """Run detailed backtest of 5-minute configuration
    
    Args:
        config: Configuration object
        config_name: Name of the configuration
        use_pine_logic: If True, use Pine Script's exact ml.backtest() logic
    """
    
    print(f"\n{'='*80}")
    print(f"🎯 TESTING: {config_name}")
    if use_pine_logic:
        print("📌 Using Pine Script ml.backtest() logic")
    print(f"{'='*80}")
    
    print(config.get_description())
    
    # Get data
    symbol = config.symbol
    end_date = datetime.now()
    start_date = end_date - timedelta(days=config.lookback_days)
    
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return None
    
    # Check if index is datetime, if not, try to convert or skip time filtering
    has_datetime_index = isinstance(df.index, pd.DatetimeIndex)
    
    if has_datetime_index:
        print(f"\n📊 Data: {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    else:
        print(f"\n📊 Data: {len(df)} bars (no datetime index, time filtering disabled)")
        # If there's a 'date' or 'datetime' column, set it as index
        if 'datetime' in df.columns:
            df = df.set_index('datetime')
            has_datetime_index = True
        elif 'date' in df.columns:
            df = df.set_index('date')
            has_datetime_index = True
    
    # Create processor
    processor = EnhancedBarProcessor(config, symbol, "5minute")
    
    # Track detailed metrics
    trades = []
    current_position = None
    equity = config.initial_capital
    equity_curve = [equity]
    
    ml_signals = 0
    filtered_signals = 0
    
    # Pine Script ml.backtest() tracking variables
    if use_pine_logic:
        start_long_trade = 0.0
        start_short_trade = 0.0
        total_short_profit = 0.0
        total_long_profit = 0.0
        wins = 0
        losses = 0
        trade_count = 0
        early_signal_flip_count = 0
    
    for i, (idx, row) in enumerate(df.iterrows()):
        # Skip market open/close if configured and we have datetime index
        if has_datetime_index and isinstance(idx, pd.Timestamp):
            time_of_day = idx.time()
            if config.avoid_first_minutes > 0:
                market_open = pd.Timestamp(f"{idx.date()} {config.market_open_time}").time()
                first_trade_time = (pd.Timestamp(f"{idx.date()} {config.market_open_time}") + 
                                  timedelta(minutes=config.avoid_first_minutes)).time()
                if market_open <= time_of_day < first_trade_time:
                    continue
            
            if config.avoid_last_minutes > 0:
                market_close = pd.Timestamp(f"{idx.date()} {config.market_close_time}").time()
                last_trade_time = (pd.Timestamp(f"{idx.date()} {config.market_close_time}") - 
                                 timedelta(minutes=config.avoid_last_minutes)).time()
                if last_trade_time < time_of_day <= market_close:
                    continue
        
        # Process bar
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        if i < config.max_bars_back:
            continue
        
        # Track ML signals
        if result.signal != 0:
            ml_signals += 1
            if result.filter_all:
                filtered_signals += 1
        
        # Pine Script ml.backtest() logic
        if use_pine_logic and i >= config.max_bars_back:
            # Calculate market price as per Pine Script
            market_price = result.close if config.use_worst_case else (row['high'] + row['low'] + row['open'] + row['open']) / 4
            
            # Reset counters for this bar
            if i == config.max_bars_back:
                trade_count = 0
                wins = 0
                losses = 0
                early_signal_flip_count = 0
            
            # Handle trade starts and ends
            if result.start_long_trade:
                start_short_trade = 0.0
                early_signal_flip_count = 1 if hasattr(result, 'is_early_signal_flip') and result.is_early_signal_flip else 0
                start_long_trade = market_price
                trade_count = 1
                # Track position entry for bar counting
                if not current_position:
                    current_position = {
                        'type': 'long',
                        'entry_bar': i,
                        'entry_date': idx if has_datetime_index else i,
                        'entry_price': market_price
                    }
            
            if result.end_long_trade and start_long_trade > 0:
                delta = market_price - start_long_trade
                wins = 1 if delta > 0 else 0
                losses = 1 if delta < 0 else 0
                total_long_profit = delta * 1  # lot_size = 1
                
                # Record trade
                trade = {
                    'entry_date': current_position['entry_date'] if current_position else idx,
                    'exit_date': idx,
                    'type': 'long',
                    'entry_price': start_long_trade,
                    'exit_price': market_price,
                    'pnl_pct': delta / start_long_trade * 100,
                    'pnl_amount': total_long_profit,
                    'bars_held': i - (current_position['entry_bar'] if current_position else i),
                    'exit_reason': 'pine_signal',
                    'ml_strength': abs(result.prediction)
                }
                trades.append(trade)
                start_long_trade = 0.0
                current_position = None
            
            if result.start_short_trade:
                start_long_trade = 0.0
                start_short_trade = market_price
                trade_count = 1
                # Track position entry for bar counting
                if not current_position:
                    current_position = {
                        'type': 'short',
                        'entry_bar': i,
                        'entry_date': idx if has_datetime_index else i,
                        'entry_price': market_price
                    }
            
            if result.end_short_trade and start_short_trade > 0:
                early_signal_flip_count = 1 if hasattr(result, 'is_early_signal_flip') and result.is_early_signal_flip else 0
                delta = start_short_trade - market_price
                wins = 1 if delta > 0 else 0
                losses = 1 if delta < 0 else 0
                total_short_profit = delta * 1  # lot_size = 1
                
                # Record trade
                trade = {
                    'entry_date': current_position['entry_date'] if current_position else idx,
                    'exit_date': idx,
                    'type': 'short',
                    'entry_price': start_short_trade,
                    'exit_price': market_price,
                    'pnl_pct': delta / start_short_trade * 100,
                    'pnl_amount': total_short_profit,
                    'bars_held': i - (current_position['entry_bar'] if current_position else i),
                    'exit_reason': 'pine_signal',
                    'ml_strength': abs(result.prediction)
                }
                trades.append(trade)
                start_short_trade = 0.0
                current_position = None
            
            # Skip regular position handling if using Pine logic
            continue
        
        # Handle position (regular logic)
        if current_position:
            bars_held = i - current_position['entry_bar']
            
            # Calculate PnL
            if current_position['type'] == 'long':
                current_pnl = (row['close'] - current_position['entry_price']) / current_position['entry_price'] * 100
                high_pnl = (row['high'] - current_position['entry_price']) / current_position['entry_price'] * 100
                low_pnl = (row['low'] - current_position['entry_price']) / current_position['entry_price'] * 100
            else:
                current_pnl = (current_position['entry_price'] - row['close']) / current_position['entry_price'] * 100
                high_pnl = (current_position['entry_price'] - row['low']) / current_position['entry_price'] * 100
                low_pnl = (current_position['entry_price'] - row['high']) / current_position['entry_price'] * 100
            
            exit_price = None
            exit_reason = None
            
            # Multi-target exit logic
            if config.use_multi_targets and current_position['position_size'] > 0:
                # Check targets
                if high_pnl >= config.target_1_percent and not current_position.get('target_1_hit'):
                    # Partial exit at target 1
                    exit_size = config.target_1_size / 100 * current_position['original_size']
                    partial_pnl = config.target_1_percent * (exit_size / current_position['original_size'])
                    current_position['realized_pnl'] += partial_pnl
                    current_position['position_size'] -= exit_size
                    current_position['target_1_hit'] = True
                    
                    # Move stop to breakeven
                    current_position['stop_loss'] = current_position['entry_price']
                
                if high_pnl >= config.target_2_percent and not current_position.get('target_2_hit'):
                    # Partial exit at target 2
                    exit_size = config.target_2_size / 100 * current_position['original_size']
                    partial_pnl = config.target_2_percent * (exit_size / current_position['original_size'])
                    current_position['realized_pnl'] += partial_pnl
                    current_position['position_size'] -= exit_size
                    current_position['target_2_hit'] = True
                
                # Trailing stop
                if config.use_trailing_stop and high_pnl >= config.trailing_activation_percent:
                    current_position['highest_pnl'] = max(current_position.get('highest_pnl', 0), high_pnl)
                    trailing_stop_pnl = current_position['highest_pnl'] - config.trailing_distance_percent
                    if current_pnl <= trailing_stop_pnl:
                        exit_price = row['close']
                        exit_reason = 'trailing_stop'
            
            # Regular exit checks
            if not exit_price:
                # Stop loss
                if low_pnl <= -config.stop_loss_percent:
                    exit_price = current_position['stop_loss']
                    exit_reason = 'stop_loss'
                # Take profit (if not using multi-targets)
                elif not config.use_multi_targets and high_pnl >= config.take_profit_percent:
                    if current_position['type'] == 'long':
                        exit_price = current_position['entry_price'] * (1 + config.take_profit_percent / 100)
                    else:
                        exit_price = current_position['entry_price'] * (1 - config.take_profit_percent / 100)
                    exit_reason = 'take_profit'
                # Time exit
                elif bars_held >= config.fixed_exit_bars:
                    exit_price = row['close']
                    exit_reason = 'time_exit'
            
            # Process exit
            if exit_price:
                # Calculate final PnL
                if config.use_multi_targets:
                    remaining_size = current_position['position_size']
                    if remaining_size > 0:
                        if current_position['type'] == 'long':
                            final_pnl = (exit_price - current_position['entry_price']) / current_position['entry_price'] * 100
                        else:
                            final_pnl = (current_position['entry_price'] - exit_price) / current_position['entry_price'] * 100
                        
                        final_pnl = final_pnl * (remaining_size / current_position['original_size'])
                        total_pnl = current_position['realized_pnl'] + final_pnl
                    else:
                        total_pnl = current_position['realized_pnl']
                else:
                    if current_position['type'] == 'long':
                        total_pnl = (exit_price - current_position['entry_price']) / current_position['entry_price'] * 100
                    else:
                        total_pnl = (current_position['entry_price'] - exit_price) / current_position['entry_price'] * 100
                
                # Update equity
                position_value = equity * (config.position_size_percent / 100)
                pnl_amount = position_value * (total_pnl / 100)
                equity += pnl_amount
                equity_curve.append(equity)
                
                trade = {
                    'entry_date': current_position['entry_date'],
                    'exit_date': idx if has_datetime_index else i,
                    'type': current_position['type'],
                    'entry_price': current_position['entry_price'],
                    'exit_price': exit_price,
                    'pnl_pct': total_pnl,
                    'pnl_amount': pnl_amount,
                    'bars_held': bars_held,
                    'exit_reason': exit_reason,
                    'ml_strength': abs(current_position['ml_prediction'])
                }
                trades.append(trade)
                current_position = None
        
        # New entries
        if not current_position:
            if result.start_long_trade:
                current_position = {
                    'type': 'long',
                    'entry_bar': i,
                    'entry_date': idx if has_datetime_index else i,
                    'entry_price': row['close'],
                    'stop_loss': row['close'] * (1 - config.stop_loss_percent / 100),
                    'ml_prediction': result.prediction,
                    'position_size': 100,
                    'original_size': 100,
                    'realized_pnl': 0
                }
            elif result.start_short_trade:
                current_position = {
                    'type': 'short',
                    'entry_bar': i,
                    'entry_date': idx if has_datetime_index else i,
                    'entry_price': row['close'],
                    'stop_loss': row['close'] * (1 + config.stop_loss_percent / 100),
                    'ml_prediction': result.prediction,
                    'position_size': 100,
                    'original_size': 100,
                    'realized_pnl': 0
                }
    
    # Calculate final metrics
    if trades:
        trades_df = pd.DataFrame(trades)
        
        # Performance metrics
        total_return = (equity - config.initial_capital) / config.initial_capital * 100
        
        winners = trades_df[trades_df['pnl_pct'] > 0]
        losers = trades_df[trades_df['pnl_pct'] <= 0]
        
        win_rate = len(winners) / len(trades) * 100
        avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
        avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0
        
        # Risk metrics
        returns = trades_df['pnl_pct'].values / 100
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252.0 * 75.0) if np.std(returns) > 0 else 0  # 75 bars per day
        
        # Drawdown
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max * 100
        max_drawdown = drawdown.min()
        
        print(f"\n📊 BACKTEST RESULTS{' (Pine Script Logic)' if use_pine_logic else ''}:")
        print(f"{'='*60}")
        print(f"\nSignal Analysis:")
        print(f"  ML Signals: {ml_signals}")
        print(f"  After Filters: {filtered_signals} ({filtered_signals/ml_signals*100:.1f}%)")
        print(f"  Trades Executed: {len(trades)}")
        
        print(f"\nPerformance Metrics:")
        print(f"  Total Return: {total_return:.2f}%")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Avg Win: {avg_win:.2f}%")
        print(f"  Avg Loss: {avg_loss:.2f}%")
        print(f"  Risk/Reward: {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "  Risk/Reward: N/A")
        if not use_pine_logic:
            print(f"  Sharpe Ratio: {sharpe:.2f}")
            print(f"  Max Drawdown: {max_drawdown:.2f}%")
        
        # Exit analysis
        print(f"\nExit Analysis:")
        for reason, group in trades_df.groupby('exit_reason'):
            count = len(group)
            pct = count / len(trades) * 100
            avg_pnl = group['pnl_pct'].mean()
            print(f"  {reason}: {count} ({pct:.1f}%), avg {avg_pnl:.2f}%")
        
        # Save results
        trades_df.to_csv(f'5min_final_{config_name.replace(" ", "_")}.csv', index=False)
        print(f"\n💾 Trade details saved to 5min_final_{config_name.replace(' ', '_')}.csv")
        
        return {
            'config': config_name,
            'trades': len(trades),
            'win_rate': win_rate,
            'total_return': total_return,
            'sharpe': sharpe,
            'max_dd': max_drawdown
        }
    else:
        print("\n❌ No trades generated!")
        return None


def main():
    """Test optimized 5-minute configurations"""
    
    print("="*80)
    print("🎯 FINAL VERIFICATION: 5-MINUTE OPTIMIZED CONFIGURATIONS")
    print("="*80)
    
    # Test configuration - using exact Pine Script settings
    configs = [
        (FIVEMIN_EXACT, "5-Min Exact Pine Script Settings", False),
        (FIVEMIN_EXACT, "5-Min Pine Script ml.backtest() Logic", True)
    ]
    
    results = []
    
    for config, name, use_pine in configs:
        result = backtest_5min_config(config, name, use_pine_logic=use_pine)
        if result:
            results.append(result)
    
    # Summary
    if results:
        print("\n\n" + "="*80)
        print("📊 FINAL COMPARISON")
        print("="*80)
        
        results_df = pd.DataFrame(results)
        print("\n" + results_df.to_string(index=False))
        
        print("\n\n🔍 PINE SCRIPT VS REGULAR BACKTESTING:")
        print("-"*60)
        print("Pine Script ml.backtest() logic:")
        print("- Uses market price: (high + low + open + open) / 4")
        print("- Exits only on signal changes")
        print("- No stop loss or take profit targets")
        print("- Win/loss calculated at trade end only")
        print("\nRegular backtesting:")
        print("- Uses exact entry/exit prices")
        print("- Implements stop loss and take profit")
        print("- Multi-target exit system")
        print("- More realistic for actual trading")
        
        print("\n\n✅ RECOMMENDATIONS:")
        print("-"*60)
        print("1. Pine Script shows theoretical signal accuracy")
        print("2. Regular backtesting shows practical trading results")
        print("3. Use Pine Script metrics to validate ML model")
        print("4. Use regular backtesting for actual trading expectations")


if __name__ == "__main__":
    main()