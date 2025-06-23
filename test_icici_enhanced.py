#!/usr/bin/env python3
"""
Quick test of enhanced indicators with ICICI data
"""
import sys
sys.path.append('.')

import pandas as pd
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor


def test_icici_enhanced():
    """Test enhanced processor with real ICICI data"""
    
    print("="*70)
    print("🔍 TESTING ENHANCED INDICATORS WITH ICICI DATA")
    print("="*70)
    
    # Load ICICI data
    df = pd.read_csv('NSE_ICICIBANK, 1D.csv')
    print(f"\n✅ Loaded {len(df)} bars of ICICI daily data")
    print(f"   Date range: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
    
    # Configuration
    config = TradingConfig(
        # Use Pine Script defaults
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,  # OFF by default
        regime_threshold=-0.1,
        adx_threshold=20
    )
    
    # Create processor
    processor = EnhancedBarProcessor(config, "ICICIBANK", "1D")
    
    # Track results
    ml_predictions = []
    filter_results = {
        'volatility': [],
        'regime': [],
        'adx': []
    }
    
    print("\n📊 Processing bars...")
    
    # Process first 100 bars to test
    for i, row in df.head(100).iterrows():
        # Process bar
        result = processor.process_bar(
            float(row['open']),
            float(row['high']),
            float(row['low']),
            float(row['close']),
            float(row.get('volume', 1000000))  # Default volume if missing
        )
        
        if result and result.bar_index > 50:  # After warmup
            # Track ML prediction
            if result.prediction != 0:
                ml_predictions.append(result.prediction)
            
            # Track filters
            if result.filter_states:
                for filter_name, passed in result.filter_states.items():
                    if filter_name in filter_results:
                        filter_results[filter_name].append(passed)
            
            # Print sample every 20 bars
            if result.bar_index % 20 == 0:
                print(f"\n   Bar {result.bar_index} ({row['time']}):")
                print(f"     Price: ₹{result.close:.2f}")
                print(f"     ML Prediction: {result.prediction:.2f}")
                print(f"     Filters: {result.filter_states}")
    
    # Summary
    print("\n" + "="*70)
    print("📊 RESULTS SUMMARY")
    print("="*70)
    
    # ML Predictions
    if ml_predictions:
        print(f"\n1️⃣ ML Predictions:")
        print(f"   Count: {len(ml_predictions)}")
        print(f"   Range: {min(ml_predictions):.1f} to {max(ml_predictions):.1f}")
        print(f"   Average: {sum(ml_predictions)/len(ml_predictions):.2f}")
    
    # Filter Performance
    print(f"\n2️⃣ Filter Performance:")
    for filter_name, results in filter_results.items():
        if results:
            passes = sum(results)
            total = len(results)
            pass_rate = passes / total * 100
            print(f"   {filter_name.capitalize()}: {passes}/{total} ({pass_rate:.1f}%)")
            
            # Debug first few values
            if pass_rate == 0:
                print(f"      → First 5 values: {results[:5]}")
    
    # Check if filters are the issue
    if all(sum(results) == 0 for results in filter_results.values() if results):
        print("\n⚠️  ALL FILTERS BLOCKING SIGNALS!")
        print("   This explains the 0% filter pass rate in comprehensive test")
        
        # Test without filters
        print("\n3️⃣ Testing without filters...")
        config_no_filters = TradingConfig(
            use_volatility_filter=False,
            use_regime_filter=False,
            use_adx_filter=False
        )
        
        processor_no_filters = EnhancedBarProcessor(config_no_filters, "ICICIBANK", "1D")
        
        # Process a few bars
        for i, row in df.head(60).iterrows():
            result = processor_no_filters.process_bar(
                float(row['open']),
                float(row['high']),
                float(row['low']),
                float(row['close']),
                float(row.get('volume', 1000000))
            )
            
            if result and result.bar_index == 55:
                print(f"   Without filters - ML Prediction: {result.prediction:.2f}")
                print(f"   Signal: {result.signal}")
                break
    
    print("\n✅ Test complete!")


if __name__ == "__main__":
    test_icici_enhanced()
