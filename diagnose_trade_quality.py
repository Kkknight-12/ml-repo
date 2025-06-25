#!/usr/bin/env python3
"""
Diagnose Trade Quality and Win Rate Issues
==========================================

Analyzes why win rate is low and why we're taking losing trades.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import json
from typing import List, Dict, Tuple

from backtest_framework import BacktestEngine, BacktestMetrics, TradeResult
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
from config.fixed_optimized_settings import FixedOptimizedTradingConfig
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


class TradeQualityAnalyzer(BacktestEngine):
    """Extended backtest engine that captures detailed trade entry information"""
    
    def __init__(self):
        super().__init__()
        self.trade_details = []
    
    def run_detailed_backtest(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        config: TradingConfig
    ) -> Tuple[BacktestMetrics, List[Dict]]:
        """Run backtest and capture detailed trade information"""
        
        # Get historical data
        df = self._get_historical_data(symbol, start_date, end_date)
        if df.empty:
            raise ValueError("No data available for backtesting")
        
        # Initialize processor
        processor = EnhancedBarProcessor(config, symbol, "5minute")
        
        # Initialize tracking
        self.trades = []
        self.trade_details = []
        equity_curve = [self.initial_capital]
        current_position = None
        bars_processed = 0
        
        for idx, row in df.iterrows():
            bars_processed += 1
            
            # Process bar through ML
            result = processor.process_bar(
                row['open'], row['high'], row['low'], 
                row['close'], row['volume']
            )
            
            # Skip warmup period
            if bars_processed < config.max_bars_back:
                equity_curve.append(equity_curve[-1])
                continue
            
            # Check for exit
            if current_position:
                exit_signal = self._check_exit(
                    current_position, row, result, config
                )
                
                if exit_signal:
                    # Close position
                    trade = self._close_position(
                        current_position, row, exit_signal, bars_processed
                    )
                    self.trades.append(trade)
                    
                    # Store detailed trade info
                    self.trade_details.append({
                        'symbol': symbol,
                        'entry_date': current_position['entry_date'],
                        'entry_price': current_position['entry_price'],
                        'exit_date': row.name,
                        'exit_price': row['close'],
                        'direction': current_position['direction'],
                        'pnl_percent': trade.pnl_percent,
                        'is_winner': trade.is_winner,
                        'hold_time_bars': trade.hold_time_bars,
                        'exit_reason': exit_signal,
                        # Entry conditions
                        'entry_ml_prediction': current_position['ml_prediction'],
                        'entry_signal': current_position['signal'],
                        'entry_filters': current_position['filters'],
                        'entry_prediction_strength': current_position['prediction_strength'],
                        # Market conditions at entry
                        'entry_volatility': current_position['volatility_pass'],
                        'entry_regime': current_position['regime_pass'],
                        'entry_adx': current_position['adx_pass'],
                        'entry_kernel': current_position['kernel_pass']
                    })
                    
                    # Update equity
                    pnl = self.initial_capital * (trade.pnl_percent / 100)
                    equity_curve.append(equity_curve[-1] + pnl - 0.002 * self.initial_capital)
                    current_position = None
                else:
                    equity_curve.append(equity_curve[-1])
            
            # Check for entry
            elif not current_position:
                if result.start_long_trade or result.start_short_trade:
                    # Capture detailed entry conditions
                    current_position = {
                        'symbol': symbol,
                        'entry_bar': bars_processed,
                        'entry_date': idx,
                        'entry_price': row['close'],
                        'direction': 1 if result.start_long_trade else -1,
                        'stop_loss': self._calculate_stop_loss(row, config),
                        # ML and signal info
                        'ml_prediction': result.prediction,
                        'signal': result.signal,
                        'filters': result.filter_states.copy(),
                        'prediction_strength': result.prediction_strength,
                        # Individual filter states
                        'volatility_pass': result.filter_volatility,
                        'regime_pass': result.filter_regime,
                        'adx_pass': result.filter_adx,
                        'kernel_pass': result.filter_states.get('kernel', True)
                    }
                    equity_curve.append(equity_curve[-1])
                else:
                    equity_curve.append(equity_curve[-1])
            else:
                equity_curve.append(equity_curve[-1])
        
        # Close any open position at end
        if current_position:
            trade = self._close_position(
                current_position, df.iloc[-1], "END_OF_DATA", bars_processed
            )
            self.trades.append(trade)
        
        # Calculate metrics
        metrics = self._calculate_metrics(
            self.trades, equity_curve, bars_processed
        )
        
        return metrics, self.trade_details


def analyze_trade_quality():
    """Analyze why trades are losing and win rate is low"""
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print("="*80)
    print("🔍 TRADE QUALITY ANALYSIS")
    print("="*80)
    
    analyzer = TradeQualityAnalyzer()
    
    # Test baseline configuration
    print("\nAnalyzing BASELINE configuration...")
    config = TradingConfig()
    config.use_dynamic_exits = True
    
    metrics, trade_details = analyzer.run_detailed_backtest(
        symbol, start_date, end_date, config
    )
    
    # Convert to DataFrame for analysis
    trades_df = pd.DataFrame(trade_details)
    
    if trades_df.empty:
        print("No trades to analyze!")
        return
    
    # Basic statistics
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"Total trades: {len(trades_df)}")
    print(f"Winners: {trades_df['is_winner'].sum()} ({trades_df['is_winner'].sum()/len(trades_df)*100:.1f}%)")
    print(f"Losers: {(~trades_df['is_winner']).sum()} ({(~trades_df['is_winner']).sum()/len(trades_df)*100:.1f}%)")
    print(f"Avg win: {trades_df[trades_df['is_winner']]['pnl_percent'].mean():.2f}%")
    print(f"Avg loss: {trades_df[~trades_df['is_winner']]['pnl_percent'].mean():.2f}%")
    
    # Analyze ML predictions for winners vs losers
    print(f"\n🧠 ML PREDICTION ANALYSIS:")
    winners_df = trades_df[trades_df['is_winner']]
    losers_df = trades_df[~trades_df['is_winner']]
    
    print(f"\nWinning trades:")
    print(f"  Avg ML prediction: {winners_df['entry_ml_prediction'].mean():.2f}")
    print(f"  Avg prediction strength: {winners_df['entry_prediction_strength'].mean():.3f}")
    
    print(f"\nLosing trades:")
    print(f"  Avg ML prediction: {losers_df['entry_ml_prediction'].mean():.2f}")
    print(f"  Avg prediction strength: {losers_df['entry_prediction_strength'].mean():.3f}")
    
    # Analyze filter effectiveness
    print(f"\n🔍 FILTER EFFECTIVENESS:")
    
    # Check how often each filter was true for winners vs losers
    filters = ['entry_volatility', 'entry_regime', 'entry_adx', 'entry_kernel']
    
    for filter_name in filters:
        winner_pass_rate = winners_df[filter_name].mean() * 100 if len(winners_df) > 0 else 0
        loser_pass_rate = losers_df[filter_name].mean() * 100 if len(losers_df) > 0 else 0
        
        print(f"\n{filter_name.replace('entry_', '').upper()} filter:")
        print(f"  Winners: {winner_pass_rate:.1f}% passed")
        print(f"  Losers: {loser_pass_rate:.1f}% passed")
        
        if winner_pass_rate > loser_pass_rate:
            print(f"  ✅ Better for winners (+{winner_pass_rate - loser_pass_rate:.1f}%)")
        else:
            print(f"  ❌ Better for losers (+{loser_pass_rate - winner_pass_rate:.1f}%)")
    
    # Analyze exit reasons
    print(f"\n📤 EXIT REASON ANALYSIS:")
    exit_reasons = trades_df.groupby(['exit_reason', 'is_winner']).size().unstack(fill_value=0)
    print(exit_reasons)
    
    # Analyze hold times
    print(f"\n⏱️ HOLD TIME ANALYSIS:")
    print(f"Winners avg hold: {winners_df['hold_time_bars'].mean():.1f} bars")
    print(f"Losers avg hold: {losers_df['hold_time_bars'].mean():.1f} bars")
    
    # Analyze by signal strength
    print(f"\n💪 SIGNAL STRENGTH ANALYSIS:")
    
    # Create bins for ML prediction strength
    trades_df['prediction_bin'] = pd.cut(
        trades_df['entry_ml_prediction'].abs(), 
        bins=[0, 3, 5, 8, 100], 
        labels=['3-5', '5-8', '8+', 'MAX']
    )
    
    strength_analysis = trades_df.groupby('prediction_bin').agg({
        'is_winner': ['count', 'sum', 'mean'],
        'pnl_percent': 'mean'
    })
    
    print("\nWin rate by prediction strength:")
    print(strength_analysis)
    
    # Find patterns in losing trades
    print(f"\n❌ LOSING TRADE PATTERNS:")
    
    # Count how many losers had all filters pass
    all_filters_pass_losers = losers_df[
        losers_df['entry_volatility'] & 
        losers_df['entry_regime'] & 
        losers_df['entry_adx'] & 
        losers_df['entry_kernel']
    ]
    
    print(f"Losers with ALL filters passed: {len(all_filters_pass_losers)} ({len(all_filters_pass_losers)/len(losers_df)*100:.1f}%)")
    
    # Check if certain combinations are problematic
    if len(trades_df) > 10:
        print("\n🔄 FILTER COMBINATION ANALYSIS:")
        
        # Group by filter combinations
        trades_df['filter_combo'] = (
            trades_df['entry_volatility'].astype(str) + 
            trades_df['entry_regime'].astype(str) + 
            trades_df['entry_adx'].astype(str) + 
            trades_df['entry_kernel'].astype(str)
        )
        
        combo_analysis = trades_df.groupby('filter_combo').agg({
            'is_winner': ['count', 'mean'],
            'pnl_percent': 'mean'
        }).sort_values(('is_winner', 'count'), ascending=False)
        
        print("\nTop filter combinations by frequency:")
        print(combo_analysis.head())
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if metrics.win_rate < 50:
        print("⚠️ Win rate is below 50% - ML model may need retraining or better features")
    
    if abs(metrics.average_win) < abs(metrics.average_loss) * 1.5:
        print("⚠️ Risk/reward ratio is poor - consider adjusting exit strategies")
    
    if len(all_filters_pass_losers) > len(losers_df) * 0.5:
        print("⚠️ Filters are not effectively screening out bad trades")
    
    # Save detailed results
    trades_df.to_csv('trade_quality_analysis.csv', index=False)
    print(f"\n💾 Detailed results saved to trade_quality_analysis.csv")


if __name__ == "__main__":
    analyze_trade_quality()