"""
Phase 3 with ML Threshold - Improved Profitability
==================================================

Test flexible ML with optimal threshold to reduce false signals
and improve profitability.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from data.smart_data_manager import SmartDataManager
from scanner.flexible_bar_processor import FlexibleBarProcessor
from config.settings import TradingConfig


class OptimizedBacktest:
    """Backtest with ML threshold and better exit strategy"""
    
    def __init__(self, initial_capital=100000, ml_threshold=3.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.ml_threshold = ml_threshold
        self.commission_pct = 0.0003  # 0.03%
        self.trades = []
        self.position = None
        
    def check_signal(self, result):
        """Only take signals with strong ML prediction"""
        if not result:
            return False, 0
            
        # Check ML threshold
        prediction = result.flexible_prediction if hasattr(result, 'flexible_prediction') else result.prediction
        
        if abs(prediction) < self.ml_threshold:
            return False, 0
            
        # Check for entry signals
        if result.start_long_trade:
            return True, 1
        elif result.start_short_trade:
            return True, -1
            
        return False, 0
    
    def execute_trade(self, signal_type, entry_price, entry_time, entry_bar):
        """Open position"""
        position_size = self.capital * 0.95
        shares = position_size / entry_price
        commission = position_size * self.commission_pct
        
        self.position = {
            'type': 'long' if signal_type > 0 else 'short',
            'entry_price': entry_price,
            'entry_time': entry_time,
            'entry_bar': entry_bar,
            'shares': shares,
            'commission_in': commission,
            'stop_loss': entry_price * (0.99 if signal_type > 0 else 1.01),  # 1% stop
            'take_profit': entry_price * (1.015 if signal_type > 0 else 0.985)  # 1.5% target
        }
    
    def check_exit(self, bar_data, bar_index):
        """Check for exit conditions"""
        if not self.position:
            return False
            
        high = bar_data['high']
        low = bar_data['low']
        close = bar_data['close']
        
        # Check stop loss and take profit
        if self.position['type'] == 'long':
            if low <= self.position['stop_loss']:
                return True, self.position['stop_loss']
            elif high >= self.position['take_profit']:
                return True, self.position['take_profit']
        else:  # short
            if high >= self.position['stop_loss']:
                return True, self.position['stop_loss']
            elif low <= self.position['take_profit']:
                return True, self.position['take_profit']
        
        # Time-based exit (max 50 bars for 5min = ~4 hours)
        if bar_index - self.position['entry_bar'] >= 50:
            return True, close
            
        return False, 0
    
    def close_position(self, exit_price, exit_time):
        """Close position and calculate P&L"""
        if not self.position:
            return
            
        pos = self.position
        exit_value = exit_price * pos['shares']
        commission_out = exit_value * self.commission_pct
        
        if pos['type'] == 'long':
            gross_pnl = (exit_price - pos['entry_price']) * pos['shares']
        else:
            gross_pnl = (pos['entry_price'] - exit_price) * pos['shares']
            
        net_pnl = gross_pnl - pos['commission_in'] - commission_out
        
        self.capital += net_pnl
        
        self.trades.append({
            'entry_time': pos['entry_time'],
            'exit_time': exit_time,
            'type': pos['type'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'return_pct': (net_pnl / (pos['entry_price'] * pos['shares'])) * 100
        })
        
        self.position = None
    
    def get_metrics(self):
        """Calculate performance metrics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_return_pct': 0,
                'net_pnl': 0
            }
            
        trades_df = pd.DataFrame(self.trades)
        winning = trades_df[trades_df['net_pnl'] > 0]
        
        return {
            'total_trades': len(trades_df),
            'win_rate': len(winning) / len(trades_df) * 100,
            'total_return_pct': ((self.capital - self.initial_capital) / self.initial_capital) * 100,
            'net_pnl': self.capital - self.initial_capital,
            'avg_win': winning['return_pct'].mean() if len(winning) > 0 else 0,
            'avg_loss': trades_df[trades_df['net_pnl'] <= 0]['return_pct'].mean() if len(trades_df) > len(winning) else 0
        }


