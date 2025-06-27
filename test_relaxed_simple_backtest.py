#!/usr/bin/env python3
"""
Simple Backtest of Relaxed Configuration
========================================

Quick performance comparison of standard vs relaxed signal generation
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import pandas as pd
import json
import numpy as np

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from scanner.enhanced_bar_processor_relaxed import EnhancedBarProcessorRelaxed
from config.settings import TradingConfig
from config.relaxed_settings import RelaxedTradingConfig, RELAXED_NO_THRESHOLD, RELAXED_WITH_THRESHOLD
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def simulate_trades(config_name: str, config, processor_class, symbol: str, df: pd.DataFrame):
    """Simulate trades and calculate performance"""
    
    print(f"\n{'='*60}")
    print(f"Testing: {config_name}")
    print(f"{'='*60}")
    
    # Create processor
    processor = processor_class(config, symbol, "5minute")
    
    # Default parameters
    stop_loss_pct = getattr(config, 'stop_loss_percent', 1.0)
    
    # Track trades
    trades = []
    current_position = None
    entry_signals = 0
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        if i < config.max_bars_back:
            continue
        
        # Handle exits first
        if current_position:
            exit_price = None
            exit_reason = None
            
            # Check stop loss
            if current_position['type'] == 'long':
                if row['low'] <= current_position['stop_loss']:
                    exit_price = current_position['stop_loss']
                    exit_reason = 'stop_loss'
            else:  # short
                if row['high'] >= current_position['stop_loss']:
                    exit_price = current_position['stop_loss']
                    exit_reason = 'stop_loss'
            
            # Check fixed bar exit (5 bars)
            if not exit_price and i - current_position['entry_bar'] >= 5:
                exit_price = row['close']
                exit_reason = 'time_exit'
            
            if exit_price:
                # Calculate PnL
                if current_position['type'] == 'long':
                    pnl_pct = (exit_price - current_position['entry_price']) / current_position['entry_price'] * 100
                else:
                    pnl_pct = (current_position['entry_price'] - exit_price) / current_position['entry_price'] * 100
                
                trades.append({
                    'entry_bar': current_position['entry_bar'],
                    'exit_bar': i,
                    'entry_price': current_position['entry_price'],
                    'exit_price': exit_price,
                    'type': current_position['type'],
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason
                })
                current_position = None
        
        # Handle new entries
        if not current_position:
            if result.start_long_trade:
                entry_signals += 1
                current_position = {
                    'type': 'long',
                    'entry_bar': i,
                    'entry_price': row['close'],
                    'stop_loss': row['close'] * (1 - stop_loss_pct / 100)
                }
            
            elif result.start_short_trade:
                entry_signals += 1
                current_position = {
                    'type': 'short',
                    'entry_bar': i,
                    'entry_price': row['close'],
                    'stop_loss': row['close'] * (1 + stop_loss_pct / 100)
                }
    
    # Calculate metrics
    if trades:
        pnls = [t['pnl_pct'] for t in trades]
        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p <= 0]
        
        win_rate = len(winners) / len(trades) * 100
        avg_win = np.mean(winners) if winners else 0
        avg_loss = np.mean(losers) if losers else 0
        
        # Calculate total return (compound)
        capital = 100
        for pnl in pnls:
            capital *= (1 + pnl / 100)
        total_return = capital - 100
        
        # Risk metrics
        returns = np.array(pnls) / 100
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Win/loss ratio
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else avg_win
        
        # Profit factor
        gross_profit = sum(winners)
        gross_loss = abs(sum(losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit
        
    else:
        win_rate = avg_win = avg_loss = total_return = sharpe = win_loss_ratio = profit_factor = 0
    
    # Print results
    print(f"\n📊 RESULTS:")
    print(f"Entry signals: {entry_signals}")
    print(f"Trades executed: {len(trades)}")
    print(f"Win rate: {win_rate:.1f}%")
    print(f"Avg win: {avg_win:.2f}%")
    print(f"Avg loss: {avg_loss:.2f}%")
    print(f"Win/loss ratio: {win_loss_ratio:.2f}")
    print(f"Profit factor: {profit_factor:.2f}")
    print(f"Total return: {total_return:.2f}%")
    print(f"Sharpe ratio: {sharpe:.2f}")
    
    # Show sample trades
    if trades:
        print(f"\nSample trades (first 5):")
        for i, trade in enumerate(trades[:5]):
            print(f"  Trade {i+1}: {trade['type']}, PnL: {trade['pnl_pct']:.2f}%, Exit: {trade['exit_reason']}")
    
    return {
        'config': config_name,
        'signals': entry_signals,
        'trades': len(trades),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'win_loss_ratio': win_loss_ratio,
        'profit_factor': profit_factor,
        'total_return': total_return,
        'sharpe_ratio': sharpe
    }


def main():
    """Compare configurations"""
    
    print("="*80)
    print("🔬 SIMPLE BACKTEST: STANDARD VS RELAXED CONFIGURATIONS")
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
    
    print(f"\n📊 Data loaded: {len(df)} bars")
    print(f"   From: {df.index[0]}")
    print(f"   To: {df.index[-1]}")
    
    # Test configurations
    configs = [
        ("Standard (restrictive)", TradingConfig(), EnhancedBarProcessor),
        ("Relaxed (no threshold)", RELAXED_NO_THRESHOLD, EnhancedBarProcessorRelaxed),
        ("Relaxed (ML threshold 2.0)", RELAXED_WITH_THRESHOLD, EnhancedBarProcessorRelaxed)
    ]
    
    results = []
    
    for config_name, config, processor_class in configs:
        try:
            result = simulate_trades(config_name, config, processor_class, symbol, df)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Error testing {config_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Compare results
    print("\n\n" + "="*80)
    print("📊 COMPARISON SUMMARY")
    print("="*80)
    
    if results:
        # Print comparison table
        print(f"\n{'Config':<25} {'Signals':>8} {'Trades':>8} {'Win%':>8} {'Ret%':>8} {'Sharpe':>8} {'PF':>8}")
        print("-"*80)
        for r in results:
            print(f"{r['config']:<25} {r['signals']:>8} {r['trades']:>8} "
                  f"{r['win_rate']:>7.1f}% {r['total_return']:>7.1f}% "
                  f"{r['sharpe_ratio']:>8.2f} {r['profit_factor']:>8.2f}")
        
        # Analysis
        print("\n\n💡 KEY INSIGHTS:")
        print("-"*60)
        
        if len(results) >= 2:
            standard = results[0]
            relaxed = results[1]
            
            signal_increase = (relaxed['signals'] - standard['signals']) / standard['signals'] * 100 if standard['signals'] > 0 else 0
            print(f"📈 Signal increase: {signal_increase:+.0f}%")
            
            if relaxed['trades'] > standard['trades'] * 2:
                print("✅ Relaxed config generates significantly more trades")
            
            if relaxed['win_rate'] > standard['win_rate']:
                print(f"✅ Improved win rate: {standard['win_rate']:.1f}% → {relaxed['win_rate']:.1f}%")
            else:
                print(f"⚠️  Lower win rate: {standard['win_rate']:.1f}% → {relaxed['win_rate']:.1f}%")
            
            if relaxed['sharpe_ratio'] > standard['sharpe_ratio']:
                print("✅ Better risk-adjusted returns (Sharpe)")
            
            if relaxed['profit_factor'] > standard['profit_factor']:
                print("✅ Better profit factor")
        
        # Save results
        results_df = pd.DataFrame(results)
        results_df.to_csv('relaxed_simple_backtest.csv', index=False)
        print(f"\n💾 Results saved to relaxed_simple_backtest.csv")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()