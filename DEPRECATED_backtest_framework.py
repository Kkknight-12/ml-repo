#!/usr/bin/env python3
"""
Comprehensive Backtesting Framework
===================================

A robust backtesting system to measure and compare different configurations
of the Lorentzian Classification trading system.

Philosophy: Measure everything. Only keep what improves profitability.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import json
from dataclasses import dataclass, asdict
import matplotlib.pyplot as plt
import seaborn as sns

# Core imports
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
from config.fixed_optimized_settings import FixedOptimizedTradingConfig
from config.modular_strategies import ModularTradingSystem, StrategyModule
from data.zerodha_client import ZerodhaClient
from data.cache_manager import MarketDataCache

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TradeResult:
    """Single trade result"""
    symbol: str
    entry_date: datetime
    exit_date: datetime
    entry_price: float
    exit_price: float
    direction: int  # 1 for long, -1 for short
    pnl_percent: float
    pnl_amount: float
    hold_time_bars: int
    exit_reason: str
    pattern_score: float = 0.0
    
    @property
    def is_winner(self) -> bool:
        return self.pnl_percent > 0


@dataclass
class BacktestMetrics:
    """Complete backtest performance metrics"""
    # Basic metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # Profitability
    total_return: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    profit_factor: float
    
    # Risk metrics
    max_drawdown: float
    max_drawdown_duration: int
    sharpe_ratio: float
    sortino_ratio: float
    
    # Trade statistics
    avg_hold_time: float
    trades_per_1000_bars: float
    avg_bars_between_trades: float
    
    # Monthly breakdown
    monthly_returns: Dict[str, float]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def print_summary(self):
        """Print formatted summary"""
        print("\n" + "="*60)
        print("📊 BACKTEST RESULTS")
        print("="*60)
        
        print(f"\n📈 Trade Statistics:")
        print(f"   Total Trades: {self.total_trades}")
        print(f"   Win Rate: {self.win_rate:.1f}%")
        print(f"   Profit Factor: {self.profit_factor:.2f}")
        
        print(f"\n💰 Profitability:")
        print(f"   Total Return: {self.total_return:+.2f}%")
        print(f"   Average Win: {self.average_win:+.2f}%")
        print(f"   Average Loss: {self.average_loss:+.2f}%")
        print(f"   Largest Win: {self.largest_win:+.2f}%")
        print(f"   Largest Loss: {self.largest_loss:+.2f}%")
        
        print(f"\n📉 Risk Metrics:")
        print(f"   Max Drawdown: {self.max_drawdown:.2f}%")
        print(f"   Sharpe Ratio: {self.sharpe_ratio:.2f}")
        print(f"   Sortino Ratio: {self.sortino_ratio:.2f}")
        
        print(f"\n⏱️ Timing:")
        print(f"   Avg Hold Time: {self.avg_hold_time:.1f} bars")
        print(f"   Trades per 1000 bars: {self.trades_per_1000_bars:.1f}")


class BacktestEngine:
    """Main backtesting engine"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.cache_manager = MarketDataCache()
        self.trades: List[TradeResult] = []
        
    def run_backtest(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        config: TradingConfig,
        modular_system: Optional[ModularTradingSystem] = None,
        commission: float = 0.001  # 0.1% per trade
    ) -> BacktestMetrics:
        """Run a complete backtest
        
        NOTE: This engine does NOT implement multi-target exits.
        For multi-target functionality, use BacktestEngineEnhanced.
        """
        
        logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")
        
        # Get historical data
        df = self._get_historical_data(symbol, start_date, end_date)
        if df.empty:
            raise ValueError("No data available for backtesting")
        
        # Initialize processor
        processor = EnhancedBarProcessor(config, symbol, "5minute")
        
        # Initialize tracking
        self.trades = []
        equity_curve = [self.initial_capital]
        current_position = None
        bars_processed = 0
        
        # Process each bar
        logger.info(f"Total bars in dataset: {len(df)}")
        logger.info(f"Warmup period: {config.max_bars_back} bars")
        logger.info(f"Bars available for trading: {max(0, len(df) - config.max_bars_back)}")
        
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
            
            # Apply modular strategies if provided
            signal_score = result.prediction
            pattern_score = 5.0  # Default
            
            if modular_system:
                # Apply enabled modules
                signal_score, pattern_score = self._apply_modular_strategies(
                    result, row, modular_system
                )
            
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
                    
                    # Update equity
                    pnl = self.initial_capital * (trade.pnl_percent / 100)
                    equity_curve.append(equity_curve[-1] + pnl - commission * 2)
                    current_position = None
                else:
                    equity_curve.append(equity_curve[-1])
            
            # Check for entry
            elif not current_position:
                # Use proper entry signals that respect filters
                if result.start_long_trade:
                    current_position = {
                        'symbol': symbol,
                        'entry_bar': bars_processed,
                        'entry_date': idx,
                        'entry_price': row['close'],
                        'direction': 1,
                        'pattern_score': pattern_score,
                        'stop_loss': self._calculate_stop_loss(row, config),
                        'targets': self._calculate_targets(row, config)
                    }
                    equity_curve.append(equity_curve[-1])
                elif result.start_short_trade:
                    current_position = {
                        'symbol': symbol,
                        'entry_bar': bars_processed,
                        'entry_date': idx,
                        'entry_price': row['close'],
                        'direction': -1,
                        'pattern_score': pattern_score,
                        'stop_loss': self._calculate_stop_loss(row, config),
                        'targets': self._calculate_targets(row, config)
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
        
        return metrics
    
    def compare_configurations(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        configurations: Dict[str, Dict]
    ) -> pd.DataFrame:
        """Compare multiple configurations"""
        
        results = {}
        
        for name, config_dict in configurations.items():
            logger.info(f"Testing configuration: {name}")
            
            # Create config
            if config_dict.get('type') == 'optimized':
                config = FixedOptimizedTradingConfig()
            else:
                config = TradingConfig()
            
            # Apply any parameter overrides
            for key, value in config_dict.get('params', {}).items():
                setattr(config, key, value)
            
            # Get modular system if specified
            modular_system = None
            if 'preset' in config_dict:
                modular_system = ModularTradingSystem().create_preset(
                    config_dict['preset']
                )
            
            # Run backtest
            try:
                metrics = self.run_backtest(
                    symbol, start_date, end_date, 
                    config, modular_system
                )
                results[name] = metrics
            except Exception as e:
                logger.error(f"Failed to test {name}: {e}")
                continue
        
        # Create comparison dataframe
        comparison_data = []
        for name, metrics in results.items():
            comparison_data.append({
                'Configuration': name,
                'Total Trades': metrics.total_trades,
                'Win Rate %': metrics.win_rate,
                'Total Return %': metrics.total_return,
                'Avg Win %': metrics.average_win,
                'Avg Loss %': metrics.average_loss,
                'Profit Factor': metrics.profit_factor,
                'Max Drawdown %': metrics.max_drawdown,
                'Sharpe Ratio': metrics.sharpe_ratio,
                'Trades/1000 bars': metrics.trades_per_1000_bars
            })
        
        df = pd.DataFrame(comparison_data)
        return df
    
    def _get_historical_data(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """Get historical data with caching"""
        
        # Check cache first
        cached_data = self.cache_manager.get_cached_data(
            symbol, start_date, end_date, "5minute"
        )
        
        if cached_data is not None and not cached_data.empty:
            logger.info("Using cached data")
            # Ensure date is index
            if 'date' in cached_data.columns:
                cached_data.set_index('date', inplace=True)
            return cached_data
        
        # Fetch from API
        try:
            # Ensure access token is set
            if os.path.exists('.kite_session.json'):
                with open('.kite_session.json', 'r') as f:
                    session_data = json.load(f)
                    access_token = session_data.get('access_token')
                    os.environ['KITE_ACCESS_TOKEN'] = access_token
            
            client = ZerodhaClient()
            days = (end_date - start_date).days
            data = client.get_historical_data(symbol, "5minute", days)
            
            if data:
                # Convert list of dicts to DataFrame
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                
                # Cache for future use
                df_for_cache = df.reset_index()
                self.cache_manager.save_data(symbol, df_for_cache, "5minute")
                
                return df
            else:
                logger.warning(f"No data received for {symbol}")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to get historical data: {e}")
            return pd.DataFrame()
    
    def _apply_modular_strategies(
        self,
        ml_result,
        bar: pd.Series,
        modular_system: ModularTradingSystem
    ) -> Tuple[float, float]:
        """Apply enabled modules to adjust signal"""
        
        signal_score = ml_result.prediction
        pattern_score = 5.0
        
        # Example: Apply time window module
        if modular_system.modules[StrategyModule.AI_TIME_WINDOWS].enabled:
            current_hour = bar.name.hour + bar.name.minute / 60
            config = modular_system.modules[StrategyModule.AI_TIME_WINDOWS].parameters
            
            if not (config['no_trade_before'] <= current_hour <= config['no_trade_after']):
                signal_score = 0  # No trades outside window
            elif config['prime_start'] <= current_hour <= config['prime_end']:
                signal_score *= 1.5  # Boost in prime window
        
        # Add more module applications as needed
        
        return signal_score, pattern_score
    
    def _check_exit(
        self,
        position: Dict,
        bar: pd.Series,
        ml_result,
        config: TradingConfig
    ) -> Optional[str]:
        """Check exit conditions"""
        
        bars_held = bar.name - position['entry_date']
        bars_held = bars_held.total_seconds() / 300  # Convert to 5-min bars
        
        # Fixed bar exit (default behavior)
        if not config.use_dynamic_exits and bars_held >= 5:
            return "FIXED_5_BAR"
        
        # Stop loss
        if position['direction'] == 1:  # Long
            if bar['close'] <= position['stop_loss']:
                return "STOP_LOSS"
        else:  # Short
            if bar['close'] >= position['stop_loss']:
                return "STOP_LOSS"
        
        # Dynamic exit on signal reversal
        if config.use_dynamic_exits:
            if position['direction'] == 1 and ml_result.end_long_trade:
                return "SIGNAL_EXIT"
            elif position['direction'] == -1 and ml_result.end_short_trade:
                return "SIGNAL_EXIT"
        
        return None
    
    def _close_position(
        self,
        position: Dict,
        bar: pd.Series,
        exit_reason: str,
        current_bar: int
    ) -> TradeResult:
        """Close position and create trade result"""
        
        exit_price = bar['close']
        
        if position['direction'] == 1:  # Long
            pnl_percent = (exit_price - position['entry_price']) / position['entry_price'] * 100
        else:  # Short
            pnl_percent = (position['entry_price'] - exit_price) / position['entry_price'] * 100
        
        pnl_amount = self.initial_capital * (pnl_percent / 100)
        hold_time = current_bar - position['entry_bar']
        
        return TradeResult(
            symbol=position.get('symbol', 'UNKNOWN'),
            entry_date=position['entry_date'],
            exit_date=bar.name,
            entry_price=position['entry_price'],
            exit_price=exit_price,
            direction=position['direction'],
            pnl_percent=pnl_percent,
            pnl_amount=pnl_amount,
            hold_time_bars=hold_time,
            exit_reason=exit_reason,
            pattern_score=position.get('pattern_score', 0)
        )
    
    def _calculate_stop_loss(self, bar: pd.Series, config) -> float:
        """Calculate stop loss price"""
        # Simplified - in reality would use ATR
        if hasattr(config, 'stop_loss_atr_multiplier'):
            atr = bar['close'] * 0.02  # 2% as placeholder
            return bar['close'] - atr * config.stop_loss_atr_multiplier
        else:
            return bar['close'] * 0.98  # 2% stop
    
    def _calculate_targets(self, bar: pd.Series, config) -> List[float]:
        """Calculate profit targets"""
        targets = []
        
        if hasattr(config, 'target_1_ratio'):
            risk = bar['close'] * 0.02  # Placeholder
            targets.append(bar['close'] + risk * config.target_1_ratio)
            
            if hasattr(config, 'target_2_ratio'):
                targets.append(bar['close'] + risk * config.target_2_ratio)
        
        return targets
    
    def _calculate_metrics(
        self,
        trades: List[TradeResult],
        equity_curve: List[float],
        total_bars: int
    ) -> BacktestMetrics:
        """Calculate comprehensive metrics"""
        
        if not trades:
            return BacktestMetrics(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0, total_return=0, average_win=0, average_loss=0,
                largest_win=0, largest_loss=0, profit_factor=0,
                max_drawdown=0, max_drawdown_duration=0,
                sharpe_ratio=0, sortino_ratio=0,
                avg_hold_time=0, trades_per_1000_bars=0,
                avg_bars_between_trades=0, monthly_returns={}
            )
        
        # Basic statistics
        winning_trades = [t for t in trades if t.is_winner]
        losing_trades = [t for t in trades if not t.is_winner]
        
        # Returns
        returns = [t.pnl_percent for t in trades]
        total_return = (equity_curve[-1] - self.initial_capital) / self.initial_capital * 100
        
        # Risk metrics
        equity_series = pd.Series(equity_curve)
        drawdowns = (equity_series - equity_series.cummax()) / equity_series.cummax() * 100
        max_drawdown = abs(drawdowns.min())
        
        # Calculate Sharpe ratio (simplified)
        if len(returns) > 1:
            returns_series = pd.Series(returns)
            sharpe = returns_series.mean() / returns_series.std() * np.sqrt(252)
        else:
            sharpe = 0
        
        # Sortino ratio (downside deviation)
        negative_returns = [r for r in returns if r < 0]
        if negative_returns:
            downside_std = np.std(negative_returns)
            sortino = np.mean(returns) / downside_std * np.sqrt(252) if downside_std > 0 else 0
        else:
            sortino = sharpe
        
        # Trade timing
        avg_hold = np.mean([t.hold_time_bars for t in trades])
        trades_per_1000 = len(trades) / total_bars * 1000
        
        # Monthly returns (simplified)
        monthly_returns = {}
        for trade in trades:
            month_key = trade.exit_date.strftime("%Y-%m")
            monthly_returns[month_key] = monthly_returns.get(month_key, 0) + trade.pnl_percent
        
        # Profit factor
        gross_profit = sum(t.pnl_percent for t in winning_trades)
        gross_loss = abs(sum(t.pnl_percent for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        return BacktestMetrics(
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=len(winning_trades) / len(trades) * 100,
            total_return=total_return,
            average_win=np.mean([t.pnl_percent for t in winning_trades]) if winning_trades else 0,
            average_loss=np.mean([t.pnl_percent for t in losing_trades]) if losing_trades else 0,
            largest_win=max([t.pnl_percent for t in trades]),
            largest_loss=min([t.pnl_percent for t in trades]),
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_duration=0,  # TODO: Calculate properly
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            avg_hold_time=avg_hold,
            trades_per_1000_bars=trades_per_1000,
            avg_bars_between_trades=total_bars / len(trades) if trades else 0,
            monthly_returns=monthly_returns
        )
    
    def plot_results(self, metrics: BacktestMetrics, save_path: Optional[str] = None):
        """Create visualization of results"""
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. Monthly returns
        ax = axes[0, 0]
        if metrics.monthly_returns:
            months = list(metrics.monthly_returns.keys())
            returns = list(metrics.monthly_returns.values())
            ax.bar(months, returns, color=['green' if r > 0 else 'red' for r in returns])
            ax.set_title('Monthly Returns %')
            ax.set_xticklabels(months, rotation=45)
        
        # 2. Win/Loss distribution
        ax = axes[0, 1]
        win_loss_data = [metrics.average_win, abs(metrics.average_loss)]
        ax.bar(['Avg Win', 'Avg Loss'], win_loss_data, color=['green', 'red'])
        ax.set_title('Average Win vs Loss %')
        
        # 3. Trade distribution
        ax = axes[1, 0]
        trade_data = [metrics.winning_trades, metrics.losing_trades]
        ax.pie(trade_data, labels=['Winners', 'Losers'], 
               colors=['green', 'red'], autopct='%1.1f%%')
        ax.set_title('Win Rate Distribution')
        
        # 4. Key metrics text
        ax = axes[1, 1]
        ax.axis('off')
        metrics_text = f"""
        Total Return: {metrics.total_return:+.2f}%
        Win Rate: {metrics.win_rate:.1f}%
        Profit Factor: {metrics.profit_factor:.2f}
        Max Drawdown: {metrics.max_drawdown:.2f}%
        Sharpe Ratio: {metrics.sharpe_ratio:.2f}
        Avg Hold Time: {metrics.avg_hold_time:.1f} bars
        """
        ax.text(0.1, 0.5, metrics_text, fontsize=12, 
                verticalalignment='center', fontfamily='monospace')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()


def main():
    """Demo backtesting framework"""
    
    print("="*60)
    print("🧪 BACKTESTING FRAMEWORK DEMO")
    print("="*60)
    
    # Initialize engine
    engine = BacktestEngine()
    
    # Define test configurations
    configurations = {
        'baseline': {
            'type': 'standard',
            'params': {},
            'description': 'Default Pine Script parameters'
        },
        'optimized': {
            'type': 'optimized',
            'params': {},
            'description': 'Optimized parameters with multi-targets'
        },
        'ai_enhanced': {
            'type': 'standard',
            'preset': 'ai_enhanced',
            'description': 'With AI trading rules'
        },
        'conservative': {
            'type': 'optimized',
            'params': {
                'neighbors_count': 10,
                'min_prediction_strength': 4.0
            },
            'description': 'Conservative settings'
        }
    }
    
    # Test parameters
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    print(f"\nTesting configurations on {symbol}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    
    # Compare configurations
    comparison_df = engine.compare_configurations(
        symbol, start_date, end_date, configurations
    )
    
    print("\n📊 Configuration Comparison:")
    print(comparison_df.to_string(index=False))
    
    # Find best configuration
    if not comparison_df.empty:
        best_config = comparison_df.loc[comparison_df['Total Return %'].idxmax()]
        print(f"\n🏆 Best Configuration: {best_config['Configuration']}")
        print(f"   Total Return: {best_config['Total Return %']:+.2f}%")
        print(f"   Win Rate: {best_config['Win Rate %']:.1f}%")
        print(f"   Profit Factor: {best_config['Profit Factor']:.2f}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_df.to_csv(f'backtest_results_{timestamp}.csv', index=False)
    print(f"\n💾 Results saved to backtest_results_{timestamp}.csv")


if __name__ == "__main__":
    main()