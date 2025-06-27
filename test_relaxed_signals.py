#!/usr/bin/env python3
"""
Test Relaxed Signal Generator
=============================

Compare entry generation between standard and relaxed signal generators
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import pandas as pd
import json

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from scanner.enhanced_bar_processor_relaxed import EnhancedBarProcessorRelaxed
from config.settings import TradingConfig
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def compare_signal_generators():
    """Compare standard vs relaxed signal generation"""
    
    print("="*80)
    print("🔬 COMPARING SIGNAL GENERATORS")
    print("="*80)
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # Get data
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return
    
    print(f"\n📊 Processing {len(df)} bars for {symbol}")
    print(f"   From: {df.index[0]}")
    print(f"   To: {df.index[-1]}")
    
    # Test configurations
    configs = [
        ("Standard (restrictive)", TradingConfig()),
        ("Relaxed (no ML threshold)", TradingConfig()),
        ("Relaxed (ML threshold 3.0)", TradingConfig())
    ]
    
    # Set ML threshold for third config
    configs[2][1].ml_prediction_threshold = 3.0
    
    results = {}
    
    for config_name, config in configs:
        print(f"\n\n{'='*60}")
        print(f"Testing: {config_name}")
        print(f"{'='*60}")
        
        # Choose processor based on config
        if "Relaxed" in config_name:
            processor = EnhancedBarProcessorRelaxed(config, symbol, "5minute")
        else:
            processor = EnhancedBarProcessor(config, symbol, "5minute")
        
        # Process bars
        entries = []
        ml_signals = 0
        
        for i, (idx, row) in enumerate(df.iterrows()):
            result = processor.process_bar(
                row['open'], row['high'], row['low'], 
                row['close'], row['volume']
            )
            
            # After warmup
            if i >= config.max_bars_back:
                if result.signal != 0:
                    ml_signals += 1
                
                if result.start_long_trade or result.start_short_trade:
                    entries.append({
                        'bar': i,
                        'date': idx,
                        'type': 'long' if result.start_long_trade else 'short',
                        'ml_prediction': result.prediction,
                        'signal': result.signal
                    })
        
        # Store results
        results[config_name] = {
            'ml_signals': ml_signals,
            'entries': len(entries),
            'conversion_rate': len(entries) / ml_signals * 100 if ml_signals > 0 else 0,
            'sample_entries': entries[:5]  # First 5 entries
        }
        
        # Get statistics if available
        if hasattr(processor, 'get_statistics'):
            stats = processor.get_statistics()
            results[config_name]['stats'] = stats
    
    # Print comparison
    print("\n\n" + "="*80)
    print("📊 COMPARISON RESULTS")
    print("="*80)
    
    print("\n1. SIGNAL GENERATION:")
    print("-"*60)
    print(f"{'Config':<30} {'ML Signals':>12} {'Entries':>10} {'Conv Rate':>10}")
    print("-"*60)
    
    for config_name, result in results.items():
        print(f"{config_name:<30} {result['ml_signals']:>12} {result['entries']:>10} {result['conversion_rate']:>9.1f}%")
    
    # Show improvement
    if len(results) >= 2:
        standard_entries = results["Standard (restrictive)"]['entries']
        relaxed_entries = results["Relaxed (no ML threshold)"]['entries']
        
        if standard_entries > 0:
            improvement = (relaxed_entries - standard_entries) / standard_entries * 100
            print(f"\n📈 Improvement: {improvement:+.0f}% more entries with relaxed conditions")
        else:
            print(f"\n📈 Improvement: {relaxed_entries} entries (vs 0 with standard)")
    
    # Show sample entries
    print("\n\n2. SAMPLE ENTRIES:")
    print("-"*60)
    
    for config_name, result in results.items():
        print(f"\n{config_name}:")
        if result['sample_entries']:
            for i, entry in enumerate(result['sample_entries']):
                print(f"  Entry {i+1}: Bar {entry['bar']}, {entry['type']}, ML={entry['ml_prediction']:.2f}")
        else:
            print("  No entries generated")
    
    # Detailed statistics
    print("\n\n3. DETAILED STATISTICS:")
    print("-"*60)
    
    for config_name, result in results.items():
        if 'stats' in result:
            print(f"\n{config_name}:")
            stats = result['stats']
            for key, value in stats.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.2f}")
                else:
                    print(f"  {key}: {value}")
    
    # Recommendations
    print("\n\n💡 RECOMMENDATIONS:")
    print("-"*60)
    
    if results["Relaxed (no ML threshold)"]['entries'] > results["Standard (restrictive)"]['entries'] * 5:
        print("✅ Relaxed conditions significantly increase trade frequency")
        print("   Consider using relaxed signal generator for better opportunity capture")
    
    if results["Relaxed (ML threshold 3.0)"]['entries'] < results["Relaxed (no ML threshold)"]['entries'] / 2:
        print("⚠️  ML threshold 3.0 may be too restrictive")
        print("   Consider lowering threshold or removing it entirely")
    
    # Save detailed results
    results_df = pd.DataFrame([
        {
            'config': config_name,
            'ml_signals': result['ml_signals'],
            'entries': result['entries'],
            'conversion_rate': result['conversion_rate']
        }
        for config_name, result in results.items()
    ])
    
    results_df.to_csv('signal_generator_comparison.csv', index=False)
    print(f"\n💾 Detailed results saved to signal_generator_comparison.csv")


if __name__ == "__main__":
    compare_signal_generators()