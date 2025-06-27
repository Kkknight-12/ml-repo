"""
Multi-Stock Optimization Framework - FIXED VERSION
==================================================

Tests the comprehensive Lorentzian system across multiple stocks
with ALL exit strategies in a SINGLE pass for efficiency.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# Import our components
from data.smart_data_manager import SmartDataManager
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from scanner.ml_quality_filter import MLQualityFilter
from scanner.smart_exit_manager import SmartExitManager
from config.adaptive_config import create_adaptive_config
from data.data_types import Settings, FilterSettings
from utils.kelly_criterion import KellyCriterion


class MultiStockOptimizerFixed:
    """
    Framework for testing and optimizing across multiple stocks
    OPTIMIZED: Tests all exit strategies in a single pass
    """
    
    def __init__(self, symbols: List[str], timeframe: str = "5minute",
                 lookback_days: int = 90):
        """Initialize multi-stock optimizer"""
        self.symbols = symbols
        self.timeframe = timeframe
        self.lookback_days = lookback_days
        
        # Check for saved session
        if os.path.exists('.kite_session.json'):
            with open('.kite_session.json', 'r') as f:
                session_data = json.load(f)
                access_token = session_data.get('access_token')
                if access_token:
                    os.environ['KITE_ACCESS_TOKEN'] = access_token
        
        # Initialize components
        self.data_manager = SmartDataManager()
        self.ml_filter = MLQualityFilter(min_confidence=3.0, high_confidence=5.0)
        
        # Results storage for ALL strategies
        self.results_by_strategy = {
            'conservative': {},
            'scalping': {},
            'adaptive': {},
            'atr': {}
        }
        self.detailed_trades_by_strategy = {
            'conservative': {},
            'scalping': {},
            'adaptive': {},
            'atr': {}
        }
        
        # Ensure we have sufficient data for all stocks
        self._ensure_sufficient_data()
    
    def _ensure_sufficient_data(self):
        """Ensure all stocks have sufficient data for testing"""
        min_required_bars = 2500
        
        print(f"\n{'='*60}")
        print("CHECKING DATA AVAILABILITY")
        print(f"{'='*60}")
        
        bars_per_day = 75 if self.timeframe == "5minute" else 1
        
        for symbol in self.symbols:
            df = self.data_manager.get_data(
                symbol=symbol,
                interval=self.timeframe,
                days=self.lookback_days
            )
            
            current_bars = len(df) if df is not None else 0
            print(f"\n{symbol}: {current_bars} bars available")
            
            if current_bars < min_required_bars:
                print(f"  ⚠️  Insufficient data (need {min_required_bars}+)")
                
                days_to_try = [self.lookback_days * 2, 250, 365, 500, 730]
                
                for days in days_to_try:
                    print(f"  📊 Trying {days} days...", end='')
                    
                    df_extended = self.data_manager.get_data(
                        symbol=symbol,
                        interval=self.timeframe,
                        days=days
                    )
                    
                    new_bars = len(df_extended) if df_extended is not None else 0
                    print(f" Got {new_bars} bars")
                    
                    if new_bars >= min_required_bars:
                        print(f"  ✅ Success!")
                        self.actual_days_fetched = max(getattr(self, 'actual_days_fetched', self.lookback_days), days)
                        break
                else:
                    print(f"  ❌ Could not get sufficient data")
            else:
                print(f"  ✅ Sufficient data available")
    
    def test_all_strategies(self) -> Dict:
        """
        Test ALL exit strategies in a SINGLE pass per stock
        Much more efficient than running separate loops
        """
        print(f"\n{'='*60}")
        print(f"OPTIMIZED TEST - All Strategies in Single Pass")
        print(f"Stocks: {len(self.symbols)}, Strategies: 4")
        print(f"{'='*60}\n")
        
        # Test each stock ONCE with all strategies
        for symbol in self.symbols:
            print(f"\nProcessing {symbol}...")
            try:
                self._test_single_stock_all_strategies(symbol)
            except Exception as e:
                import traceback
                print(f"Error processing {symbol}: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                # Store error for all strategies
                for strategy in self.results_by_strategy:
                    self.results_by_strategy[strategy][symbol] = {'error': str(e)}
        
        # Generate summaries for all strategies
        all_summaries = {}
        for strategy in self.results_by_strategy:
            summary = self._generate_summary(strategy)
            all_summaries[strategy] = summary
            print(f"\n{'='*50}")
            print(f"RESULTS FOR {strategy.upper()} STRATEGY")
            print(f"{'='*50}")
            self._print_results(summary)
        
        return all_summaries
    
    def _test_single_stock_all_strategies(self, symbol: str):
        """
        Test a single stock with ALL exit strategies in one pass
        This is the KEY optimization - process data once, test all strategies
        """
        # Initialize Kelly calculators for each strategy
        kelly_calcs = {
            strategy: KellyCriterion(kelly_fraction=0.25) 
            for strategy in self.results_by_strategy
        }
        
        # Get data ONCE
        days_to_use = getattr(self, 'actual_days_fetched', self.lookback_days)
        df = self.data_manager.get_data(
            symbol=symbol,
            interval=self.timeframe,
            days=days_to_use
        )
        
        min_required_bars = 2500
        if df is None or len(df) < min_required_bars:
            actual_bars = len(df) if df is not None else 0
            error_msg = f'Insufficient data: {actual_bars} bars (need {min_required_bars}+)'
            for strategy in self.results_by_strategy:
                self.results_by_strategy[strategy][symbol] = {'error': error_msg}
            return
        
        # Get stock statistics for adaptive config
        stats = self.data_manager.analyze_price_movement(df)
        config = create_adaptive_config(symbol, self.timeframe, stats)
        
        # Initialize processor ONCE
        from config.settings import TradingConfig
        
        trading_config = TradingConfig(
            source=config.source,
            neighbors_count=config.neighbors_count,
            max_bars_back=config.max_bars_back,
            feature_count=config.feature_count,
            color_compression=config.color_compression,
            use_volatility_filter=config.use_volatility_filter,
            use_regime_filter=config.use_regime_filter,
            use_adx_filter=config.use_adx_filter,
            use_kernel_filter=config.use_kernel_filter,
            use_ema_filter=config.use_ema_filter,
            use_sma_filter=config.use_sma_filter,
            regime_threshold=config.regime_threshold,
            adx_threshold=config.adx_threshold,
            kernel_lookback=config.kernel_lookback,
            kernel_relative_weight=config.kernel_relative_weight,
            kernel_regression_level=config.kernel_regression_level,
            kernel_lag=config.kernel_lag,
            use_kernel_smoothing=config.use_kernel_smoothing,
            features=config.features
        )
        
        processor = EnhancedBarProcessor(
            config=trading_config,
            symbol=symbol,
            timeframe=self.timeframe
        )
        
        # Define ALL exit configurations
        # FIXED: Increased max_holding_bars and disabled trailing stops
        exit_configs = {
            'conservative': {
                'stop_loss_percent': 1.0,
                'take_profit_targets': [2.0],
                'target_sizes': [100],
                'use_trailing_stop': False,
                'max_holding_bars': 200  # Increased from 78
            },
            'scalping': {
                'stop_loss_percent': 0.5,
                'take_profit_targets': [0.5, 0.75, 1.0],
                'target_sizes': [50, 30, 20],
                'use_trailing_stop': False,  # Disabled for now
                'trailing_activation': 0.5,
                'trailing_distance': 0.25,
                'max_holding_bars': 100  # Increased from 20!
            },
            'adaptive': {
                'stop_loss_percent': 2.0,
                'take_profit_targets': [1.0, 2.0, 3.0],
                'target_sizes': [40, 40, 20],
                'use_trailing_stop': False,  # Disabled for now
                'trailing_activation': 1.0,
                'trailing_distance': 0.5,
                'max_holding_bars': 200  # Increased from 40
            },
            'atr': {
                'use_atr_stops': True,
                'atr_stop_multiplier': 2.0,
                'atr_profit_multipliers': [1.5, 3.0, 5.0],
                'target_sizes': [50, 30, 20],
                'use_trailing_stop': False,  # Disabled for now
                'atr_trailing_multiplier': 1.5,
                'max_holding_bars': 200  # Increased from 78
            }
        }
        
        # Create exit managers for ALL strategies
        exit_managers = {}
        for strategy, exit_config in exit_configs.items():
            # CRITICAL FIX: Only pass exit config, NOT mixed with adaptive
            use_atr = exit_config.get('use_atr_stops', False)
            exit_managers[strategy] = SmartExitManager(exit_config.copy(), use_atr_stops=use_atr)
        
        # Storage for trades by strategy
        trades_by_strategy = {strategy: [] for strategy in exit_configs}
        positions_by_strategy = {strategy: None for strategy in exit_configs}
        
        # Process bars ONCE for all strategies
        current_date = None
        
        print(f"  Processing {len(df)} bars for all strategies...")
        
        for idx, row in df.iterrows():
            bar_date = idx.date() if hasattr(idx, 'date') else idx
            bar_time = idx.time() if hasattr(idx, 'time') else None
            
            # Check for new trading day - close overnight positions for ALL strategies
            if current_date and bar_date != current_date:
                for strategy in exit_configs:
                    position = positions_by_strategy[strategy]
                    if position:
                        exit_price = row['open']
                        entry_price = position['entry_price']
                        direction = position['direction']
                        
                        if direction == 1:
                            pnl_pct = (exit_price - entry_price) / entry_price * 100
                        else:
                            pnl_pct = (entry_price - exit_price) / entry_price * 100
                        
                        trades_by_strategy[strategy].append({
                            'symbol': symbol,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl_pct': pnl_pct,
                            'bars_held': 1,
                            'direction': direction,
                            'exit_reason': 'day_end',
                            'quantity': position.get('quantity', 100)
                        })
                        
                        if exit_managers[strategy] and symbol in exit_managers[strategy].positions:
                            del exit_managers[strategy].positions[symbol]
                        
                        positions_by_strategy[strategy] = None
            
            current_date = bar_date
            
            # Update ATR for strategies that use it
            for strategy, exit_mgr in exit_managers.items():
                if hasattr(exit_mgr, 'update_atr'):
                    exit_mgr.update_atr(row['high'], row['low'], row['close'])
            
            # Process bar ONCE
            result = processor.process_bar(
                open_price=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume']
            )
            
            if result is None:
                continue
            
            current_signal = result.signal
            ml_prediction = result.prediction
            
            # Create signal dict for ML filter
            signal_dict = {
                'timestamp': idx,
                'signal': current_signal,
                'prediction': ml_prediction,
                'filter_states': result.filter_states,
                'features': {}
            }
            
            # Apply ML filter
            if current_signal != 0:
                ml_signal = self.ml_filter.filter_signal(signal_dict, symbol)
                if ml_signal is None:
                    current_signal = 0
            
            # Check time constraints
            can_enter = True
            if bar_time:
                if (bar_time.hour == 9 and bar_time.minute < 30) or \
                   (bar_time.hour == 15 and bar_time.minute >= 15):
                    can_enter = False
            
            # Process each strategy
            for strategy in exit_configs:
                position = positions_by_strategy[strategy]
                exit_mgr = exit_managers[strategy]
                
                # Check exits if in position
                if position and exit_mgr and symbol in exit_mgr.positions:
                    exit_pos = exit_mgr.positions[symbol]
                    exit_pos.current_price = row['close']
                    
                    # Update max profit
                    if exit_pos.direction == 1:
                        current_profit = (row['close'] - exit_pos.entry_price) / exit_pos.entry_price * 100
                    else:
                        current_profit = (exit_pos.entry_price - row['close']) / exit_pos.entry_price * 100
                    exit_pos.max_profit = max(exit_pos.max_profit, current_profit)
                    
                    exit_signal = exit_mgr.check_exit(
                        symbol=symbol,
                        current_price=row['close'],
                        current_ml_signal=ml_prediction,
                        timestamp=idx,
                        high=row['high'],
                        low=row['low']
                    )
                    
                    if exit_signal and exit_signal.should_exit:
                        exit_record = exit_mgr.execute_exit(symbol, exit_signal)
                        
                        trades_by_strategy[strategy].append({
                            'symbol': symbol,
                            'entry_price': exit_record.get('entry_price', row['close']),
                            'exit_price': exit_record.get('exit_price', row['close']),
                            'pnl_pct': exit_record.get('pnl_pct', 0),
                            'bars_held': exit_record.get('bars_held', 1),
                            'direction': exit_record.get('direction', 1),
                            'exit_reason': exit_record.get('exit_type', 'smart_exit'),
                            'quantity': exit_record.get('quantity', 100)
                        })
                        
                        kelly_calcs[strategy].add_trade(exit_record.get('pnl_pct', 0))
                        
                        if symbol not in exit_mgr.positions:
                            positions_by_strategy[strategy] = None
                
                # Check for new entry if not in position
                if not position and current_signal != 0 and result.bar_index >= 2000 and can_enter:
                    direction = 1 if current_signal > 0 else -1
                    entry_price = row['close']
                    
                    # Use Kelly sizing
                    kelly_calc = kelly_calcs[strategy]
                    if kelly_calc and exit_mgr:
                        if direction == 1:
                            stop_loss = entry_price * (1 - exit_mgr.stop_loss_pct / 100)
                        else:
                            stop_loss = entry_price * (1 + exit_mgr.stop_loss_pct / 100)
                        
                        account_balance = 1000000
                        kelly_position = kelly_calc.calculate_position_size(
                            account_balance=account_balance,
                            entry_price=entry_price,
                            stop_loss=stop_loss
                        )
                        quantity = kelly_position['shares']
                    else:
                        quantity = 100
                    
                    # Enter position
                    exit_mgr.enter_position(
                        symbol=symbol,
                        entry_price=entry_price,
                        quantity=quantity,
                        direction=direction,
                        ml_signal=ml_prediction,
                        timestamp=idx
                    )
                    
                    positions_by_strategy[strategy] = {
                        'entry_price': entry_price,
                        'entry_time': idx,
                        'entry_bar': result.bar_index,
                        'direction': direction,
                        'quantity': quantity
                    }
        
        # Force exit any remaining positions
        for strategy in exit_configs:
            position = positions_by_strategy[strategy]
            if position:
                exit_price = df.iloc[-1]['close']
                entry_price = position['entry_price']
                direction = position['direction']
                
                if direction == 1:
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price * 100
                
                trades_by_strategy[strategy].append({
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'bars_held': 1,
                    'direction': direction,
                    'exit_reason': 'end_of_data',
                    'quantity': position.get('quantity', 100)
                })
        
        # Calculate statistics for each strategy
        for strategy, trades in trades_by_strategy.items():
            if trades:
                # Debug: Show exit reasons for first stock of each strategy
                if symbol == 'RELIANCE':
                    print(f"\nDEBUG {symbol} - {strategy}:")
                    
                    # Count exit reasons
                    trades_df_temp = pd.DataFrame(trades)
                    exit_counts = trades_df_temp['exit_reason'].value_counts()
                    print(f"Exit reason breakdown ({len(trades)} total trades):")
                    for reason, count in exit_counts.items():
                        print(f"  {reason}: {count} ({count/len(trades)*100:.1f}%)")
                    
                    # Show average P&L by exit type
                    avg_pnl_by_exit = trades_df_temp.groupby('exit_reason')['pnl_pct'].mean()
                    print(f"\nAverage P&L by exit type:")
                    for reason, avg_pnl in avg_pnl_by_exit.items():
                        print(f"  {reason}: {avg_pnl:.3f}%")
                
                result = self._calculate_statistics(trades, strategy, exit_configs[strategy])
                self.results_by_strategy[strategy][symbol] = result
                self.detailed_trades_by_strategy[strategy][symbol] = pd.DataFrame(trades)
                
                # Add ML accuracy
                ml_stats = self.ml_filter.get_accuracy_stats(symbol)
                if ml_stats and ml_stats['total_signals'] > 0:
                    result['ml_accuracy'] = ml_stats['overall_accuracy']
            else:
                self.results_by_strategy[strategy][symbol] = {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'total_return': 0,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'expectancy': 0,
                    'profit_factor': 0,
                    'max_drawdown': 0,
                    'car_maxdd': 0,
                    'config': f"{strategy.upper()} strategy - no trades"
                }
    
    def _calculate_statistics(self, trades: List[Dict], strategy: str, exit_config: Dict) -> Dict:
        """
        CRITICAL: Calculate statistics with CORRECT compound returns
        """
        trades_df = pd.DataFrame(trades)
        winning_trades = trades_df[trades_df['pnl_pct'] > 0]
        losing_trades = trades_df[trades_df['pnl_pct'] <= 0]
        
        # CRITICAL FIX: Compound returns correctly
        trade_multipliers = 1 + trades_df['pnl_pct'] / 100
        compound_multiplier = trade_multipliers.prod()
        total_return = (compound_multiplier - 1) * 100
        
        # Debug check for unrealistic returns
        if abs(total_return) > 1000:
            print(f"\n⚠️  WARNING: Extreme return detected: {total_return:.2f}%")
            print(f"   Trades: {len(trades_df)}, Multiplier: {compound_multiplier:.4f}")
            print(f"   Sample PnLs: {trades_df['pnl_pct'].head(10).tolist()}")
        
        win_rate = len(winning_trades) / len(trades_df) * 100
        avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
        avg_loss = abs(losing_trades['pnl_pct'].mean()) if len(losing_trades) > 0 else 0
        
        # Additional stats for debugging
        max_win = winning_trades['pnl_pct'].max() if len(winning_trades) > 0 else 0
        max_loss = abs(losing_trades['pnl_pct'].min()) if len(losing_trades) > 0 else 0
        
        # Debug if average win/loss seem wrong
        if avg_win < 0.5 and win_rate > 70:
            print(f"\n⚠️  SUSPICIOUS: High win rate ({win_rate:.1f}%) but tiny avg win ({avg_win:.3f}%)")
            print(f"   Max win: {max_win:.2f}%, Max loss: {max_loss:.2f}%")
            print(f"   This suggests targets are NOT being hit!")
        
        # Expectancy
        expectancy = (win_rate/100 * avg_win) - ((100-win_rate)/100 * avg_loss)
        
        # Profit Factor
        total_wins = winning_trades['pnl_pct'].sum() if len(winning_trades) > 0 else 0
        total_losses = abs(losing_trades['pnl_pct'].sum()) if len(losing_trades) > 0 else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # CRITICAL: Calculate drawdown using COMPOUND returns
        cumulative_multiplier = trade_multipliers.cumprod()
        cumulative_returns_pct = (cumulative_multiplier - 1) * 100
        running_max = cumulative_returns_pct.expanding().max()
        drawdown = cumulative_returns_pct - running_max
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0
        
        # Annualized metrics
        # We need to know the actual timespan, not just number of trades
        # For now, use a simple approximation based on number of trades
        # Assuming ~2-5 trades per day on average
        trading_days = len(trades_df) / 3  # Rough estimate
        years = trading_days / 252 if trading_days > 0 else 1
        
        # Protect against extreme annualization
        if years < 0.1:  # Less than ~25 trading days
            annualized_return = total_return  # Don't annualize
        else:
            annualized_return = ((compound_multiplier ** (1/years)) - 1) * 100 if compound_multiplier > 0 else -100
        
        car_maxdd = annualized_return / max_drawdown if max_drawdown > 0 else 0
        
        # Create proper config description
        config_desc = f"\n{strategy.upper()} Strategy Configuration\n"
        config_desc += "="*50 + "\n"
        if strategy == 'atr':
            config_desc += f"Stop Loss: {exit_config.get('atr_stop_multiplier', 2.0)}x ATR\n"
            config_desc += f"Targets: {exit_config.get('atr_profit_multipliers', [])} x ATR\n"
        else:
            config_desc += f"Stop Loss: {exit_config.get('stop_loss_percent', 0)}%\n"
            config_desc += f"Targets: {exit_config.get('take_profit_targets', [])}%\n"
        config_desc += f"Position Sizes: {exit_config.get('target_sizes', [])}%\n"
        config_desc += f"Trailing Stop: {exit_config.get('use_trailing_stop', False)}\n"
        config_desc += f"Max Hold: {exit_config.get('max_holding_bars', 0)} bars\n"
        
        return {
            'total_trades': len(trades_df),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_return': total_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'expectancy': expectancy,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'car_maxdd': car_maxdd,
            'annualized_return': annualized_return,
            'config': config_desc
        }
    
    def _generate_summary(self, strategy: str) -> Dict:
        """Generate summary statistics for a specific strategy"""
        valid_results = {k: v for k, v in self.results_by_strategy[strategy].items() 
                        if 'error' not in v}
        
        if not valid_results:
            return {'error': 'No valid results', 'strategy': strategy}
        
        # Aggregate metrics
        total_trades = sum(r['total_trades'] for r in valid_results.values())
        total_wins = sum(r['winning_trades'] for r in valid_results.values())
        
        overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        avg_return = np.mean([r['total_return'] for r in valid_results.values()])
        
        # Weighted expectancy
        total_expectancy = sum(r['expectancy'] * r['total_trades'] for r in valid_results.values())
        overall_expectancy = total_expectancy / total_trades if total_trades > 0 else 0
        
        # Best and worst performers
        returns_by_stock = {k: v['total_return'] for k, v in valid_results.items()}
        best_stock = max(returns_by_stock, key=returns_by_stock.get)
        worst_stock = min(returns_by_stock, key=returns_by_stock.get)
        
        return {
            'strategy': strategy,
            'stocks_tested': len(valid_results),
            'total_trades': total_trades,
            'overall_win_rate': overall_win_rate,
            'avg_return_per_stock': avg_return,
            'total_return': avg_return,
            'overall_expectancy': overall_expectancy,
            'best_performer': {
                'symbol': best_stock,
                'return': returns_by_stock[best_stock],
                'trades': valid_results[best_stock]['total_trades']
            },
            'worst_performer': {
                'symbol': worst_stock,
                'return': returns_by_stock[worst_stock],
                'trades': valid_results[worst_stock]['total_trades']
            },
            'individual_results': valid_results
        }
    
    def _print_results(self, summary: Dict):
        """Print formatted results"""
        if 'error' in summary:
            print(f"Error: {summary['error']}")
            return
        
        print(f"Total Trades: {summary['total_trades']}")
        print(f"Win Rate: {summary['overall_win_rate']:.1f}%")
        print(f"Avg Return: {summary['avg_return_per_stock']:.2f}%")
        print(f"Expectancy: {summary['overall_expectancy']:.3f}")
        
        # Quick summary table
        print(f"\n{'Symbol':<10} {'Trades':<8} {'Win%':<8} {'Return%':<10} {'Expectancy':<12}")
        print("-" * 50)
        
        for symbol, result in summary['individual_results'].items():
            print(f"{symbol:<10} {result['total_trades']:<8} "
                  f"{result['win_rate']:<8.1f} {result['total_return']:<10.2f} "
                  f"{result['expectancy']:<12.3f}")


def main():
    """Run the optimized multi-stock test"""
    
    test_stocks = [
        'RELIANCE',
        'INFY',
        'AXISBANK',
        'ITC',
        'TCS'
    ]
    
    optimizer = MultiStockOptimizerFixed(
        symbols=test_stocks,
        timeframe='5minute',
        lookback_days=180
    )
    
    # Run ALL strategies in single pass
    all_results = optimizer.test_all_strategies()
    
    # Find best strategy
    print(f"\n{'='*60}")
    print("STRATEGY COMPARISON SUMMARY")
    print(f"{'='*60}\n")
    
    comparison = []
    for strategy, summary in all_results.items():
        if 'error' not in summary:
            comparison.append({
                'strategy': strategy,
                'return': summary['avg_return_per_stock'],
                'win_rate': summary['overall_win_rate'],
                'expectancy': summary['overall_expectancy'],
                'trades': summary['total_trades']
            })
    
    # Sort by return
    comparison.sort(key=lambda x: x['return'], reverse=True)
    
    print(f"{'Strategy':<15} {'Return%':<10} {'Win%':<8} {'Expectancy':<12} {'Trades':<8}")
    print("-" * 60)
    
    for comp in comparison:
        print(f"{comp['strategy']:<15} {comp['return']:<10.2f} "
              f"{comp['win_rate']:<8.1f} {comp['expectancy']:<12.3f} "
              f"{comp['trades']:<8}")
    
    # Save results
    output = {
        'timestamp': datetime.now().isoformat(),
        'stocks': test_stocks,
        'results': all_results,
        'comparison': comparison
    }
    
    with open('optimized_results.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\n✅ Results saved to optimized_results.json")
    
    # Recommendation
    if comparison:
        best = comparison[0]
        print(f"\n🏆 RECOMMENDATION: Use {best['strategy'].upper()} strategy")
        print(f"   Expected Return: {best['return']:.2f}%")
        print(f"   Win Rate: {best['win_rate']:.1f}%")
        print(f"   Expectancy: {best['expectancy']:.3f}")


if __name__ == "__main__":
    main()