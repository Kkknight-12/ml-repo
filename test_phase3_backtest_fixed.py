"""
Phase 3 Comprehensive Backtest - Fixed Version
===============================================

Tests original vs flexible ML systems with proper error handling
and simplified configuration.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from data.smart_data_manager import SmartDataManager
from scanner.flexible_bar_processor import FlexibleBarProcessor
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
import matplotlib.pyplot as plt
import seaborn as sns


class BacktestEngine:
    """Simplified backtest engine"""
    
    def __init__(self, commission=0.001, slippage=0.0005):
        self.commission = commission
        self.slippage = slippage
        self.trades = []
        self.equity_curve = [1.0]
        
    def simulate_trades(self, signals, df):
        """Simulate trades from signals"""
        position = None
        
        for signal in signals:
            if signal['bar_index'] >= len(df) - 10:
                continue
                
            entry_price = df.iloc[signal['bar_index']]['close']
            
            # Close existing position if opposite signal
            if position:
                if (position['type'] == 'long' and signal['signal'] < 0) or \
                   (position['type'] == 'short' and signal['signal'] > 0):
                    # Exit at signal bar
                    exit_price = entry_price
                    if position['type'] == 'long':
                        position['return'] = (exit_price - position['entry_price']) / position['entry_price'] - self.commission
                    else:
                        position['return'] = (position['entry_price'] - exit_price) / position['entry_price'] - self.commission
                    
                    position['exit_time'] = df.index[signal['bar_index']]
                    position['exit_price'] = exit_price
                    position['bars_held'] = signal['bar_index'] - position['entry_bar']
                    self.trades.append(position)
                    
                    # Update equity
                    self.equity_curve.append(self.equity_curve[-1] * (1 + position['return']))
                    position = None
            
            # Enter new position
            if not position:
                position = {
                    'type': 'long' if signal['signal'] > 0 else 'short',
                    'entry_price': entry_price * (1 + self.slippage if signal['signal'] > 0 else 1 - self.slippage),
                    'entry_time': df.index[signal['bar_index']],
                    'entry_bar': signal['bar_index'],
                    'prediction': signal['prediction']
                }
        
        # Close final position
        if position and len(df) > 0:
            exit_price = df.iloc[-1]['close']
            if position['type'] == 'long':
                position['return'] = (exit_price - position['entry_price']) / position['entry_price'] - self.commission
            else:
                position['return'] = (position['entry_price'] - exit_price) / position['entry_price'] - self.commission
            
            position['exit_time'] = df.index[-1]
            position['exit_price'] = exit_price
            position['bars_held'] = len(df) - position['entry_bar']
            self.trades.append(position)
            self.equity_curve.append(self.equity_curve[-1] * (1 + position['return']))
    
    def calculate_metrics(self):
        """Calculate performance metrics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0
            }
        
        returns = [t['return'] for t in self.trades]
        wins = sum(1 for r in returns if r > 0)
        
        # Equity curve metrics
        peak = 1.0
        max_dd = 0
        for equity in self.equity_curve:
            peak = max(peak, equity)
            dd = (peak - equity) / peak
            max_dd = max(max_dd, dd)
        
        # Sharpe ratio
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252)
        else:
            sharpe = 0
        
        return {
            'total_trades': len(self.trades),
            'win_rate': (wins / len(self.trades)) * 100 if self.trades else 0,
            'total_return': (self.equity_curve[-1] - 1) * 100,
            'avg_return': np.mean(returns) * 100 if returns else 0,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd * 100,
            'avg_win': np.mean([r for r in returns if r > 0]) * 100 if wins else 0,
            'avg_loss': np.mean([r for r in returns if r < 0]) * 100 if (len(returns) - wins) else 0
        }


