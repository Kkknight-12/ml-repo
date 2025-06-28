"""
Quick verification script to check data availability for all test stocks
"""

from data.smart_data_manager import SmartDataManager

def verify_stock_data():
    """Check if we have sufficient data for all stocks"""
    data_manager = SmartDataManager()
    stocks = ['RELIANCE', 'INFY', 'TCS', 'HDFC', 'ICICIBANK', 'WIPRO', 'AXISBANK', 'KOTAKBANK']
    
    print("Verifying data availability for 180-day backtest...")
    print("="*60)
    
    for symbol in stocks:
        try:
            df = data_manager.get_data(symbol, interval='5minute', days=180)
            if df is not None:
                print(f"{symbol:>10}: {len(df):>6} bars | {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
            else:
                print(f"{symbol:>10}: NO DATA")
        except Exception as e:
            print(f"{symbol:>10}: ERROR - {str(e)}")
    
    print("="*60)
    print("\nMinimum required bars for ML warmup: 2000")
    print("Recommended bars for 180-day test: 8000+")

if __name__ == "__main__":
    verify_stock_data()