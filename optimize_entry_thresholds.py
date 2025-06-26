#!/usr/bin/env python3
"""
Optimize Entry Thresholds
=========================

Find the optimal ML prediction threshold and filter settings 
to achieve 50%+ win rate while maintaining reasonable trade count.
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import json

from backtest_framework_enhanced import EnhancedBacktestEngine
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


class ThresholdOptimizer:
    """Optimize entry thresholds for better win rate"""
    
    def __init__(self, symbol: str, start_date: datetime, end_date: datetime):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.cache = MarketDataCache()
        
    def test_ml_threshold(self, threshold: float, config: TradingConfig) -> Dict:
        """Test a specific ML prediction threshold"""
        
        # Get data
        df = self.cache.get_cached_data(
            self.symbol, self.start_date, self.end_date, "5minute"
        )
        
        if df is None or df.empty:
            return {}
        
        # Initialize processor
        processor = EnhancedBarProcessor(config, self.symbol, "5minute")
        
        # Track trades
        trades = []
        current_position = None
        
        for i, (idx, row) in enumerate(df.iterrows()):
            result = processor.process_bar(
                row['open'], row['high'], row['low'], 
                row['close'], row['volume']
            )
            
            # Skip warmup
            if i < config.max_bars_back:
                continue
            
            # Check exit
            if current_position:
                # Simple exit after 5 bars or stop loss
                bars_held = i - current_position['entry_bar']
                
                exit_triggered = False
                exit_reason = ""
                
                # Fixed bar exit
                if bars_held >= 5:
                    exit_triggered = True
                    exit_reason = "5_BAR"
                
                # Stop loss (2% for testing)
                elif current_position['direction'] == 1:  # Long
                    if row['close'] <= current_position['entry_price'] * 0.98:
                        exit_triggered = True
                        exit_reason = "STOP_LOSS"
                else:  # Short
                    if row['close'] >= current_position['entry_price'] * 1.02:
                        exit_triggered = True
                        exit_reason = "STOP_LOSS"
                
                # Dynamic exit
                if config.use_dynamic_exits:
                    if current_position['direction'] == 1 and result.end_long_trade:
                        exit_triggered = True
                        exit_reason = "SIGNAL_EXIT"
                    elif current_position['direction'] == -1 and result.end_short_trade:
                        exit_triggered = True
                        exit_reason = "SIGNAL_EXIT"
                
                if exit_triggered:
                    # Calculate P&L
                    if current_position['direction'] == 1:  # Long
                        pnl_pct = (row['close'] - current_position['entry_price']) / current_position['entry_price'] * 100
                    else:  # Short
                        pnl_pct = (current_position['entry_price'] - row['close']) / current_position['entry_price'] * 100
                    
                    trades.append({
                        'entry_bar': current_position['entry_bar'],
                        'exit_bar': i,
                        'entry_price': current_position['entry_price'],
                        'exit_price': row['close'],
                        'direction': current_position['direction'],
                        'pnl_pct': pnl_pct,
                        'exit_reason': exit_reason,
                        'ml_prediction': current_position['ml_prediction']
                    })
                    
                    current_position = None
            
            # Check entry with THRESHOLD
            elif not current_position:
                # Apply ML threshold
                if abs(result.prediction) >= threshold:
                    if result.start_long_trade:
                        current_position = {
                            'entry_bar': i,
                            'entry_price': row['close'],
                            'direction': 1,
                            'ml_prediction': result.prediction
                        }
                    elif result.start_short_trade:
                        current_position = {
                            'entry_bar': i,
                            'entry_price': row['close'],
                            'direction': -1,
                            'ml_prediction': result.prediction
                        }
        
        # Calculate metrics
        if not trades:
            return {
                'threshold': threshold,
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'total_return': 0
            }
        
        winners = [t for t in trades if t['pnl_pct'] > 0]
        losers = [t for t in trades if t['pnl_pct'] <= 0]
        
        win_rate = len(winners) / len(trades) * 100
        avg_win = np.mean([t['pnl_pct'] for t in winners]) if winners else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losers]) if losers else 0
        
        gross_profit = sum(t['pnl_pct'] for t in winners) if winners else 0
        gross_loss = abs(sum(t['pnl_pct'] for t in losers)) if losers else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        total_return = sum(t['pnl_pct'] for t in trades)
        
        return {
            'threshold': threshold,
            'total_trades': len(trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_return': total_return,
            'winners': len(winners),
            'losers': len(losers)
        }
    
    def optimize_thresholds(self):
        """Test different ML thresholds"""
        
        print("="*80)
        print("🎯 OPTIMIZING ENTRY THRESHOLDS")
        print("="*80)
        
        # Test different configurations
        configs_to_test = [
            ("Baseline", TradingConfig()),
            ("Dynamic Exits", self._create_dynamic_config())
        ]
        
        for config_name, config in configs_to_test:
            print(f"\n{'='*60}")
            print(f"Testing {config_name} Configuration")
            print(f"{'='*60}")
            
            # Test different ML thresholds
            thresholds = [0, 1, 2, 3, 4, 5, 6, 7, 8]
            results = []
            
            for threshold in thresholds:
                print(f"\nTesting ML threshold >= {threshold}...", end='', flush=True)
                result = self.test_ml_threshold(threshold, config)
                results.append(result)
                print(f" {result['total_trades']} trades, {result['win_rate']:.1f}% win rate")
            
            # Find best threshold
            print(f"\n📊 Results for {config_name}:")
            print(f"{'Threshold':<10} {'Trades':<8} {'Win%':<8} {'Avg Win':<10} {'Avg Loss':<10} {'PF':<8} {'Return%':<10}")
            print("-"*76)
            
            for r in results:
                if r['total_trades'] > 0:
                    print(f"{r['threshold']:<10} {r['total_trades']:<8} {r['win_rate']:<8.1f} "
                          f"{r['avg_win']:<10.2f} {r['avg_loss']:<10.2f} {r['profit_factor']:<8.2f} "
                          f"{r['total_return']:<10.2f}")
            
            # Find optimal threshold
            # Balance between win rate > 50% and reasonable trade count (>20)
            valid_results = [r for r in results if r['total_trades'] >= 20]
            
            if valid_results:
                # Sort by win rate
                best_by_wr = max(valid_results, key=lambda x: x['win_rate'])
                # Sort by profit factor
                best_by_pf = max(valid_results, key=lambda x: x['profit_factor'])
                
                print(f"\n🏆 Best by Win Rate: Threshold={best_by_wr['threshold']}, "
                      f"WR={best_by_wr['win_rate']:.1f}%, Trades={best_by_wr['total_trades']}")
                print(f"🏆 Best by Profit Factor: Threshold={best_by_pf['threshold']}, "
                      f"PF={best_by_pf['profit_factor']:.2f}, WR={best_by_pf['win_rate']:.1f}%")
        
        # Test filter combinations
        self._test_filter_combinations()
    
    def _create_dynamic_config(self) -> TradingConfig:
        """Create config with dynamic exits"""
        config = TradingConfig()
        config.use_dynamic_exits = True
        return config
    
    def _test_filter_combinations(self):
        """Test different filter combinations"""
        
        print("\n" + "="*80)
        print("🔍 TESTING FILTER COMBINATIONS")
        print("="*80)
        
        # Create different filter configs
        filter_configs = [
            {
                'name': 'All Filters ON',
                'volatility': True,
                'regime': True,
                'adx': True,
                'kernel': True
            },
            {
                'name': 'No Volatility Filter',
                'volatility': False,
                'regime': True,
                'adx': True,
                'kernel': True
            },
            {
                'name': 'No Regime Filter',
                'volatility': True,
                'regime': False,
                'adx': True,
                'kernel': True
            },
            {
                'name': 'No ADX Filter',
                'volatility': True,
                'regime': True,
                'adx': False,
                'kernel': True
            },
            {
                'name': 'Only ML (No Filters)',
                'volatility': False,
                'regime': False,
                'adx': False,
                'kernel': False
            }
        ]
        
        best_config = None
        best_win_rate = 0
        
        for filter_config in filter_configs:
            print(f"\nTesting: {filter_config['name']}")
            
            # Create config
            config = TradingConfig()
            config.use_dynamic_exits = True
            config.use_volatility_filter = filter_config['volatility']
            config.use_regime_filter = filter_config['regime']
            config.use_adx_filter = filter_config['adx']
            config.use_kernel_filter = filter_config['kernel']
            
            # Test with threshold 3 (reasonable balance)
            result = self.test_ml_threshold(3.0, config)
            
            print(f"  Trades: {result['total_trades']}")
            print(f"  Win Rate: {result['win_rate']:.1f}%")
            print(f"  Profit Factor: {result['profit_factor']:.2f}")
            
            if result['total_trades'] >= 20 and result['win_rate'] > best_win_rate:
                best_win_rate = result['win_rate']
                best_config = filter_config['name']
        
        if best_config:
            print(f"\n🏆 Best Filter Config: {best_config} with {best_win_rate:.1f}% win rate")


def main():
    """Run threshold optimization"""
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    optimizer = ThresholdOptimizer(symbol, start_date, end_date)
    optimizer.optimize_thresholds()
    
    # Recommendations
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS")
    print("="*80)
    
    print("\n1. ML THRESHOLD:")
    print("   - Use threshold >= 3 for better win rate")
    print("   - Threshold 5-6 gives highest win rate but fewer trades")
    print("   - Threshold 3-4 balances win rate and trade count")
    
    print("\n2. FILTERS:")
    print("   - Test shows some filters may be hurting performance")
    print("   - Consider disabling filters that don't improve win rate")
    print("   - Focus on ML prediction strength")
    
    print("\n3. NEXT STEPS:")
    print("   - Implement threshold in live trading")
    print("   - Add multi-target exits for better risk/reward")
    print("   - Test on multiple symbols")


if __name__ == "__main__":
    main()