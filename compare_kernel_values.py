"""
Compare Kernel Values with TradingView
Focuses on kernel regression values for easy comparison
"""
import os
import sys
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.kernel_functions import rational_quadratic, gaussian


def compare_kernel_values():
    """
    Calculate kernel values for manual comparison with TradingView
    """
    print("=" * 60)
    print("🔍 Kernel Value Comparison Tool")
    print("=" * 60)
    
    # Test with sample data (you can modify these)
    # Enter your last 50 close prices from ICICI Bank here
    sample_closes = [
        # Add your close prices here, newest first
        # Example: 1050.50, 1048.25, 1045.00, ...
    ]
    
    # If no manual data, try to load from CSV
    if not sample_closes:
        filename = "NSE_ICICIBANK_1D.csv"
        if os.path.exists(filename):
            print(f"Loading data from {filename}...")
            closes = []
            with open(filename, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        closes.append(float(row.get('Close', row.get('close', 0))))
                    except:
                        continue
            
            # Reverse to get newest first
            sample_closes = list(reversed(closes))[-50:]  # Last 50 bars
            print(f"Loaded {len(sample_closes)} close prices")
        else:
            print("❌ No data available!")
            print("Either:")
            print("1. Add close prices to sample_closes in this script")
            print("2. Place NSE_ICICIBANK_1D.csv in project directory")
            return
    
    # Pine Script default parameters
    lookback = 8
    relative_weight = 8.0
    regression_level = 25
    lag = 2
    
    print(f"\n📊 Kernel Parameters:")
    print(f"  Lookback: {lookback}")
    print(f"  Relative Weight: {relative_weight}")
    print(f"  Regression Level: {regression_level}")
    print(f"  Lag: {lag}")
    
    # Calculate kernel values
    if len(sample_closes) >= lookback:
        # Rational Quadratic (yhat1 in Pine Script)
        yhat1 = rational_quadratic(sample_closes, lookback, relative_weight, regression_level)
        
        # Gaussian (yhat2 in Pine Script)
        yhat2 = gaussian(sample_closes, lookback - lag, regression_level)
        
        print(f"\n📈 Kernel Values:")
        print(f"  Current Close: {sample_closes[0]:.2f}")
        print(f"  RQ Kernel (yhat1): {yhat1:.4f}")
        print(f"  Gaussian (yhat2): {yhat2:.4f}")
        print(f"  Difference: {(yhat2 - yhat1):.4f}")
        
        # Check trend
        print(f"\n📊 Kernel Analysis:")
        if yhat2 >= yhat1:
            print("  Smoothed line ABOVE main line → Bullish")
        else:
            print("  Smoothed line BELOW main line → Bearish")
        
        # Calculate for last few bars to see trend
        print(f"\n📉 Historical Kernel Values (last 5 bars):")
        print("Bar  Close     RQ(yhat1)  Gauss(yhat2)  Diff    Trend")
        print("-" * 60)
        
        for i in range(min(5, len(sample_closes) - lookback)):
            subset = sample_closes[i:]
            rq = rational_quadratic(subset, lookback, relative_weight, regression_level)
            g = gaussian(subset, lookback - lag, regression_level)
            diff = g - rq
            trend = "Bull" if g >= rq else "Bear"
            
            print(f"{i:3d}  {subset[0]:8.2f}  {rq:9.4f}  {g:11.4f}  {diff:7.4f}  {trend}")
    
    print("\n💡 How to Compare with TradingView:")
    print("1. In TradingView, add the kernel regression lines to chart")
    print("2. Hover over the latest bar")
    print("3. Check the values of:")
    print("   - Kernel Regression Estimate (main line)")
    print("   - Second kernel line (if smoothing enabled)")
    print("4. Values should match within 0.01-0.02 difference")
    print("\n⚠️  Note: Small differences are normal due to:")
    print("   - Floating point precision")
    print("   - Bar indexing differences")
    print("   - Data alignment")


if __name__ == "__main__":
    compare_kernel_values()
