"""
Test Time-of-Day Trading Filters
=================================

Test if avoiding first/last 30 minutes improves performance
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from data.smart_data_manager import SmartDataManager
from scanner.flexible_bar_processor import FlexibleBarProcessor
from config.settings import TradingConfig
from test_phase3_financial_analysis import DetailedBacktestEngine


def run_backtest_with_time_filter(symbol: str, days: int = 90, 
                                 skip_first_minutes: int = 0,
                                 skip_last_minutes: int = 0):
    """Run backtest with time-of-day filters"""
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=days)
    
    if df is None or len(df) < 2500:
        return None
    
    # Add time components for filtering
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    df['time_minutes'] = df['hour'] * 60 + df['minute']
    
    # Market hours: 9:15 AM to 3:30 PM (IST)
    market_open_minutes = 9 * 60 + 15  # 555
    market_close_minutes = 15 * 60 + 30  # 930
    
    # Calculate allowed trading window
    trade_start_minutes = market_open_minutes + skip_first_minutes
    trade_end_minutes = market_close_minutes - skip_last_minutes
    
    # Configuration
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
    
    # Initialize backtest
    backtest = DetailedBacktestEngine(initial_capital=100000, use_smart_exits=True)
    
    # Process bars
    signals = []
    signals_filtered_time = 0
    signals_filtered_ml = 0
    warmup_complete = False
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'],
            row['close'], row['volume']
        )
        
        if i == 2000:
            warmup_complete = True
        
        if warmup_complete and result:
            # Check for signals
            if result.start_long_trade or result.start_short_trade:
                prediction = result.flexible_prediction if hasattr(result, 'flexible_prediction') else result.prediction
                
                # ML threshold filter
                if abs(prediction) >= 3.0:
                    # Time filter
                    current_time_minutes = row['time_minutes']
                    
                    if trade_start_minutes <= current_time_minutes <= trade_end_minutes:
                        signal = {
                            'bar_index': i,
                            'signal': 1 if result.start_long_trade else -1,
                            'prediction': prediction,
                            'time': idx.time()
                        }
                        signals.append(signal)
                        backtest.execute_trade(signal, row, i)
                    else:
                        signals_filtered_time += 1
                else:
                    signals_filtered_ml += 1
            
            # Check for exits
            if backtest.open_position:
                # Smart exit checks
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
                    
                    # Time-based exit
                    if not should_exit and (i - pos['entry_bar']) >= 50:
                        should_exit = True
                        exit_price = row['close']
                    
                    if should_exit:
                        backtest.close_position(exit_price, idx, i)
    
    # Close any open position
    if backtest.open_position and len(df) > 0:
        last_row = df.iloc[-1]
        backtest.close_position(last_row['close'], df.index[-1], len(df)-1)
    
    # Calculate metrics
    metrics = backtest.calculate_metrics()
    metrics['signals_taken'] = len(signals)
    metrics['signals_filtered_time'] = signals_filtered_time
    metrics['signals_filtered_ml'] = signals_filtered_ml
    
    # Add time distribution analysis
    if signals:
        signal_times = [s['time'] for s in signals]
        signal_hours = [t.hour for t in signal_times]
        metrics['signals_by_hour'] = pd.Series(signal_hours).value_counts().to_dict()
    
    return metrics


def analyze_time_filters():
    """Test different time filter configurations"""
    
    print("\n" + "="*80)
    print("TIME-OF-DAY FILTER ANALYSIS")
    print("Testing impact of avoiding market open/close volatility")
    print("="*80)
    
    # Test configurations
    time_configs = [
        {'name': 'No Filter', 'skip_first': 0, 'skip_last': 0},
        {'name': 'Skip First 30min', 'skip_first': 30, 'skip_last': 0},
        {'name': 'Skip Last 30min', 'skip_first': 0, 'skip_last': 30},
        {'name': 'Skip Both 30min', 'skip_first': 30, 'skip_last': 30},
        {'name': 'Skip First 60min', 'skip_first': 60, 'skip_last': 0},
        {'name': 'Prime Hours Only', 'skip_first': 120, 'skip_last': 120}  # 11:15 AM - 1:30 PM
    ]
    
    symbols = ['RELIANCE', 'INFY', 'TCS']
    
    results = {}
    
    for config in time_configs:
        config_name = config['name']
        results[config_name] = {
            'total_pnl': 0,
            'total_trades': 0,
            'avg_win_rate': 0,
            'stocks': {}
        }
        
        print(f"\n\nTesting: {config_name}")
        print(f"Skip first {config['skip_first']} minutes, last {config['skip_last']} minutes")
        print("-" * 60)
        
        win_rates = []
        
        for symbol in symbols:
            metrics = run_backtest_with_time_filter(
                symbol=symbol,
                days=90,
                skip_first_minutes=config['skip_first'],
                skip_last_minutes=config['skip_last']
            )
            
            if metrics:
                results[config_name]['total_pnl'] += metrics['total_net_pnl']
                results[config_name]['total_trades'] += metrics['total_trades']
                win_rates.append(metrics['win_rate'])
                
                results[config_name]['stocks'][symbol] = {
                    'pnl': metrics['total_net_pnl'],
                    'trades': metrics['total_trades'],
                    'win_rate': metrics['win_rate'],
                    'filtered_time': metrics['signals_filtered_time']
                }
                
                print(f"{symbol}: P&L=₹{metrics['total_net_pnl']:,.2f}, "
                      f"Trades={metrics['total_trades']}, "
                      f"Win Rate={metrics['win_rate']:.1f}%, "
                      f"Time Filtered={metrics['signals_filtered_time']}")
        
        if win_rates:
            results[config_name]['avg_win_rate'] = np.mean(win_rates)
    
    # Summary comparison
    print("\n\n" + "="*80)
    print("TIME FILTER COMPARISON SUMMARY")
    print("="*80)
    
    print(f"\n{'Configuration':>20} {'Total P&L':>15} {'Avg Trades':>12} {'Avg Win Rate':>15} {'vs Baseline':>15}")
    print("-" * 80)
    
    baseline_pnl = results['No Filter']['total_pnl']
    
    sorted_results = sorted(results.items(), key=lambda x: x[1]['total_pnl'], reverse=True)
    
    for config_name, data in sorted_results:
        avg_trades = data['total_trades'] / len(symbols)
        vs_baseline = data['total_pnl'] - baseline_pnl
        
        print(f"{config_name:>20} ₹{data['total_pnl']:>13,.2f} "
              f"{avg_trades:>12.1f} {data['avg_win_rate']:>14.1f}% "
              f"₹{vs_baseline:>13,.2f}")
    
    # Best configuration
    best_config = sorted_results[0]
    print(f"\n✅ BEST TIME FILTER: {best_config[0]}")
    
    if best_config[0] != 'No Filter':
        print(f"   Improvement: ₹{best_config[1]['total_pnl'] - baseline_pnl:,.2f}")
        print("\n📊 RECOMMENDATION: Implement time-of-day filtering")
    else:
        print("\n❌ RECOMMENDATION: No time filtering needed")
    
    # Time distribution analysis
    print("\n\n📈 SIGNAL DISTRIBUTION BY HOUR")
    print("-" * 40)
    
    no_filter_results = results['No Filter']['stocks']
    all_hours = {}
    
    # Aggregate signals by hour across all stocks
    for symbol in symbols:
        if symbol in no_filter_results:
            stock_data = no_filter_results[symbol]
            # Note: We'd need to modify the function to return hour distribution
            # For now, just show the concept
    
    print("\nMarket Hours Signal Distribution:")
    print("9:15-10:15 AM: Opening volatility")
    print("10:15-12:00 PM: Morning session")
    print("12:00-2:00 PM: Lunch period")
    print("2:00-3:00 PM: Afternoon session")
    print("3:00-3:30 PM: Closing volatility")


if __name__ == "__main__":
    analyze_time_filters()