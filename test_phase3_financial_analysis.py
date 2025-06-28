"""
Phase 3 Financial Analysis - Detailed P&L Report
================================================

Comprehensive financial analysis comparing Original vs Flexible ML systems
with realistic trading simulation starting with ₹1,00,000 capital.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')
import logging
# Reduce logging noise
logging.getLogger('core.regime_filter_fix_v2').setLevel(logging.WARNING)
logging.getLogger('scanner').setLevel(logging.WARNING)

from data.smart_data_manager import SmartDataManager
from scanner.flexible_bar_processor import FlexibleBarProcessor
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from scanner.mode_aware_processor import ModeAwareBarProcessor
from scanner.confirmation_processor import ConfirmationProcessor
from scanner.smart_exit_manager import SmartExitManager
from scanner.dynamic_threshold_calculator import DynamicThresholdCalculator
from config.settings import TradingConfig
from config.phase2_optimized_settings import get_phase2_config, get_confirmation_processor_params
# import matplotlib.pyplot as plt
# import seaborn as sns


class DetailedBacktestEngine:
    """Enhanced backtest engine with detailed financial tracking"""
    
    def __init__(self, initial_capital=100000, commission_percent=0.03, slippage_percent=0.05, use_smart_exits=True):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.commission_percent = commission_percent / 100  # Convert to decimal
        self.slippage_percent = slippage_percent / 100
        self.use_smart_exits = use_smart_exits
        
        # Trade tracking
        self.trades = []
        self.open_position = None
        self.equity_curve = [initial_capital]
        self.daily_pnl = []
        
        # Metrics
        self.total_commission = 0
        self.total_slippage = 0
        
    def execute_trade(self, signal, bar_data, bar_index):
        """Execute trade with realistic costs"""
        close_price = bar_data['close']
        
        # Close existing position if opposite signal
        if self.open_position:
            if (self.open_position['type'] == 'long' and signal['signal'] < 0) or \
               (self.open_position['type'] == 'short' and signal['signal'] > 0):
                self.close_position(close_price, bar_data.name, bar_index)
        
        # Open new position
        if not self.open_position and signal['signal'] != 0:
            position_size = self.capital * 0.95  # Use 95% of capital
            
            # Apply slippage to entry
            if signal['signal'] > 0:  # Long
                entry_price = close_price * (1 + self.slippage_percent)
                position_type = 'long'
            else:  # Short
                entry_price = close_price * (1 - self.slippage_percent)
                position_type = 'short'
            
            # Calculate shares and commission
            shares = position_size / entry_price
            entry_commission = position_size * self.commission_percent
            self.total_commission += entry_commission
            
            # Set stop loss and take profit levels
            if self.use_smart_exits:
                if position_type == 'long':
                    stop_loss = entry_price * 0.99  # 1% stop loss
                    take_profit = entry_price * 1.015  # 1.5% take profit
                else:  # short
                    stop_loss = entry_price * 1.01  # 1% stop loss
                    take_profit = entry_price * 0.985  # 1.5% take profit
            else:
                stop_loss = None
                take_profit = None
            
            self.open_position = {
                'type': position_type,
                'entry_price': entry_price,
                'entry_time': bar_data.name,
                'entry_bar': bar_index,
                'shares': shares,
                'entry_commission': entry_commission,
                'prediction': signal['prediction'],
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
    
    def close_position(self, exit_price, exit_time, exit_bar):
        """Close position and calculate P&L"""
        if not self.open_position:
            return
        
        pos = self.open_position
        
        # Apply slippage to exit
        if pos['type'] == 'long':
            exit_price = exit_price * (1 - self.slippage_percent)
            gross_pnl = (exit_price - pos['entry_price']) * pos['shares']
        else:  # Short
            exit_price = exit_price * (1 + self.slippage_percent)
            gross_pnl = (pos['entry_price'] - exit_price) * pos['shares']
        
        # Calculate commission
        exit_value = exit_price * pos['shares']
        exit_commission = exit_value * self.commission_percent
        self.total_commission += exit_commission
        
        # Net P&L
        net_pnl = gross_pnl - pos['entry_commission'] - exit_commission
        return_pct = net_pnl / (pos['entry_price'] * pos['shares']) * 100
        
        # Update capital
        self.capital += net_pnl
        self.equity_curve.append(self.capital)
        
        # Record trade
        trade = {
            'entry_time': pos['entry_time'],
            'exit_time': exit_time,
            'type': pos['type'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'shares': pos['shares'],
            'gross_pnl': gross_pnl,
            'commission': pos['entry_commission'] + exit_commission,
            'net_pnl': net_pnl,
            'return_pct': return_pct,
            'bars_held': exit_bar - pos['entry_bar'],
            'prediction': pos['prediction']
        }
        self.trades.append(trade)
        self.open_position = None
    
    def calculate_metrics(self):
        """Calculate comprehensive performance metrics"""
        if not self.trades:
            return self._empty_metrics()
        
        # Convert trades to DataFrame for analysis
        trades_df = pd.DataFrame(self.trades)
        
        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = trades_df[trades_df['net_pnl'] > 0]
        losing_trades = trades_df[trades_df['net_pnl'] <= 0]
        
        win_rate = len(winning_trades) / total_trades * 100
        
        # P&L metrics
        total_gross_pnl = trades_df['gross_pnl'].sum()
        total_net_pnl = trades_df['net_pnl'].sum()
        total_return_pct = (self.capital - self.initial_capital) / self.initial_capital * 100
        
        # Average metrics
        avg_win = winning_trades['net_pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['net_pnl'].mean() if len(losing_trades) > 0 else 0
        avg_win_pct = winning_trades['return_pct'].mean() if len(winning_trades) > 0 else 0
        avg_loss_pct = losing_trades['return_pct'].mean() if len(losing_trades) > 0 else 0
        
        # Risk metrics
        profit_factor = abs(winning_trades['net_pnl'].sum() / losing_trades['net_pnl'].sum()) if len(losing_trades) > 0 and losing_trades['net_pnl'].sum() != 0 else 0
        
        # Max drawdown
        equity_array = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity_array)
        drawdown = (peak - equity_array) / peak * 100
        max_drawdown = np.max(drawdown)
        
        # Sharpe ratio (simplified)
        if len(trades_df) > 1:
            returns = trades_df['return_pct'].values
            sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe = 0
        
        return {
            # Trade Statistics
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            
            # Capital & Returns
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_gross_pnl': total_gross_pnl,
            'total_commission': self.total_commission,
            'total_net_pnl': total_net_pnl,
            'total_return_pct': total_return_pct,
            
            # Per Trade Metrics
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_win_pct': avg_win_pct,
            'avg_loss_pct': avg_loss_pct,
            'avg_bars_held': trades_df['bars_held'].mean(),
            
            # Risk Metrics
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe,
            
            # Largest wins/losses
            'largest_win': trades_df['net_pnl'].max(),
            'largest_loss': trades_df['net_pnl'].min(),
        }
    
    def _empty_metrics(self):
        """Return empty metrics structure"""
        return {
            'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0,
            'win_rate': 0, 'initial_capital': self.initial_capital,
            'final_capital': self.capital, 'total_gross_pnl': 0,
            'total_commission': 0, 'total_net_pnl': 0, 'total_return_pct': 0,
            'avg_win': 0, 'avg_loss': 0, 'avg_win_pct': 0, 'avg_loss_pct': 0,
            'avg_bars_held': 0, 'profit_factor': 0, 'max_drawdown': 0,
            'sharpe_ratio': 0, 'largest_win': 0, 'largest_loss': 0
        }


def run_financial_backtest(symbol: str, use_flexible: bool = False, days: int = 180, ml_threshold: float = 3.0, use_mode_filter: bool = True, use_full_system: bool = False, use_dynamic_threshold: bool = False):
    """Run detailed financial backtest with ML threshold and mode filtering"""
    
    mode_str = " + Mode Filter" if use_mode_filter else ""
    threshold_str = "dynamic" if use_dynamic_threshold else f"{ml_threshold}"
    print(f"\n{'='*80}")
    print(f"Testing {symbol} with {'FLEXIBLE' if use_flexible else 'ORIGINAL'} ML (threshold={threshold_str}){mode_str}")
    print(f"{'='*80}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=days)
    
    if df is None or len(df) < 2500:
        print(f"Insufficient data: {len(df) if df is not None else 0} bars")
        return None
    
    print(f"Data loaded: {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    
    # Analyze stock characteristics for adaptive configuration
    stock_stats = None
    if use_full_system:
        print("Analyzing stock characteristics for optimization...")
        stock_stats = data_manager.analyze_price_movement(df)
        print(f"  Average range: {stock_stats.get('avg_range_pct', 0):.2f}%")
        print(f"  Volatility profile: {'High' if stock_stats.get('avg_range_pct', 0) > 1.5 else 'Normal'}")
        
        # Adaptive ML threshold based on volatility
        if ml_threshold is None:
            avg_range = stock_stats.get('avg_range_pct', 1.0)
            if avg_range > 2.0:  # High volatility
                ml_threshold = 3.5
            elif avg_range < 0.5:  # Low volatility
                ml_threshold = 2.0
            else:  # Normal volatility
                ml_threshold = 2.5
            print(f"  Adaptive ML threshold: {ml_threshold}")
    
    if ml_threshold is None:
        ml_threshold = 3.0  # Default
    
    # Configuration - use adaptive settings if full system enabled
    if use_full_system and stock_stats:
        # Adaptive configuration based on stock characteristics
        avg_range = stock_stats.get('avg_range_pct', 1.0)
        neighbors = 10 if avg_range > 1.5 else 8  # More neighbors for volatile stocks
        
        config = TradingConfig(
            source='close',
            neighbors_count=neighbors,
            max_bars_back=2000,
            feature_count=5,
            use_volatility_filter=True,
            use_regime_filter=True,
            use_adx_filter=False,
            regime_threshold=-0.1
        )
        print(f"Using adaptive configuration: neighbors={neighbors}")
    elif use_mode_filter:
        # Standard Phase 2 configuration
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
        print("Using Phase 2 optimized configuration")
    else:
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
    
    # Create processor with mode filtering if enabled
    if use_mode_filter:
        # Use Mode Aware Processor for market condition filtering
        processor = ModeAwareBarProcessor(
            config=config,
            symbol=symbol,
            timeframe='5minute',
            allow_trend_trades=False  # Only trade in cycling markets
        )
        print("Mode filtering enabled - will only trade in cycling markets")
    elif use_flexible:
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
    
    # Initialize backtest engine with smart exits
    backtest = DetailedBacktestEngine(initial_capital=100000, use_smart_exits=True)
    
    # Initialize smart exit manager if using full system
    if use_full_system and stock_stats:
        # Choose exit strategy based on stock volatility
        avg_range = stock_stats.get('avg_range_pct', 1.0)
        if avg_range > 1.5:
            exit_strategy = 'aggressive'  # For volatile stocks
        elif avg_range < 0.8:
            exit_strategy = 'scalping'    # For low volatility
        else:
            exit_strategy = 'balanced'    # Normal stocks
            
        backtest.exit_manager = SmartExitManager(strategy=exit_strategy)
        print(f"Using {exit_strategy} exit strategy")
    
    # Initialize confirmation processor if using full system
    confirmation_processor = None
    if use_full_system:
        confirm_params = get_confirmation_processor_params()
        # Simple confirmation check - just use volume for now
        confirmation_processor = None  # Simplified for testing
        print("Confirmation filters enabled")
    
    # Initialize dynamic threshold calculator if enabled
    dynamic_calc = None
    if use_dynamic_threshold:
        dynamic_calc = DynamicThresholdCalculator(lookback_period=500, percentile=85)
        print("Dynamic ML threshold calculation enabled")
    
    # Process bars and collect signals
    signals = []
    signals_filtered = 0
    mode_filtered = 0
    warmup_complete = False
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'],
            row['close'], row['volume']
        )
        
        if i == 2000:
            warmup_complete = True
            print("ML warmup complete at bar 2000")
        
        # Collect predictions for dynamic threshold AFTER warmup
        if warmup_complete and result and use_dynamic_threshold:
            if hasattr(result, 'flexible_prediction') and use_flexible:
                prediction = result.flexible_prediction
            else:
                prediction = result.prediction
                
            # Only collect non-zero predictions
            if prediction != 0:
                dynamic_calc.add_prediction(prediction)
                
                # Initialize threshold after collecting some predictions
                if len(dynamic_calc.predictions) == 100 and ml_threshold == 3.0:
                    calculated_threshold = dynamic_calc.calculate_threshold()
                    # Use hybrid approach: max of calculated and static minimum
                    ml_threshold = max(calculated_threshold, 2.8)
                    print(f"Dynamic threshold initialized to {ml_threshold:.2f} (calc: {calculated_threshold:.2f}) after 100 predictions")
                
                # Update threshold every 100 predictions
                elif len(dynamic_calc.predictions) % 100 == 0:
                    old_threshold = ml_threshold
                    ml_threshold = dynamic_calc.calculate_threshold()
                    if abs(ml_threshold - old_threshold) > 0.1:
                        print(f"Dynamic threshold updated: {old_threshold:.2f} → {ml_threshold:.2f}")
        
        if warmup_complete and result:
            # Check for signals with ML threshold filter
            if result.start_long_trade or result.start_short_trade:
                # Get prediction value
                if hasattr(result, 'flexible_prediction') and use_flexible:
                    prediction = result.flexible_prediction
                else:
                    prediction = result.prediction
                
                # Apply ML threshold filter
                if abs(prediction) >= ml_threshold:
                    signal = {
                        'bar_index': i,
                        'signal': 1 if result.start_long_trade else -1,
                        'prediction': prediction
                    }
                    signals.append(signal)
                    backtest.execute_trade(signal, row, i)
                else:
                    signals_filtered += 1
        
        # Track mode filtering if available
        if use_mode_filter and result and hasattr(result, 'market_mode'):
            # ModeAwareBarResult includes market_mode field
            if result.market_mode == 'trending' and (result.start_long_trade or result.start_short_trade):
                mode_filtered += 1
            
            # Check for exits
            if backtest.open_position:
                # Check smart exits first (stop loss / take profit)
                if backtest.use_smart_exits:
                    should_exit = False
                    exit_price = None
                    
                    pos = backtest.open_position
                    if pos['type'] == 'long':
                        if row['low'] <= pos['stop_loss']:
                            should_exit = True
                            exit_price = pos['stop_loss']
                        elif row['high'] >= pos['take_profit']:
                            should_exit = True
                            exit_price = pos['take_profit']
                    else:  # short
                        if row['high'] >= pos['stop_loss']:
                            should_exit = True
                            exit_price = pos['stop_loss']
                        elif row['low'] <= pos['take_profit']:
                            should_exit = True
                            exit_price = pos['take_profit']
                    
                    # Time-based exit after 50 bars (~4 hours)
                    if not should_exit and (i - pos['entry_bar']) >= 50:
                        should_exit = True
                        exit_price = row['close']
                    
                    if should_exit:
                        backtest.close_position(exit_price, idx, i)
                
                # Check signal-based exits
                elif result.end_long_trade or result.end_short_trade:
                    backtest.close_position(row['close'], idx, i)
    
    # Close any open position at end
    if backtest.open_position and len(df) > 0:
        last_row = df.iloc[-1]
        backtest.close_position(last_row['close'], df.index[-1], len(df)-1)
    
    if use_mode_filter:
        print(f"Total signals: {len(signals)} taken, {signals_filtered} filtered by ML threshold, {mode_filtered} filtered by market mode")
    else:
        print(f"Total signals: {len(signals)} taken, {signals_filtered} filtered by ML threshold")
    
    # Calculate and return metrics
    metrics = backtest.calculate_metrics()
    metrics['symbol'] = symbol
    metrics['ml_system'] = 'flexible' if use_flexible else 'original'
    
    return metrics, backtest.trades


def print_detailed_report(metrics):
    """Print detailed financial report"""
    print(f"\n{'='*60}")
    print(f"FINANCIAL PERFORMANCE REPORT - {metrics['ml_system'].upper()} ML")
    print(f"{'='*60}")
    
    print(f"\n📊 TRADING SUMMARY")
    print(f"  Total Trades: {metrics['total_trades']}")
    print(f"  Winning Trades: {metrics['winning_trades']}")
    print(f"  Losing Trades: {metrics['losing_trades']}")
    print(f"  Win Rate: {metrics['win_rate']:.1f}%")
    
    print(f"\n💰 CAPITAL & RETURNS")
    print(f"  Initial Capital: ₹{metrics['initial_capital']:,.0f}")
    print(f"  Final Capital: ₹{metrics['final_capital']:,.0f}")
    print(f"  Total Gross P&L: ₹{metrics['total_gross_pnl']:,.2f}")
    print(f"  Total Commission: ₹{metrics['total_commission']:,.2f}")
    print(f"  Total Net P&L: ₹{metrics['total_net_pnl']:,.2f}")
    print(f"  Total Return: {metrics['total_return_pct']:.2f}%")
    
    print(f"\n📈 PER TRADE METRICS")
    print(f"  Average Win: ₹{metrics['avg_win']:,.2f} ({metrics['avg_win_pct']:.2f}%)")
    print(f"  Average Loss: ₹{metrics['avg_loss']:,.2f} ({metrics['avg_loss_pct']:.2f}%)")
    print(f"  Average Bars Held: {metrics['avg_bars_held']:.0f}")
    
    print(f"\n⚠️ RISK METRICS")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.1f}%")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Largest Win: ₹{metrics['largest_win']:,.2f}")
    print(f"  Largest Loss: ₹{metrics['largest_loss']:,.2f}")


def main():
    """Run comprehensive financial analysis with ML threshold options"""
    
    print("\n" + "="*80)
    print("PHASE 3 FINANCIAL ANALYSIS - ₹1,00,000 Starting Capital")
    print("Extended Analysis: 180 days, 8 stocks")
    print("="*80)
    
    # Ask user for ML threshold preference
    # Automatically use optimal settings
    print("\nUsing optimal settings:")
    print("- ML threshold of 3.0 for signal quality")
    print("- Market mode filtering (trades only in cycling markets)")
    print("- Smart exits: 1% stop loss, 1.5% take profit")
    print("- Volume confirmation from Phase 2")
    print("- Testing period: 180 days (6 months)")
    print("- Stock universe: 6 major stocks (with sufficient data)\n")
    
    # For now, run with basic system (set use_full_system=True to enable all components)
    run_with_threshold(ml_threshold=3.0, use_full_system=False)


def run_with_threshold(ml_threshold=3.0, use_full_system=False):
    """Run analysis with specific ML threshold"""
    # Extended stock list with diverse volatility profiles
    # Note: Only using stocks with sufficient data for 180-day backtest
    symbols = ['RELIANCE', 'INFY', 'TCS', 'AXISBANK', 'ICICIBANK', 'KOTAKBANK']
    all_results = {'original': [], 'flexible': []}
    
    for symbol in symbols:
        print(f"\n{'*'*80}")
        print(f"ANALYZING {symbol}")
        print(f"{'*'*80}")
        
        if use_full_system:
            # Test with FULL SYSTEM
            full_metrics, full_trades = run_financial_backtest(
                symbol, 
                use_flexible=True,
                ml_threshold=ml_threshold,
                use_mode_filter=True,
                use_full_system=True
            )
            if full_metrics:
                all_results['full_system'] = all_results.get('full_system', [])
                all_results['full_system'].append(full_metrics)
                print_detailed_report(full_metrics)
        else:
            # Test with mode filtering (Phase 2 + smart exits)
            mode_metrics, mode_trades = run_financial_backtest(
                symbol, 
                use_flexible=False,
                ml_threshold=ml_threshold,
                use_mode_filter=True,
                use_full_system=False,
                days=180  # Extended timeframe
            )
            if mode_metrics:
                all_results['mode_filtered'] = all_results.get('mode_filtered', [])
                all_results['mode_filtered'].append(mode_metrics)
                print_detailed_report(mode_metrics)
            
            # Test flexible ML for comparison
            flex_metrics, flex_trades = run_financial_backtest(
                symbol,
                use_flexible=True,
                ml_threshold=ml_threshold,
                use_mode_filter=False,
                use_full_system=False,
                days=180  # Extended timeframe
            )
            if flex_metrics:
                all_results['flexible'].append(flex_metrics)
                print_detailed_report(flex_metrics)
    
    # Portfolio Summary
    print("\n" + "="*80)
    print("PORTFOLIO SUMMARY - ALL STOCKS COMBINED (180 DAYS)")
    print("="*80)
    
    for system in ['original', 'flexible']:
        if all_results[system]:
            print(f"\n{system.upper()} ML SYSTEM:")
            
            # Aggregate metrics
            total_trades = sum(m['total_trades'] for m in all_results[system])
            total_pnl = sum(m['total_net_pnl'] for m in all_results[system])
            avg_win_rate = np.mean([m['win_rate'] for m in all_results[system]])
            avg_return = np.mean([m['total_return_pct'] for m in all_results[system]])
            total_commission = sum(m['total_commission'] for m in all_results[system])
            
            print(f"  Total Trades (All Stocks): {total_trades}")
            print(f"  Average Win Rate: {avg_win_rate:.1f}%")
            print(f"  Total Net P&L: ₹{total_pnl:,.2f}")
            print(f"  Average Return per Stock: {avg_return:.2f}%")
            print(f"  Total Commission Paid: ₹{total_commission:,.2f}")
            
            # Per stock performance
            print("\n  Per Stock Performance:")
            for metrics in all_results[system]:
                print(f"    {metrics['symbol']}: ₹{metrics['total_net_pnl']:,.2f} "
                      f"({metrics['total_return_pct']:.2f}%) - "
                      f"{metrics['total_trades']} trades")
    
    # Final Comparison
    if 'original' in all_results and 'full_system' in all_results:
        print("\n" + "="*80)
        print("FULL SYSTEM vs ORIGINAL ML COMPARISON")
        print("="*80)
        
        orig_total_pnl = sum(m['total_net_pnl'] for m in all_results['original'])
        full_total_pnl = sum(m['total_net_pnl'] for m in all_results['full_system'])
        
        improvement = ((full_total_pnl - orig_total_pnl) / abs(orig_total_pnl) * 100) if orig_total_pnl != 0 else 0
        
        print(f"\nOriginal ML Total P&L: ₹{orig_total_pnl:,.2f}")
        print(f"Full System Total P&L: ₹{full_total_pnl:,.2f}")
        print(f"Improvement: ₹{full_total_pnl - orig_total_pnl:,.2f} ({improvement:+.1f}%)")
        
        if full_total_pnl > orig_total_pnl:
            print("\n✅ RECOMMENDATION: Deploy Full System with All Components")
        else:
            print("\n❌ RECOMMENDATION: Needs further optimization")


def test_multiple_thresholds():
    """Test multiple ML thresholds to find optimal"""
    print("\n" + "="*80)
    print("ML THRESHOLD OPTIMIZATION ANALYSIS")
    print("="*80)
    
    thresholds = [0.0, 2.0, 3.0, 4.0]
    symbols = ['RELIANCE', 'INFY', 'TCS']
    threshold_results = {}
    
    for threshold in thresholds:
        print(f"\n{'='*80}")
        print(f"TESTING ML THRESHOLD = {threshold}")
        print(f"{'='*80}")
        
        all_results = {'original': [], 'flexible': []}
        
        for symbol in symbols:
            # Only test flexible ML with different thresholds
            flex_metrics, _ = run_financial_backtest(symbol, use_flexible=True, ml_threshold=threshold)
            if flex_metrics:
                all_results['flexible'].append(flex_metrics)
        
        if all_results['flexible']:
            # Calculate aggregate metrics
            total_trades = sum(m['total_trades'] for m in all_results['flexible'])
            avg_win_rate = np.mean([m['win_rate'] for m in all_results['flexible']])
            total_pnl = sum(m['total_net_pnl'] for m in all_results['flexible'])
            avg_return = np.mean([m['total_return_pct'] for m in all_results['flexible']])
            
            threshold_results[threshold] = {
                'total_trades': total_trades,
                'avg_win_rate': avg_win_rate,
                'total_pnl': total_pnl,
                'avg_return': avg_return
            }
    
    # Display summary
    print("\n" + "="*80)
    print("ML THRESHOLD COMPARISON SUMMARY")
    print("="*80)
    
    print(f"\n{'Threshold':>10} {'Trades':>8} {'Win Rate':>10} {'Total P&L':>15} {'Avg Return':>12}")
    print("-" * 65)
    
    for threshold, metrics in threshold_results.items():
        print(f"{threshold:>10.1f} {metrics['total_trades']:>8} "
              f"{metrics['avg_win_rate']:>9.1f}% "
              f"₹{metrics['total_pnl']:>13,.2f} "
              f"{metrics['avg_return']:>11.2f}%")
    
    # Find best threshold
    if threshold_results:
        best_threshold = max(threshold_results.keys(), key=lambda k: threshold_results[k]['total_pnl'])
        print(f"\n✅ OPTIMAL ML THRESHOLD: {best_threshold}")
        print(f"   Expected Win Rate: {threshold_results[best_threshold]['avg_win_rate']:.1f}%")
        print(f"   Expected Return: {threshold_results[best_threshold]['avg_return']:.2f}%")
        print(f"   Expected P&L: ₹{threshold_results[best_threshold]['total_pnl']:,.2f}")


def test_dynamic_vs_static_threshold():
    """Test dynamic threshold vs static threshold"""
    print("\n" + "="*80)
    print("DYNAMIC vs STATIC ML THRESHOLD COMPARISON")
    print("Testing adaptive threshold calculation")
    print("="*80)
    
    symbols = ['RELIANCE', 'INFY', 'TCS']  # Test on best performers
    days = 90  # Shorter test for quick results
    
    results_comparison = {}
    
    for symbol in symbols:
        print(f"\n{'*'*80}")
        print(f"TESTING {symbol}")
        print(f"{'*'*80}")
        
        # Test with static threshold (3.0)
        static_metrics, _ = run_financial_backtest(
            symbol,
            use_flexible=True,
            days=days,
            ml_threshold=3.0,
            use_mode_filter=False,
            use_dynamic_threshold=False
        )
        
        # Test with dynamic threshold
        dynamic_metrics, _ = run_financial_backtest(
            symbol,
            use_flexible=True,
            days=days,
            ml_threshold=3.0,  # Will be overridden by dynamic
            use_mode_filter=False,
            use_dynamic_threshold=True
        )
        
        if static_metrics and dynamic_metrics:
            results_comparison[symbol] = {
                'static': static_metrics,
                'dynamic': dynamic_metrics
            }
    
    # Print comparison summary
    print("\n" + "="*80)
    print("DYNAMIC vs STATIC THRESHOLD - SUMMARY")
    print("="*80)
    
    print(f"\n{'Stock':>10} {'Static P&L':>15} {'Dynamic P&L':>15} {'Improvement':>15} {'Win Rate Change':>20}")
    print("-" * 80)
    
    for symbol, results in results_comparison.items():
        static = results['static']
        dynamic = results['dynamic']
        
        improvement = dynamic['total_net_pnl'] - static['total_net_pnl']
        win_rate_change = dynamic['win_rate'] - static['win_rate']
        
        print(f"{symbol:>10} ₹{static['total_net_pnl']:>13,.2f} ₹{dynamic['total_net_pnl']:>13,.2f} "
              f"₹{improvement:>13,.2f} {win_rate_change:>18.1f}%")
    
    # Overall performance
    total_static_pnl = sum(r['static']['total_net_pnl'] for r in results_comparison.values())
    total_dynamic_pnl = sum(r['dynamic']['total_net_pnl'] for r in results_comparison.values())
    total_improvement = total_dynamic_pnl - total_static_pnl
    
    print(f"\n{'TOTAL':>10} ₹{total_static_pnl:>13,.2f} ₹{total_dynamic_pnl:>13,.2f} "
          f"₹{total_improvement:>13,.2f} ({(total_improvement/abs(total_static_pnl)*100):>6.1f}%)")
    
    if total_improvement > 0:
        print("\n✅ RECOMMENDATION: Implement Dynamic ML Threshold")
    else:
        print("\n❌ RECOMMENDATION: Keep Static Threshold")


if __name__ == "__main__":
    # Uncomment the test you want to run:
    
    # main()  # Original comprehensive test
    test_dynamic_vs_static_threshold()  # New dynamic threshold test