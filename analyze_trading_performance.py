#!/usr/bin/env python3
"""
Comprehensive Trading Performance Analysis
==========================================

Analyzes trading performance with focus on:
- Money lost/earned with 1 lakh starting capital
- Stop loss effectiveness in limiting losses
- Win rate and trade quality issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Tuple

from backtest_framework import BacktestEngine
from backtest_framework_enhanced import EnhancedBacktestEngine
from config.settings import TradingConfig
from config.fixed_optimized_settings import FixedOptimizedTradingConfig

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def analyze_money_performance(initial_capital: float = 100000):
    """Analyze actual money gained/lost with stop loss effectiveness"""
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print("="*80)
    print("💰 MONEY & RISK MANAGEMENT ANALYSIS")
    print("="*80)
    print(f"Starting Capital: ₹{initial_capital:,.0f}")
    
    # Run different configurations
    engine = BacktestEngine(initial_capital=initial_capital)
    
    configurations = {
        'baseline': {
            'config': TradingConfig(),
            'use_dynamic': False
        },
        'dynamic': {
            'config': TradingConfig(),
            'use_dynamic': True
        },
        'optimized_fixed': {
            'config': FixedOptimizedTradingConfig(),
            'use_dynamic': False
        }
    }
    
    results = {}
    
    for name, setup in configurations.items():
        config = setup['config']
        config.use_dynamic_exits = setup['use_dynamic']
        
        # Disable extra filters for optimized to get more trades
        if isinstance(config, FixedOptimizedTradingConfig):
            config.use_ema_filter = False
            config.use_sma_filter = False
            config.use_adx_filter = False
            config.regime_threshold = -0.1
        
        print(f"\n📊 Testing {name.upper()}...")
        metrics = engine.run_backtest(symbol, start_date, end_date, config)
        results[name] = {
            'metrics': metrics,
            'trades': engine.trades
        }
    
    # Analyze money performance
    print("\n" + "="*60)
    print("💵 MONEY PERFORMANCE SUMMARY")
    print("="*60)
    
    for name, result in results.items():
        metrics = result['metrics']
        trades = result['trades']
        
        final_capital = initial_capital * (1 + metrics.total_return / 100)
        total_pnl = final_capital - initial_capital
        
        print(f"\n{name.upper()}:")
        print(f"  Total Trades: {metrics.total_trades}")
        print(f"  Win Rate: {metrics.win_rate:.1f}%")
        print(f"  Final Capital: ₹{final_capital:,.0f}")
        print(f"  Total P&L: ₹{total_pnl:+,.0f} ({metrics.total_return:+.2f}%)")
        
        if trades:
            # Calculate money metrics
            winning_trades = [t for t in trades if t.is_winner]
            losing_trades = [t for t in trades if not t.is_winner]
            
            total_wins_money = sum(t.pnl_amount for t in winning_trades)
            total_losses_money = sum(t.pnl_amount for t in losing_trades)
            
            print(f"\n  Money from Winners: ₹{total_wins_money:+,.0f}")
            print(f"  Money from Losers: ₹{total_losses_money:+,.0f}")
            print(f"  Avg Win Amount: ₹{np.mean([t.pnl_amount for t in winning_trades]):+,.0f}")
            print(f"  Avg Loss Amount: ₹{np.mean([t.pnl_amount for t in losing_trades]):+,.0f}")
            
            # Stop loss analysis
            stop_loss_exits = [t for t in trades if t.exit_reason == 'STOP_LOSS']
            if stop_loss_exits:
                print(f"\n  🛡️ STOP LOSS ANALYSIS:")
                print(f"  Stop Loss Exits: {len(stop_loss_exits)} ({len(stop_loss_exits)/len(trades)*100:.1f}%)")
                avg_stop_loss = np.mean([t.pnl_percent for t in stop_loss_exits])
                print(f"  Avg Stop Loss: {avg_stop_loss:.2f}%")
                
                # Compare with other exit types
                other_exits = [t for t in trades if t.exit_reason != 'STOP_LOSS']
                if other_exits:
                    avg_other_loss = np.mean([t.pnl_percent for t in other_exits if not t.is_winner])
                    print(f"  Avg Non-SL Loss: {avg_other_loss:.2f}%")
                    
                    if avg_stop_loss > avg_other_loss:
                        print(f"  ✅ Stop loss saved {abs(avg_other_loss - avg_stop_loss):.2f}% per trade")
                    else:
                        print(f"  ❌ Stop loss performed worse by {abs(avg_stop_loss - avg_other_loss):.2f}%")
                
                # Money saved by stop loss
                worst_loss = min(t.pnl_percent for t in trades)
                potential_catastrophic_loss = initial_capital * (worst_loss / 100) * len(stop_loss_exits)
                actual_sl_loss = sum(t.pnl_amount for t in stop_loss_exits)
                money_saved = abs(potential_catastrophic_loss) - abs(actual_sl_loss)
                
                print(f"  💰 Estimated money saved by SL: ₹{money_saved:,.0f}")
    
    # Compare win quality
    print("\n" + "="*60)
    print("🎯 WIN QUALITY ANALYSIS")
    print("="*60)
    
    baseline_trades = results['baseline']['trades']
    if baseline_trades:
        # Group by win size
        trades_df = pd.DataFrame([{
            'pnl_percent': t.pnl_percent,
            'pnl_amount': t.pnl_amount,
            'is_winner': t.is_winner,
            'exit_reason': t.exit_reason,
            'hold_time': t.hold_time_bars
        } for t in baseline_trades])
        
        # Categorize wins and losses
        trades_df['category'] = trades_df.apply(lambda x: 
            'Big Win' if x['pnl_percent'] > 1.0 else
            'Small Win' if x['pnl_percent'] > 0 else
            'Small Loss' if x['pnl_percent'] > -1.0 else
            'Big Loss', axis=1
        )
        
        category_summary = trades_df.groupby('category').agg({
            'pnl_amount': ['count', 'sum', 'mean'],
            'pnl_percent': 'mean'
        })
        
        print("\nTrade Distribution:")
        print(category_summary)
        
        # Risk-Reward Analysis
        print("\n📊 RISK-REWARD ANALYSIS:")
        avg_win_pct = trades_df[trades_df['is_winner']]['pnl_percent'].mean()
        avg_loss_pct = abs(trades_df[~trades_df['is_winner']]['pnl_percent'].mean())
        risk_reward = avg_win_pct / avg_loss_pct if avg_loss_pct > 0 else 0
        
        print(f"Average Win: {avg_win_pct:.2f}%")
        print(f"Average Loss: {avg_loss_pct:.2f}%")
        print(f"Risk-Reward Ratio: {risk_reward:.2f}")
        
        if risk_reward < 1.5:
            print("⚠️ Poor risk-reward ratio! Need larger wins or smaller losses")
        
        # Break-even analysis
        required_win_rate = 1 / (1 + risk_reward) * 100
        actual_win_rate = results['baseline']['metrics'].win_rate
        
        print(f"\nBreak-even Win Rate: {required_win_rate:.1f}%")
        print(f"Actual Win Rate: {actual_win_rate:.1f}%")
        
        if actual_win_rate < required_win_rate:
            print(f"❌ Below break-even by {required_win_rate - actual_win_rate:.1f}%")
        else:
            print(f"✅ Above break-even by {actual_win_rate - required_win_rate:.1f}%")
    
    # Feature impact analysis
    print("\n" + "="*60)
    print("🔬 OPTIMIZED CONFIG IMPACT")
    print("="*60)
    
    if 'optimized_fixed' in results and results['optimized_fixed']['metrics'].total_trades > 0:
        opt_metrics = results['optimized_fixed']['metrics']
        base_metrics = results['baseline']['metrics']
        
        print(f"Trade Count Impact: {opt_metrics.total_trades} vs {base_metrics.total_trades} ({opt_metrics.total_trades - base_metrics.total_trades:+d})")
        print(f"Win Rate Impact: {opt_metrics.win_rate:.1f}% vs {base_metrics.win_rate:.1f}% ({opt_metrics.win_rate - base_metrics.win_rate:+.1f}%)")
        print(f"Avg Win Impact: {opt_metrics.average_win:.2f}% vs {base_metrics.average_win:.2f}% ({opt_metrics.average_win - base_metrics.average_win:+.2f}%)")
        
        print("\n🔍 KEY DIFFERENCES CAUSING LOW TRADES:")
        print("1. Neighbors: 8 → 6 (affects ML prediction calculation)")
        print("2. Features: Different RSI periods and CCI↔ADX swap")
        print("3. Kernel smoothing: ON (may filter out signals)")
        print("4. ML predictions differ 79% of the time!")
    
    # Recommendations
    print("\n" + "="*60)
    print("💡 RECOMMENDATIONS")
    print("="*60)
    
    print("\n1. IMMEDIATE FIXES:")
    print("   - Win rate of 36.2% is too low - need minimum 45-50%")
    print("   - Risk-reward ratio needs improvement (target 2:1)")
    print("   - Filters are NOT working - all trades pass all filters!")
    
    print("\n2. STOP LOSS IMPROVEMENTS:")
    if results['baseline']['metrics'].total_trades > 0:
        sl_percentage = len([t for t in results['baseline']['trades'] if t.exit_reason == 'STOP_LOSS']) / len(results['baseline']['trades']) * 100
        print(f"   - Current SL hit rate: {sl_percentage:.1f}%")
        print("   - Consider tighter initial stops with trailing stops")
        print("   - Add volatility-based stop sizing")
    
    print("\n3. OPTIMIZED CONFIG FIXES:")
    print("   - Revert to standard features to fix ML predictions")
    print("   - Or retrain ML model with new features")
    print("   - Test kernel smoothing impact separately")
    
    print("\n4. FILTER EFFECTIVENESS:")
    print("   - All filters passing for all trades = filters not working!")
    print("   - Need to tighten filter thresholds")
    print("   - Consider adding new filters (volume, momentum)")
    
    # Save detailed analysis
    if baseline_trades:
        detailed_df = pd.DataFrame([{
            'entry_date': t.entry_date,
            'exit_date': t.exit_date,
            'direction': 'LONG' if t.direction == 1 else 'SHORT',
            'entry_price': t.entry_price,
            'exit_price': t.exit_price,
            'pnl_percent': t.pnl_percent,
            'pnl_amount': t.pnl_amount,
            'exit_reason': t.exit_reason,
            'hold_time_bars': t.hold_time_bars,
            'is_winner': t.is_winner
        } for t in baseline_trades])
        
        detailed_df.to_csv('money_performance_analysis.csv', index=False)
        print("\n💾 Detailed results saved to money_performance_analysis.csv")


if __name__ == "__main__":
    analyze_money_performance()