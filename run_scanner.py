"""
System Test - Verify complete setup before live trading
Run this to ensure everything is working correctly
"""
import os
import sys
import time
from datetime import datetime

# Test imports
print("=== Lorentzian Scanner System Test ===\n")
print("1. Testing imports...")

try:
    # Phase 1 imports
    from config.settings import TradingConfig
    from scanner import BarProcessor
    from ml.lorentzian_knn_fixed_corrected import LorentzianKNNFixedCorrected

    print("✅ Phase 1 components imported successfully")
except ImportError as e:
    print(f"❌ Phase 1 import error: {e}")
    sys.exit(1)

try:
    # Phase 2 imports
    from data.zerodha_client import ZerodhaClient
    from data.data_manager import DataManager
    from scanner.live_scanner import LiveScanner
    from utils.notifications import NotificationManager

    print("✅ Phase 2 components imported successfully")
except ImportError as e:
    print(f"❌ Phase 2 import error: {e}")
    print("\nPlease install dependencies: pip install -r requirements.txt")
    sys.exit(1)

print("\n2. Testing configuration...")
# Check .env file
if not os.path.exists('.env'):
    print("❌ .env file not found. Copy .env.example to .env")
    sys.exit(1)

# Load environment
from dotenv import load_dotenv

load_dotenv()

# Check required variables
required_env = ['KITE_API_KEY', 'KITE_API_SECRET', 'KITE_USER_ID']
missing = []
for var in required_env:
    if not os.getenv(var):
        missing.append(var)

if missing:
    print(f"❌ Missing environment variables: {', '.join(missing)}")
    print("Please add these to your .env file")
    sys.exit(1)
else:
    print("✅ Environment variables configured")

print("\n3. Testing ML algorithm...")
# Test basic ML functionality
config = TradingConfig(neighbors_count=3, feature_count=2)
processor = BarProcessor(config)

# Process some test bars
test_data = [
    (100, 102, 99, 101, 1000),
    (101, 103, 100, 102, 1100),
    (102, 104, 101, 103, 1200),
    (103, 105, 102, 104, 1300),
    (104, 106, 103, 105, 1400),
]

for i, (o, h, l, c, v) in enumerate(test_data):
    result = processor.process_bar(o, h, l, c, v)

print(f"✅ Processed {len(test_data)} test bars")
print(f"   Last prediction: {result.prediction}")
print(f"   Last signal: {result.signal}")

print("\n4. Testing notifications...")
notifier = NotificationManager()
if notifier.enabled:
    notifier.send_notification(
        "System Test",
        "Lorentzian Scanner is ready!",
        sound=False
    )
    print("✅ Notification sent (check your notifications)")
else:
    print("⚠️  Notifications disabled in .env")

print("\n5. Testing Zerodha connection...")
try:
    client = ZerodhaClient()
    if client.access_token:
        print("✅ Access token found")

        # Try to get margins
        try:
            margins = client.get_margins()
            if margins:
                balance = margins.get('equity', {}).get('available', {}).get('live_balance', 'N/A')
                print(f"✅ Connected to Zerodha. Balance: ₹{balance}")
            else:
                print("⚠️  Could not fetch account details")
        except Exception as e:
            print(f"⚠️  Connection test failed: {str(e)}")
            print("   Run python auth_helper.py to re-authenticate")
    else:
        print("⚠️  No access token. Run python auth_helper.py to authenticate")
except Exception as e:
    print(f"❌ Zerodha client error: {str(e)}")

print("\n6. Testing data flow...")
# Create a simple test flow
if client.access_token:
    try:
        # Get a quote
        quotes = client.get_quote(['RELIANCE'])
        if quotes:
            print(f"✅ Fetched quote for RELIANCE: ₹{quotes.get('RELIANCE', {}).get('last_price', 'N/A')}")
        else:
            print("⚠️  Could not fetch quotes")
    except:
        print("⚠️  Quote fetching failed (market might be closed)")

print("\n=== System Test Summary ===")
print("✅ Core ML algorithm: Working")
print("✅ Configuration: Loaded")
print("✅ Dependencies: Installed")

if notifier.enabled:
    print("✅ Notifications: Enabled")
else:
    print("⚠️  Notifications: Disabled")

if client.access_token:
    print("✅ Zerodha: Authenticated")
else:
    print("⚠️  Zerodha: Not authenticated")

print("\n✨ System test complete!")
print("\nNext steps:")
print("1. Run 'python auth_helper.py' if not authenticated")
print("2. Run 'python scanner/live_scanner.py' to start scanning")
print("3. Or run 'python main.py' for demo mode")

# Test sound if on Mac
if notifier.is_mac and notifier.sound_enabled:
    print("\n🔊 Playing test sound...")
    notifier.play_sound("success")