def test_with_threshold(symbol='RELIANCE', ml_threshold=3.0):
    """Test with ML threshold"""
    
    print(f"\n{'='*60}")
    print(f"Testing {symbol} with ML Threshold = {ml_threshold}")
    print(f"{'='*60}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=90)
    
    if df is None or len(df) < 2500:
        print(f"Insufficient data")
        return None
        
    # Config with filters
    config = TradingConfig(
        source='close',
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False
    )
    
    # Create processor
    processor = FlexibleBarProcessor(
        config=config,
        symbol=symbol,
        timeframe='5minute',
        use_flexible_ml=True,
        feature_config={
            'original_features': ['rsi', 'wt', 'cci', 'adx', 'features_4'],
            'phase3_features': ['fisher', 'vwm', 'order_flow'],
            'use_phase3': True
        }
    )
    
    # Backtest
    backtest = OptimizedBacktest(ml_threshold=ml_threshold)
    
    signals_taken = 0
    signals_filtered = 0
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if i < 2000:  # Skip warmup
            processor.process_bar(row['open'], row['high'], row['low'], row['close'], row['volume'])
            continue
            
        result = processor.process_bar(
            row['open'], row['high'], row['low'], row['close'], row['volume']
        )
        
        # Check for exit first
        if backtest.position:
            should_exit, exit_price = backtest.check_exit(row, i)
            if should_exit:
                backtest.close_position(exit_price, idx)
        
        # Check for entry
        if not backtest.position and result:
            valid_signal, signal_type = backtest.check_signal(result)
            
            if result.start_long_trade or result.start_short_trade:
                pred = result.flexible_prediction if hasattr(result, 'flexible_prediction') else result.prediction
                if abs(pred) < ml_threshold:
                    signals_filtered += 1
                    
            if valid_signal:
                signals_taken += 1
                backtest.execute_trade(signal_type, row['close'], idx, i)
    
    # Close final position
    if backtest.position:
        backtest.close_position(df.iloc[-1]['close'], df.index[-1])
    
    metrics = backtest.get_metrics()
    
    print(f"\nSignals: {signals_taken} taken, {signals_filtered} filtered out")
    print(f"Trades: {metrics['total_trades']}")
    print(f"Win Rate: {metrics['win_rate']:.1f}%")
    print(f"Net P&L: ₹{metrics['net_pnl']:,.2f}")
    print(f"Return: {metrics['total_return_pct']:.2f}%")
    if metrics['total_trades'] > 0:
        print(f"Avg Win: {metrics['avg_win']:.2f}%")
        print(f"Avg Loss: {metrics['avg_loss']:.2f}%")
    
    return metrics


def main():
    """Test different ML thresholds"""
    
    print("\n" + "="*80)
    print("PHASE 3 - ML THRESHOLD OPTIMIZATION")
    print("="*80)
    
    symbols = ['RELIANCE', 'INFY', 'TCS']
    thresholds = [0.0, 2.0, 3.0, 4.0]
    
    results = {}
    
    for threshold in thresholds:
        print(f"\n{'*'*80}")
        print(f"TESTING WITH ML THRESHOLD = {threshold}")
        print(f"{'*'*80}")
        
        threshold_results = []
        
        for symbol in symbols:
            metrics = test_with_threshold(symbol, threshold)
            if metrics:
                threshold_results.append(metrics)
        
        if threshold_results:
            # Aggregate results
            total_trades = sum(m['total_trades'] for m in threshold_results)
            avg_win_rate = np.mean([m['win_rate'] for m in threshold_results])
            total_pnl = sum(m['net_pnl'] for m in threshold_results)
            avg_return = np.mean([m['total_return_pct'] for m in threshold_results])
            
            results[threshold] = {
                'total_trades': total_trades,
                'avg_win_rate': avg_win_rate,
                'total_pnl': total_pnl,
                'avg_return': avg_return
            }
    
    # Summary
    print("\n" + "="*80)
    print("THRESHOLD COMPARISON SUMMARY")
    print("="*80)
    
    print(f"\n{'Threshold':>10} {'Trades':>8} {'Win Rate':>10} {'Total P&L':>15} {'Avg Return':>12}")
    print("-" * 65)
    
    for threshold, metrics in results.items():
        print(f"{threshold:>10.1f} {metrics['total_trades']:>8} "
              f"{metrics['avg_win_rate']:>9.1f}% "
              f"₹{metrics['total_pnl']:>13,.2f} "
              f"{metrics['avg_return']:>11.2f}%")
    
    # Find best threshold
    best_threshold = max(results.keys(), key=lambda k: results[k]['total_pnl'])
    print(f"\n✅ OPTIMAL ML THRESHOLD: {best_threshold}")
    print(f"   Expected Return: {results[best_threshold]['avg_return']:.2f}%")
    print(f"   Expected P&L: ₹{results[best_threshold]['total_pnl']:,.2f}")


if __name__ == "__main__":
    main()