#!/usr/bin/env python3
"""
Test ML Array Persistence
=========================

Check if predictions array persists across bars
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import json

from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.fivemin_optimized_settings import FIVEMIN_BALANCED
from data.cache_manager import MarketDataCache

# Set up access token
if os.path.exists('.kite_session.json'):
    with open('.kite_session.json', 'r') as f:
        session_data = json.load(f)
        access_token = session_data.get('access_token')
        os.environ['KITE_ACCESS_TOKEN'] = access_token


def test_persistence():
    """Test ML array persistence"""
    
    print("🔍 TESTING ML ARRAY PERSISTENCE")
    print("="*80)
    
    # Get data
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    cache = MarketDataCache()
    df = cache.get_cached_data(symbol, start_date, end_date, "5minute")
    
    if df is None or df.empty:
        print("No data available")
        return
    
    # Create processor
    processor = EnhancedBarProcessor(FIVEMIN_BALANCED, symbol, "5minute")
    ml_model = processor.ml_model
    
    # Process bars and track predictions array
    print("\n🔄 Processing bars and tracking predictions array...")
    
    predictions_history = []
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if i > 2010:  # Process a few bars past warmup
            break
            
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # Track state at key bars
        if i in [1999, 2000, 2001, 2002, 2003, 2004, 2005]:
            print(f"\n📍 Bar {i}:")
            print(f"   Predictions array: {ml_model.predictions}")
            print(f"   Distances array size: {len(ml_model.distances)}")
            print(f"   ML prediction value: {result.prediction}")
            print(f"   self.prediction: {ml_model.prediction}")
            
            # Check if sum matches
            if ml_model.predictions:
                manual_sum = sum(ml_model.predictions)
                print(f"   Manual sum: {manual_sum}")
                print(f"   Sum matches self.prediction: {manual_sum == ml_model.prediction}")


if __name__ == "__main__":
    test_persistence()