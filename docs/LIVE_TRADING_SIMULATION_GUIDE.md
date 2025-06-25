# Live Trading Simulation Guide

## 🎯 Overview

The Lorentzian Classifier now includes powerful live market testing capabilities that allow you to simulate trading in real-time without risking actual capital. This guide covers everything you need to know about testing the system with live market data.

## 📋 Available Test Scripts

### 1. **test_live_market.py** - Standard Live Testing
Basic live market testing with default Pine Script settings and real-time signal generation.

### 2. **test_live_market_ai_enhanced.py** - AI-Enhanced Testing
Advanced version incorporating proven trading rules from the AI Trading Knowledge Base:
- Stock screening based on price range (₹50-₹500), volume, and momentum
- Time-based trading windows (no trades before 11 AM)
- Strict 2 trades per day limit
- Pattern quality scoring (minimum 7/10)
- Partial profit taking at ₹20/₹40 targets

## 🚀 Quick Start

### Prerequisites

1. **Install Dependencies**
```bash
pip install -r requirements.txt
# Or specifically:
pip install kiteconnect pandas numpy
```

2. **Authenticate with Zerodha**
```bash
python auth_helper.py
```
Follow the prompts to login and save your access token.

3. **Verify Connection**
```bash
python test_auth_connection.py
```

### Running Live Tests

**Standard Test (1 hour)**
```bash
python test_live_market.py
```

**AI-Enhanced Test with Custom Settings**
```bash
python test_live_market_ai_enhanced.py
# Enter capital when prompted (default: ₹10,000)
```

## 📊 What Happens During Testing

### 1. **Stock Selection Phase**
- **Standard Version**: Tests 15 major Nifty 50 stocks
- **AI-Enhanced**: Screens stocks based on:
  - Price range: ₹50-₹500
  - Volume: 2x+ average
  - Movement: 2%+ from open
  - Liquidity: ₹50L+ turnover

### 2. **Historical Data Warmup**
```
⏳ Warming up RELIANCE...
✅ RELIANCE: Processed 8640 historical bars
   Current bar index: 8640
   ML predictions started: True
```
- Fetches 30 days of 5-minute historical data
- Processes through the ML model to establish patterns
- Ensures indicators are properly initialized

### 3. **Live Signal Generation**
During market hours (9:15 AM - 3:30 PM), the system:
- Fetches live quotes every 5 seconds
- Processes through the Lorentzian ML algorithm
- Checks all filters (volatility, regime, kernel)
- Generates entry/exit signals

**Example Signal Output:**
```
🟢 LONG SIGNAL - INFY (Trade #1/2)
==================================================
📊 Entry Details:
   Price: ₹1614.50 x 12 shares
   Stop Loss: ₹1598.36 (-1.0%)
   Target 1: ₹1634.50 (+₹20) [50% exit]
   Target 2: ₹1654.50 (+₹40) [full exit]
📈 Signal Quality:
   ML Prediction: 6.2
   Pattern Score: 8.5/10
   Factors: Strong ML signal, Prime trading window, 3 filters passed
💰 Risk Management:
   Capital at Risk: ₹193.68
   Max Profit: ₹480.00
   Risk/Reward: 1:2.5
```

### 4. **Position Management**
The system automatically tracks and manages positions:

**Partial Exit at Target 1:**
```
💰 PARTIAL EXIT - INFY
   Exit: 6 shares @ ₹1634.50
   P&L: ₹120.00
   Remaining: 6 shares
   Stop moved to breakeven
```

**Full Position Close:**
```
✅ POSITION CLOSED - INFY
==================================================
📊 Exit Details:
   Exit Price: ₹1654.50
   Exit Reason: TARGET_2
   Hold Time: 45.2 minutes
💰 P&L Summary:
   Trade P&L: ₹360.00 (+2.47%)
   Daily P&L: ₹360.00
   Trades Today: 1/2
```

### 5. **Real-Time Status Display**
```
📊 🟢 PRIME WINDOW (85% win) | Active: 2 | Trades: 1/2 | P&L: ₹+360.00 | Win: 100% | 02:15:30 PM
```

## 📈 Understanding the Output

### Trading Windows (AI-Enhanced Version)
- **🚫 NO TRADING (before 11 AM)** - 0% historical win rate
- **🟢 PRIME WINDOW (11:30 AM - 1:30 PM)** - 85% win rate
- **🟡 GOOD WINDOW (11:00 AM - 2:30 PM)** - 70% win rate
- **🔴 AVOID (after 2:30 PM)** - Poor performance

### Filter States
Each signal shows which filters passed:
- **Volatility Filter**: Sufficient price movement
- **Regime Filter**: Trend alignment
- **Kernel Filter**: Kernel regression confirmation
- **ADX Filter**: Trend strength (optional)

### Pattern Quality Score (AI-Enhanced)
Scores from 1-10 based on:
- ML prediction strength (±2 points)
- Filter alignment (±0.5 per filter)
- Time window bonus (±1.5 points)
- Trend confirmation (±1 point)

**Minimum score for entry: 7.0/10**

## 📊 Performance Analysis

