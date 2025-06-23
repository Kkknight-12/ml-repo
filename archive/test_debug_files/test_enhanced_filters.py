#!/usr/bin/env python3
"""
Test Enhanced Filters with Real ICICI Data
Check why filter pass rate is 0%
"""
import sys
sys.path.append('.')

import pandas as pd
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from core.ml_extensions import enhanced_regime_filter, enhanced_filter_adx, enhanced_filter_volatility
from core.indicators import get_indicator_manager


def test_filters_step_by_step():
    """Test each filter individually to diagnose the issue"""
    
    print("="*70)
    print("🔍 ENHANCED FILTER DIAGNOSTIC TEST")
    print("="*70)
    
    # Load ICICI data from CSV
    try:
        # Try different CSV files
        csv_files = [
            'NSE_ICICIBANK, 1D.csv',
            'zerodha_complete_data.csv',
            'pinescript_style_ICICIBANK_2000bars.csv'
        ]
        
        df = None
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                print(f"\n✅ Loaded data from {csv_file}")
                print(f"   Rows: {len(df)}")
                break
            except:
                continue
                
        if df is None:
            print("\n❌ No CSV data found. Please run Zerodha fetch first.")
            return
            
    except Exception as e:
        print(f"\n❌ Error loading data: {e}")
        return
    
    # Configuration
    config = TradingConfig(
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,  # OFF by default
        regime_threshold=-0.1,
        adx_threshold=20
    )
    
    # Test parameters
    symbol = "ICICIBANK"
    timeframe = "1D"
    
    # Reset indicators
    manager = get_indicator_manager()
    manager.clear_symbol(symbol)
    
    # Process bars and check filters
    print(f"\n📊 Processing {len(df)} bars...")
    
    volatility_passes = 0
    regime_passes = 0
    adx_passes = 0
    all_pass = 0
    
    # Track filter values
    volatility_values = []
    regime_values = []
    adx_values = []
    
    for i, row in df.iterrows():
        if i < 50:  # Skip warmup
            continue
            
        # Get OHLC data
        high = float(row.get('high', row.get('High', 0)))
        low = float(row.get('low', row.get('Low', 0)))
        close = float(row.get('close', row.get('Close', 0)))
        
        if close == 0:
            continue
            
        # Calculate ohlc4
        open_price = float(row.get('open', row.get('Open', close)))
        ohlc4 = (open_price + high + low + close) / 4
        
        # Test each filter
        try:
            # Volatility filter
            vol_result = enhanced_filter_volatility(
                high, low, close,
                symbol, timeframe,
                1, 10, True
            )
            if vol_result:
                volatility_passes += 1
            volatility_values.append(vol_result)
            
            # Regime filter (needs previous ohlc4)
            if i > 0:
                prev_row = df.iloc[i-1]
                prev_ohlc4 = (
                    float(prev_row.get('open', prev_row.get('Open', 0))) +
                    float(prev_row.get('high', prev_row.get('High', 0))) +
                    float(prev_row.get('low', prev_row.get('Low', 0))) +
                    float(prev_row.get('close', prev_row.get('Close', 0)))
                ) / 4
                
                regime_result = enhanced_regime_filter(
                    ohlc4, high, low, prev_ohlc4,
                    symbol, timeframe,
                    -0.1, True
                )
                if regime_result:
                    regime_passes += 1
                regime_values.append(regime_result)
            
            # ADX filter (even though OFF by default)
            adx_result = enhanced_filter_adx(
                high, low, close,
                symbol, timeframe,
                14, 20, False  # OFF by default
            )
            if adx_result:
                adx_passes += 1
            adx_values.append(adx_result)
            
            # All filters
            if vol_result and (regime_result if i > 0 else True) and adx_result:
                all_pass += 1
                
        except Exception as e:
            print(f"\n❌ Error at row {i}: {e}")
            break
    
    # Calculate stats
    total_bars = len(df) - 50  # Excluding warmup
    
    print(f"\n📊 FILTER RESULTS:")
    print(f"   Total bars tested: {total_bars}")
    
    print(f"\n1️⃣ Volatility Filter:")
    print(f"   Passes: {volatility_passes} ({volatility_passes/total_bars*100:.1f}%)")
    print(f"   Fails: {total_bars - volatility_passes}")
    
    print(f"\n2️⃣ Regime Filter:")
    print(f"   Passes: {regime_passes} ({regime_passes/max(1, len(regime_values))*100:.1f}%)")
    print(f"   Fails: {len(regime_values) - regime_passes}")
    
    print(f"\n3️⃣ ADX Filter (OFF by default):")
    print(f"   Passes: {adx_passes} ({adx_passes/total_bars*100:.1f}%)")
    print(f"   Should be 100% since it's OFF")
    
    print(f"\n4️⃣ All Filters Combined:")
    print(f"   Passes: {all_pass} ({all_pass/total_bars*100:.1f}%)")
    
    # Sample filter values
    if volatility_values:
        print(f"\n🔍 Sample Volatility Values (last 10):")
        for i, val in enumerate(volatility_values[-10:]):
            print(f"   Bar {len(volatility_values)-10+i}: {val}")
    
    if regime_values:
        print(f"\n🔍 Sample Regime Values (last 10):")
        for i, val in enumerate(regime_values[-10:]):
            print(f"   Bar {len(regime_values)-10+i}: {val}")
    
    # Check if filters are too restrictive
    print(f"\n💡 DIAGNOSIS:")
    if volatility_passes == 0:
        print("   ❌ Volatility filter blocking ALL signals!")
        print("      → Check ATR calculation in enhanced version")
    
    if regime_passes == 0:
        print("   ❌ Regime filter blocking ALL signals!")
        print("      → Check KLMF calculation in enhanced version")
    
    if adx_passes < total_bars and not config.use_adx_filter:
        print("   ⚠️  ADX filter should pass 100% when OFF")
        print("      → Check filter logic in enhanced version")
    
    print("\n📌 RECOMMENDATIONS:")
    if volatility_passes == 0 or regime_passes == 0:
        print("   1. Enhanced filters may need debugging")
        print("   2. Check if stateful indicators are initializing correctly")
        print("   3. Compare with old non-enhanced version")
        print("   4. May need to adjust thresholds for daily data")


