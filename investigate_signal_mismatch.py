#!/usr/bin/env python3
"""
Investigation Script: Pine Script vs Python Signal Mismatch
===========================================================

This script investigates why Python signals don't match Pine Script signals.
It performs detailed analysis of:
1. Signal generation logic differences
2. Filter calculation differences
3. ML prediction differences
4. Data alignment issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime
import csv
from typing import Dict, List, Tuple

# Import our modules
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from data.zerodha_client import ZerodhaClient
import json


class SignalMismatchInvestigator:
    """Investigate signal mismatches between Pine Script and Python"""
    
    def __init__(self):
        self.config = TradingConfig(
            # Pine Script defaults
            neighbors_count=8,
            max_bars_back=2000,
            feature_count=5,
            color_compression=1,
            source='close',
            use_volatility_filter=True,
            use_regime_filter=True,
            use_adx_filter=False,
            regime_threshold=-0.1,
            adx_threshold=20,
            use_kernel_filter=True,
            use_kernel_smoothing=False,
            kernel_lookback=8,
            kernel_relative_weight=8.0,
            kernel_regression_level=25,
            kernel_lag=2,
            use_ema_filter=False,
            ema_period=200,
            use_sma_filter=False,
            sma_period=200,
            show_bar_colors=True,
            show_bar_predictions=True,
            use_atr_offset=False,
            bar_predictions_offset=0.0,
            show_exits=False,
            use_dynamic_exits=False
        )
        
    def load_pine_script_signals(self, symbol: str) -> Dict[str, Tuple[str, float]]:
        """Load Pine Script signals from CSV"""
        pine_csv = f"archive/data_files/NSE_{symbol}, 1D.csv"
        
        if not os.path.exists(pine_csv):
            print(f"❌ Pine Script CSV not found: {pine_csv}")
            return {}
            
        signals = {}
        with open(pine_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row['time']
                if row['Buy'] != 'NaN':
                    signals[date] = ('BUY', float(row['Buy']))
                elif row['Sell'] != 'NaN':
                    signals[date] = ('SELL', float(row['Sell']))
                    
        print(f"✅ Loaded {len(signals)} Pine Script signals")
        return signals
    
    def load_python_signals(self, csv_path: str) -> Dict[str, Tuple[str, float]]:
        """Load Python signals from CSV"""
        if not os.path.exists(csv_path):
            print(f"❌ Python CSV not found: {csv_path}")
            return {}
            
        signals = {}
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row['time']
                if row['Buy'] != 'NaN':
                    signals[date] = ('BUY', float(row['Buy']))
                elif row['Sell'] != 'NaN':
                    signals[date] = ('SELL', float(row['Sell']))
                    
        print(f"✅ Loaded {len(signals)} Python signals")
        return signals
    
    def analyze_signal_differences(self, pine_signals: Dict, python_signals: Dict, df: pd.DataFrame):
        """Detailed analysis of signal differences"""
        print("\n" + "="*70)
        print("📊 DETAILED SIGNAL ANALYSIS")
        print("="*70)
        
        # Create date lookup for price data
        date_price_map = {}
        for idx, row in df.iterrows():
            date_str = row['date'].strftime('%Y-%m-%d')
            date_price_map[date_str] = {
                'open': row['open'],
                'high': row['high'], 
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume']
            }
        
        # 1. Analyze Pine Script signals
        print("\n📌 Pine Script Signals Analysis:")
        for date, (signal_type, price) in sorted(pine_signals.items()):
            if date in date_price_map:
                prices = date_price_map[date]
                print(f"\n{date}: {signal_type} @ ₹{price:.2f}")
                print(f"  OHLC: O={prices['open']:.2f}, H={prices['high']:.2f}, "
                      f"L={prices['low']:.2f}, C={prices['close']:.2f}")
                
                # Check which price Pine Script used
                if signal_type == 'BUY':
                    if abs(price - prices['low']) < 0.01:
                        print(f"  ✓ Using LOW price for BUY")
                    elif abs(price - prices['close']) < 0.01:
                        print(f"  ⚠️ Using CLOSE price for BUY (not LOW)")
                    else:
                        print(f"  ❌ Price doesn't match any OHLC value")
                        
                elif signal_type == 'SELL':
                    if abs(price - prices['high']) < 0.01:
                        print(f"  ✓ Using HIGH price for SELL")
                    elif abs(price - prices['close']) < 0.01:
                        print(f"  ⚠️ Using CLOSE price for SELL (not HIGH)")
                    else:
                        print(f"  ❌ Price doesn't match any OHLC value")
        
        # 2. Compare matching and non-matching signals
        print("\n" + "="*70)
        print("🔍 SIGNAL COMPARISON")
        print("="*70)
        
        # Find exact matches
        matching_dates = set(pine_signals.keys()) & set(python_signals.keys())
        pine_only_dates = set(pine_signals.keys()) - set(python_signals.keys())
        python_only_dates = set(python_signals.keys()) - set(pine_signals.keys())
        
        print(f"\n📊 Summary:")
        print(f"  Dates with signals in both: {len(matching_dates)}")
        print(f"  Pine Script only: {len(pine_only_dates)}")
        print(f"  Python only: {len(python_only_dates)}")
        
        # Analyze matching dates
        if matching_dates:
            print(f"\n✅ Matching Dates Analysis:")
            for date in sorted(matching_dates):
                pine_type, pine_price = pine_signals[date]
                py_type, py_price = python_signals[date]
                
                if pine_type == py_type:
                    print(f"  {date}: ✓ Same signal type ({pine_type})")
                    print(f"    Pine: ₹{pine_price:.2f}, Python: ₹{py_price:.2f}")
                else:
                    print(f"  {date}: ❌ Different signals!")
                    print(f"    Pine: {pine_type} @ ₹{pine_price:.2f}")
                    print(f"    Python: {py_type} @ ₹{py_price:.2f}")
        
        # 3. Analyze signal timing patterns
        print("\n" + "="*70)
        print("📅 SIGNAL TIMING ANALYSIS")
        print("="*70)
        
        # Check if signals are offset by days
        print("\n🔍 Checking for day offsets...")
        for pine_date in sorted(pine_only_dates)[:5]:  # Check first 5
            pine_type, pine_price = pine_signals[pine_date]
            
            # Check if Python has signal within ±3 days
            pine_dt = pd.to_datetime(pine_date)
            for offset in [-3, -2, -1, 1, 2, 3]:
                check_date = (pine_dt + pd.Timedelta(days=offset)).strftime('%Y-%m-%d')
                if check_date in python_signals:
                    py_type, py_price = python_signals[check_date]
                    print(f"\n  Pine {pine_date} ({pine_type}) might match Python {check_date} ({py_type})")
                    print(f"  Offset: {offset} days")
                    break
        
        return {
            'matching_dates': matching_dates,
            'pine_only_dates': pine_only_dates,
            'python_only_dates': python_only_dates
        }
    
    def trace_specific_signal(self, symbol: str, date_str: str, df: pd.DataFrame):
        """Trace why a signal was or wasn't generated on a specific date"""
        print(f"\n" + "="*70)
        print(f"🔬 TRACING SIGNAL GENERATION FOR {date_str}")
        print("="*70)
        
        # Find the bar index for this date
        bar_idx = None
        for idx, row in df.iterrows():
            if row['date'].strftime('%Y-%m-%d') == date_str:
                bar_idx = idx
                break
                
        if bar_idx is None:
            print(f"❌ Date {date_str} not found in data")
            return
            
        # Process bars up to and including this date
        processor = EnhancedBarProcessor(self.config, symbol, "day")
        
        print(f"\n📊 Processing {bar_idx + 1} bars up to {date_str}...")
        
        # Process each bar
        for idx in range(bar_idx + 1):
            row = df.iloc[idx]
            result = processor.process_bar(
                row['open'], row['high'], row['low'], row['close'], row['volume']
            )
            
            # Show details for the last few bars
            if idx >= bar_idx - 2:
                print(f"\n🔍 Bar {idx} ({row['date'].strftime('%Y-%m-%d')}):")
                print(f"  OHLC: {row['open']:.2f}, {row['high']:.2f}, {row['low']:.2f}, {row['close']:.2f}")
                
                if result:
                    print(f"  ML Prediction: {result.prediction}")
                    print(f"  Signal: {result.signal}")
                    print(f"  Filters: {result.filter_states}")
                    print(f"  Entry signals: Long={result.start_long_trade}, Short={result.start_short_trade}")
                    
                    # If this is our target date, show why signal was/wasn't generated
                    if idx == bar_idx:
                        print(f"\n📌 Signal Generation Analysis:")
                        print(f"  1. ML Prediction: {result.prediction} {'✓' if result.prediction != 0 else '❌'}")
                        print(f"  2. Filters passed: {all(result.filter_states.values())} "
                              f"{'✓' if all(result.filter_states.values()) else '❌'}")
                        print(f"  3. Signal changed: {result.signal != processor.signal_history[1] if len(processor.signal_history) > 1 else 'N/A'}")
                        print(f"  4. Is early flip: {result.is_early_signal_flip} {'❌' if result.is_early_signal_flip else '✓'}")
    
    def run_investigation(self, symbol: str, python_csv: str):
        """Run complete investigation"""
        print(f"\n" + "="*70)
        print(f"🔍 INVESTIGATING SIGNAL MISMATCH FOR {symbol}")
        print("="*70)
        
        # Load signals
        pine_signals = self.load_pine_script_signals(symbol)
        python_signals = self.load_python_signals(python_csv)
        
        if not pine_signals or not python_signals:
            print("❌ Cannot proceed without signal data")
            return
            
        # Load market data
        print(f"\n📊 Loading market data for analysis...")
        
        # Initialize Zerodha client
        if os.path.exists('.kite_session.json'):
            with open('.kite_session.json', 'r') as f:
                session_data = json.load(f)
                access_token = session_data.get('access_token')
                os.environ['KITE_ACCESS_TOKEN'] = access_token
                
        kite_client = ZerodhaClient(use_cache=True)
        kite_client.get_instruments("NSE")
        
        # Fetch data (will use cache)
        data = kite_client.get_historical_data(symbol, "day", days=3000)
        if not data:
            print("❌ Failed to fetch market data")
            return
            
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Analyze differences
        analysis = self.analyze_signal_differences(pine_signals, python_signals, df)
        
        # Trace specific signals
        print("\n" + "="*70)
        print("🔬 DETAILED SIGNAL TRACING")
        print("="*70)
        
        # Trace a Pine-only signal
        if analysis['pine_only_dates']:
            pine_only_date = sorted(analysis['pine_only_dates'])[0]
            print(f"\n1️⃣ Tracing Pine-only signal: {pine_only_date}")
            self.trace_specific_signal(symbol, pine_only_date, df)
        
        # Trace a matching signal
        if analysis['matching_dates']:
            matching_date = sorted(analysis['matching_dates'])[0]
            print(f"\n2️⃣ Tracing matching signal: {matching_date}")
            self.trace_specific_signal(symbol, matching_date, df)
        
        print("\n" + "="*70)
        print("✅ INVESTIGATION COMPLETE")
        print("="*70)


def main():
    """Run the investigation"""
    # Configuration
    SYMBOL = 'HDFCBANK'
    PYTHON_CSV = 'python_signals_HDFCBANK_20250625_010142.csv'
    
    # Create investigator
    investigator = SignalMismatchInvestigator()
    
    # Run investigation
    investigator.run_investigation(SYMBOL, PYTHON_CSV)


if __name__ == "__main__":
    main()