def test_ml_system(symbol: str, use_flexible: bool = False):
    """Test a single ML system"""
    
    print(f"\n{'='*60}")
    print(f"Testing {symbol} with {'FLEXIBLE' if use_flexible else 'ORIGINAL'} ML")
    print(f"{'='*60}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=60)
    
    if df is None or len(df) < 2500:
        print(f"Insufficient data: {len(df) if df is not None else 0} bars")
        return None
    
    print(f"Data loaded: {len(df)} bars")
    
    # Create simple configuration
    config = TradingConfig(
        source='close',
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        regime_threshold=-0.1
    )
    
    # Create processor
    if use_flexible:
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
    else:
        processor = EnhancedBarProcessor(
            config=config,
            symbol=symbol,
            timeframe='5minute'
        )
    
    # Process bars and collect signals
    signals = []
    warmup_complete = False
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'],
            row['close'], row['volume']
        )
        
        if i == 2000:
            warmup_complete = True
            print("ML warmup complete at bar 2000")
        
        if warmup_complete and result and result.start_long_trade:
            signals.append({
                'bar_index': i,
                'signal': 1,
                'prediction': result.prediction
            })
        elif warmup_complete and result and result.start_short_trade:
            signals.append({
                'bar_index': i,
                'signal': -1,
                'prediction': result.prediction
            })
    
    print(f"Signals generated: {len(signals)}")
    
    # Run backtest
    if signals:
        backtest = BacktestEngine()
        backtest.simulate_trades(signals, df)
        metrics = backtest.calculate_metrics()
        
        print(f"\nPerformance Metrics:")
        print(f"  Total Trades: {metrics['total_trades']}")
        print(f"  Win Rate: {metrics['win_rate']:.1f}%")
        print(f"  Total Return: {metrics['total_return']:.2f}%")
        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {metrics['max_drawdown']:.1f}%")
        
        return metrics
    else:
        print("No trading signals generated")
        return None


def main():
    """Run comprehensive comparison"""
    
    print("\n" + "="*80)
    print("PHASE 3 ML SYSTEM COMPARISON - FIXED VERSION")
    print("="*80)
    
    symbols = ['RELIANCE', 'INFY', 'TCS']
    results = {'original': [], 'flexible': []}
    
    for symbol in symbols:
        # Test original
        orig_metrics = test_ml_system(symbol, use_flexible=False)
        if orig_metrics:
            orig_metrics['symbol'] = symbol
            results['original'].append(orig_metrics)
        
        # Test flexible
        flex_metrics = test_ml_system(symbol, use_flexible=True)
        if flex_metrics:
            flex_metrics['symbol'] = symbol
            results['flexible'].append(flex_metrics)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY COMPARISON")
    print("="*80)
    
    for system_name, system_results in results.items():
        if system_results:
            print(f"\n{system_name.upper()} ML:")
            avg_trades = np.mean([r['total_trades'] for r in system_results])
            avg_win_rate = np.mean([r['win_rate'] for r in system_results])
            avg_return = np.mean([r['total_return'] for r in system_results])
            avg_sharpe = np.mean([r['sharpe_ratio'] for r in system_results])
            
            print(f"  Avg Trades: {avg_trades:.0f}")
            print(f"  Avg Win Rate: {avg_win_rate:.1f}%")
            print(f"  Avg Return: {avg_return:.2f}%")
            print(f"  Avg Sharpe: {avg_sharpe:.2f}")
    
    # Recommendation
    if results['original'] and results['flexible']:
        orig_return = np.mean([r['total_return'] for r in results['original']])
        flex_return = np.mean([r['total_return'] for r in results['flexible']])
        
        print("\n" + "="*80)
        print("RECOMMENDATION")
        print("="*80)
        
        improvement = ((flex_return - orig_return) / abs(orig_return) * 100) if orig_return != 0 else 0
        print(f"\nFlexible ML vs Original: {improvement:+.1f}% improvement")
        
        if improvement > 10:
            print("✅ Deploy Flexible ML System")
        elif improvement > 0:
            print("🟡 Gradual Rollout Recommended")
        else:
            print("❌ Keep Original System")


if __name__ == "__main__":
    main()