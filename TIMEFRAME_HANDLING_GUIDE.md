# Pine Script Timeframe Handling Guide

## How Pine Script Handles Different Timeframes

### 1. **Built-in Timeframe Support**
Pine Script automatically handles timeframe data through the TradingView platform:

```pine
// Current chart timeframe (automatic)
close     // Close price of current timeframe
close[1]  // Previous bar of current timeframe

// Access other timeframes
dailyClose = request.security(syminfo.tickerid, "D", close)   // Daily
weeklyClose = request.security(syminfo.tickerid, "W", close)  // Weekly
hourlyClose = request.security(syminfo.tickerid, "60", close) // Hourly
```

### 2. **Key Differences from Python**
- **Pine Script**: Platform automatically aligns data to chart timeframe
- **Python**: You must manually handle timeframe conversions
- **Pine Script**: Built-in resampling with `request.security()`
- **Python**: Need pandas resample or manual aggregation

## How Pine Script Adjusts Filters for Multiple Timeframes

### **IMPORTANT**: Pine Script does NOT automatically adjust filters!

Filters in Pine Script remain static unless you explicitly code timeframe-based logic:

```pine
// Manual adjustment example in Pine Script
atrLength = timeframe.period == "D" ? 14 : 
            timeframe.period == "60" ? 20 : 
            timeframe.period == "5" ? 50 : 14

regimeThreshold = timeframe.isintraday ? 0.0 : -0.1

// Volatility filter adjustment
volatilityMultiplier = timeframe.period == "D" ? 1.5 : 
                       timeframe.period == "5" ? 2.5 : 2.0
```

## Our Python Implementation Approach

### 1. **Timeframe Configuration**
We handle timeframes through configuration parameters:

```python
# Daily Configuration (ICICI Bank NSE)
daily_config = TradingConfig(
    neighbors_count=8,           # Good for daily
    max_bars_back=2000,         # 2000 days history
    regime_threshold=-0.1,      # Daily trending
    adx_threshold=20,           # Standard daily
    kernel_lookback=8,          # 8 days
)

# 5-Minute Configuration
fivemin_config = TradingConfig(
    neighbors_count=5,          # Faster adaptation
    max_bars_back=1000,        # 1000 * 5min bars
    regime_threshold=0.0,      # Neutral for intraday
    adx_threshold=15,          # Lower for ranging
    kernel_lookback=12,        # 1 hour (12 * 5min)
)
```

### 2. **No Automatic Adjustment**
Just like Pine Script, our Python implementation:
- ❌ Does NOT auto-adjust parameters
- ✅ Requires manual configuration per timeframe
- ✅ Allows full control over each parameter

## Testing on 1-Day Timeframe (ICICI Bank NSE)

### Yes, you can test on daily ICICI Bank data!

Run the test script:
```bash
python test_icici_daily.py
```

This script:
1. Generates ICICI-like daily data (₹950-1050 range)
2. Uses daily-optimized parameters
3. Shows Pine Script style history access
4. Tracks ML predictions over days

### Configuration for ICICI Daily:
```python
config = TradingConfig(
    # Core settings
    neighbors_count=8,
    max_bars_back=2000,      # ~8 years of daily data
    
    # Daily-optimized filters
    regime_threshold=-0.1,   # Good for daily trends
    adx_threshold=20,        # Standard for daily
    
    # Kernel for daily
    kernel_lookback=8,       # 8 trading days
    
    # Optional trend filters
    ema_period=200,          # 200-day moving average
    sma_period=200,          # 200-day simple MA
)
```

## Pine Script Style History Referencing

### New Utility Functions Added:

1. **Enhanced Bar Data** (`data/enhanced_bar_data.py`):
```python
# Pine Script style access
close_today = bars.close[0]      # Current day
close_yesterday = bars.close[1]  # Previous day
close_week_ago = bars.close[5]   # 5 days ago

# Automatic calculations
hlc3 = bars.hlc3[0]  # (high + low + close) / 3
ohlc4 = bars.ohlc4[0]  # (open + high + low + close) / 4
```

2. **Custom Series** (for indicators):
```python
# Create custom series
rsi = create_series("RSI")
rsi.update(65.5)  # Current RSI

# Access history
current_rsi = rsi[0]   # 65.5
previous_rsi = rsi[1]  # Yesterday's RSI
```

3. **Arrays with History**:
```python
# Create array like Pine Script
predictions = PineArray(size=10)
predictions.set(0, 5.5)
predictions.new_bar()  # Save state

# Access previous bar's array
prev_array = predictions[1]
```

## Key Takeaways

1. **Timeframe Handling**: Manual configuration required (same as Pine Script)
2. **Filter Adjustment**: Not automatic - you must set parameters
3. **ICICI Daily Testing**: Fully supported with test script
4. **History Access**: Now works like Pine Script with [] operator

## Quick Start Commands

```bash
# Test Pine Script functions
python test_pine_functions.py

# Test ICICI Bank daily
python test_icici_daily.py

# Test with enhanced debugging
python test_enhanced_current_conditions.py
```

## Recommended Daily Parameters for NSE Stocks

| Parameter | Daily Value | Reason |
|-----------|------------|---------|
| neighbors_count | 8 | Standard for daily |
| max_bars_back | 2000 | ~8 years history |
| regime_threshold | -0.1 | Trend detection |
| adx_threshold | 20 | Daily trends |
| kernel_lookback | 8 | 8 trading days |
| ema_period | 200 | Long-term trend |

Remember: The Lorentzian Classification was designed for 4H-12H timeframes. Daily timeframe should work well, but may need parameter tuning based on results.