### End-of-Test Summary
```
==================================================
📊 LIVE MARKET TEST SUMMARY
==================================================

💰 Financial Summary:
   Starting Capital: ₹10,000.00
   Daily P&L: ₹+485.50 (+4.86%)
   Ending Capital: ₹10,485.50

📈 Trading Statistics:
   Total Trades: 2
   Wins: 2 (100.0%)
   Losses: 0 (0.0%)
   Average Win: ₹242.75
   Win/Loss Ratio: N/A

⏰ Time Window Analysis:
   Prime Window Trades: 2 (100.0% win rate)
   Prime Window P&L: ₹+485.50

🏆 Notable Trades:
   Best Trade: INFY - ₹+360.00 (TARGET_2)
   Worst Trade: WIPRO - ₹+125.50 (SIGNAL_EXIT)

📊 Average Metrics:
   Avg Hold Time: 38.5 minutes
   Avg Pattern Score: 8.2/10
   Partial Exits: 2 trades
```

### Exported Files

**1. Trade History (CSV)**
```csv
symbol,type,entry_price,exit_price,position_size,pnl,pnl_percent,exit_reason,hold_minutes
INFY,LONG,1614.50,1654.50,12,360.00,2.47,TARGET_2,45.2
WIPRO,LONG,455.30,461.00,22,125.50,1.25,SIGNAL_EXIT,32.1
```

**2. Detailed Results (JSON)**
```json
{
  "session_date": "2024-06-25",
  "capital": 10000,
  "daily_pnl": 485.50,
  "total_trades": 2,
  "win_rate": 100.0,
  "stocks_traded": ["INFY", "WIPRO"],
  "ai_rules_followed": {
    "trade_limit": true,
    "loss_limit": true,
    "time_window": true,
    "pattern_quality": true
  }
}
```

## ⚙️ Configuration Options

### Standard Version (test_live_market.py)
```python
# Customize test symbols
test_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICIBANK']
tester = LiveMarketTest(test_symbols)

# Adjust test duration
tester.run_continuous_test(duration_minutes=120)  # 2 hours
```

### AI-Enhanced Version (test_live_market_ai_enhanced.py)
```python
# Initialize with custom capital
trader = AIEnhancedLiveMarketTest(capital=50000.0)

# The system will automatically:
# - Screen stocks based on criteria
# - Enforce 2 trades per day limit
# - Block trades before 11 AM
# - Require pattern score ≥ 7.0
```

## 🛡️ Risk Management Features

### Position Sizing
Automatically calculates position size based on:
- 1.8% risk per trade
- Maximum 50% of capital per position
- Price-based limits (e.g., max 50 shares for stocks under ₹100)

### Stop Loss Rules
- Fixed 1% stop loss from entry
- Moved to breakeven after first target hit
- Time-based exit after 30 minutes if no movement

### Daily Limits (AI-Enhanced)
- Maximum 2 trades per day
- Daily loss limit: 2% of capital
- No trading before 11 AM
- Extra caution after first loss

## 🔍 Troubleshooting

### Common Issues

**1. Authentication Error**
```
❌ Failed to initialize Zerodha: Incorrect `api_key` or `access_token`
```
**Solution**: Run `python auth_helper.py` to get a fresh token

**2. No Historical Data**
```
❌ No historical data for SYMBOL
```
**Solution**: Check if you have historical data API access (₹2000/month subscription)

**3. Import Errors**
```
❌ KiteConnect not installed!
```
**Solution**: `pip install kiteconnect`

### Debug Mode
For detailed logging, modify the script:
```python
# Change logging level
logging.basicConfig(level=logging.DEBUG)

# Use debug processor
from scanner.enhanced_bar_processor_debug import EnhancedBarProcessorDebug
processor = EnhancedBarProcessorDebug(config, symbol, "5min")
```

## 📈 Best Practices

### 1. **Test During Market Hours**
Run tests between 9:15 AM - 3:30 PM for live data

### 2. **Start with Paper Trading**
Use the simulation to understand system behavior before real trading

### 3. **Monitor Different Market Conditions**
- Trending markets
- Sideways markets
- High volatility days
- News-driven movements

### 4. **Analyze Results**
- Review exported CSV files
- Check win rates by time window
- Identify best performing setups

### 5. **Gradual Scaling**
- Start with default 2 trades/day
- Test with small capital
- Scale up only after consistent results

## 🎯 Key Metrics to Track

1. **Win Rate by Time Window**
   - Prime window (11:30 AM - 1:30 PM) target: 70%+
   - Overall target: 60%+

2. **Average Risk/Reward**
   - Target: 1:2 or better
   - Partial exits help lock in profits

3. **Hold Time**
   - Optimal: 15-45 minutes
   - Exit if no movement after 30 minutes

4. **Pattern Quality Score**
   - Average should be 7.5+
   - Never take trades below 7.0

## 🚀 Next Steps

1. **Run Initial Tests**
   - Start with 1-hour sessions
   - Test during prime window (11:30 AM - 1:30 PM)
   - Use default capital (₹10,000)

2. **Analyze Performance**
   - Review trade history CSV
   - Check time window performance
   - Identify best setups

3. **Optimize Settings**
   - Adjust pattern quality threshold
   - Test different stock universes
   - Fine-tune position sizing

4. **Scale Gradually**
   - Increase test duration
   - Add more capital
   - Consider real trading only after consistent profits

## 📚 Related Documentation

- [README.md](../README.md) - Project overview
- [NEXT_CHAT_CONTEXT.md](../NEXT_CHAT_CONTEXT.md) - Technical details
- [AI-Trading-Knowledge-Base.md](../AI-Trading-Knowledge-Base.md) - Trading rules
- [ANALYSIS_GUIDE.md](project_documentation/ANALYSIS_GUIDE.md) - Code analysis

---

**Remember**: This is a simulation tool for testing and learning. Always practice risk management and never trade with money you can't afford to lose.