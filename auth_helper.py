#!/usr/bin/env python3
"""
Zerodha Authentication Helper
Helps with login and storing access token
"""
import os
import json
from datetime import datetime
from kiteconnect import KiteConnect
from urllib.parse import urlparse, parse_qs
import webbrowser


def load_credentials():
    """Load API credentials from .env file"""
    credentials = {}
    
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    credentials[key] = value.strip('"').strip("'")
    
    return credentials


def save_session(access_token, api_key):
    """Save session data for reuse"""
    session_data = {
        'access_token': access_token,
        'api_key': api_key,
        'created_at': datetime.now().isoformat()
    }
    
    with open('.kite_session.json', 'w') as f:
        json.dump(session_data, f, indent=2)
    
    print("✅ Session saved to .kite_session.json")


def main():
    """Main authentication flow"""
    
    print("=" * 70)
    print("🔐 Zerodha Kite Authentication Helper")
    print("=" * 70)
    
    # Load credentials
    creds = load_credentials()
    
    if not creds.get('KITE_API_KEY') or not creds.get('KITE_API_SECRET'):
        print("\n❌ Missing API credentials!")
        print("\n📝 Please create a .env file with:")
        print("   KITE_API_KEY=your_api_key")
        print("   KITE_API_SECRET=your_api_secret")
        print("\n💡 Get your API credentials from: https://developers.kite.trade/")
        return
    
    api_key = creds['KITE_API_KEY']
    api_secret = creds['KITE_API_SECRET']
    
    # Initialize Kite
    kite = KiteConnect(api_key=api_key)
    
    # Check if we have a saved session
    if os.path.exists('.kite_session.json'):
        print("\n📋 Found existing session")
        with open('.kite_session.json', 'r') as f:
            session = json.load(f)
        
        print(f"   Created: {session['created_at']}")
        use_existing = input("\nUse existing session? (y/n): ").lower().strip()
        
        if use_existing == 'y':
            try:
                kite.set_access_token(session['access_token'])
                profile = kite.profile()
                print(f"\n✅ Logged in as: {profile['user_name']} ({profile['email']})")
                return
            except Exception as e:
                print(f"❌ Session expired or invalid: {str(e)}")
                print("Proceeding with new login...")
    
    # Get login URL
    login_url = kite.login_url()
    
    print(f"\n🌐 Please login at this URL:")
    print(f"   {login_url}")
    
    # Try to open in browser
    try:
        webbrowser.open(login_url)
        print("\n✅ Opened in your default browser")
    except:
        print("\n⚠️  Could not open browser automatically")
    
    print("\n📋 After login, you'll be redirected to a URL like:")
    print("   http://127.0.0.1/?request_token=xxxxx&action=login&status=success")
    
    redirect_url = input("\n🔗 Paste the complete redirect URL here: ").strip()
    
    try:
        # Parse the URL
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)
        
        if 'request_token' not in params:
            print("❌ Invalid URL - no request_token found")
            return
        
        request_token = params['request_token'][0]
        print(f"\n🔑 Request token: {request_token[:10]}...")
        
        # Generate session
        print("\n⏳ Generating access token...")
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]
        
        print(f"✅ Access token generated!")
        
        # Set access token
        kite.set_access_token(access_token)
        
        # Verify by fetching profile
        profile = kite.profile()
        print(f"\n👤 Logged in successfully!")
        print(f"   Name: {profile['user_name']}")
        print(f"   Email: {profile['email']}")
        print(f"   Broker: {profile['broker']}")
        
        # Save session
        save_session(access_token, api_key)
        
        print("\n✅ Authentication complete!")
        print("\n💡 You can now run test_real_market_data.py")
        
    except Exception as e:
        print(f"\n❌ Authentication failed: {str(e)}")
        print("\n🔍 Common issues:")
        print("   1. Request token expired (login again)")
        print("   2. Wrong API secret")
        print("   3. Invalid redirect URL format")


if __name__ == "__main__":
    main()
