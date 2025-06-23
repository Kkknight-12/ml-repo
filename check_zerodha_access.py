#!/usr/bin/env python3
"""
Check Zerodha API Status and Historical Data Access
===================================================
Purpose: Verify if your Zerodha account has historical data API access
Historical data API is a paid add-on (₹2000/month)
"""

from data.zerodha_client import ZerodhaClient
from dotenv import load_dotenv

def check_zerodha_access():
    """Check Zerodha API access and features"""
    
    print("=" * 60)
    print("🔍 Zerodha API Access Check")
    print("=" * 60)
    print()
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize client
        print("🔌 Connecting to Zerodha...")
        client = ZerodhaClient()
        print("✅ Connection successful!")
        print()
        
        # Check API status
        client.get_api_usage_summary()
        
        # Specific test for ICICIBANK
        print("\n🏦 Testing ICICIBANK data access...")
        print("-" * 40)
        
        # Load instruments
        print("Loading NSE instruments...")
        instruments = client.get_instruments("NSE")
        
        # Find ICICIBANK
        icici_found = False
        for inst in instruments:
            if inst['tradingsymbol'] == 'ICICIBANK':
                icici_found = True
                print(f"✅ ICICIBANK found:")
                print(f"   Token: {inst['instrument_token']}")
                print(f"   Exchange: {inst['exchange']}")
                print(f"   Segment: {inst['segment']}")
                break
        
        if not icici_found:
            print("❌ ICICIBANK not found in instruments!")
            return
        
        # Try fetching 1 day of 5-minute data
        print("\n📊 Testing 5-minute data fetch...")
        test_data = client.get_historical_data(
            symbol="ICICIBANK",
            interval="5minute",
            days=1
        )
        
        if test_data:
            print(f"✅ Successfully fetched {len(test_data)} candles")
            print(f"   First candle: {test_data[0]['date']}")
            print(f"   Last candle: {test_data[-1]['date']}")
            
            # Test larger fetch
            print("\n📊 Testing 45-day data fetch (for 2000 bars)...")
            large_data = client.get_historical_data(
                symbol="ICICIBANK",
                interval="5minute",
                days=45
            )
            
            if large_data:
                print(f"✅ Successfully fetched {len(large_data)} candles")
                print(f"   Date range: {large_data[0]['date']} to {large_data[-1]['date']}")
                
                if len(large_data) >= 2000:
                    print(f"✅ Sufficient data for testing (need 2000, got {len(large_data)})")
                else:
                    print(f"⚠️  Less than 2000 bars fetched. May need more days.")
            
        else:
            print("❌ No data returned - check historical data subscription")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        
        if "token" in str(e).lower():
            print("\n💡 Tip: Your access token may have expired.")
            print("   Run: python auth_helper.py")
        elif "historical" in str(e).lower() or "subscription" in str(e).lower():
            print("\n💡 Tip: Historical data API requires subscription")
            print("   Cost: ₹2000/month")
            print("   Subscribe at: https://kite.zerodha.com/")
        else:
            print("\n💡 Check your .env file for correct credentials")

if __name__ == "__main__":
    check_zerodha_access()
