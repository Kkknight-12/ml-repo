#!/usr/bin/env python3
"""
Verify 5-Min with EXACT Pine Script Logic
=========================================

No stop loss or take profit - exits only on signal change
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


def backtest_pine_logic(config, name="Pine Logic"):
    """
    Backtest with exact Pine Script logic - no stops/targets
    Exits only on signal change
    """
    print("\n" + "="*80)
    print(f"🎯 TESTING: {name}")
    print("="*80)
    print(config.get_description())
    
    # Get data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=config.lookback_days)
    
    cache = MarketDataCache()
    df = cache.get_cached_data(config.symbol, start_date, end_date, config.timeframe)
    
    if df is None or df.empty:
        print("No data available")
        return None
    
    print(f"\n📊 Data: {len(df)} bars")
    
    # Create processor
    processor = EnhancedBarProcessor(config, config.symbol, config.timeframe)
    
    # Track trades
    trades = []
    current_position = None
    equity = config.initial_capital
    
    ml_signals = 0
    filtered_signals = 0
    
    # Process bars
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        if result.signal != 0:
            ml_signals += 1
            if result.filter_all:
                filtered_signals += 1
        
        # PINE SCRIPT LOGIC: Exit on signal change or opposite entry
        if current_position:
            exit_trade = False
            exit_reason = None
            
            # Check for signal change
            if current_position['type'] == 'long':
                if result.signal <= 0 or result.start_short_trade:
                    exit_trade = True
                    exit_reason = 'signal_change'
            else:  # short
                if result.signal >= 0 or result.start_long_trade:
                    exit_trade = True
                    exit_reason = 'signal_change'
            
            # Check for dynamic exit (if enabled)
            if config.use_dynamic_exits:
                if (current_position['type'] == 'long' and result.end_long_trade) or \
                   (current_position['type'] == 'short' and result.end_short_trade):
                    exit_trade = True
                    exit_reason = 'dynamic_exit'
            
            if exit_trade:
                # Close position
                exit_price = result.close
                if current_position['type'] == 'long':
                    pnl_pct = (exit_price - current_position['entry_price']) / current_position['entry_price'] * 100
                else:  # short
                    pnl_pct = (current_position['entry_price'] - exit_price) / current_position['entry_price'] * 100
                
                pnl_pct -= config.commission_percent * 2  # Entry + exit commission
                
                trade_result = {
                    **current_position,
                    'exit_bar': i,
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'pnl_pct': pnl_pct,
                    'bars_held': i - current_position['entry_bar']
                }
                trades.append(trade_result)
                
                equity *= (1 + pnl_pct / 100)
                current_position = None
        
        # Check for new entry (only if no position)
        if not current_position:
            if result.start_long_trade:
                current_position = {
                    'type': 'long',
                    'entry_bar': i,
                    'entry_price': result.close,
                    'signal': result.signal,
                    'ml_prediction': result.prediction
                }
            elif result.start_short_trade:
                current_position = {
                    'type': 'short',
                    'entry_bar': i,
                    'entry_price': result.close,
                    'signal': result.signal,
                    'ml_prediction': result.prediction
                }
    
    # Close any open position at end
    if current_position:
        exit_price = df.iloc[-1]['close']
        if current_position['type'] == 'long':
            pnl_pct = (exit_price - current_position['entry_price']) / current_position['entry_price'] * 100
        else:
            pnl_pct = (current_position['entry_price'] - exit_price) / current_position['entry_price'] * 100
        
        pnl_pct -= config.commission_percent * 2
        
        trade_result = {
            **current_position,
            'exit_bar': len(df) - 1,
            'exit_price': exit_price,
            'exit_reason': 'end_of_data',
            'pnl_pct': pnl_pct,
            'bars_held': len(df) - 1 - current_position['entry_bar']
        }
        trades.append(trade_result)
    
    # Calculate metrics
    if trades:
        trade_df = pd.DataFrame(trades)
        wins = trade_df[trade_df['pnl_pct'] > 0]
        losses = trade_df[trade_df['pnl_pct'] <= 0]
        
        win_rate = len(wins) / len(trades) * 100
        avg_win = wins['pnl_pct'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl_pct'].mean() if len(losses) > 0 else 0
        
        total_return = (equity - config.initial_capital) / config.initial_capital * 100
        
        # Exit reason analysis
        exit_reasons = trade_df['exit_reason'].value_counts()
        
        print(f"\n📊 BACKTEST RESULTS (Pine Script Logic):")
        print("="*60)
        print(f"\nSignal Analysis:")
        print(f"  ML Signals: {ml_signals}")
        print(f"  After Filters: {filtered_signals} ({filtered_signals/ml_signals*100:.1f}%)")
        print(f"  Trades Executed: {len(trades)}")
        
        print(f"\nPerformance Metrics:")
        print(f"  Total Return: {total_return:.2f}%")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Avg Win: {avg_win:.2f}%")
        print(f"  Avg Loss: {avg_loss:.2f}%")
        print(f"  Avg Bars Held: {trade_df['bars_held'].mean():.1f}")
        
        print(f"\nExit Analysis:")
        for reason, count in exit_reasons.items():
            reason_trades = trade_df[trade_df['exit_reason'] == reason]
            avg_pnl = reason_trades['pnl_pct'].mean()
            print(f"  {reason}: {count} ({count/len(trades)*100:.1f}%), avg {avg_pnl:.2f}%")
        
        # Save trades
        filename = f"5min_pine_exact_{name.replace(' ', '_')}.csv"
        trade_df.to_csv(filename, index=False)
        print(f"\n💾 Trade details saved to {filename}")
        
        return {
            'config': name,
            'trades': len(trades),
            'win_rate': win_rate,
            'total_return': total_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_bars_held': trade_df['bars_held'].mean()
        }
    else:
        print("\n❌ No trades generated!")
        return {
            'config': name,
            'trades': 0,
            'win_rate': 0,
            'total_return': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'avg_bars_held': 0
        }


def main():
    """Run Pine Script exact backtest"""
    print("="*80)
    print("🎯 PINE SCRIPT EXACT LOGIC TEST (NO STOPS/TARGETS)")
    print("="*80)
    print("\nTrades exit only on:")
    print("1. Signal change (long → short or vice versa)")
    print("2. Dynamic exits (if enabled)")
    print("3. End of data")
    
    # Test with Pine Script exact settings
    configs = [
        (FIVEMIN_EXACT, "Pine Script Exact (No Stops/Targets)")
    ]
    
    results = []
    
    for config, name in configs:
        result = backtest_pine_logic(config, name)
        if result:
            results.append(result)
    
    # Summary
    if results:
        print("\n" + "="*80)
        print("📊 COMPARISON")
        print("="*80)
        
        results_df = pd.DataFrame(results)
        print(f"\n{results_df.to_string(index=False)}")
        
        print("\n💡 INSIGHTS:")
        print("- Pine Script uses signal changes for exits")
        print("- No fixed stops or targets")
        print("- Win rate depends on signal accuracy")
        print("- Average holding period shows signal persistence")


if __name__ == "__main__":
    main()