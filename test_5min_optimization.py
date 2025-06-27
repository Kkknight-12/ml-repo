#!/usr/bin/env python3
"""
Fine-tune Lorentzian Classification for 5-minute timeframe
==========================================================

Test different exit strategies and parameters while keeping
the original restrictive entry conditions that work on TradingView
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import pandas as pd
import json
import numpy as np
from typing import Dict, List, Tuple

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
from config.ml_optimized_settings import MLOptimizedTradingConfig
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


class FiveMinuteOptimizer:
    """Optimize settings for 5-minute timeframe"""
    
    def __init__(self, symbol: str = "RELIANCE"):
        self.symbol = symbol
        self.cache = MarketDataCache()
        
    def test_configuration(self, config_name: str, config: TradingConfig, 
                         exit_strategy: Dict, df: pd.DataFrame) -> Dict:
        """Test a configuration with specific exit strategy"""
        
        print(f"\n{'='*60}")
        print(f"Testing: {config_name}")
        print(f"Exit Strategy: {exit_strategy['name']}")
        print(f"{'='*60}")
        
        # Create processor
        processor = EnhancedBarProcessor(config, self.symbol, "5minute")
        
        # Track trades
        trades = []
        current_position = None
        signals_generated = 0
        
        for i, (idx, row) in enumerate(df.iterrows()):
            result = processor.process_bar(
                row['open'], row['high'], row['low'], 
                row['close'], row['volume']
            )
            
            if i < config.max_bars_back:
                continue
            
            # Count signals
            if result.start_long_trade or result.start_short_trade:
                signals_generated += 1
            
            # Handle position management
            if current_position:
                bars_held = i - current_position['entry_bar']
                
                # Calculate current PnL
                if current_position['type'] == 'long':
                    current_pnl = (row['close'] - current_position['entry_price']) / current_position['entry_price'] * 100
                    high_pnl = (row['high'] - current_position['entry_price']) / current_position['entry_price'] * 100
                    low_pnl = (row['low'] - current_position['entry_price']) / current_position['entry_price'] * 100
                else:
                    current_pnl = (current_position['entry_price'] - row['close']) / current_position['entry_price'] * 100
                    high_pnl = (current_position['entry_price'] - row['low']) / current_position['entry_price'] * 100
                    low_pnl = (current_position['entry_price'] - row['high']) / current_position['entry_price'] * 100
                
                # Track MFE/MAE
                current_position['mfe'] = max(current_position['mfe'], high_pnl)
                current_position['mae'] = min(current_position['mae'], low_pnl)
                
                exit_price = None
                exit_reason = None
                
                # Apply exit strategy
                if exit_strategy['type'] == 'fixed_targets':
                    # Check stop loss
                    if low_pnl <= -exit_strategy['stop_loss']:
                        exit_price = current_position['stop_loss']
                        exit_reason = 'stop_loss'
                    # Check profit target
                    elif high_pnl >= exit_strategy['take_profit']:
                        if current_position['type'] == 'long':
                            exit_price = current_position['entry_price'] * (1 + exit_strategy['take_profit'] / 100)
                        else:
                            exit_price = current_position['entry_price'] * (1 - exit_strategy['take_profit'] / 100)
                        exit_reason = 'take_profit'
                    # Time exit
                    elif bars_held >= exit_strategy.get('max_bars', 5):
                        exit_price = row['close']
                        exit_reason = 'time_exit'
                
                elif exit_strategy['type'] == 'atr_based':
                    # ATR-based exits (would need ATR calculation)
                    # For now, use fixed percentages
                    atr_multiplier = exit_strategy['atr_multiplier']
                    stop_distance = 0.5 * atr_multiplier  # Approximate
                    target_distance = 1.0 * atr_multiplier
                    
                    if low_pnl <= -stop_distance:
                        exit_price = current_position['stop_loss']
                        exit_reason = 'atr_stop'
                    elif high_pnl >= target_distance:
                        if current_position['type'] == 'long':
                            exit_price = current_position['entry_price'] * (1 + target_distance / 100)
                        else:
                            exit_price = current_position['entry_price'] * (1 - target_distance / 100)
                        exit_reason = 'atr_target'
                    elif bars_held >= exit_strategy.get('max_bars', 10):
                        exit_price = row['close']
                        exit_reason = 'time_exit'
                
                elif exit_strategy['type'] == 'trailing_stop':
                    # Trailing stop
                    if current_position['mfe'] >= exit_strategy['activation']:
                        # Trail by specified amount
                        trailing_level = current_position['mfe'] - exit_strategy['trail_distance']
                        if current_pnl <= trailing_level:
                            exit_price = row['close']
                            exit_reason = 'trailing_stop'
                    
                    # Regular stop
                    if low_pnl <= -exit_strategy['stop_loss']:
                        exit_price = current_position['stop_loss']
                        exit_reason = 'stop_loss'
                    elif bars_held >= exit_strategy.get('max_bars', 10):
                        exit_price = row['close']
                        exit_reason = 'time_exit'
                
                # Process exit
                if exit_price:
                    # Calculate final PnL
                    if current_position['type'] == 'long':
                        final_pnl = (exit_price - current_position['entry_price']) / current_position['entry_price'] * 100
                    else:
                        final_pnl = (current_position['entry_price'] - exit_price) / current_position['entry_price'] * 100
                    
                    trade = {
                        'entry_bar': current_position['entry_bar'],
                        'exit_bar': i,
                        'bars_held': bars_held,
                        'type': current_position['type'],
                        'pnl': final_pnl,
                        'mfe': current_position['mfe'],
                        'mae': current_position['mae'],
                        'exit_reason': exit_reason,
                        'ml_strength': abs(current_position['ml_prediction'])
                    }
                    trades.append(trade)
                    current_position = None
            
            # New entries
            if not current_position:
                if result.start_long_trade:
                    stop_loss = exit_strategy.get('stop_loss', 1.0)
                    current_position = {
                        'type': 'long',
                        'entry_bar': i,
                        'entry_price': row['close'],
                        'stop_loss': row['close'] * (1 - stop_loss / 100),
                        'ml_prediction': result.prediction,
                        'mfe': 0,
                        'mae': 0
                    }
                elif result.start_short_trade:
                    stop_loss = exit_strategy.get('stop_loss', 1.0)
                    current_position = {
                        'type': 'short',
                        'entry_bar': i,
                        'entry_price': row['close'],
                        'stop_loss': row['close'] * (1 + stop_loss / 100),
                        'ml_prediction': result.prediction,
                        'mfe': 0,
                        'mae': 0
                    }
        
        # Calculate metrics
        if trades:
            trades_df = pd.DataFrame(trades)
            winners = trades_df[trades_df['pnl'] > 0]
            losers = trades_df[trades_df['pnl'] <= 0]
            
            metrics = {
                'config': config_name,
                'exit_strategy': exit_strategy['name'],
                'signals': signals_generated,
                'trades': len(trades),
                'win_rate': len(winners) / len(trades) * 100,
                'avg_win': winners['pnl'].mean() if len(winners) > 0 else 0,
                'avg_loss': losers['pnl'].mean() if len(losers) > 0 else 0,
                'avg_pnl': trades_df['pnl'].mean(),
                'profit_factor': abs(winners['pnl'].sum() / losers['pnl'].sum()) if len(losers) > 0 and losers['pnl'].sum() != 0 else 0,
                'avg_mfe': trades_df['mfe'].mean(),
                'avg_bars': trades_df['bars_held'].mean(),
                'time_exits': len(trades_df[trades_df['exit_reason'] == 'time_exit']) / len(trades) * 100
            }
            
            # Risk/reward ratio
            if metrics['avg_loss'] != 0:
                metrics['risk_reward'] = abs(metrics['avg_win'] / metrics['avg_loss'])
            else:
                metrics['risk_reward'] = metrics['avg_win']
            
            return metrics
        else:
            return {
                'config': config_name,
                'exit_strategy': exit_strategy['name'],
                'signals': signals_generated,
                'trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'avg_pnl': 0,
                'profit_factor': 0,
                'risk_reward': 0,
                'avg_mfe': 0,
                'avg_bars': 0,
                'time_exits': 0
            }
    
    def run_optimization(self):
        """Run comprehensive optimization for 5-minute timeframe"""
        
        print("="*80)
        print("🎯 FINE-TUNING FOR 5-MINUTE TIMEFRAME")
        print("="*80)
        
        # Get data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        df = self.cache.get_cached_data(self.symbol, start_date, end_date, "5minute")
        if df is None or df.empty:
            print("No data available")
            return
        
        print(f"\n📊 Testing on {len(df)} bars for {self.symbol}")
        print(f"   From: {df.index[0]}")
        print(f"   To: {df.index[-1]}")
        
        # Test configurations
        configs = [
            ("Original", TradingConfig()),
            ("ML Optimized", MLOptimizedTradingConfig())
        ]
        
        # Exit strategies optimized for 5-minute
        exit_strategies = [
            {
                'name': 'Original (5-bar)',
                'type': 'fixed_targets',
                'stop_loss': 1.0,
                'take_profit': 100.0,  # No target
                'max_bars': 5
            },
            {
                'name': 'Scalping (0.3%/0.5%)',
                'type': 'fixed_targets',
                'stop_loss': 0.5,
                'take_profit': 0.3,
                'max_bars': 10
            },
            {
                'name': 'Balanced (0.5%/0.75%)',
                'type': 'fixed_targets',
                'stop_loss': 0.75,
                'take_profit': 0.5,
                'max_bars': 15
            },
            {
                'name': 'Risk 1:2 (0.75%/1.5%)',
                'type': 'fixed_targets',
                'stop_loss': 0.75,
                'take_profit': 1.5,
                'max_bars': 20
            },
            {
                'name': 'ATR-based',
                'type': 'atr_based',
                'atr_multiplier': 1.5,
                'max_bars': 20
            },
            {
                'name': 'Trailing (0.5% activation)',
                'type': 'trailing_stop',
                'stop_loss': 1.0,
                'activation': 0.5,
                'trail_distance': 0.3,
                'max_bars': 20
            }
        ]
        
        # Run tests
        results = []
        
        for config_name, config in configs:
            for exit_strategy in exit_strategies:
                try:
                    metrics = self.test_configuration(config_name, config, exit_strategy, df)
                    results.append(metrics)
                    
                    # Print summary
                    if metrics['trades'] > 0:
                        print(f"\n📊 Results:")
                        print(f"   Trades: {metrics['trades']}")
                        print(f"   Win Rate: {metrics['win_rate']:.1f}%")
                        print(f"   Risk/Reward: {metrics['risk_reward']:.2f}")
                        print(f"   Avg PnL: {metrics['avg_pnl']:.2f}%")
                        print(f"   Time Exits: {metrics['time_exits']:.1f}%")
                    
                except Exception as e:
                    print(f"\n❌ Error testing {config_name} with {exit_strategy['name']}: {e}")
        
        # Analyze results
        if results:
            results_df = pd.DataFrame(results)
            
            print("\n\n" + "="*80)
            print("📊 OPTIMIZATION RESULTS")
            print("="*80)
            
            # Find best performers
            results_df['score'] = (
                results_df['win_rate'] * 0.3 +
                results_df['risk_reward'] * 20 +
                results_df['profit_factor'] * 10 -
                results_df['time_exits'] * 0.1
            )
            
            results_df = results_df.sort_values('score', ascending=False)
            
            print("\n🏆 TOP 5 CONFIGURATIONS:")
            print("-"*80)
            
            for i, row in results_df.head(5).iterrows():
                print(f"\n{i+1}. {row['config']} + {row['exit_strategy']}")
                print(f"   Trades: {row['trades']}")
                print(f"   Win Rate: {row['win_rate']:.1f}%")
                print(f"   Risk/Reward: {row['risk_reward']:.2f}")
                print(f"   Profit Factor: {row['profit_factor']:.2f}")
                print(f"   Avg PnL: {row['avg_pnl']:.2f}%")
                print(f"   Time Exits: {row['time_exits']:.1f}%")
            
            # Key insights
            print("\n\n💡 KEY INSIGHTS FOR 5-MINUTE:")
            print("-"*60)
            
            # Average MFE analysis
            avg_mfe = results_df['avg_mfe'].mean()
            print(f"\n1. Average Maximum Favorable Excursion: {avg_mfe:.2f}%")
            if avg_mfe < 0.5:
                print("   ⚠️ Very small moves - need tight stops and quick profits")
                print("   ✅ Scalping strategy (0.3-0.5% targets) recommended")
            elif avg_mfe < 1.0:
                print("   ✅ Moderate moves - balanced approach works")
                print("   ✅ 0.5-0.75% targets with 0.75% stops")
            else:
                print("   ✅ Good momentum - can use wider targets")
                print("   ✅ 1:2 risk/reward feasible")
            
            # Time exit analysis
            avg_time_exits = results_df['time_exits'].mean()
            print(f"\n2. Average Time Exits: {avg_time_exits:.1f}%")
            if avg_time_exits > 70:
                print("   ⚠️ Most trades don't reach targets")
                print("   ✅ Lower profit targets or use trailing stops")
            
            # Best performing strategy
            best_row = results_df.iloc[0]
            print(f"\n3. Best Configuration: {best_row['config']} + {best_row['exit_strategy']}")
            print(f"   Why: {best_row['win_rate']:.1f}% win rate with {best_row['risk_reward']:.2f} R:R")
            
            # Save results
            results_df.to_csv('5min_optimization_results.csv', index=False)
            print(f"\n💾 Detailed results saved to 5min_optimization_results.csv")
            
            return results_df


if __name__ == "__main__":
    optimizer = FiveMinuteOptimizer()
    results = optimizer.run_optimization()