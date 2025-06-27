#!/usr/bin/env python3
"""
Test Relaxed Configuration with Backtesting
===========================================

Compare performance of standard vs relaxed signal generation
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import pandas as pd
import json
import numpy as np

from backtest_framework_enhanced import EnhancedBacktestEngine
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from scanner.enhanced_bar_processor_relaxed import EnhancedBarProcessorRelaxed
from config.settings import TradingConfig
from config.relaxed_settings import RelaxedTradingConfig
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def backtest_configuration(config_name: str, config, processor_class, symbol: str, df: pd.DataFrame):
    """Run backtest for a specific configuration"""
    
    print(f"\n{'='*60}")
    print(f"Backtesting: {config_name}")
    print(f"{'='*60}")
    
    # Create processor
    processor = processor_class(config, symbol, "5minute")
    
    # Default backtest parameters
    initial_capital = getattr(config, 'initial_capital', 100000)
    position_size_pct = getattr(config, 'position_size_percent', 10.0)
    commission_pct = getattr(config, 'commission_percent', 0.03)
    slippage_pct = getattr(config, 'slippage_percent', 0.05)
    stop_loss_pct = getattr(config, 'stop_loss_percent', 1.0)
    
    # Create backtest engine
    engine = EnhancedBacktestEngine(initial_capital=initial_capital)
    
    # Run backtest
    trades = []
    current_position = None
    entry_count = 0
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        if i < config.max_bars_back:
            continue
        
        # Handle exits first
        if current_position:
            # Check stop loss
            if current_position['type'] == 'long':
                if row['low'] <= current_position['stop_loss']:
                    exit_price = current_position['stop_loss']
                    exit_result = engine.exit_trade(exit_price, idx)
                    if exit_result:
                        trades.append(exit_result)
                    current_position = None
                    continue
            else:  # short
                if row['high'] >= current_position['stop_loss']:
                    exit_price = current_position['stop_loss']
                    exit_result = engine.exit_trade(exit_price, idx)
                    if exit_result:
                        trades.append(exit_result)
                    current_position = None
                    continue
            
            # Check fixed bar exit (5 bars)
            if i - current_position['entry_bar'] >= 5:
                exit_result = engine.exit_trade(row['close'], idx)
                if exit_result:
                    trades.append(exit_result)
                current_position = None
        
        # Handle new entries
        if not current_position:
            if result.start_long_trade:
                entry_count += 1
                if engine.enter_trade('long', row['close'], idx):
                    # Calculate stop loss
                    stop_loss = row['close'] * (1 - config.stop_loss_percent / 100)
                    current_position = {
                        'type': 'long',
                        'entry_bar': i,
                        'stop_loss': stop_loss
                    }
            
            elif result.start_short_trade:
                entry_count += 1
                if engine.enter_trade('short', row['close'], idx):
                    # Calculate stop loss
                    stop_loss = row['close'] * (1 + config.stop_loss_percent / 100)
                    current_position = {
                        'type': 'short',
                        'entry_bar': i,
                        'stop_loss': stop_loss
                    }
    
    # Close any open position
    if current_position:
        exit_result = engine.exit_trade(df.iloc[-1]['close'], df.index[-1])
        if exit_result:
            trades.append(exit_result)
    
    # Get performance metrics
    metrics = engine.get_performance_metrics()
    
    # Print results
    print(f"\n📊 RESULTS:")
    print(f"Total signals generated: {entry_count}")
    print(f"Total trades executed: {metrics['total_trades']}")
    print(f"Win rate: {metrics['win_rate']:.1f}%")
    print(f"Avg win: {metrics['avg_win']:.2f}%")
    print(f"Avg loss: {metrics['avg_loss']:.2f}%")
    print(f"Profit factor: {metrics['profit_factor']:.2f}")
    print(f"Total return: {metrics['total_return']:.2f}%")
    print(f"Max drawdown: {metrics['max_drawdown']:.2f}%")
    print(f"Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Win/loss ratio: {metrics['win_loss_ratio']:.2f}")
    
    return {
        'config': config_name,
        'trades': len(trades),
        'win_rate': metrics['win_rate'],
        'total_return': metrics['total_return'],
        'sharpe_ratio': metrics['sharpe_ratio'],
        'max_drawdown': metrics['max_drawdown'],
        'profit_factor': metrics['profit_factor']
    }


def main():
    """Compare standard vs relaxed configurations"""
    
    print("="*80)
    print("🔬 BACKTESTING STANDARD VS RELAXED SIGNAL GENERATION")
    print("="*80)
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
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
        ("Relaxed (no threshold)", RelaxedTradingConfig(), EnhancedBarProcessorRelaxed),
        ("Relaxed (ML threshold 2.0)", RelaxedTradingConfig(ml_prediction_threshold=2.0), EnhancedBarProcessorRelaxed)
    ]
    
    results = []
    
    for config_name, config, processor_class in configs:
        try:
            result = backtest_configuration(config_name, config, processor_class, symbol, df)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Error backtesting {config_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Compare results
    print("\n\n" + "="*80)
    print("📊 COMPARISON SUMMARY")
    print("="*80)
    
    results_df = pd.DataFrame(results)
    print("\n" + results_df.to_string(index=False))
    
    # Recommendations
    print("\n\n💡 RECOMMENDATIONS:")
    print("-"*60)
    
    if len(results) >= 2:
        standard_result = results[0]
        relaxed_result = results[1]
        
        if relaxed_result['trades'] > standard_result['trades'] * 3:
            print("✅ Relaxed configuration generates significantly more trades")
        
        if relaxed_result['win_rate'] > standard_result['win_rate']:
            print("✅ Relaxed configuration has better win rate")
        elif relaxed_result['win_rate'] < standard_result['win_rate'] - 5:
            print("⚠️  Relaxed configuration has lower win rate - may need tuning")
        
        if relaxed_result['sharpe_ratio'] > standard_result['sharpe_ratio']:
            print("✅ Relaxed configuration has better risk-adjusted returns")
        
        if relaxed_result['total_return'] > standard_result['total_return']:
            print("✅ Relaxed configuration has better total returns")
    
    # Save results
    results_df.to_csv('relaxed_backtest_results.csv', index=False)
    print(f"\n💾 Results saved to relaxed_backtest_results.csv")


if __name__ == "__main__":
    main()