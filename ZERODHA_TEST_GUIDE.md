# Zerodha Comprehensive Test Usage Guide

## Overview
The `test_zerodha_comprehensive.py` script performs a complete test of the Lorentzian Classification system using real market data from Zerodha.

## Prerequisites

1. **Zerodha Account**: Active trading account
2. **Kite API Subscription**: ₹2000/month for API access
3. **Historical Data API**: Additional ₹2000/month for historical data

## Setup Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Authentication
```bash
# First, create .env file with your credentials
cp .env.example .env

# Edit .env and add:
# KITE_API_KEY=your_api_key_here
# KITE_API_SECRET=your_api_secret_here

# Then authenticate
python auth_helper.py
```

### 3. Run the Comprehensive Test
```bash
python test_zerodha_comprehensive.py
```

## What the Test Does

### 1. Data Fetching
- Fetches 5 years (1825 days) of daily data
- Tests on RELIANCE, INFY, ICICIBANK
- Handles rate limits automatically
- Performs data quality checks

### 2. ML Label Analysis
- Analyzes price movements using Pine Script logic
- Shows label distribution (LONG/SHORT/NEUTRAL)
- Calculates movement strength statistics

### 3. ML Testing (Pine Script Style)
- **No train/test split** - continuous learning like Pine Script
- Bar-by-bar processing with sliding window
- Tracks ML predictions (-8 to +8 range)
- Monitors signal transitions and entries

### 4. Comprehensive Metrics
- ML prediction statistics
- Signal distribution analysis
- Filter performance metrics
- Trade entry/exit tracking
- Pine Script style state tracking

## Expected Output

```
🚀 COMPREHENSIVE LORENTZIAN CLASSIFICATION TEST
==================================================

📊 Fetching RELIANCE from 2019-01-20 to 2024-01-20
✅ Fetched 1234 days for RELIANCE
  📈 Price range: ₹1200.00 - ₹2800.00
  
🏷️ ML Label Analysis for RELIANCE:
  Direction Distribution:
    LONG: 612 (49.6%)
    SHORT: 598 (48.5%)
    NEUTRAL: 24 (1.9%)
    
🤖 ML TEST: RELIANCE
  Bar 500: Price=₹1856.50, ML=5.0, Signal=1, Filters=3/3
  
📊 DETAILED RESULTS: RELIANCE
  ML Predictions:
    Total predictions: 1180
    Range: -7.0 to 8.0
    Distribution: 52.3% positive, 47.7% negative
    
  Trading Signals:
    Signal distribution: LONG 35.2%, SHORT 32.8%, NEUTRAL 32.0%
    Signal transitions: 87
    
  Trade Entries:
    Total entries: 42 (34.1 per 1000 bars)
    Long entries: 23
    Short entries: 19
```

## Key Features Demonstrated

### 1. Pine Script Compatibility
- Uses `nz()` function for NA handling
- History referencing with `bars.close[n]`
- Series tracking for custom indicators
- Exact Pine Script default configuration

### 2. Bug Fixes Applied
- ✅ Sliding window approach (no total_bars dependency)
- ✅ Correct neighbor selection (i % 4 != 0)
- ✅ Proper array ordering (append, not insert)
- ✅ ML prediction vs signal separation
- ✅ Correct filter defaults (ADX OFF)

### 3. Enhanced Features
- EnhancedBarProcessor for Pine Script arrays
- Custom series tracking
- Comprehensive state management
- Detailed performance metrics

## Interpreting Results

### ML Predictions
- Range: -8 to +8 (sum of k-nearest neighbors)
- Positive: Bullish bias
- Negative: Bearish bias
- |pred| ≥ 4: Strong signals

### Signal Transitions
- Shows how often the system changes positions
- Too many: System may be overtrading
- Too few: Filters may be too restrictive

### Entry Signals
- Actual trading opportunities
- Should see reasonable frequency (20-50 per 1000 bars)
- Each entry includes signal strength

### Filter Performance
- Shows which filters are most/least restrictive
- Helps identify if adjustments needed
- All filters must pass for entry signal

## Troubleshooting

### "No access token found"
Run `python auth_helper.py` and complete authentication

### "Rate limit exceeded"
Wait a few seconds and retry. Script handles this automatically.

### "Symbol not found"
Ensure symbol is exact match (e.g., 'RELIANCE' not 'RELIANCE.NS')

### No entry signals
- Check filter pass rates
- May need to adjust thresholds
- Ensure sufficient data (need 50+ bars warmup)

## Next Steps

1. **Review Results**: Check if entry frequency matches expectations
2. **Adjust Filters**: If needed, modify filter thresholds
3. **Test More Symbols**: Add more stocks to test
4. **Live Trading**: Use `scanner/live_scanner.py` for real-time
5. **Backtest**: Compare with Pine Script results

## Important Notes

- This test uses **real market data** - results reflect actual market behavior
- System follows Pine Script exactly - no train/test split
- ML learns continuously from all available data
- Signal persistence is by design - prevents overtrading
- Daily timeframe provides stable, reliable signals
