#!/usr/bin/env python3
"""
Analyze Trade Quality and Risk/Reward Issues
===========================================

Investigate why relaxed configuration has poor risk/reward ratio
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import pandas as pd
import json
import numpy as np
import matplotlib.pyplot as plt

from scanner.enhanced_bar_processor_relaxed import EnhancedBarProcessorRelaxed
from config.relaxed_settings import RELAXED_NO_THRESHOLD
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def analyze_trade_distribution():
    """Analyze trade outcomes and patterns"""
    
    print("="*80)
    print("🔍 ANALYZING TRADE QUALITY AND RISK/REWARD")
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
    
    print(f"\n📊 Analyzing {len(df)} bars for {symbol}")
    
    # Create processor
    config = RELAXED_NO_THRESHOLD
    processor = EnhancedBarProcessorRelaxed(config, symbol, "5minute")
    
    # Track detailed trade info
    trades = []
    signals = []
    current_position = None
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        if i < config.max_bars_back:
            continue
        
        # Track all signals
        if result.signal != 0:
            signals.append({
                'bar': i,
                'signal': result.signal,
                'ml_prediction': result.prediction,
                'close': row['close']
            })
        
        # Handle exits
        if current_position:
            bars_held = i - current_position['entry_bar']
            
            # Track maximum favorable/adverse excursion
            if current_position['type'] == 'long':
                current_position['mfe'] = max(current_position['mfe'], 
                    (row['high'] - current_position['entry_price']) / current_position['entry_price'] * 100)
                current_position['mae'] = min(current_position['mae'], 
                    (row['low'] - current_position['entry_price']) / current_position['entry_price'] * 100)
            else:  # short
                current_position['mfe'] = max(current_position['mfe'], 
                    (current_position['entry_price'] - row['low']) / current_position['entry_price'] * 100)
                current_position['mae'] = min(current_position['mae'], 
                    (current_position['entry_price'] - row['high']) / current_position['entry_price'] * 100)
            
            # Check exits
            exit_price = None
            exit_reason = None
            
            # Stop loss
            if current_position['type'] == 'long':
                if row['low'] <= current_position['stop_loss']:
                    exit_price = current_position['stop_loss']
                    exit_reason = 'stop_loss'
            else:
                if row['high'] >= current_position['stop_loss']:
                    exit_price = current_position['stop_loss']
                    exit_reason = 'stop_loss'
            
            # Time exit
            if not exit_price and bars_held >= 5:
                exit_price = row['close']
                exit_reason = 'time_exit'
            
            if exit_price:
                # Calculate final PnL
                if current_position['type'] == 'long':
                    pnl_pct = (exit_price - current_position['entry_price']) / current_position['entry_price'] * 100
                else:
                    pnl_pct = (current_position['entry_price'] - exit_price) / current_position['entry_price'] * 100
                
                trade = {
                    'entry_bar': current_position['entry_bar'],
                    'exit_bar': i,
                    'bars_held': bars_held,
                    'type': current_position['type'],
                    'entry_price': current_position['entry_price'],
                    'exit_price': exit_price,
                    'ml_prediction': current_position['ml_prediction'],
                    'pnl_pct': pnl_pct,
                    'mfe': current_position['mfe'],
                    'mae': current_position['mae'],
                    'exit_reason': exit_reason
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
                    'stop_loss': row['close'] * 0.99,  # 1% stop
                    'ml_prediction': result.prediction,
                    'mfe': 0,
                    'mae': 0
                }
            elif result.start_short_trade:
                current_position = {
                    'type': 'short',
                    'entry_bar': i,
                    'entry_price': row['close'],
                    'stop_loss': row['close'] * 1.01,  # 1% stop
                    'ml_prediction': result.prediction,
                    'mfe': 0,
                    'mae': 0
                }
    
    # Analyze results
    if not trades:
        print("No trades to analyze")
        return
    
    trades_df = pd.DataFrame(trades)
    
    print(f"\n📊 TRADE ANALYSIS ({len(trades)} trades):")
    print("="*60)
    
    # Basic stats
    winners = trades_df[trades_df['pnl_pct'] > 0]
    losers = trades_df[trades_df['pnl_pct'] <= 0]
    
    print(f"\n1. BASIC STATISTICS:")
    print(f"   Total trades: {len(trades)}")
    print(f"   Winners: {len(winners)} ({len(winners)/len(trades)*100:.1f}%)")
    print(f"   Losers: {len(losers)} ({len(losers)/len(trades)*100:.1f}%)")
    print(f"   Avg PnL: {trades_df['pnl_pct'].mean():.2f}%")
    
    # Exit reason analysis
    print(f"\n2. EXIT REASONS:")
    for reason, group in trades_df.groupby('exit_reason'):
        avg_pnl = group['pnl_pct'].mean()
        count = len(group)
        win_rate = len(group[group['pnl_pct'] > 0]) / count * 100
        print(f"   {reason}: {count} trades, {avg_pnl:.2f}% avg PnL, {win_rate:.1f}% win rate")
    
    # MFE/MAE analysis
    print(f"\n3. MAXIMUM EXCURSION ANALYSIS:")
    print(f"   Avg MFE (potential profit): {trades_df['mfe'].mean():.2f}%")
    print(f"   Avg MAE (potential loss): {trades_df['mae'].mean():.2f}%")
    
    # Missed profit analysis
    trades_df['missed_profit'] = trades_df['mfe'] - trades_df['pnl_pct']
    avg_missed = trades_df['missed_profit'].mean()
    print(f"   Avg missed profit: {avg_missed:.2f}%")
    
    # Win vs loss magnitude
    if len(winners) > 0:
        print(f"\n4. WIN/LOSS CHARACTERISTICS:")
        print(f"   Avg win: {winners['pnl_pct'].mean():.2f}%")
        print(f"   Avg win MFE: {winners['mfe'].mean():.2f}%")
        print(f"   Winners hitting 0.5%+: {len(winners[winners['mfe'] >= 0.5])}")
        print(f"   Winners hitting 1.0%+: {len(winners[winners['mfe'] >= 1.0])}")
    
    if len(losers) > 0:
        print(f"   Avg loss: {losers['pnl_pct'].mean():.2f}%")
        print(f"   Avg loss MAE: {losers['mae'].mean():.2f}%")
    
    # ML prediction vs outcome
    print(f"\n5. ML PREDICTION STRENGTH VS OUTCOME:")
    trades_df['ml_strength'] = trades_df['ml_prediction'].abs()
    for threshold in [2, 3, 4, 5]:
        strong_trades = trades_df[trades_df['ml_strength'] >= threshold]
        if len(strong_trades) > 0:
            win_rate = len(strong_trades[strong_trades['pnl_pct'] > 0]) / len(strong_trades) * 100
            avg_pnl = strong_trades['pnl_pct'].mean()
            print(f"   ML >= {threshold}: {len(strong_trades)} trades, {win_rate:.1f}% win rate, {avg_pnl:.2f}% avg PnL")
    
    # Time-based analysis
    print(f"\n6. HOLDING TIME ANALYSIS:")
    for bars in [1, 2, 3, 4, 5]:
        mask = trades_df['bars_held'] >= bars
        if mask.any():
            subset = trades_df[mask]
            win_rate = len(subset[subset['pnl_pct'] > 0]) / len(subset) * 100
            avg_pnl = subset['pnl_pct'].mean()
            print(f"   Held {bars}+ bars: {len(subset)} trades, {win_rate:.1f}% win rate, {avg_pnl:.2f}% avg PnL")
    
    # Recommendations
    print(f"\n\n💡 KEY INSIGHTS:")
    print("="*60)
    
    if avg_missed > 0.3:
        print(f"⚠️  High missed profit ({avg_missed:.2f}%) - exits are too early")
        print("   Consider:")
        print("   - Implementing profit targets at 0.5%, 1.0%, 1.5%")
        print("   - Using trailing stops after reaching first target")
        print("   - Dynamic exits based on momentum")
    
    if trades_df['mfe'].mean() > trades_df['pnl_pct'].mean() * 3:
        print(f"\n⚠️  MFE ({trades_df['mfe'].mean():.2f}%) >> Realized PnL ({trades_df['pnl_pct'].mean():.2f}%)")
        print("   The system identifies good entries but exits poorly")
    
    time_exits = trades_df[trades_df['exit_reason'] == 'time_exit']
    if len(time_exits) > len(trades) * 0.7:
        time_exit_pnl = time_exits['pnl_pct'].mean()
        print(f"\n⚠️  {len(time_exits)/len(trades)*100:.0f}% of trades exit on time ({time_exit_pnl:.2f}% avg)")
        print("   Fixed 5-bar exit is too rigid")
    
    # Save detailed results
    trades_df.to_csv('trade_quality_analysis.csv', index=False)
    print(f"\n💾 Detailed results saved to trade_quality_analysis.csv")
    
    # Plot MFE vs PnL
    if len(trades) > 10:
        plt.figure(figsize=(10, 6))
        plt.scatter(trades_df['mfe'], trades_df['pnl_pct'], alpha=0.6)
        plt.plot([0, trades_df['mfe'].max()], [0, trades_df['mfe'].max()], 'r--', alpha=0.5)
        plt.xlabel('Maximum Favorable Excursion (%)')
        plt.ylabel('Realized PnL (%)')
        plt.title('MFE vs Realized PnL - Missed Profit Analysis')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('mfe_vs_pnl.png')
        print(f"\n📊 MFE vs PnL chart saved to mfe_vs_pnl.png")


if __name__ == "__main__":
    analyze_trade_distribution()