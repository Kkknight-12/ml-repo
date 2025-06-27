"""
Modular Multi-Stock Optimization
================================

Refactored version with clean separation of concerns.
Each component handles one specific task.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Import modular components
from data.smart_data_manager import SmartDataManager
from strategies.strategy_factory import StrategyFactory
from execution.trade_executor import TradeExecutor
from analysis.results_analyzer import ResultsAnalyzer, TradingMetrics
from config.adaptive_config import create_adaptive_config
from config.settings import TradingConfig


class ModularStockOptimizer:
    """Main orchestrator using modular components"""
    
    def __init__(self, symbols: List[str], timeframe: str = "5minute",
                 lookback_days: int = 90, ml_threshold: float = 3.0):
        self.symbols = symbols
        self.timeframe = timeframe
        self.lookback_days = lookback_days
        self.ml_threshold = ml_threshold
        
        # Initialize data manager
        self.data_manager = SmartDataManager()
        self._check_session()
        
        # Get all strategies
        self.strategies = StrategyFactory.get_all_strategies()
        
        # Results storage
        self.results_by_strategy = {name: {} for name in self.strategies}
        self.trades_by_strategy = {name: {} for name in self.strategies}
        
    def _check_session(self):
        """Check for saved trading session"""
        if os.path.exists('.kite_session.json'):
            with open('.kite_session.json', 'r') as f:
                session_data = json.load(f)
                access_token = session_data.get('access_token')
                if access_token:
                    os.environ['KITE_ACCESS_TOKEN'] = access_token
    
    def run_optimization(self) -> Dict:
        """Run the complete optimization"""
        print(f"\n{'='*60}")
        print(f"MODULAR OPTIMIZATION FRAMEWORK")
        print(f"Stocks: {len(self.symbols)}, Strategies: {len(self.strategies)}")
        print(f"{'='*60}\n")
        
        # Process each stock
        for symbol in self.symbols:
            print(f"\nProcessing {symbol}...")
            self._process_symbol(symbol)
        
        # Generate comprehensive results
        return self._generate_results()
    
    def _process_symbol(self, symbol: str):
        """Process a single symbol with all strategies"""
        # Get data
        df = self._get_symbol_data(symbol)
        if df is None:
            return
        
        # Create trading config
        stats = self.data_manager.analyze_price_movement(df)
        adaptive_config = create_adaptive_config(symbol, self.timeframe, stats)
        trading_config = self._create_trading_config(adaptive_config)
        
        # Create executor
        executor = TradeExecutor(symbol, self.timeframe, self.ml_threshold)
        executor.initialize_processor(trading_config)
        
        # Process with all strategies
        trades = executor.process_data(df, self.strategies)
        
        # Analyze results for each strategy
        for strategy_name, strategy_trades in trades.items():
            if strategy_trades:
                metrics = ResultsAnalyzer.calculate_metrics(
                    strategy_trades, 
                    f"{symbol}-{strategy_name}"
                )
                
                self.results_by_strategy[strategy_name][symbol] = metrics
                self.trades_by_strategy[strategy_name][symbol] = strategy_trades
                
                # Print exit analysis for first stock
                if symbol == self.symbols[0]:
                    ResultsAnalyzer.print_exit_analysis(
                        strategy_trades, symbol, strategy_name
                    )
            else:
                self.results_by_strategy[strategy_name][symbol] = None
    
    def _get_symbol_data(self, symbol: str) -> pd.DataFrame:
        """Get data for symbol with sufficient history"""
        min_required_bars = 2500
        
        df = self.data_manager.get_data(
            symbol=symbol,
            interval=self.timeframe,
            days=self.lookback_days
        )
        
        if df is None or len(df) < min_required_bars:
            print(f"  ⚠️  Insufficient data for {symbol}")
            # Try to fetch more
            for days in [180, 250, 365]:
                df = self.data_manager.get_data(
                    symbol=symbol,
                    interval=self.timeframe,
                    days=days
                )
                if df is not None and len(df) >= min_required_bars:
                    break
            else:
                return None
        
        print(f"  ✅ Got {len(df)} bars for {symbol}")
        return df
    
    def _create_trading_config(self, adaptive_config) -> TradingConfig:
        """Create TradingConfig from adaptive config"""
        return TradingConfig(
            source=adaptive_config.source,
            neighbors_count=adaptive_config.neighbors_count,
            max_bars_back=adaptive_config.max_bars_back,
            feature_count=adaptive_config.feature_count,
            color_compression=adaptive_config.color_compression,
            use_volatility_filter=adaptive_config.use_volatility_filter,
            use_regime_filter=adaptive_config.use_regime_filter,
            use_adx_filter=adaptive_config.use_adx_filter,
            use_kernel_filter=adaptive_config.use_kernel_filter,
            use_ema_filter=adaptive_config.use_ema_filter,
            use_sma_filter=adaptive_config.use_sma_filter,
            regime_threshold=adaptive_config.regime_threshold,
            adx_threshold=adaptive_config.adx_threshold,
            kernel_lookback=adaptive_config.kernel_lookback,
            kernel_relative_weight=adaptive_config.kernel_relative_weight,
            kernel_regression_level=adaptive_config.kernel_regression_level,
            kernel_lag=adaptive_config.kernel_lag,
            use_kernel_smoothing=adaptive_config.use_kernel_smoothing,
            features=adaptive_config.features
        )
    
    def _generate_results(self) -> Dict:
        """Generate comprehensive results"""
        all_results = {}
        
        for strategy_name in self.strategies:
            summary = self._summarize_strategy(strategy_name)
            all_results[strategy_name] = summary
            
            print(f"\n{'='*50}")
            print(f"RESULTS FOR {strategy_name.upper()} STRATEGY")
            print(f"{'='*50}")
            self._print_summary(summary)
        
        # Compare strategies
        comparison = self._compare_strategies(all_results)
        
        # Save results
        self._save_results(all_results, comparison)
        
        # Print recommendation
        self._print_recommendation(comparison)
        
        return all_results
    
    def _summarize_strategy(self, strategy_name: str) -> Dict:
        """Summarize results for a strategy"""
        results = self.results_by_strategy[strategy_name]
        valid_results = {k: v for k, v in results.items() if v is not None}
        
        if not valid_results:
            return {'error': 'No valid results', 'strategy': strategy_name}
        
        # Aggregate metrics
        total_trades = sum(m.total_trades for m in valid_results.values())
        total_wins = sum(m.winning_trades for m in valid_results.values())
        
        overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        avg_return = np.mean([m.total_return for m in valid_results.values()])
        
        # Weighted expectancy
        total_expectancy = sum(
            m.expectancy * m.total_trades 
            for m in valid_results.values()
        )
        overall_expectancy = total_expectancy / total_trades if total_trades > 0 else 0
        
        # Best and worst performers
        returns_by_stock = {k: v.total_return for k, v in valid_results.items()}
        best_stock = max(returns_by_stock, key=returns_by_stock.get)
        worst_stock = min(returns_by_stock, key=returns_by_stock.get)
        
        return {
            'strategy': strategy_name,
            'stocks_tested': len(valid_results),
            'total_trades': total_trades,
            'overall_win_rate': overall_win_rate,
            'avg_return_per_stock': avg_return,
            'overall_expectancy': overall_expectancy,
            'best_performer': {
                'symbol': best_stock,
                'return': returns_by_stock[best_stock],
                'trades': valid_results[best_stock].total_trades
            },
            'worst_performer': {
                'symbol': worst_stock,
                'return': returns_by_stock[worst_stock],
                'trades': valid_results[worst_stock].total_trades
            },
            'individual_results': {
                symbol: self._metrics_to_dict(metrics)
                for symbol, metrics in valid_results.items()
            }
        }
    
    def _metrics_to_dict(self, metrics: TradingMetrics) -> Dict:
        """Convert TradingMetrics to dictionary"""
        strategy = next(
            s for s in self.strategies.values() 
            if metrics in self.results_by_strategy[s.name].values()
        )
        
        return {
            'total_trades': metrics.total_trades,
            'winning_trades': metrics.winning_trades,
            'losing_trades': metrics.losing_trades,
            'win_rate': metrics.win_rate,
            'total_return': metrics.total_return,
            'avg_win': metrics.avg_win,
            'avg_loss': metrics.avg_loss,
            'expectancy': metrics.expectancy,
            'profit_factor': metrics.profit_factor,
            'max_drawdown': metrics.max_drawdown,
            'car_maxdd': metrics.car_maxdd,
            'annualized_return': metrics.annualized_return,
            'config': strategy.get_description()
        }
    
    def _print_summary(self, summary: Dict):
        """Print formatted summary"""
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
    
    def _compare_strategies(self, all_results: Dict) -> List[Dict]:
        """Compare all strategies"""
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
        
        print(f"\n{'='*60}")
        print("STRATEGY COMPARISON")
        print(f"{'='*60}\n")
        
        print(f"{'Strategy':<15} {'Return%':<10} {'Win%':<8} {'Expectancy':<12} {'Trades':<8}")
        print("-" * 60)
        
        for comp in comparison:
            print(f"{comp['strategy']:<15} {comp['return']:<10.2f} "
                  f"{comp['win_rate']:<8.1f} {comp['expectancy']:<12.3f} "
                  f"{comp['trades']:<8}")
        
        return comparison
    
    def _save_results(self, all_results: Dict, comparison: List[Dict]):
        """Save results to file"""
        output = {
            'timestamp': datetime.now().isoformat(),
            'stocks': self.symbols,
            'results': all_results,
            'comparison': comparison
        }
        
        with open('modular_results.json', 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"\n✅ Results saved to modular_results.json")
    
    def _print_recommendation(self, comparison: List[Dict]):
        """Print strategy recommendation"""
        if comparison:
            best = comparison[0]
            print(f"\n🏆 RECOMMENDATION: Use {best['strategy'].upper()} strategy")
            print(f"   Expected Return: {best['return']:.2f}%")
            print(f"   Win Rate: {best['win_rate']:.1f}%")
            print(f"   Expectancy: {best['expectancy']:.3f}")


def main():
    """Run the modular optimization"""
    test_stocks = [
        'RELIANCE',
        'INFY',
        'AXISBANK',
        'ITC',
        'TCS'
    ]
    
    optimizer = ModularStockOptimizer(
        symbols=test_stocks,
        timeframe='5minute',
        lookback_days=180,
        ml_threshold=3.0
    )
    
    results = optimizer.run_optimization()


if __name__ == "__main__":
    main()