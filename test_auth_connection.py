#!/usr/bin/env python3
"""
Test Zerodha Authentication and Connection
"""
import os
import json
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.zerodha_client import ZerodhaClient

def test_connection():
    """Test if Zerodha connection works"""
    print("="*60)
    print("🔐 Testing Zerodha Connection")
    print("="*60)
    
    # Check for saved session
    if os.path.exists('.kite_session.json'):
        print("\n✅ Found saved session file")
        with open('.kite_session.json', 'r') as f:
            session_data = json.load(f)
            print(f"   Access token: {session_data['access_token'][:10]}...")
            print(f"   Created at: {session_data['created_at']}")
        
        # Set token in environment
        os.environ['KITE_ACCESS_TOKEN'] = session_data['access_token']
        
        try:
            # Initialize client
            print("\n📡 Initializing Zerodha client...")
            client = ZerodhaClient(use_cache=True, cache_dir="data_cache")
            
            # Test profile
            print("\n👤 Getting profile...")
            profile = client.kite.profile()
            print(f"   User: {profile.get('user_name', 'Unknown')}")
            print(f"   Email: {profile.get('email', 'Unknown')}")
            print(f"   Broker: {profile.get('broker', 'Unknown')}")
            
            # Test quote
            print("\n📊 Testing market quote...")
            quotes = client.kite.quote(["NSE:RELIANCE"])
            if quotes:
                reliance = quotes.get("NSE:RELIANCE", {})
                print(f"   RELIANCE LTP: ₹{reliance.get('last_price', 'N/A')}")
                print(f"   Volume: {reliance.get('volume', 'N/A')}")
            
            print("\n✅ All tests passed! Connection is working.")
            return True
            
        except Exception as e:
            print(f"\n❌ Connection failed: {e}")
            print("\n💡 Try running auth_helper.py to get a new access token")
            return False
    else:
        print("\n❌ No saved session found")
        print("   Please run auth_helper.py first to authenticate")
        return False

if __name__ == "__main__":
    test_connection()