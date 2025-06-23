"""
Zerodha Data Fetcher and TradingView Comparison Tool
Fetches ICICIBANK 1D data and provides detailed comparison
"""
import os
import sys
import csv
from datetime import datetime, timedelta
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.zerodha_client import ZerodhaClient
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor


class TradingViewComparator:
    """Compare Python implementation with TradingView signals"""
    
    def __init__(self):
        self.zerodha = None
        self.processor = None
        self.data = []
        
    def setup_zerodha(self):
        """Initialize Zerodha client"""
        print("🔐 Setting up Zerodha connection...")
        
        # Check for saved token
        token_file = '.zerodha_token.json'
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                token_data = json.load(f)
                access_token = token_data.get('access_token')
                
            if access_token:
                self.zerodha = ZerodhaClient()
                self.zerodha.set_access_token(access_token)
                print("✅ Using saved access token")
                return True
        
        print("❌ No access token found. Please run auth_helper.py first")
        return False
    
    def fetch_icici_data(self, days=300):
        """Fetch ICICIBANK daily data from Zerodha"""
        print(f"\n📊 Fetching {days} days of ICICIBANK data...")
        
        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        
        # Fetch historical data
        instrument_token = 1270529  # ICICIBANK token
        
        try:
            historical = self.zerodha.get_historical_data(
                instrument_token=instrument_token,
                from_date=from_date.strftime("%Y-%m-%d"),
                to_date=to_date.strftime("%Y-%m-%d"),
                interval="day"
            )
            
            if historical:
                self.data = historical
                print(f"✅ Fetched {len(historical)} bars")
                
                # Save to CSV for reference
                self.save_to_csv(historical)
                return True
            else:
                print("❌ No data received")
                return False
                
        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            return False
    
    def save_to_csv(self, data):
        """Save fetched data to CSV"""
        filename = "ICICIBANK_zerodha_data.csv"
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
            
            for bar in data:
                writer.writerow([
                    bar['date'].strftime("%Y-%m-%d") if hasattr(bar['date'], 'strftime') else bar['date'],
                    bar['open'],
                    bar['high'],
                    bar['low'],
                    bar['close'],
                    bar['volume']
                ])
        
        print(f"📁 Data saved to {filename}")
    
    def process_with_correct_settings(self):
        """Process data with proper bar index handling"""
        print("\n🔧 Processing with correct settings...")
        
        # Configuration matching TradingView
        config = TradingConfig(
            # Core ML settings
            neighbors_count=8,
            max_bars_back=2000,  # Important!
            feature_count=5,
            
            # Kernel settings
            use_kernel_filter=True,
            kernel_lookback=8,
            kernel_relative_weight=8.0,
            kernel_regression_level=25,
            use_kernel_smoothing=True,
            kernel_lag=2,
            
            # Dynamic exits
            use_dynamic_exits=False,  # Start with fixed exits
            
            # Filters
            use_volatility_filter=True,
            use_regime_filter=True,
            use_adx_filter=False,
            
            # MA filters
            use_ema_filter=False,
            use_sma_filter=False,
            
            # Features (Pine Script defaults)
            features={
                "f1": ("RSI", 14, 1),
                "f2": ("WT", 10, 11),
                "f3": ("CCI", 20, 1),
                "f4": ("ADX", 20, 2),
                "f5": ("RSI", 9, 1)
            }
        )
        
        # CRITICAL: Set total bars correctly!
        total_bars = len(self.data)
        self.processor = BarProcessor(config, total_bars=total_bars)
        
        print(f"📊 Total bars: {total_bars}")
        print(f"🎯 ML will start after bar: {self.processor.max_bars_back_index}")
        
        # Process all bars
        results = []
        signals = []
        kernel_tracking = []
        
        for i, bar in enumerate(self.data):
            result = self.processor.process_bar(
                bar['open'],
                bar['high'],
                bar['low'],
                bar['close'],
                bar.get('volume', 0)
            )
            
            if result:
                # Store all results for detailed comparison
                results.append({
                    'bar': i,
                    'date': bar['date'],
                    'open': bar['open'],
                    'high': bar['high'],
                    'low': bar['low'],
                    'close': bar['close'],
                    'prediction': result.prediction,
                    'signal': result.signal,
                    'filters': result.filter_states,
                    'ml_active': i >= self.processor.max_bars_back_index
                })
                
                # Track signals
                if result.start_long_trade or result.start_short_trade:
                    signals.append({
                        'bar': i,
                        'date': bar['date'],
                        'type': 'BUY' if result.start_long_trade else 'SELL',
                        'price': bar['close'],
                        'prediction': result.prediction,
                        'strength': result.prediction_strength,
                        'sl': result.stop_loss,
                        'tp': result.take_profit
                    })
                
                # Track kernel values periodically
                if i % 10 == 0 and i >= 50:  # Every 10 bars after warmup
                    from core.kernel_functions import calculate_kernel_values
                    
                    source_values = []
                    for j in range(min(100, len(self.processor.close_values))):
                        source_values.append(self.processor.close_values[j])
                    
                    if len(source_values) >= config.kernel_lookback:
                        yhat1, _, yhat2, _ = calculate_kernel_values(
                            source_values,
                            config.kernel_lookback,
                            config.kernel_relative_weight,
                            config.kernel_regression_level,
                            config.kernel_lag
                        )
                        
                        kernel_tracking.append({
                            'bar': i,
                            'date': bar['date'],
                            'close': bar['close'],
                            'yhat1': yhat1,
                            'yhat2': yhat2
                        })
        
        return results, signals, kernel_tracking
    
    def create_comparison_report(self, results, signals, kernel_tracking):
        """Create detailed comparison report"""
        print("\n📋 Creating Comparison Report...")
        
        # Save detailed results
        with open('comparison_detailed.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Bar', 'Date', 'Open', 'High', 'Low', 'Close',
                'Prediction', 'Signal', 'ML_Active', 'Volatility_Filter',
                'Regime_Filter', 'ADX_Filter'
            ])
            
            for r in results[-100:]:  # Last 100 bars for manageable size
                writer.writerow([
                    r['bar'], r['date'], r['open'], r['high'], r['low'], r['close'],
                    r['prediction'], r['signal'], r['ml_active'],
                    r['filters'].get('volatility', ''),
                    r['filters'].get('regime', ''),
                    r['filters'].get('adx', '')
                ])
        
        # Save signals
        with open('comparison_signals.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Bar', 'Date', 'Type', 'Price', 'Prediction', 'Strength', 'SL', 'TP'])
            
            for sig in signals:
                writer.writerow([
                    sig['bar'], sig['date'], sig['type'], sig['price'],
                    sig['prediction'], f"{sig['strength']:.4f}",
                    sig.get('sl', ''), sig.get('tp', '')
                ])
        
        # Save kernel values
        with open('comparison_kernels.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Bar', 'Date', 'Close', 'RQ_Kernel', 'Gaussian_Kernel', 'Difference'])
            
            for k in kernel_tracking:
                writer.writerow([
                    k['bar'], k['date'], k['close'],
                    f"{k['yhat1']:.4f}", f"{k['yhat2']:.4f}",
                    f"{k['yhat2'] - k['yhat1']:.4f}"
                ])
        
        print("\n✅ Comparison files created:")
        print("  - comparison_detailed.csv (bar-by-bar data)")
        print("  - comparison_signals.csv (entry/exit signals)")
        print("  - comparison_kernels.csv (kernel values)")
        
        # Print summary
        print("\n📊 Summary:")
        print(f"  Total bars processed: {len(results)}")
        print(f"  ML started at bar: {self.processor.max_bars_back_index}")
        print(f"  Total signals: {len(signals)}")
        
        if signals:
            print("\n  Recent signals:")
            for sig in signals[-5:]:
                print(f"    {sig['date']}: {sig['type']} @ {sig['price']:.2f}")
    
    def compare_with_tradingview(self):
        """Guide for TradingView comparison"""
        print("\n" + "=" * 60)
        print("🔍 HOW TO COMPARE WITH TRADINGVIEW")
        print("=" * 60)
        
        print("\n1️⃣ In TradingView:")
        print("   - Add Lorentzian Classification indicator")
        print("   - Set these EXACT parameters:")
        print("     • Neighbors Count: 8")
        print("     • Max Bars Back: 2000")
        print("     • Feature Count: 5")
        print("     • Use Volatility Filter: ✓")
        print("     • Use Regime Filter: ✓")
        print("     • Use ADX Filter: ✗")
        print("     • Show Default Exits: ✓")
        print("     • Use Dynamic Exits: ✗")
        
        print("\n2️⃣ Check these values:")
        print("   a) Kernel Lines:")
        print("      - Note RQ kernel value on latest bar")
        print("      - Note Gaussian kernel value")
        print("      - Compare with comparison_kernels.csv")
        
        print("\n   b) Signals:")
        print("      - Note all Buy/Sell signals")
        print("      - Check dates and prices")
        print("      - Compare with comparison_signals.csv")
        
        print("\n   c) Prediction Values:")
        print("      - Enable 'Show Bar Prediction Values'")
        print("      - Note prediction numbers on bars")
        print("      - Compare with Prediction column in comparison_detailed.csv")
        
        print("\n3️⃣ Expected Differences:")
        print("   - Signal timing: ±1 bar is normal")
        print("   - Kernel values: ±0.01-0.02 is acceptable")
        print("   - ML should NOT generate signals before bar 2000")
        
        print("\n4️⃣ If Major Differences:")
        print("   - Verify all settings match exactly")
        print("   - Check feature parameters (RSI, WT, CCI, ADX)")
        print("   - Ensure same data range is used")
        print("   - Verify filters are configured identically")


def main():
    """Main comparison workflow"""
    comparator = TradingViewComparator()
    
    # Option 1: Use Zerodha data
    use_zerodha = input("Fetch fresh data from Zerodha? (y/n): ").lower() == 'y'
    
    if use_zerodha:
        if not comparator.setup_zerodha():
            print("Please run auth_helper.py first to login to Zerodha")
            return
        
        if not comparator.fetch_icici_data(300):
            print("Failed to fetch data")
            return
    else:
        # Option 2: Use existing CSV
        print("\nUsing existing CSV data...")
        # Load from your CSV
        filename = "NSE_ICICIBANK, 1D.csv"
        if not os.path.exists(filename):
            print(f"❌ File not found: {filename}")
            return
        
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
        comparator.data = data
    
    # Process data
    results, signals, kernel_tracking = comparator.process_with_correct_settings()
    
    # Create comparison files
    comparator.create_comparison_report(results, signals, kernel_tracking)
    
    # Show comparison guide
    comparator.compare_with_tradingview()


if __name__ == "__main__":
    main()
