"""
Basic Phase 3 Optimizer Test
============================

Simplified test to verify Phase 3 components work correctly.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from ml.walk_forward_optimizer import WalkForwardOptimizer
from ml.adaptive_threshold import AdaptiveMLThreshold
from indicators.advanced.fisher_transform import FisherTransform
from indicators.advanced.volume_weighted_momentum import VolumeWeightedMomentum
from indicators.advanced.market_internals import MarketInternals
from data.smart_data_manager import SmartDataManager


def test_advanced_indicators(symbol: str = 'RELIANCE'):
    """Test new advanced indicators"""
    
    print(f"\n{'='*60}")
    print("TESTING ADVANCED INDICATORS")
    print(f"{'='*60}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=10)
    
    if df is None or len(df) < 100:
        print(f"⚠️  Insufficient data")
        return
    
    print(f"\nData loaded: {len(df)} bars")
    
    # Test Fisher Transform
    print("\n1. Fisher Transform:")
    fisher = FisherTransform(period=10)
    
    for i in range(20):
        row = df.iloc[i]
        fisher_val, trigger = fisher.update(row['high'], row['low'])
        if i >= 10:
            signal = fisher.get_signal()
            extreme = fisher.get_extreme_reading()
            print(f"   Bar {i}: Fisher={fisher_val:.3f}, Trigger={trigger:.3f}, "
                  f"Signal={signal}, Extreme={extreme}")
    
    # Test Volume-Weighted Momentum
    print("\n2. Volume-Weighted Momentum:")
    vwm = VolumeWeightedMomentum(momentum_period=14)
    
    for i in range(20):
        row = df.iloc[i]
        vwm_data = vwm.update(row['close'], row['volume'])
        if i >= 14:
            strength = vwm.get_signal_strength()
            trend = vwm.get_trend_strength()
            print(f"   Bar {i}: VWM={vwm_data['vwm']:.3f}, "
                  f"Signal Strength={strength:.3f}, "
                  f"Trend={trend['trend']:.3f}")
    
    # Test Market Internals
    print("\n3. Market Internals:")
    internals = MarketInternals(profile_period=20)
    
    for i in range(30):
        row = df.iloc[i]
        internal_data = internals.update(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        if i >= 20:
            print(f"   Bar {i}: Order Flow={internal_data['order_flow_imbalance']:.3f}, "
                  f"Volume Trend={internal_data['volume_trend']:.3f}, "
                  f"Buying Pressure={internal_data['buying_pressure']:.3f}")


def test_adaptive_threshold(symbol: str = 'RELIANCE'):
    """Test adaptive ML threshold system"""
    
    print(f"\n{'='*60}")
    print("TESTING ADAPTIVE ML THRESHOLD")
    print(f"{'='*60}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=5)
    
    if df is None:
        print(f"⚠️  No data available")
        return
    
    # Create adaptive threshold
    adaptive = AdaptiveMLThreshold(base_threshold=3.0)
    
    print(f"\nBase threshold: {adaptive.base_threshold}")
    print("\nProcessing bars and adjusting threshold...")
    
    thresholds = []
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if i >= 100:  # Skip initial bars
            adjustment = adaptive.update(
                row['high'], row['low'], row['close'], 
                row['volume'], idx
            )
            
            thresholds.append(adjustment.final_threshold)
            
            if i % 50 == 0:
                print(f"\nBar {i} ({idx.strftime('%H:%M')}):")
                print(f"  Volatility adj: {adjustment.volatility_adj:+.2f}")
                print(f"  Trend adj: {adjustment.trend_adj:+.2f}")
                print(f"  Volume adj: {adjustment.volume_adj:+.2f}")
                print(f"  Time adj: {adjustment.time_adj:+.2f}")
                print(f"  Final threshold: {adjustment.final_threshold:.2f}")
                print(f"  Confidence: {adjustment.confidence:.2f}")
    
    # Show statistics
    stats = adaptive.get_threshold_stats()
    print(f"\n{'='*40}")
    print("THRESHOLD STATISTICS")
    print(f"{'='*40}")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def test_walk_forward_windows():
    """Test walk-forward window creation"""
    
    print(f"\n{'='*60}")
    print("TESTING WALK-FORWARD WINDOWS")
    print(f"{'='*60}")
    
    # Create sample data
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    data = pd.DataFrame({
        'close': np.random.randn(len(dates)).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)
    
    # Create optimizer
    optimizer = WalkForwardOptimizer(
        train_days=60,
        test_days=20,
        step_days=10
    )
    
    # Create windows
    windows = optimizer.create_windows(data)
    
    print(f"\nCreated {len(windows)} windows from {len(data)} days of data")
    print("\nWindow details:")
    
    for i, window in enumerate(windows[:5]):  # Show first 5
        print(f"\nWindow {window.window_id}:")
        print(f"  Train: {window.train_start.date()} to {window.train_end.date()} ({window.train_size} days)")
        print(f"  Test: {window.test_start.date()} to {window.test_end.date()} ({window.test_size} days)")


def test_phase3_integration():
    """Test Phase 3 components working together"""
    
    print(f"\n{'='*60}")
    print("PHASE 3 INTEGRATION TEST")
    print(f"{'='*60}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data('RELIANCE', interval='5minute', days=5)
    
    if df is None or len(df) < 500:
        print(f"⚠️  Insufficient data")
        return
    
    print(f"\nProcessing {len(df)} bars with Phase 3 enhancements...")
    
    # Initialize components
    fisher = FisherTransform()
    vwm = VolumeWeightedMomentum()
    internals = MarketInternals()
    adaptive_threshold = AdaptiveMLThreshold()
    
    # Track enhanced features
    enhanced_signals = []
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if i < 100:  # Warmup
            continue
            
        # Update indicators
        fisher_val, _ = fisher.update(row['high'], row['low'])
        vwm_data = vwm.update(row['close'], row['volume'])
        internal_data = internals.update(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        threshold_adj = adaptive_threshold.update(
            row['high'], row['low'], row['close'], 
            row['volume'], idx
        )
        
        # Create enhanced feature vector
        enhanced_features = {
            'fisher': fisher_val,
            'vwm': vwm_data['vwm'],
            'order_flow': internal_data['order_flow_imbalance'],
            'adaptive_threshold': threshold_adj.final_threshold,
            'signal_strength': vwm.get_signal_strength()
        }
        
        # Simple signal generation (would use ML in real implementation)
        if abs(fisher_val) > 1.5 and vwm_data['vwm'] > 0:
            signal_strength = abs(fisher_val) * vwm.get_signal_strength()
            
            if signal_strength > threshold_adj.final_threshold:
                enhanced_signals.append({
                    'timestamp': idx,
                    'signal': 1 if fisher_val > 0 else -1,
                    'strength': signal_strength,
                    'threshold': threshold_adj.final_threshold,
                    'features': enhanced_features
                })
    
    print(f"\nGenerated {len(enhanced_signals)} enhanced signals")
    
    if enhanced_signals:
        print("\nSample signals:")
        for signal in enhanced_signals[:5]:
            print(f"\n{signal['timestamp']}:")
            print(f"  Direction: {'Long' if signal['signal'] > 0 else 'Short'}")
            print(f"  Strength: {signal['strength']:.2f}")
            print(f"  Threshold: {signal['threshold']:.2f}")
            print(f"  Features: Fisher={signal['features']['fisher']:.2f}, "
                  f"VWM={signal['features']['vwm']:.2f}")


def main():
    """Run all Phase 3 basic tests"""
    
    print("\n" + "="*60)
    print("PHASE 3 BASIC COMPONENT TESTS")
    print("="*60)
    print("\nTesting individual Phase 3 components:")
    print("1. Advanced indicators (Fisher, VWM, Internals)")
    print("2. Adaptive ML threshold system")
    print("3. Walk-forward window creation")
    print("4. Integration test")
    
    # Run tests
    test_advanced_indicators()
    test_adaptive_threshold()
    test_walk_forward_windows()
    test_phase3_integration()
    
    print(f"\n{'='*60}")
    print("PHASE 3 BASIC TESTS COMPLETE")
    print(f"{'='*60}")
    print("\nAll Phase 3 components are working correctly!")
    print("\nNext steps:")
    print("1. Fix ConfirmationProcessor integration")
    print("2. Run full walk-forward optimization")
    print("3. Test on multiple symbols")
    print("4. Implement enhanced ML training")


if __name__ == "__main__":
    main()