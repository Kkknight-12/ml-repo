"""
Quick test to verify enhanced bar processor fixes
"""
import sys
import os
import json
sys.path.append('.')

from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from data.data_manager import DataManager
from data.zerodha_client import ZerodhaClient
import time

def test_enhanced_processor():
    """Test the enhanced bar processor with fixed imports and parameters"""
    print("=" * 70)
    print("🔧 TESTING ENHANCED BAR PROCESSOR FIXES")
    print("=" * 70)
    
    # Initialize Zerodha client first
    try:
        # Check for saved session
        if os.path.exists('.kite_session.json'):
            with open('.kite_session.json', 'r') as f:
                session_data = json.load(f)
                access_token = session_data.get('access_token')
            
            # Set token in environment
            os.environ['KITE_ACCESS_TOKEN'] = access_token
            zerodha_client = ZerodhaClient()
            print("✅ Zerodha connection established")
        else:
            print("❌ No access token found. Run auth_helper.py first")
            return
    except Exception as e:
        print(f"❌ Zerodha error: {str(e)}")
        return
    
    # Create config
    config = TradingConfig(
        neighbors_count=8,
        feature_count=5,
        max_bars_back=2000,
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,  # OFF by default like Pine Script
        use_kernel_filter=False  # Simplified for testing
    )
    
    # Create EnhancedBarProcessor directly for testing
    print("\n1️⃣ Creating EnhancedBarProcessor for ICICIBANK...")
    processor = EnhancedBarProcessor(config, "ICICIBANK", "day")
    
    # Load historical data
    print("\n2️⃣ Loading ICICIBANK historical data...")
    try:
        # Get instruments first
        zerodha_client.get_instruments("NSE")
        
        # Debug: Show ICICI related symbols
        icici_symbols = [sym for sym in zerodha_client.symbol_token_map.keys() if 'ICICI' in sym]
        print(f"   Available ICICI symbols: {icici_symbols[:5]}...")
        
        # Fetch historical data
        from datetime import datetime, timedelta
        to_date = datetime.now()
        from_date = to_date - timedelta(days=30)
        
        if "ICICIBANK" in zerodha_client.symbol_token_map:
            instrument_token = zerodha_client.symbol_token_map["ICICIBANK"]
            historical_data = zerodha_client.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date.strftime("%Y-%m-%d %H:%M:%S"),
                to_date=to_date.strftime("%Y-%m-%d %H:%M:%S"),
                interval="day"
            )
            print(f"✅ Loaded {len(historical_data)} bars of historical data")
        else:
            print("❌ ICICIBANK not found in instruments")
            return
    except Exception as e:
        print(f"❌ Error loading historical data: {str(e)}")
        return
        
    # Check that we're using enhanced processor
    if hasattr(processor, 'get_indicator_stats'):
        print("✅ Using EnhancedBarProcessor")
    else:
        print("❌ Not using EnhancedBarProcessor!")
        return
    
    # Process some bars
    print(f"\n3️⃣ Processing first 100 bars...")
    
    results = []
    filter_pass_count = 0
    
    for i in range(min(100, len(historical_data))):
        bar = historical_data[i]
        
        try:
            result = processor.process_bar(
                bar['open'], bar['high'], bar['low'], 
                bar['close'], bar.get('volume', 0)
            )
            
            if result:
                results.append(result)
                
                # Count filter passes
                if all(result.filter_states.values()):
                    filter_pass_count += 1
                    
                # Print every 20th bar
                if (i + 1) % 20 == 0:
                    print(f"   Bar {i+1}: Filters={result.filter_states}, "
                          f"All Pass={all(result.filter_states.values())}")
                          
        except Exception as e:
            print(f"❌ Error processing bar {i}: {str(e)}")
            import traceback
            traceback.print_exc()
            return
    
    # Show results
    print(f"\n4️⃣ Results Summary:")
    print(f"   Total bars processed: {len(results)}")
    print(f"   Bars where all filters passed: {filter_pass_count}")
    if len(results) > 0:
        print(f"   Filter pass rate: {filter_pass_count/len(results)*100:.1f}%")
    else:
        print(f"   Filter pass rate: 0.0%")
    
    # Get indicator stats
    stats = processor.get_indicator_stats()
    print(f"\n5️⃣ Indicator Stats:")
    print(f"   Total indicators created: {stats['total_indicators']}")
    print(f"   Indicator types: {stats['by_type']}")
    
    # Show individual filter performance
    if len(results) > 0:
        print(f"\n6️⃣ Individual Filter Performance:")
        volatility_passes = sum(1 for r in results if r.filter_states.get('volatility', False))
        regime_passes = sum(1 for r in results if r.filter_states.get('regime', False))
        adx_passes = sum(1 for r in results if r.filter_states.get('adx', False))
        
        print(f"   Volatility: {volatility_passes}/{len(results)} ({volatility_passes/len(results)*100:.1f}%)")
        print(f"   Regime: {regime_passes}/{len(results)} ({regime_passes/len(results)*100:.1f}%)")
        print(f"   ADX: {adx_passes}/{len(results)} ({adx_passes/len(results)*100:.1f}%)")
        print(f"   All Pass: {filter_pass_count}/{len(results)} ({filter_pass_count/len(results)*100:.1f}%)")
    
    print("\n✅ Enhanced processor test completed successfully!")

if __name__ == "__main__":
    test_enhanced_processor()
