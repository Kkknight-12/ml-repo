#!/usr/bin/env python3
"""
Simple ML Optimization Test
===========================

Basic test to ensure ML threshold and multi-targets work
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import json
import traceback

from backtest_framework_enhanced import EnhancedBacktestEngine
from config.settings import TradingConfig
from config.ml_optimized_settings import MLOptimizedTradingConfig

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def test_simple():
    """Simple test of baseline vs ML-optimized"""
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    engine = EnhancedBacktestEngine()
    
    print("="*80)
    print("🧪 SIMPLE ML OPTIMIZATION TEST")
    print("="*80)
    
    # Test 1: Baseline
    print("\n1️⃣ BASELINE CONFIG:")
    try:
        config1 = TradingConfig()
        config1.use_dynamic_exits = True
        print(f"   Dynamic exits: {config1.use_dynamic_exits}")
        print(f"   ML threshold: {getattr(config1, 'ml_prediction_threshold', 'None')}")
        print(f"   Multi-targets: {hasattr(config1, 'target_1_ratio')}")
        
        metrics1 = engine.run_backtest(symbol, start_date, end_date, config1)
        print(f"\n   Results:")
        print(f"   Trades: {metrics1.total_trades}")
        print(f"   Win Rate: {metrics1.win_rate:.1f}%")
        print(f"   Risk/Reward: {abs(metrics1.average_win/metrics1.average_loss):.2f}")
        
    except Exception as e:
        print(f"   ERROR: {e}")
        traceback.print_exc()
    
    # Test 2: ML-Optimized
    print("\n2️⃣ ML-OPTIMIZED CONFIG:")
    try:
        config2 = MLOptimizedTradingConfig()
        print(f"   Dynamic exits: {config2.use_dynamic_exits}")
        print(f"   ML threshold: {config2.ml_prediction_threshold}")
        print(f"   Multi-targets: {config2.target_1_ratio}R@{int(config2.target_1_percent*100)}% + {config2.target_2_ratio}R@{int(config2.target_2_percent*100)}%")
        print(f"   Volatility filter: {config2.use_volatility_filter}")
        
        metrics2 = engine.run_backtest(symbol, start_date, end_date, config2)
        print(f"\n   Results:")
        print(f"   Trades: {metrics2.total_trades}")
        print(f"   Win Rate: {metrics2.win_rate:.1f}%")
        print(f"   Risk/Reward: {abs(metrics2.average_win/metrics2.average_loss):.2f}")
        
    except Exception as e:
        print(f"   ERROR: {e}")
        traceback.print_exc()
    
    # Test 3: ML-Optimized with lower threshold
    print("\n3️⃣ ML-OPTIMIZED WITH LOWER THRESHOLD:")
    try:
        config3 = MLOptimizedTradingConfig()
        config3.ml_prediction_threshold = 2.0  # Lower threshold
        print(f"   ML threshold: {config3.ml_prediction_threshold}")
        
        metrics3 = engine.run_backtest(symbol, start_date, end_date, config3)
        print(f"\n   Results:")
        print(f"   Trades: {metrics3.total_trades}")
        print(f"   Win Rate: {metrics3.win_rate:.1f}%")
        print(f"   Risk/Reward: {abs(metrics3.average_win/metrics3.average_loss):.2f}")
        
    except Exception as e:
        print(f"   ERROR: {e}")
        traceback.print_exc()
    
    # Test 4: Baseline with multi-targets (no ML threshold)
    print("\n4️⃣ BASELINE WITH MULTI-TARGETS (No ML threshold):")
    try:
        config4 = TradingConfig()
        config4.use_dynamic_exits = True
        config4.target_1_ratio = 1.5
        config4.target_1_percent = 0.5
        config4.target_2_ratio = 3.0
        config4.target_2_percent = 0.3
        config4.trailing_stop_distance_ratio = 1.0
        print(f"   Multi-targets: {config4.target_1_ratio}R@{int(config4.target_1_percent*100)}% + {config4.target_2_ratio}R@{int(config4.target_2_percent*100)}%")
        print(f"   ML threshold: None")
        
        metrics4 = engine.run_backtest(symbol, start_date, end_date, config4)
        print(f"\n   Results:")
        print(f"   Trades: {metrics4.total_trades}")
        print(f"   Win Rate: {metrics4.win_rate:.1f}%")
        print(f"   Risk/Reward: {abs(metrics4.average_win/metrics4.average_loss):.2f}")
        
    except Exception as e:
        print(f"   ERROR: {e}")
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("💡 ANALYSIS:")
    print("="*80)
    print("Compare the results above to see:")
    print("1. Impact of ML threshold on trade count and win rate")
    print("2. Impact of multi-targets on risk/reward")
    print("3. Combined effect of both optimizations")


if __name__ == "__main__":
    test_simple()