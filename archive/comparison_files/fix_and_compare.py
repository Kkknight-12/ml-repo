"""
Fix Bar Index Issue and Compare with TradingView
This script ensures ML starts at the correct bar
"""
import os
import sys
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor


def test_bar_index_fix():
    """Test with proper bar index handling"""
    print("=" * 60)
    print("🔧 Testing Bar Index Fix")
    print("=" * 60)
    
    # Load your data
    filename = "NSE_ICICIBANK, 1D.csv"
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        return
    
    # Load data
    data = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'date': row.get('Date', ''),
                'open': float(row.get('Open', 0)),
                'high': float(row.get('High', 0)),
                'low': float(row.get('Low', 0)),
                'close': float(row.get('Close', 0)),
                'volume': float(row.get('Volume', 0))
            })
    
    print(f"✅ Loaded {len(data)} bars")
    
    # Test different max_bars_back values
    test_configs = [
        (2000, "Pine Script Default"),
        (len(data), "Full Dataset"),
        (100, "Small Dataset Test")
    ]
    
    for max_bars_back, description in test_configs:
        print(f"\n📊 Testing with max_bars_back = {max_bars_back} ({description})")
        
        config = TradingConfig(
            max_bars_back=max_bars_back,
            neighbors_count=8,
            feature_count=5
        )
        
        # CRITICAL: Pass total_bars!
        processor = BarProcessor(config, total_bars=len(data))
        
        print(f"  Total bars: {len(data)}")
        print(f"  Max bars back: {max_bars_back}")
        print(f"  Expected ML start: bar {processor.max_bars_back_index}")
        
        # Process first few bars to check
        first_prediction_bar = None
        for i in range(min(len(data), max_bars_back + 10)):
            bar = data[i]
            result = processor.process_bar(
                bar['open'], bar['high'], bar['low'], bar['close'], bar['volume']
            )
            
            if result and result.prediction != 0 and first_prediction_bar is None:
                first_prediction_bar = i
                print(f"  ✅ First ML prediction at bar: {i}")
                break
        
        if first_prediction_bar is None and len(data) > max_bars_back:
            print(f"  ❌ No predictions found (check after bar {max_bars_back})")


def create_bar_by_bar_comparison():
    """Create detailed bar-by-bar comparison file"""
    print("\n" + "=" * 60)
    print("📊 Creating Bar-by-Bar Comparison")
    print("=" * 60)
    
    # Load data
    filename = "NSE_ICICIBANK, 1D.csv"
    data = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'date': row.get('Date', ''),
                'open': float(row.get('Open', 0)),
                'high': float(row.get('High', 0)),
                'low': float(row.get('Low', 0)),
                'close': float(row.get('Close', 0)),
                'volume': float(row.get('Volume', 0))
            })
    
    # Use small max_bars_back for testing (so we get signals earlier)
    config = TradingConfig(
        max_bars_back=50,  # Small value for testing
        neighbors_count=8,
        feature_count=5,
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,
        use_kernel_filter=True,
        use_dynamic_exits=False
    )
    
    processor = BarProcessor(config, total_bars=len(data))
    
    # Process all bars and save results
    with open('bar_by_bar_comparison.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Bar', 'Date', 'Close', 'Prediction', 'Signal',
            'Entry', 'Exit', 'Volatility', 'Regime', 'ADX',
            'ML_Active', 'Notes'
        ])
        
        for i, bar in enumerate(data):
            result = processor.process_bar(
                bar['open'], bar['high'], bar['low'], bar['close'], bar['volume']
            )
            
            if result:
                entry = ''
                if result.start_long_trade:
                    entry = 'BUY'
                elif result.start_short_trade:
                    entry = 'SELL'
                
                exit = ''
                if result.end_long_trade:
                    exit = 'EXIT_LONG'
                elif result.end_short_trade:
                    exit = 'EXIT_SHORT'
                
                ml_active = 'YES' if i >= processor.max_bars_back_index else 'NO'
                
                notes = ''
                if i == processor.max_bars_back_index:
                    notes = 'ML STARTS HERE'
                
                writer.writerow([
                    i,
                    bar['date'],
                    f"{bar['close']:.2f}",
                    f"{result.prediction:.0f}",
                    result.signal,
                    entry,
                    exit,
                    result.filter_states.get('volatility', ''),
                    result.filter_states.get('regime', ''),
                    result.filter_states.get('adx', ''),
                    ml_active,
                    notes
                ])
    
    print("✅ Created bar_by_bar_comparison.csv")
    print("\n📋 How to use this file:")
    print("1. Open in Excel/Google Sheets")
    print("2. In TradingView, go through each bar")
    print("3. Compare:")
    print("   - Prediction values (number on each bar)")
    print("   - Entry/Exit signals")
    print("   - Filter states")
    print("4. ML should only be active after 'ML STARTS HERE' row")


def suggest_better_comparison_methods():
    """Suggest better ways to compare with TradingView"""
    print("\n" + "=" * 60)
    print("💡 BETTER COMPARISON METHODS")
    print("=" * 60)
    
    print("\n1️⃣ Visual Signal Comparison:")
    print("   - Take screenshots of TradingView signals")
    print("   - Mark signal dates on a spreadsheet")
    print("   - Compare with Python signal dates")
    
    print("\n2️⃣ Kernel Value Spot Checks:")
    print("   - Pick 5-10 specific dates")
    print("   - Note kernel values in TradingView")
    print("   - Run Python for same dates")
    print("   - Values should match within 0.01")
    
    print("\n3️⃣ Create TradingView Alert Log:")
    print("   - Set alerts for all signals in TradingView")
    print("   - Export alert history")
    print("   - Compare with Python signals")
    
    print("\n4️⃣ Use Pine Script Debugging:")
    print("   - Add plot() statements in Pine Script:")
    print("     plot(prediction, \"Prediction\")")
    print("     plot(bar_index, \"Bar Index\")")
    print("   - Compare values with Python output")
    
    print("\n5️⃣ Focus on Key Metrics:")
    print("   - First ML prediction bar (should be >= max_bars_back)")
    print("   - Total number of signals")
    print("   - Signal dates (±1 bar is acceptable)")
    print("   - Kernel crossover points")


def main():
    """Run all comparison tests"""
    # Test bar index fix
    test_bar_index_fix()
    
    # Create detailed comparison
    create_bar_by_bar_comparison()
    
    # Suggest better methods
    suggest_better_comparison_methods()
    
    print("\n" + "=" * 60)
    print("🎯 CRITICAL POINTS FOR COMPARISON:")
    print("=" * 60)
    print("1. ML predictions should NOT start before max_bars_back")
    print("2. With max_bars_back=2000 and 300 bars of data:")
    print("   - You should see NO ML predictions!")
    print("   - Need at least 2000 bars for ML to start")
    print("3. Try setting max_bars_back=50 in both TV and Python")
    print("   - This will allow signals with your 300 bars")
    print("   - Easier to compare")


if __name__ == "__main__":
    main()
