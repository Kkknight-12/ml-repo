"""
Phase 3 Simple Profitability Test
=================================

Quick test to verify flexible ML is working and compare profitability.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from data.smart_data_manager import SmartDataManager
from scanner.flexible_bar_processor import FlexibleBarProcessor
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig


def quick_backtest(symbol='RELIANCE', days=60):
    """Quick backtest comparison"""
    
    print(f"\n{'='*80}")
    print(f"QUICK PROFITABILITY TEST - {symbol}")
    print(f"{'='*80}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=days)
    
    if df is None or len(df) < 1000:
        print(f"Insufficient data: {len(df) if df is not None else 0} bars")
        return
    
    print(f"\nData loaded: {len(df)} bars")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    
    # Use relaxed config to get more signals
    config = TradingConfig(
        source='close',
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,
        # Relaxed filters
        use_volatility_filter=False,
        use_regime_filter=True,
        use_adx_filter=False,
        regime_threshold=-0.1
    )
    
    # Test both systems
    for use_flexible in [False, True]:
        print(f"\n{'='*60}")
        print(f"{'FLEXIBLE' if use_flexible else 'ORIGINAL'} ML SYSTEM")
        print(f"{'='*60}")
        
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
        
        # Process bars
        signals = []
        predictions = []
        warmup_bars = 2000  # ML requires 2000 bars warmup
        
        print(f"\nProcessing {len(df)} bars (warmup: {warmup_bars})...")
        
        # Check if we have enough data for ML warmup
        if len(df) < warmup_bars + 100:
            print(f"WARNING: Only {len(df)} bars available, need {warmup_bars + 100} for proper testing")
            print("Flexible ML will not generate predictions without sufficient warmup data!")
        
        for i, (idx, row) in enumerate(df.iterrows()):
            result = processor.process_bar(
                row['open'], row['high'], row['low'],
                row['close'], row['volume']
            )
            
            if i >= warmup_bars and result:
                # Track predictions
                if result.prediction != 0:
                    predictions.append(result.prediction)
                
                # Track entry signals
                if result.start_long_trade:
                    signals.append({
                        'time': idx,
                        'type': 'long',
                        'price': row['close'],
                        'prediction': result.prediction
                    })
                elif result.start_short_trade:
                    signals.append({
                        'time': idx,
                        'type': 'short',
                        'price': row['close'],
                        'prediction': result.prediction
                    })
        
        print(f"\nResults:")
        print(f"  Non-zero predictions: {len(predictions)}")
        print(f"  Trading signals: {len(signals)}")
        
        if predictions:
            print(f"  Avg prediction strength: {np.mean([abs(p) for p in predictions]):.2f}")
            print(f"  Max prediction: {max(predictions):.2f}")
            print(f"  Min prediction: {min(predictions):.2f}")
        
        # Simple P&L calculation
        if signals:
            # Simulate trades
            pnl = 0
            wins = 0
            
            for i, signal in enumerate(signals):
                # Exit at next signal or after 20 bars
                exit_price = None
                exit_idx = None
                
                # Find exit
                signal_idx = df.index.get_loc(signal['time'])
                
                # Look for exit in next 20 bars
                for j in range(signal_idx + 1, min(signal_idx + 20, len(df))):
                    # Exit on 1% move or next signal
                    if signal['type'] == 'long':
                        if df.iloc[j]['high'] >= signal['price'] * 1.01:  # 1% profit
                            exit_price = signal['price'] * 1.01
                            exit_idx = j
                            break
                        elif df.iloc[j]['low'] <= signal['price'] * 0.995:  # 0.5% stop
                            exit_price = signal['price'] * 0.995
                            exit_idx = j
                            break
                    else:  # short
                        if df.iloc[j]['low'] <= signal['price'] * 0.99:  # 1% profit
                            exit_price = signal['price'] * 0.99
                            exit_idx = j
                            break
                        elif df.iloc[j]['high'] >= signal['price'] * 1.005:  # 0.5% stop
                            exit_price = signal['price'] * 1.005
                            exit_idx = j
                            break
                
                # If no exit, use last price
                if exit_price is None and signal_idx + 20 < len(df):
                    exit_price = df.iloc[signal_idx + 20]['close']
                
                # Calculate P&L
                if exit_price:
                    if signal['type'] == 'long':
                        trade_pnl = (exit_price - signal['price']) / signal['price']
                    else:
                        trade_pnl = (signal['price'] - exit_price) / signal['price']
                    
                    pnl += trade_pnl
                    if trade_pnl > 0:
                        wins += 1
            
            # Display metrics
            win_rate = (wins / len(signals)) * 100 if signals else 0
            total_return = pnl * 100
            
            print(f"\nTrading Performance:")
            print(f"  Win Rate: {win_rate:.1f}%")
            print(f"  Total Return: {total_return:.2f}%")
            print(f"  Avg Return per Trade: {(total_return / len(signals)):.2f}%")
            
            # Show sample signals
            if len(signals) >= 3:
                print(f"\nSample Signals:")
                for i, sig in enumerate(signals[:3]):
                    print(f"  {i+1}. {sig['time']} - {sig['type'].upper()} @ {sig['price']:.2f} (pred: {sig['prediction']:.1f})")
    
    # Check flexible ML statistics
    if use_flexible and hasattr(processor, 'get_comparison_stats'):
        stats = processor.get_comparison_stats()
        if stats and stats.get('comparisons', 0) > 0:
            print(f"\n{'='*60}")
            print("FLEXIBLE ML DIAGNOSTICS")
            print(f"{'='*60}")
            print(f"Comparisons made: {stats['comparisons']}")
            print(f"Avg difference: {stats['avg_difference']:.3f}")
            print(f"Max difference: {stats['max_difference']:.3f}")


def main():
    """Run simple profitability test"""
    
    print("\n" + "="*80)
    print("PHASE 3 FLEXIBLE ML - SIMPLE PROFITABILITY TEST")
    print("="*80)
    print("\nThis test uses relaxed settings to generate more signals")
    print("and provides a quick profitability comparison.")
    
    # Test on available data
    symbols = ['RELIANCE', 'INFY', 'TCS']
    
    for symbol in symbols:
        try:
            quick_backtest(symbol, days=60)  # Need 60 days for 2000+ bars
        except Exception as e:
            print(f"\n❌ Error testing {symbol}: {str(e)}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()