#!/usr/bin/env python3
"""
Test ML Prediction Issue
========================

Direct test of ML predictions
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


def test_ml_predictions():
    """Test ML predictions directly"""
    
    print("🔍 TESTING ML PREDICTIONS DIRECTLY")
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
    
    print(f"\n📊 Total bars: {len(df)}")
    
    # Create processor
    processor = EnhancedBarProcessor(FIVEMIN_BALANCED, symbol, "5minute")
    
    # Hook into ML model
    ml_model = processor.ml_model
    
    # Process bars up to and past warmup
    print("\n🔄 Processing bars...")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        result = processor.process_bar(
            row['open'], row['high'], row['low'], 
            row['close'], row['volume']
        )
        
        # Check specific bars
        if i == 1999:
            print(f"\n📍 Bar 1999 (last warmup bar):")
            print(f"   ML Prediction: {result.prediction}")
            print(f"   ML predictions array size: {len(ml_model.predictions)}")
            print(f"   ML distances array size: {len(ml_model.distances)}")
            print(f"   Training labels: {len(ml_model.y_train_array)}")
        
        elif i == 2000:
            print(f"\n📍 Bar 2000 (first active bar):")
            print(f"   Bar index from BarData: {processor.bars.bar_index}")
            print(f"   ML Prediction: {result.prediction}")
            print(f"   ML predictions array: {ml_model.predictions}")
            print(f"   ML distances array: {ml_model.distances}")
            print(f"   Training labels: {len(ml_model.y_train_array)}")
            
            # Check if predict was called
            print(f"\n   Checking ML state after predict:")
            print(f"   self.prediction = {ml_model.prediction}")
            print(f"   len(self.predictions) = {len(ml_model.predictions)}")
        
        elif i == 2005:
            print(f"\n📍 Bar 2005:")
            print(f"   ML Prediction: {result.prediction}")
            print(f"   ML predictions array size: {len(ml_model.predictions)}")
            print(f"   Training labels: {len(ml_model.y_train_array)}")
            
            if len(ml_model.predictions) > 0:
                print(f"   Predictions array: {ml_model.predictions}")
            
            break
    
    # Final check
    print(f"\n📊 FINAL CHECK:")
    print(f"   Max neighbors seen: {ml_model.max_neighbors_seen}")
    print(f"   Current prediction: {ml_model.prediction}")
    print(f"   Predictions array: {ml_model.predictions}")


if __name__ == "__main__":
    test_ml_predictions()