#!/usr/bin/env python3
"""
Simple Multi-Target Exit Test
=============================

Tests multi-target exits using standard TradingConfig to isolate issues.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import json

# Import frameworks
from backtest_framework import BacktestEngine
from backtest_framework_enhanced import EnhancedBacktestEngine
from config.settings import TradingConfig

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def test_simple_multi_target():
    """Test multi-target exits with minimal configuration"""
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print("="*80)
    print("🎯 SIMPLE MULTI-TARGET TEST")
    print("="*80)
    
    # 1. Standard dynamic exits
    print("\n1️⃣ Testing STANDARD DYNAMIC EXITS...")
    standard_config = TradingConfig()
    standard_config.use_dynamic_exits = True
    
    standard_engine = BacktestEngine()
    standard_metrics = standard_engine.run_backtest(
        symbol, start_date, end_date, standard_config
    )
    
    print(f"Standard Results:")
    print(f"  Trades: {standard_metrics.total_trades}")
    print(f"  Win Rate: {standard_metrics.win_rate:.1f}%")
    print(f"  Avg Win: {standard_metrics.average_win:.2f}%")
    print(f"  Total Return: {standard_metrics.total_return:.2f}%")
    
    # 2. Multi-target with same base config
    print("\n2️⃣ Testing MULTI-TARGET WITH SAME CONFIG...")
    multi_config = TradingConfig()
    multi_config.use_dynamic_exits = True
    
    # Add multi-target parameters
    multi_config.target_1_ratio = 1.5
    multi_config.target_1_percent = 0.5
    multi_config.target_2_ratio = 3.0
    multi_config.target_2_percent = 0.3
    multi_config.trailing_stop_distance_ratio = 1.0
    
    enhanced_engine = EnhancedBacktestEngine()
    multi_metrics = enhanced_engine.run_backtest(
        symbol, start_date, end_date, multi_config
    )
    
    print(f"\nMulti-Target Results:")
    print(f"  Trades: {multi_metrics.total_trades}")
    print(f"  Win Rate: {multi_metrics.win_rate:.1f}%")
    print(f"  Avg Win: {multi_metrics.average_win:.2f}%")
    print(f"  Total Return: {multi_metrics.total_return:.2f}%")
    
    # Compare
    print("\n📊 COMPARISON:")
    print(f"Trade difference: {multi_metrics.total_trades - standard_metrics.total_trades}")
    print(f"Avg win improvement: {multi_metrics.average_win - standard_metrics.average_win:.2f}%")
    
    # If still low trades, investigate
    if multi_metrics.total_trades < 10:
        print("\n⚠️ WARNING: Very few trades generated!")
        print("Possible issues:")
        print("- Entry logic in enhanced engine might be different")
        print("- Multi-target config might be affecting entries")
        print("- Need to check if enhanced engine is using correct processor")


if __name__ == "__main__":
    test_simple_multi_target()