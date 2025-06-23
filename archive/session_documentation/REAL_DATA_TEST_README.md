# Real Market Data Test - Instructions

## Overview
This test fetches real market data from Zerodha for RELIANCE, INFY, and ICICIBANK using 1-day timeframe (5 years of history) to test our ML system with actual market movements.

## Prerequisites

1. **Zerodha Account**: You need an active Zerodha trading account
2. **Kite API Subscription**: Subscribe at https://developers.kite.trade/
3. **Historical Data API**: Additional ₹2000/month subscription required

## Setup Steps

### 1. Install Dependencies
```bash
pip install kiteconnect pandas numpy
```

### 2. Create .env File
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```
KITE_API_KEY=your_api_key_here
KITE_API_SECRET=your_api_secret_here
```

### 3. Authenticate with Zerodha
```bash
python auth_helper.py
```

This will:
- Open login URL in browser
- Ask you to paste redirect URL after login
- Save access token to `.kite_session.json`

### 4. Run the Test
```bash
python test_real_market_data.py
```

## What the Test Does

1. **Fetches Historical Data**:
   - 5 years of daily data for each stock
   - Analyzes price movements and ML label distribution

2. **Runs ML System**:
   - Uses EnhancedBarProcessor with Pine Script defaults
   - Tracks ML predictions, signals, and transitions
   - Shows filter performance

3. **Analyzes Results**:
   - ML prediction distribution
   - Signal transition frequency
   - Entry signal generation
   - Filter pass rates

## Expected Results

With real market data, you should see:
- **More Balanced ML Predictions**: Real markets have natural up/down cycles
- **Natural Signal Transitions**: Unlike synthetic data
- **Realistic Entry Signals**: Based on actual market movements
- **Better Filter Performance**: Filters designed for real volatility

## Fallback Mode

If Zerodha is not available, the script automatically runs with sample data that mimics real market behavior.

## Key Insights

The test demonstrates that:
1. Signal persistence is BY DESIGN - prevents overtrading
2. Real market data has sufficient volatility for signal transitions
3. ML predictions work correctly with actual price movements
4. Daily timeframe provides stable, reliable signals

## Troubleshooting

### "No access token found"
Run `python auth_helper.py` first

### "Insufficient Historical Data API"
You need the ₹2000/month historical data subscription

### "Rate limit exceeded"
Zerodha has rate limits:
- Historical API: 3 requests/second
- Wait a few seconds between runs

### No signal transitions
This would indicate:
- Filters too restrictive
- Need to adjust thresholds
- Check filter pass rates in output
