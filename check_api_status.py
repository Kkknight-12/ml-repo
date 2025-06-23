"""
Check Zerodha API Status and Limits
Run this to monitor your API usage
"""
import sys
sys.path.append('.')

from data.zerodha_client import ZerodhaClient

def main():
    print("=== Zerodha API Status Checker ===\n")
    
    try:
        # Initialize client
        client = ZerodhaClient()
        
        if not client.access_token:
            print("❌ No access token found. Please run auth_helper.py first")
            return
        
        # Get comprehensive API status
        client.get_api_usage_summary()
        
        # Additional checks
        print("\n=== Quick Tests ===")
        
        # Test quote API
        print("\nTesting Quote API...")
        quotes = client.get_quote(['RELIANCE'])
        if quotes:
            print(f"✓ Quote API working - RELIANCE LTP: ₹{quotes.get('RELIANCE', {}).get('last_price', 'N/A')}")
        else:
            print("❌ Quote API failed")
        
        # Test margins
        print("\nTesting Margins API...")
        margins = client.get_margins()
        if margins:
            balance = margins.get('equity', {}).get('available', {}).get('live_balance', 0)
            print(f"✓ Margins API working - Balance: ₹{balance:,.2f}")
        else:
            print("❌ Margins API failed")
            
        print("\n=== API Usage Tips ===")
        print("• Your current scan (16 stocks every 10 min) = ~96 calls/hour")
        print("• Well within rate limits! ✅")
        print("• Historical data loads only once per session")
        print("• WebSocket is more efficient for real-time data")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("Make sure you have authenticated with Zerodha first")

if __name__ == "__main__":
    main()
