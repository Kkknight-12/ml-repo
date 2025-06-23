"""
Quick script to find ICICI related symbols
"""
import sys
import os
import json
sys.path.append('.')

from data.zerodha_client import ZerodhaClient

def find_icici_symbols():
    """Find all ICICI related symbols"""
    print("🔍 Finding ICICI related symbols...")
    
    try:
        # Initialize Zerodha client
        if os.path.exists('.kite_session.json'):
            with open('.kite_session.json', 'r') as f:
                session_data = json.load(f)
                access_token = session_data.get('access_token')
            
            os.environ['KITE_ACCESS_TOKEN'] = access_token
            zerodha_client = ZerodhaClient()
            print("✅ Zerodha connection established")
        else:
            print("❌ No access token found")
            return
            
        # Get NSE instruments
        instruments = zerodha_client.get_instruments("NSE")
        
        # Find ICICI symbols
        icici_symbols = []
        for inst in instruments:
            symbol = inst['tradingsymbol']
            if 'ICICI' in symbol.upper():
                icici_symbols.append({
                    'symbol': symbol,
                    'name': inst.get('name', ''),
                    'instrument_type': inst.get('instrument_type', ''),
                    'segment': inst.get('segment', '')
                })
        
        # Sort and display
        icici_symbols.sort(key=lambda x: x['symbol'])
        
        print(f"\n📊 Found {len(icici_symbols)} ICICI related symbols:")
        print("-" * 80)
        print(f"{'Symbol':<20} {'Name':<40} {'Type':<10} {'Segment':<10}")
        print("-" * 80)
        
        for sym in icici_symbols[:20]:  # Show first 20
            print(f"{sym['symbol']:<20} {sym['name'][:40]:<40} {sym['instrument_type']:<10} {sym['segment']:<10}")
            
        # Look for exact matches
        print("\n🎯 Equity symbols (for trading):")
        equity_symbols = [s for s in icici_symbols if s['instrument_type'] == 'EQ']
        for sym in equity_symbols:
            print(f"  - {sym['symbol']}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    find_icici_symbols()