def test_with_enhanced_processor():
    """Test using the EnhancedBarProcessor directly"""
    
    print("\n\n" + "="*70)
    print("🤖 TESTING WITH ENHANCED BAR PROCESSOR")
    print("="*70)
    
    # Load data
    try:
        df = pd.read_csv('NSE_ICICIBANK, 1D.csv')
        print(f"\n✅ Loaded {len(df)} bars of ICICI data")
    except:
        print("\n❌ Could not load ICICI data")
        return
    
    # Create processor
    config = TradingConfig()
    processor = EnhancedBarProcessor(config, "ICICIBANK", "1D")
    
    # Track filter results
    filter_results = {
        'volatility': [],
        'regime': [],
        'adx': []
    }
    
    print("\n📊 Processing bars...")
    
    for i, row in df.iterrows():
        if i < 50:  # Skip warmup
            continue
            
        if i > 100:  # Test first 50 bars after warmup
            break
        
        # Process bar
        result = processor.process_bar(
            float(row.get('open', row.get('Open', 0))),
            float(row.get('high', row.get('High', 0))),
            float(row.get('low', row.get('Low', 0))),
            float(row.get('close', row.get('Close', 0))),
            float(row.get('volume', row.get('Volume', 0)))
        )
        
        if result and result.filter_states:
            for filter_name, passed in result.filter_states.items():
                if filter_name in filter_results:
                    filter_results[filter_name].append(passed)
            
            # Print sample
            if i % 10 == 0:
                print(f"   Bar {i}: Filters = {result.filter_states}")
    
    # Summary
    print("\n📊 FILTER SUMMARY:")
    for filter_name, results in filter_results.items():
        if results:
            passes = sum(results)
            total = len(results)
            print(f"   {filter_name}: {passes}/{total} ({passes/total*100:.1f}%)")


if __name__ == "__main__":
    # Test filters individually
    test_filters_step_by_step()
    
    # Test with processor
    test_with_enhanced_processor()
    
    print("\n✅ Filter diagnostic complete!")
