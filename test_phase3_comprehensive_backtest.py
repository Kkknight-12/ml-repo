"""
Comprehensive Phase 3 Flexible ML Backtest
==========================================

Full profitability test comparing original vs flexible ML systems
with proper warmup, realistic trading simulation, and detailed metrics.
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
from config.adaptive_config import create_adaptive_config
import matplotlib.pyplot as plt
import seaborn as sns


class ComprehensiveBacktest:
    """Comprehensive backtesting framework for ML comparison"""
    
    def __init__(self, commission=0.001, slippage=0.0005):
        self.commission = commission
        self.slippage = slippage
        self.trades = []
        self.equity_curve = []
        self.signals_log = []
        
    def simulate_trade(self, signal, df, idx, entry_bar):
        """Simulate a single trade with realistic execution"""
        
        # Get entry price with slippage
        entry_price = df.iloc[entry_bar]['close']
        
        if signal['signal'] > 0:  # Long
            entry_price *= (1 + self.slippage)
            trade_type = 'long'
        else:  # Short
            entry_price *= (1 - self.slippage)
            trade_type = 'short'
        
        # Find exit (next opposite signal or end of data)
        exit_bar = None
        exit_reason = 'end_of_data'
        
        # Look for exit signal
        for i in range(entry_bar + 1, min(entry_bar + 100, len(df))):  # Max 100 bars hold
            bar = df.iloc[i]
            
            # Check for stop loss (2% adverse move)
            if trade_type == 'long' and bar['low'] < entry_price * 0.98:
                exit_bar = i
                exit_reason = 'stop_loss'
                exit_price = entry_price * 0.98
                break
            elif trade_type == 'short' and bar['high'] > entry_price * 1.02:
                exit_bar = i
                exit_reason = 'stop_loss'
                exit_price = entry_price * 1.02
                break
            
            # Check for take profit (3% favorable move)
            if trade_type == 'long' and bar['high'] > entry_price * 1.03:
                exit_bar = i
                exit_reason = 'take_profit'
                exit_price = entry_price * 1.03
                break
            elif trade_type == 'short' and bar['low'] < entry_price * 0.97:
                exit_bar = i
                exit_reason = 'take_profit'
                exit_price = entry_price * 0.97
                break
        
        # If no exit signal, exit at end of available data
        if exit_bar is None:
            exit_bar = len(df) - 1
            exit_price = df.iloc[exit_bar]['close']
            
            # Apply slippage on exit
            if trade_type == 'long':
                exit_price *= (1 - self.slippage)
            else:
                exit_price *= (1 + self.slippage)
        
        # Calculate return
        if trade_type == 'long':
            trade_return = (exit_price - entry_price) / entry_price - self.commission
        else:
            trade_return = (entry_price - exit_price) / entry_price - self.commission
        
        # Record trade
        trade = {
            'entry_time': df.index[entry_bar],
            'exit_time': df.index[exit_bar],
            'type': trade_type,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'return': trade_return,
            'pnl': trade_return * 100,  # Percentage
            'bars_held': exit_bar - entry_bar,
            'exit_reason': exit_reason,
            'ml_prediction': signal['prediction'],
            'ml_system': signal.get('ml_system', 'unknown')
        }
        
        self.trades.append(trade)
        return trade, exit_bar
    
    def run_backtest(self, processor, df, warmup_bars=2000):
        """Run backtest with given processor"""
        
        print(f"\n{'='*60}")
        print(f"Running backtest with {processor.__class__.__name__}")
        print(f"{'='*60}")
        
        # Reset state
        self.trades = []
        self.equity_curve = [1.0]  # Start with 1.0 (100%)
        self.signals_log = []
        
        # Process all bars
        bar_count = 0
        last_exit_bar = 0
        signals_generated = 0
        
        for i, (idx, row) in enumerate(df.iterrows()):
            # Process bar
            result = processor.process_bar(
                row['open'], row['high'], row['low'],
                row['close'], row['volume']
            )
            
            bar_count += 1
            
            # Log progress
            if bar_count % 500 == 0:
                print(f"  Processed {bar_count} bars...")
            
            # Check for signals after warmup
            if bar_count > warmup_bars and result:
                # Log all ML predictions for analysis
                if result.prediction != 0:
                    self.signals_log.append({
                        'bar': bar_count,
                        'timestamp': idx,
                        'prediction': result.prediction,
                        'signal': result.signal,
                        'filters_passed': result.filter_all
                    })
                
                # Trade on entry signals only
                if result.start_long_trade or result.start_short_trade:
                    # Skip if we're still in a trade
                    if i > last_exit_bar:
                        signal = {
                            'timestamp': idx,
                            'signal': 1 if result.start_long_trade else -1,
                            'prediction': result.prediction,
                            'ml_system': result.ml_system_used if hasattr(result, 'ml_system_used') else 'original'
                        }
                        
                        trade, exit_bar = self.simulate_trade(signal, df, i, i)
                        last_exit_bar = exit_bar
                        signals_generated += 1
                        
                        # Update equity curve
                        new_equity = self.equity_curve[-1] * (1 + trade['return'])
                        self.equity_curve.append(new_equity)
        
        print(f"\nBacktest complete:")
        print(f"  Bars processed: {bar_count}")
        print(f"  Signals generated: {signals_generated}")
        print(f"  Trades executed: {len(self.trades)}")
        
        return self.calculate_metrics()
    
    def calculate_metrics(self):
        """Calculate comprehensive performance metrics"""
        
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'avg_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'profit_factor': 0,
                'avg_bars_held': 0
            }
        
        # Basic metrics
        returns = [t['return'] for t in self.trades]
        wins = [t for t in self.trades if t['return'] > 0]
        losses = [t for t in self.trades if t['return'] < 0]
        
        # Calculate max drawdown from equity curve
        peak = self.equity_curve[0]
        max_dd = 0
        for equity in self.equity_curve:
            peak = max(peak, equity)
            dd = (peak - equity) / peak
            max_dd = max(max_dd, dd)
        
        # Sharpe ratio (annualized for 5-min bars)
        if len(returns) > 1 and np.std(returns) > 0:
            # ~78 5-min bars per day, ~252 trading days per year
            sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(78 * 252)
        else:
            sharpe = 0
        
        # Profit factor
        total_wins = sum(t['return'] for t in wins) if wins else 0
        total_losses = abs(sum(t['return'] for t in losses)) if losses else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Calculate monthly returns for consistency
        monthly_returns = self._calculate_monthly_returns()
        positive_months = sum(1 for r in monthly_returns if r > 0)
        
        metrics = {
            'total_trades': len(self.trades),
            'win_rate': len(wins) / len(self.trades) * 100,
            'total_return': (self.equity_curve[-1] - 1) * 100,  # Percentage
            'avg_return': np.mean(returns) * 100,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd * 100,
            'profit_factor': profit_factor,
            'avg_bars_held': np.mean([t['bars_held'] for t in self.trades]),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'avg_win': np.mean([t['return'] for t in wins]) * 100 if wins else 0,
            'avg_loss': np.mean([t['return'] for t in losses]) * 100 if losses else 0,
            'win_loss_ratio': abs(metrics['avg_win'] / metrics['avg_loss']) if losses and metrics.get('avg_loss') else 0,
            'total_months': len(monthly_returns),
            'positive_months': positive_months,
            'monthly_consistency': positive_months / len(monthly_returns) * 100 if monthly_returns else 0
        }
        
        return metrics
    
    def _calculate_monthly_returns(self):
        """Calculate returns by month"""
        if not self.trades:
            return []
        
        # Group trades by month
        monthly_trades = {}
        for trade in self.trades:
            month_key = trade['exit_time'].strftime('%Y-%m')
            if month_key not in monthly_trades:
                monthly_trades[month_key] = []
            monthly_trades[month_key].append(trade['return'])
        
        # Calculate monthly returns
        monthly_returns = []
        for month, returns in sorted(monthly_trades.items()):
            # Compound returns for the month
            month_return = 1.0
            for r in returns:
                month_return *= (1 + r)
            monthly_returns.append(month_return - 1)
        
        return monthly_returns
    
    def plot_results(self, title="Backtest Results"):
        """Plot equity curve and trade distribution"""
        
        if not self.trades:
            print("No trades to plot")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(title, fontsize=16)
        
        # 1. Equity Curve
        ax1 = axes[0, 0]
        equity_pct = [(e - 1) * 100 for e in self.equity_curve]
        ax1.plot(range(len(equity_pct)), equity_pct, 'b-', linewidth=2)
        ax1.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        ax1.set_title('Equity Curve')
        ax1.set_xlabel('Trade Number')
        ax1.set_ylabel('Return (%)')
        ax1.grid(True, alpha=0.3)
        
        # 2. Trade Returns Distribution
        ax2 = axes[0, 1]
        returns_pct = [t['return'] * 100 for t in self.trades]
        ax2.hist(returns_pct, bins=30, alpha=0.7, edgecolor='black')
        ax2.axvline(x=0, color='r', linestyle='--', alpha=0.5)
        ax2.set_title('Trade Returns Distribution')
        ax2.set_xlabel('Return (%)')
        ax2.set_ylabel('Frequency')
        ax2.grid(True, alpha=0.3)
        
        # 3. Win/Loss by Exit Reason
        ax3 = axes[1, 0]
        exit_reasons = {}
        for trade in self.trades:
            reason = trade['exit_reason']
            if reason not in exit_reasons:
                exit_reasons[reason] = {'wins': 0, 'losses': 0}
            if trade['return'] > 0:
                exit_reasons[reason]['wins'] += 1
            else:
                exit_reasons[reason]['losses'] += 1
        
        reasons = list(exit_reasons.keys())
        wins = [exit_reasons[r]['wins'] for r in reasons]
        losses = [exit_reasons[r]['losses'] for r in reasons]
        
        x = np.arange(len(reasons))
        width = 0.35
        ax3.bar(x - width/2, wins, width, label='Wins', color='green', alpha=0.7)
        ax3.bar(x + width/2, losses, width, label='Losses', color='red', alpha=0.7)
        ax3.set_xlabel('Exit Reason')
        ax3.set_ylabel('Count')
        ax3.set_title('Wins/Losses by Exit Reason')
        ax3.set_xticks(x)
        ax3.set_xticklabels(reasons)
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. ML Prediction vs Actual Returns
        ax4 = axes[1, 1]
        predictions = [abs(t['ml_prediction']) for t in self.trades]
        actual_returns = [abs(t['return']) * 100 for t in self.trades]
        ax4.scatter(predictions, actual_returns, alpha=0.5)
        ax4.set_xlabel('ML Prediction Strength')
        ax4.set_ylabel('Actual Return (%)')
        ax4.set_title('ML Prediction vs Actual Returns')
        ax4.grid(True, alpha=0.3)
        
        # Add trend line
        if len(predictions) > 10:
            z = np.polyfit(predictions, actual_returns, 1)
            p = np.poly1d(z)
            ax4.plot(sorted(predictions), p(sorted(predictions)), "r--", alpha=0.8)
        
        plt.tight_layout()
        plt.savefig(f'backtest_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        plt.show()


def run_comprehensive_test(symbol: str, days: int = 60):
    """Run comprehensive test on a single symbol"""
    
    print(f"\n{'='*80}")
    print(f"COMPREHENSIVE BACKTEST: {symbol}")
    print(f"{'='*80}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=days)
    
    if df is None or len(df) < 2500:
        print(f"⚠️  Insufficient data for {symbol} (need at least 2500 bars)")
        return None, None
    
    print(f"\nData loaded: {len(df)} bars covering {days} days")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    
    # Analyze price movement for adaptive config
    stats = data_manager.analyze_price_movement(df)
    print(f"\nPrice statistics:")
    print(f"  Average move: {stats['avg_move']:.3f}%")
    print(f"  Volatility: {stats['volatility']:.3f}%")
    print(f"  Trend: {stats['trend_strength']:.3f}")
    
    # Create adaptive configuration
    adaptive_config = create_adaptive_config(symbol, '5minute', stats)
    
    # Base configuration
    base_config = TradingConfig(
        source=adaptive_config.source,
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        features=adaptive_config.features,
        # Use original Pine Script filters
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        regime_threshold=-0.1,
        adx_threshold=20,
        # Kernel settings
        use_kernel_filter=True,
        show_kernel_estimate=True
    )
    
    # Test 1: Original ML System
    print(f"\n{'='*60}")
    print("TEST 1: ORIGINAL ML SYSTEM")
    print(f"{'='*60}")
    
    original_processor = EnhancedBarProcessor(
        config=base_config,
        symbol=symbol,
        timeframe='5minute'
    )
    
    original_backtest = ComprehensiveBacktest()
    original_metrics = original_backtest.run_backtest(original_processor, df, warmup_bars=2000)
    
    # Test 2: Flexible ML System
    print(f"\n{'='*60}")
    print("TEST 2: FLEXIBLE ML SYSTEM (with Phase 3 features)")
    print(f"{'='*60}")
    
    flexible_processor = FlexibleBarProcessor(
        config=base_config,
        symbol=symbol,
        timeframe='5minute',
        use_flexible_ml=True,
        feature_config={
            'original_features': ['rsi', 'wt', 'cci', 'adx', 'features_4'],
            'phase3_features': ['fisher', 'vwm', 'order_flow', 'volume_trend', 'buying_pressure'],
            'use_phase3': True
        }
    )
    
    flexible_backtest = ComprehensiveBacktest()
    flexible_metrics = flexible_backtest.run_backtest(flexible_processor, df, warmup_bars=2000)
    
    # Display detailed results
    print(f"\n{'='*80}")
    print("RESULTS COMPARISON")
    print(f"{'='*80}")
    
    print(f"\n{'Metric':<25} {'Original ML':>15} {'Flexible ML':>15} {'Difference':>15}")
    print("-" * 70)
    
    metrics_to_compare = [
        ('Total Trades', 'total_trades', '{:.0f}'),
        ('Win Rate (%)', 'win_rate', '{:.1f}'),
        ('Total Return (%)', 'total_return', '{:.2f}'),
        ('Avg Return (%)', 'avg_return', '{:.3f}'),
        ('Sharpe Ratio', 'sharpe_ratio', '{:.2f}'),
        ('Max Drawdown (%)', 'max_drawdown', '{:.1f}'),
        ('Profit Factor', 'profit_factor', '{:.2f}'),
        ('Avg Bars Held', 'avg_bars_held', '{:.1f}'),
        ('Monthly Consistency (%)', 'monthly_consistency', '{:.1f}')
    ]
    
    for display_name, metric_key, fmt in metrics_to_compare:
        orig_val = original_metrics.get(metric_key, 0)
        flex_val = flexible_metrics.get(metric_key, 0)
        
        if metric_key in ['total_trades', 'avg_bars_held']:
            diff = flex_val - orig_val
            diff_str = fmt.format(diff)
        else:
            diff = flex_val - orig_val
            diff_str = f"{diff:+.2f}"
        
        print(f"{display_name:<25} {fmt.format(orig_val):>15} {fmt.format(flex_val):>15} {diff_str:>15}")
    
    # Risk-adjusted performance
    print(f"\n{'='*60}")
    print("RISK-ADJUSTED PERFORMANCE")
    print(f"{'='*60}")
    
    # Calculate risk-adjusted returns
    for name, metrics in [("Original ML", original_metrics), ("Flexible ML", flexible_metrics)]:
        if metrics['max_drawdown'] > 0:
            return_dd_ratio = metrics['total_return'] / metrics['max_drawdown']
        else:
            return_dd_ratio = float('inf')
        
        print(f"\n{name}:")
        print(f"  Return/Drawdown Ratio: {return_dd_ratio:.2f}")
        print(f"  Win/Loss Ratio: {metrics.get('win_loss_ratio', 0):.2f}")
        print(f"  Average Win: {metrics.get('avg_win', 0):.2f}%")
        print(f"  Average Loss: {metrics.get('avg_loss', 0):.2f}%")
    
    # Plot results
    if original_metrics['total_trades'] > 0:
        original_backtest.plot_results(f"Original ML - {symbol}")
    
    if flexible_metrics['total_trades'] > 0:
        flexible_backtest.plot_results(f"Flexible ML - {symbol}")
    
    return original_metrics, flexible_metrics


def main():
    """Run comprehensive Phase 3 ML comparison"""
    
    print("\n" + "="*80)
    print("PHASE 3 FLEXIBLE ML - COMPREHENSIVE PROFITABILITY TEST")
    print("="*80)
    print("\nThis test will:")
    print("1. Load 60 days of 5-minute data for each symbol")
    print("2. Run both ML systems with 2000 bar warmup")
    print("3. Simulate realistic trading with stops and targets")
    print("4. Calculate comprehensive performance metrics")
    print("5. Generate visual analysis of results")
    
    # Test symbols
    symbols = ['RELIANCE', 'INFY', 'TCS', 'ICICIBANK', 'HDFCBANK']
    
    # Store results
    all_results = {
        'original': {},
        'flexible': {}
    }
    
    # Run tests
    for symbol in symbols:
        try:
            orig_metrics, flex_metrics = run_comprehensive_test(symbol, days=60)
            
            if orig_metrics and flex_metrics:
                all_results['original'][symbol] = orig_metrics
                all_results['flexible'][symbol] = flex_metrics
        except Exception as e:
            print(f"\n❌ Error testing {symbol}: {str(e)}")
            continue
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY - ALL SYMBOLS")
    print("="*80)
    
    # Calculate aggregate metrics
    for system_name in ['original', 'flexible']:
        results = all_results[system_name]
        
        if results:
            print(f"\n{system_name.upper()} ML SYSTEM:")
            print("-" * 40)
            
            # Aggregate metrics
            total_trades = sum(r['total_trades'] for r in results.values())
            avg_win_rate = np.mean([r['win_rate'] for r in results.values()])
            avg_return = np.mean([r['total_return'] for r in results.values()])
            avg_sharpe = np.mean([r['sharpe_ratio'] for r in results.values()])
            avg_dd = np.mean([r['max_drawdown'] for r in results.values()])
            
            print(f"Total Trades (all symbols): {total_trades}")
            print(f"Average Win Rate: {avg_win_rate:.1f}%")
            print(f"Average Total Return: {avg_return:.2f}%")
            print(f"Average Sharpe Ratio: {avg_sharpe:.2f}")
            print(f"Average Max Drawdown: {avg_dd:.1f}%")
            
            # Best and worst performers
            if len(results) > 1:
                best = max(results.items(), key=lambda x: x[1]['total_return'])
                worst = min(results.items(), key=lambda x: x[1]['total_return'])
                
                print(f"\nBest Performer: {best[0]} ({best[1]['total_return']:.2f}% return)")
                print(f"Worst Performer: {worst[0]} ({worst[1]['total_return']:.2f}% return)")
    
    # Recommendation
    print("\n" + "="*80)
    print("DEPLOYMENT RECOMMENDATION")
    print("="*80)
    
    if all_results['original'] and all_results['flexible']:
        # Compare average returns
        orig_avg_return = np.mean([r['total_return'] for r in all_results['original'].values()])
        flex_avg_return = np.mean([r['total_return'] for r in all_results['flexible'].values()])
        
        improvement = ((flex_avg_return - orig_avg_return) / abs(orig_avg_return)) * 100 if orig_avg_return != 0 else 0
        
        print(f"\nFlexible ML Performance vs Original: {improvement:+.1f}%")
        
        if improvement > 10:
            print("\n✅ STRONG BUY: Deploy Flexible ML System")
            print("   - Significant performance improvement")
            print("   - Phase 3 features adding value")
        elif improvement > 0:
            print("\n🟡 MODERATE BUY: Gradual Rollout Recommended")
            print("   - Modest improvement shown")
            print("   - Start with 20% traffic, monitor closely")
        else:
            print("\n❌ HOLD: Keep Original System")
            print("   - No significant improvement")
            print("   - Additional complexity not justified")
        
        # Risk assessment
        orig_avg_dd = np.mean([r['max_drawdown'] for r in all_results['original'].values()])
        flex_avg_dd = np.mean([r['max_drawdown'] for r in all_results['flexible'].values()])
        
        if flex_avg_dd > orig_avg_dd * 1.2:
            print("\n⚠️  WARNING: Flexible ML shows higher risk (drawdown)")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()