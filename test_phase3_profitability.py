"""
Test Phase 3 Flexible ML Profitability and Performance
======================================================

Comprehensive backtest comparing original vs flexible ML systems
on historical data to evaluate:
- Win rate
- Total returns
- Sharpe ratio
- Maximum drawdown
- Signal quality
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from data.smart_data_manager import SmartDataManager
from scanner.flexible_bar_processor import FlexibleBarProcessor
from config.settings import TradingConfig
from config.adaptive_config import create_adaptive_config


def calculate_trade_metrics(trades):
    """Calculate comprehensive trade metrics"""
    if not trades:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'total_return': 0,
            'avg_return': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'profit_factor': 0
        }
    
    returns = [t['return'] for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]
    
    # Calculate cumulative returns
    cumulative = 1.0
    cumulative_returns = []
    peak = 1.0
    max_drawdown = 0
    
    for r in returns:
        cumulative *= (1 + r)
        cumulative_returns.append(cumulative)
        peak = max(peak, cumulative)
        drawdown = (peak - cumulative) / peak
        max_drawdown = max(max_drawdown, drawdown)
    
    # Calculate metrics
    total_return = (cumulative - 1) * 100  # Percentage
    avg_return = np.mean(returns) * 100 if returns else 0
    
    # Sharpe ratio (annualized)
    if len(returns) > 1:
        return_std = np.std(returns)
        if return_std > 0:
            # Assuming 5-min bars, ~78 bars per day, ~252 trading days
            sharpe = (np.mean(returns) / return_std) * np.sqrt(78 * 252)
        else:
            sharpe = 0
    else:
        sharpe = 0
    
    # Profit factor
    if losses:
        profit_factor = abs(sum(wins) / sum(losses))
    else:
        profit_factor = float('inf') if wins else 0
    
    return {
        'total_trades': len(trades),
        'win_rate': len(wins) / len(trades) * 100 if trades else 0,
        'total_return': total_return,
        'avg_return': avg_return,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown * 100,
        'profit_factor': profit_factor,
        'winning_trades': len(wins),
        'losing_trades': len(losses)
    }


def simulate_trades(signals, df, commission=0.001):
    """Simulate trades from signals with realistic execution"""
    trades = []
    position = None
    
    for signal in signals:
        idx = signal['timestamp']
        
        if idx not in df.index:
            continue
            
        # Get current and future prices
        current_idx = df.index.get_loc(idx)
        if current_idx >= len(df) - 10:  # Need future data
            continue
        
        entry_price = df.iloc[current_idx]['close']
        
        if signal['signal'] > 0:  # Long signal
            # Exit any short position
            if position and position['type'] == 'short':
                exit_price = entry_price * (1 + commission)  # Slippage
                position['exit_price'] = exit_price
                position['exit_time'] = idx
                position['return'] = (position['entry_price'] - exit_price) / position['entry_price'] - commission
                trades.append(position)
                position = None
            
            # Enter long
            if not position:
                position = {
                    'type': 'long',
                    'entry_price': entry_price * (1 + commission),
                    'entry_time': idx,
                    'ml_prediction': signal['prediction'],
                    'ml_system': signal.get('ml_system', 'original')
                }
        
        elif signal['signal'] < 0:  # Short signal
            # Exit any long position
            if position and position['type'] == 'long':
                exit_price = entry_price * (1 - commission)
                position['exit_price'] = exit_price
                position['exit_time'] = idx
                position['return'] = (exit_price - position['entry_price']) / position['entry_price'] - commission
                trades.append(position)
                position = None
            
            # Enter short
            if not position:
                position = {
                    'type': 'short',
                    'entry_price': entry_price * (1 - commission),
                    'entry_time': idx,
                    'ml_prediction': signal['prediction'],
                    'ml_system': signal.get('ml_system', 'original')
                }
    
    # Close any open position at the end
    if position and len(df) > 0:
        exit_price = df.iloc[-1]['close']
        position['exit_price'] = exit_price
        position['exit_time'] = df.index[-1]
        
        if position['type'] == 'long':
            position['return'] = (exit_price - position['entry_price']) / position['entry_price'] - commission
        else:
            position['return'] = (position['entry_price'] - exit_price) / position['entry_price'] - commission
        
        trades.append(position)
    
    return trades


def test_ml_system_profitability(symbol: str, days: int = 30, use_flexible: bool = False):
    """Test ML system profitability on historical data"""
    
    print(f"\n{'='*60}")
    print(f"Testing {'FLEXIBLE' if use_flexible else 'ORIGINAL'} ML - {symbol}")
    print(f"{'='*60}")
    
    # Get historical data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=days)
    
    if df is None or len(df) < 500:
        print(f"⚠️  Insufficient data for {symbol}")
        return None
    
    print(f"Data loaded: {len(df)} bars ({days} days)")
    
    # Create adaptive config for symbol
    stats = data_manager.analyze_price_movement(df)
    adaptive_config = create_adaptive_config(symbol, '5minute', stats)
    
    # Use adaptive config with optimized settings
    config = TradingConfig(
        source=adaptive_config.source,
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        features=adaptive_config.features,
        # Keep filters active
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        regime_threshold=-0.1,
        adx_threshold=20
    )
    
    # Create processor
    processor = FlexibleBarProcessor(
        config,
        symbol=symbol,
        timeframe='5minute',
        use_flexible_ml=use_flexible,
        feature_config={
            'original_features': ['rsi', 'wt', 'cci', 'adx', 'features_4'],
            'phase3_features': ['fisher', 'vwm', 'order_flow'],
            'use_phase3': True
        }
    )
    
    # Process bars and collect signals
    signals = []
    ml_predictions = []
    
    print(f"\nProcessing {len(df)} bars...")
    
    warmup_period = min(500, len(df) // 3)  # Use 1/3 of data or 500 bars for warmup
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if i < warmup_period:  # Skip warmup period
            result = processor.process_bar(
                row['open'], row['high'], row['low'],
                row['close'], row['volume']
            )
            continue
        
        result = processor.process_bar(
            row['open'], row['high'], row['low'],
            row['close'], row['volume']
        )
        
        if result:
            # Track all predictions for analysis
            ml_predictions.append(result.prediction)
            
            # Only trade on actual entry signals
            if result.start_long_trade or result.start_short_trade:
                signal_type = 1 if result.start_long_trade else -1
                signals.append({
                    'timestamp': idx,
                    'signal': signal_type,
                    'prediction': result.prediction,
                    'ml_system': result.ml_system_used if hasattr(result, 'ml_system_used') else 'original',
                    'filters_passed': result.filter_all
                })
    
    print(f"\nSignals generated: {len(signals)}")
    
    if signals:
        # Simulate trades
        trades = simulate_trades(signals, df)
        
        # Calculate metrics
        metrics = calculate_trade_metrics(trades)
        
        # Additional ML-specific metrics
        if ml_predictions:
            avg_prediction = np.mean([abs(p) for p in ml_predictions])
            prediction_std = np.std(ml_predictions)
            metrics['avg_ml_confidence'] = avg_prediction
            metrics['prediction_volatility'] = prediction_std
        
        # Display results
        print(f"\n{'='*40}")
        print("PERFORMANCE METRICS")
        print(f"{'='*40}")
        print(f"Total Trades: {metrics['total_trades']}")
        print(f"Win Rate: {metrics['win_rate']:.1f}%")
        print(f"Total Return: {metrics['total_return']:.2f}%")
        print(f"Average Return: {metrics['avg_return']:.3f}%")
        print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"Max Drawdown: {metrics['max_drawdown']:.1f}%")
        print(f"Profit Factor: {metrics['profit_factor']:.2f}")
        
        if 'avg_ml_confidence' in metrics:
            print(f"\nML Metrics:")
            print(f"Avg Prediction Strength: {metrics['avg_ml_confidence']:.2f}")
            print(f"Prediction Volatility: {metrics['prediction_volatility']:.2f}")
        
        # Sample trades
        if trades:
            print(f"\n{'='*40}")
            print("SAMPLE TRADES")
            print(f"{'='*40}")
            for i, trade in enumerate(trades[:3]):
                print(f"\nTrade {i+1}:")
                print(f"  Type: {trade['type'].upper()}")
                print(f"  Entry: {trade['entry_price']:.2f} @ {trade['entry_time']}")
                print(f"  Exit: {trade['exit_price']:.2f} @ {trade['exit_time']}")
                print(f"  Return: {trade['return']*100:.2f}%")
                print(f"  ML Prediction: {trade['ml_prediction']:.2f}")
        
        return metrics
    else:
        print("❌ No trading signals generated")
        return None


def compare_ml_systems():
    """Compare original vs flexible ML across multiple symbols"""
    
    print("\n" + "="*80)
    print("PHASE 3 ML PROFITABILITY COMPARISON")
    print("="*80)
    
    symbols = ['RELIANCE', 'INFY', 'TCS', 'HDFC', 'ICICIBANK']
    days = 30  # Test on 30 days of data
    
    results = {
        'original': [],
        'flexible': []
    }
    
    for symbol in symbols:
        print(f"\n{'='*80}")
        print(f"Testing {symbol}")
        print(f"{'='*80}")
        
        # Test original ML
        original_metrics = test_ml_system_profitability(symbol, days, use_flexible=False)
        if original_metrics:
            original_metrics['symbol'] = symbol
            results['original'].append(original_metrics)
        
        # Test flexible ML
        flexible_metrics = test_ml_system_profitability(symbol, days, use_flexible=True)
        if flexible_metrics:
            flexible_metrics['symbol'] = symbol
            results['flexible'].append(flexible_metrics)
    
    # Summary comparison
    print("\n" + "="*80)
    print("SUMMARY COMPARISON")
    print("="*80)
    
    # Calculate averages
    for system_name, system_results in results.items():
        if system_results:
            print(f"\n{system_name.upper()} ML System:")
            print("-" * 40)
            
            avg_trades = np.mean([r['total_trades'] for r in system_results])
            avg_win_rate = np.mean([r['win_rate'] for r in system_results])
            avg_return = np.mean([r['total_return'] for r in system_results])
            avg_sharpe = np.mean([r['sharpe_ratio'] for r in system_results])
            avg_drawdown = np.mean([r['max_drawdown'] for r in system_results])
            
            print(f"Average Trades: {avg_trades:.1f}")
            print(f"Average Win Rate: {avg_win_rate:.1f}%")
            print(f"Average Return: {avg_return:.2f}%")
            print(f"Average Sharpe: {avg_sharpe:.2f}")
            print(f"Average Max DD: {avg_drawdown:.1f}%")
            
            # Best performer
            best_return = max(system_results, key=lambda x: x['total_return'])
            print(f"\nBest Performer: {best_return['symbol']} ({best_return['total_return']:.2f}% return)")
    
    # Direct comparison
    if results['original'] and results['flexible']:
        print("\n" + "="*80)
        print("FLEXIBLE vs ORIGINAL IMPROVEMENT")
        print("="*80)
        
        # Match symbols
        for orig in results['original']:
            flex = next((f for f in results['flexible'] if f['symbol'] == orig['symbol']), None)
            if flex:
                print(f"\n{orig['symbol']}:")
                print(f"  Win Rate: {orig['win_rate']:.1f}% → {flex['win_rate']:.1f}% "
                      f"({'↑' if flex['win_rate'] > orig['win_rate'] else '↓'} "
                      f"{flex['win_rate'] - orig['win_rate']:.1f}%)")
                print(f"  Return: {orig['total_return']:.2f}% → {flex['total_return']:.2f}% "
                      f"({'↑' if flex['total_return'] > orig['total_return'] else '↓'} "
                      f"{flex['total_return'] - orig['total_return']:.2f}%)")
                print(f"  Sharpe: {orig['sharpe_ratio']:.2f} → {flex['sharpe_ratio']:.2f}")
    
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    
    # Make recommendation based on results
    if results['flexible'] and results['original']:
        flex_avg_return = np.mean([r['total_return'] for r in results['flexible']])
        orig_avg_return = np.mean([r['total_return'] for r in results['original']])
        
        if flex_avg_return > orig_avg_return * 1.1:  # 10% improvement threshold
            print("✅ DEPLOY FLEXIBLE ML: Shows significant improvement")
        elif flex_avg_return < orig_avg_return * 0.9:  # 10% worse
            print("❌ KEEP ORIGINAL ML: Flexible system underperforms")
        else:
            print("🔄 GRADUAL ROLLOUT: Performance similar, test with small %")


def main():
    """Run comprehensive profitability test"""
    
    print("\n" + "="*80)
    print("PHASE 3 FLEXIBLE ML PROFITABILITY TEST")
    print("="*80)
    print("\nThis test will:")
    print("1. Run both ML systems on 30 days of historical data")
    print("2. Simulate realistic trading with commissions")
    print("3. Calculate win rate, returns, Sharpe ratio, drawdown")
    print("4. Compare performance across multiple symbols")
    print("5. Provide deployment recommendation")
    
    # Run comparison
    compare_ml_systems()
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()