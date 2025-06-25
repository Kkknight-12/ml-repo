#!/usr/bin/env python3
"""
Diagnose Low Trade Count Issue
==============================

Investigates why FixedOptimizedTradingConfig generates very few trades.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import json

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
from config.fixed_optimized_settings import FixedOptimizedTradingConfig
from data.zerodha_client import ZerodhaClient
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def diagnose_config_differences():
    """Compare signal generation between configs"""
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # Shorter period for diagnosis
    
    print("="*80)
    print("🔍 DIAGNOSING LOW TRADE COUNT")
    print("="*80)
    
    # Get data
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("Fetching fresh data...")
        client = ZerodhaClient()
        data = client.get_historical_data(symbol, "5minute", 30)
        if data:
            import pandas as pd
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
    
    if df.empty:
        print("No data available")
        return
    
    print(f"Data points: {len(df)}")
    
    # Test with standard config
    print("\n1️⃣ Testing STANDARD CONFIG...")
    standard_config = TradingConfig()
    standard_processor = EnhancedBarProcessor(standard_config, symbol, "5minute")
    
    standard_signals = 0
    standard_filters_passed = 0
    
    # Test with optimized config
    print("\n2️⃣ Testing OPTIMIZED CONFIG...")
    optimized_config = FixedOptimizedTradingConfig()
    optimized_processor = EnhancedBarProcessor(optimized_config, symbol, "5minute")
    
    optimized_signals = 0
    optimized_filters_passed = 0
    
    # Process bars
    bars_processed = 0
    for idx, row in df.iterrows():
        bars_processed += 1
        
        # Standard config
        std_result = standard_processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # Optimized config
        opt_result = optimized_processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # Skip warmup
        if bars_processed < 2000:
            continue
        
        # Check signals
        if abs(std_result.prediction) >= 3.0:
            standard_signals += 1
            if std_result.filter_all:
                standard_filters_passed += 1
        
        if abs(opt_result.prediction) >= 3.0:
            optimized_signals += 1
            if opt_result.filter_all:
                optimized_filters_passed += 1
        
        # Log first few differences
        if bars_processed == 2001:
            print(f"\nFirst bar after warmup:")
            print(f"  Standard - Prediction: {std_result.prediction:.2f}, Filters: {std_result.filter_all}")
            print(f"  Optimized - Prediction: {opt_result.prediction:.2f}, Filters: {opt_result.filter_all}")
            
            # Check individual filters
            print(f"\n  Filter details (Standard):")
            print(f"    Volatility: {std_result.filter_volatility}")
            print(f"    Regime: {std_result.filter_regime}")
            print(f"    ADX: {std_result.filter_adx}")
            
            print(f"\n  Filter details (Optimized):")
            print(f"    Volatility: {opt_result.filter_volatility}")
            print(f"    Regime: {opt_result.filter_regime}")
            print(f"    ADX: {opt_result.filter_adx}")
    
    # Results
    print("\n" + "="*60)
    print("📊 COMPARISON RESULTS")
    print("="*60)
    
    print(f"\nStandard Config:")
    print(f"  ML Signals (|pred| >= 3): {standard_signals}")
    print(f"  Signals with filters passed: {standard_filters_passed}")
    print(f"  Filter pass rate: {standard_filters_passed/max(1,standard_signals)*100:.1f}%")
    
    print(f"\nOptimized Config:")
    print(f"  ML Signals (|pred| >= 3): {optimized_signals}")
    print(f"  Signals with filters passed: {optimized_filters_passed}")
    print(f"  Filter pass rate: {optimized_filters_passed/max(1,optimized_signals)*100:.1f}%")
    
    print(f"\nDifference:")
    print(f"  Signal reduction: {standard_signals - optimized_signals}")
    print(f"  Trade reduction: {standard_filters_passed - optimized_filters_passed}")
    
    # Check config differences
    print("\n🔧 Key Config Differences:")
    print(f"  Neighbors: {standard_config.neighbors_count} → {optimized_config.neighbors_count}")
    print(f"  ADX Filter: {standard_config.use_adx_filter} → {optimized_config.use_adx_filter}")
    print(f"  ADX Threshold: {standard_config.adx_threshold} → {optimized_config.adx_threshold}")
    print(f"  Regime Threshold: {standard_config.regime_threshold} → {optimized_config.regime_threshold}")
    print(f"  EMA Filter: {standard_config.use_ema_filter} → {optimized_config.use_ema_filter}")
    print(f"  SMA Filter: {standard_config.use_sma_filter} → {optimized_config.use_sma_filter}")
    
    # Feature differences
    print("\n📈 Feature Differences:")
    std_features = standard_config.features
    opt_features = optimized_config.features
    for f in ['f1', 'f2', 'f3', 'f4', 'f5']:
        if std_features[f] != opt_features[f]:
            print(f"  {f}: {std_features[f]} → {opt_features[f]}")


if __name__ == "__main__":
    diagnose_config_differences()