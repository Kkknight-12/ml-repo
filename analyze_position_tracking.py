#!/usr/bin/env python3
"""
Analyze "Already in Position" Signal Blocks
==========================================

This script investigates why Pine Script blocks some signals with
"already in position" while Python generates them.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import sqlite3
from datetime import datetime
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from core.pine_functions import nz


def analyze_position_tracking():
    """Analyze position tracking and signal generation"""
    
    print("="*70)
    print("POSITION TRACKING ANALYSIS")
    print("="*70)
    
    # Initialize processor
    config = TradingConfig()
    processor = EnhancedBarProcessor(config, "ICICIBANK", "day")
    
    # Load data
    db_path = os.path.join("data_cache", "market_data.db")
    with sqlite3.connect(db_path) as conn:
        query = """
        SELECT date, open, high, low, close, volume
        FROM market_data
        WHERE symbol = 'ICICIBANK' AND interval = 'day'
        ORDER BY date
        """
        df = pd.read_sql_query(query, conn, parse_dates=['date'])
    
    print(f"\nProcessing {len(df)} bars...")
    
    # Track positions and signals
    position_tracker = {
        'current_position': 0,  # 0=flat, 1=long, -1=short
        'entry_bar': None,
        'entry_price': None,
        'signals': [],
        'blocked_signals': [],
        'position_history': []
    }
    
    # Process bars
    for idx, row in df.iterrows():
        result = processor.process_bar(
            nz(row['open'], row['close']),
            nz(row['high'], row['close']),
            nz(row['low'], row['close']),
            nz(row['close'], 0.0),
            nz(row['volume'], 0.0)
        )
        
        if result and result.bar_index >= config.max_bars_back:
            # Current position state
            prev_position = position_tracker['current_position']
            
            # Check for entry signals
            if result.start_long_trade:
                if position_tracker['current_position'] == 1:
                    # Already long - this would be blocked in Pine Script
                    position_tracker['blocked_signals'].append({
                        'bar': result.bar_index,
                        'date': row['date'],
                        'type': 'LONG_BLOCKED',
                        'reason': 'Already in long position',
                        'current_position': 'LONG',
                        'ml_prediction': result.prediction,
                        'signal': result.signal
                    })
                    print(f"\n⚠️  Bar {result.bar_index} - LONG signal blocked (already long)")
                else:
                    # Enter long position
                    position_tracker['current_position'] = 1
                    position_tracker['entry_bar'] = result.bar_index
                    position_tracker['entry_price'] = row['close']
                    position_tracker['signals'].append({
                        'bar': result.bar_index,
                        'date': row['date'],
                        'type': 'LONG_ENTRY',
                        'price': row['close'],
                        'ml_prediction': result.prediction
                    })
                    
            elif result.start_short_trade:
                if position_tracker['current_position'] == -1:
                    # Already short - this would be blocked in Pine Script
                    position_tracker['blocked_signals'].append({
                        'bar': result.bar_index,
                        'date': row['date'],
                        'type': 'SHORT_BLOCKED',
                        'reason': 'Already in short position',
                        'current_position': 'SHORT',
                        'ml_prediction': result.prediction,
                        'signal': result.signal
                    })
                    print(f"\n⚠️  Bar {result.bar_index} - SHORT signal blocked (already short)")
                else:
                    # Enter short position
                    position_tracker['current_position'] = -1
                    position_tracker['entry_bar'] = result.bar_index
                    position_tracker['entry_price'] = row['close']
                    position_tracker['signals'].append({
                        'bar': result.bar_index,
                        'date': row['date'],
                        'type': 'SHORT_ENTRY',
                        'price': row['close'],
                        'ml_prediction': result.prediction
                    })
            
            # Check for exit signals
            if result.end_long_trade and position_tracker['current_position'] == 1:
                # Exit long
                position_tracker['current_position'] = 0
                position_tracker['signals'].append({
                    'bar': result.bar_index,
                    'date': row['date'],
                    'type': 'LONG_EXIT',
                    'price': row['close']
                })
                
            elif result.end_short_trade and position_tracker['current_position'] == -1:
                # Exit short
                position_tracker['current_position'] = 0
                position_tracker['signals'].append({
                    'bar': result.bar_index,
                    'date': row['date'],
                    'type': 'SHORT_EXIT',
                    'price': row['close']
                })
            
            # Track position changes
            if position_tracker['current_position'] != prev_position:
                position_tracker['position_history'].append({
                    'bar': result.bar_index,
                    'date': row['date'],
                    'from': prev_position,
                    'to': position_tracker['current_position']
                })
    
    # Analysis results
    print(f"\n\n📊 ANALYSIS RESULTS")
    print(f"="*70)
    print(f"Total signals generated: {len(position_tracker['signals'])}")
    print(f"Blocked signals: {len(position_tracker['blocked_signals'])}")
    print(f"Position changes: {len(position_tracker['position_history'])}")
    
    if position_tracker['blocked_signals']:
        print(f"\n🚫 BLOCKED SIGNALS (Potential 'Already in Position' matches):")
        for blocked in position_tracker['blocked_signals']:
            print(f"\n   Bar {blocked['bar']} ({blocked['date'].strftime('%Y-%m-%d')}):")
            print(f"   - Type: {blocked['type']}")
            print(f"   - Reason: {blocked['reason']}")
            print(f"   - ML Prediction: {blocked['ml_prediction']:.2f}")
            print(f"   - Signal State: {blocked['signal']}")
    
    # Check for consecutive same-direction signals
    print(f"\n\n🔍 CONSECUTIVE SAME-DIRECTION SIGNALS:")
    print(f"="*70)
    
    consecutive_found = False
    for i in range(1, len(position_tracker['signals'])):
        curr = position_tracker['signals'][i]
        prev = position_tracker['signals'][i-1]
        
        # Check if we have two entries in same direction without exit
        if 'ENTRY' in curr['type'] and 'ENTRY' in prev['type']:
            if 'LONG' in curr['type'] and 'LONG' in prev['type']:
                print(f"\n⚠️  Consecutive LONG entries:")
                print(f"   1st: Bar {prev['bar']} ({prev['date'].strftime('%Y-%m-%d')})")
                print(f"   2nd: Bar {curr['bar']} ({curr['date'].strftime('%Y-%m-%d')})")
                consecutive_found = True
            elif 'SHORT' in curr['type'] and 'SHORT' in prev['type']:
                print(f"\n⚠️  Consecutive SHORT entries:")
                print(f"   1st: Bar {prev['bar']} ({prev['date'].strftime('%Y-%m-%d')})")
                print(f"   2nd: Bar {curr['bar']} ({curr['date'].strftime('%Y-%m-%d')})")
                consecutive_found = True
    
    if not consecutive_found:
        print("✅ No consecutive same-direction entries found")
    
    # SUMMARY
    print(f"\n\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    print(f"\n📌 KEY FINDINGS:")
    if len(position_tracker['blocked_signals']) > 0:
        print(f"1. Found {len(position_tracker['blocked_signals'])} signals that would be blocked by position check")
        print(f"2. These could explain the 'already in position' mismatches")
    else:
        print(f"1. No blocked signals found - position tracking may not be the issue")
        print(f"2. Need to check if Pine Script has different exit timing")
    
    print(f"\n📌 RECOMMENDATIONS:")
    print(f"1. Check if Pine Script uses different exit conditions")
    print(f"2. Verify if pyramiding is disabled in Pine Script")
    print(f"3. Compare exit timing between Pine and Python")
    
    return position_tracker


def check_pyramiding_settings():
    """Check if we're handling pyramiding correctly"""
    
    print(f"\n\n" + "="*70)
    print("PYRAMIDING ANALYSIS")
    print("="*70)
    
    print("\n📋 Pine Script Default Behavior:")
    print("- strategy.risk.max_cons_loss_days: Not set")
    print("- pyramiding: 0 (default - no pyramiding allowed)")
    print("- calc_on_order_fills: false")
    print("- calc_on_every_tick: false")
    
    print("\n📋 Python Implementation:")
    print("- Currently: Blocks new entries if already in position")
    print("- This matches Pine Script with pyramiding=0")
    
    print("\n⚠️  If Pine Script has pyramiding enabled:")
    print("- Multiple entries in same direction would be allowed")
    print("- Need to check Pine Script strategy settings")


if __name__ == "__main__":
    # Run position tracking analysis
    tracker = analyze_position_tracking()
    
    # Check pyramiding settings
    check_pyramiding_settings()
    
    print("\n\n💡 Next Steps:")
    print("1. Compare these findings with Pine Script output")
    print("2. Check if blocked signals match 'already in position' dates")
    print("3. Verify Pine Script strategy.position tracking")