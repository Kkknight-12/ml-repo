# Lorentzian Classification System Fine-Tuning Guide

## Overview
This guide consolidates all fine-tuning and optimization strategies for the Lorentzian Classification trading system, based on existing documentation, best practices, and advanced DSP techniques from John Ehlers' "Rocket Science for Traders".

## Table of Contents
1. [Core Parameters](#core-parameters)
2. [ML Model Tuning](#ml-model-tuning)
3. [Filter Optimization](#filter-optimization)
4. [Risk Management](#risk-management)
5. [Time-Based Adjustments](#time-based-adjustments)
6. [Performance Optimization](#performance-optimization)
7. [Testing & Validation](#testing-validation)

## Core Parameters

### 1. ML Settings (config/settings.py)

#### Neighbors Count
```python
neighbors_count: int = 8  # Default from Pine Script
```
**Fine-tuning guidance:**
- Range: 3-15 neighbors
- Lower values (3-5): More responsive, more false signals
- Higher values (10-15): More stable, may miss quick moves
- Sweet spot: 6-10 for most markets

#### Max Bars Back
```python
max_bars_back: int = 2000  # Default warmup period
```
**Fine-tuning guidance:**
- Minimum: 1000 bars (insufficient training data below this)
- Optimal by timeframe:
  - 15min-30min: 800-1500
  - 1H-2H: 1500-2500
  - 4H-12H: 2000 (default)
  - Daily+: 1000-1500

#### Feature Count
```python
feature_count: int = 5  # Number of technical indicators
```
**Fine-tuning guidance:**
- Range: 3-5 features
- More features ≠ better performance
- Quality over quantity
- Current features: RSI, WT, CCI, ADX variations

### 2. Feature Engineering

#### Default Features (config/constants.py)
```python
DEFAULT_FEATURES = {
    "f1": ("RSI", 14, 1),    # RSI 14
    "f2": ("WT", 10, 11),    # WaveTrend
    "f3": ("CCI", 20, 1),    # CCI 20
    "f4": ("ADX", 20, 2),    # ADX 20
    "f5": ("RSI", 9, 1)      # RSI 9
}
```

**Fine-tuning combinations:**
```python
# Trend Following Setup
features = {
    "f1": ("RSI", 14, 1),
    "f2": ("ADX", 14, 2),
    "f3": ("CCI", 20, 1),
    "f4": ("RSI", 21, 1),
    "f5": ("WT", 10, 11)
}

# Mean Reversion Setup
features = {
    "f1": ("RSI", 7, 1),
    "f2": ("CCI", 14, 1),
    "f3": ("RSI", 14, 1),
    "f4": ("WT", 10, 11),
    "f5": ("CCI", 20, 1)
}

# Momentum Setup
features = {
    "f1": ("RSI", 9, 1),
    "f2": ("ADX", 20, 2),
    "f3": ("WT", 10, 11),
    "f4": ("RSI", 14, 1),
    "f5": ("ADX", 14, 2)
}
```

## ML Model Tuning

### 1. Prediction Thresholds

Based on the optimization plan, adjust signal generation thresholds:

```python
# In signal_generator_enhanced.py
def check_entry_conditions(...):
    # Default uses any non-zero prediction
    # Fine-tune by requiring minimum strength:
    
    MIN_PREDICTION_STRENGTH = 2.0  # Adjust based on testing
    
    if abs(ml_prediction) < MIN_PREDICTION_STRENGTH:
        return False, False
```

### 2. Distance Calculation

The Lorentzian distance is core to the algorithm. While the formula shouldn't change, you can weight features:

```python
# Theoretical enhancement (not in current code)
FEATURE_WEIGHTS = [1.2, 1.0, 0.8, 1.0, 1.1]  # Weight important features more
```

## Filter Optimization

### 1. Volatility Filter
```python
use_volatility_filter: bool = True
```
**Fine-tuning:**
- Enable for ranging markets
- Disable for strong trending markets
- Adjust min/max length in enhanced_ml_extensions.py

### 2. Regime Filter
```python
use_regime_filter: bool = True
regime_threshold: float = -0.1
```
**Fine-tuning:**
- Threshold range: -0.5 to 0.5
- Lower values: More selective (fewer trades)
- Higher values: More permissive
- Optimal: -0.2 to 0.0 for most markets

### 3. ADX Filter
```python
use_adx_filter: bool = False  # Often disabled
adx_threshold: int = 20
```
**Fine-tuning:**
- Enable for trend-following strategies
- Threshold range: 15-30
- 15-20: Include weak trends
- 25-30: Strong trends only

### 4. Kernel Filter
```python
use_kernel_filter: bool = True
kernel_lookback: int = 8
kernel_relative_weight: float = 8.0
kernel_regression_level: int = 25
```
**Fine-tuning:**
- Lookback: 5-15 (shorter = more responsive)
- Relative weight: 4-12 (higher = smoother)
- Regression level: 10-50 (lower = tighter fit)

## Risk Management

### 1. Position Sizing (From Live Trading Improvements)

```python
# Risk-based position sizing
max_risk_per_trade = 0.02  # 2% default

# Fine-tuning by account size:
if capital < 10000:
    max_risk_per_trade = 0.01  # 1% for small accounts
elif capital > 100000:
    max_risk_per_trade = 0.025  # 2.5% for large accounts

# By market conditions:
if high_volatility:
    max_risk_per_trade *= 0.5  # Reduce risk in volatile markets
```

### 2. Stop Loss Settings

```python
# ATR-based stops (recommended)
atr_multiplier = 2.0  # Default

# Fine-tuning by market:
# Crypto: 2.5-3.0 (more volatile)
# Forex: 1.5-2.0 (less volatile)
# Stocks: 2.0-2.5 (moderate)
```

### 3. Profit Targets

```python
# Risk:Reward ratios
profit_target_ratio = 2.0  # Default 1:2

# Fine-tuning:
# Scalping: 1.5
# Swing trading: 2.0-3.0
# Position trading: 3.0-5.0
```

## Time-Based Adjustments

### 1. Trading Windows (AI Knowledge Base)

```python
# Indian Market Hours
prime_window_start = 11.5  # 11:30 AM
prime_window_end = 13.5    # 1:30 PM (85% win rate)

# Fine-tuning for different markets:
# US Markets
prime_window_start = 10.5  # 10:30 AM EST
prime_window_end = 11.5    # 11:30 AM EST

# Forex (24-hour)
# Focus on session overlaps
london_ny_overlap = (13.0, 17.0)  # UTC
```

### 2. Holding Period Adjustments

```python
# Exit timing based on timeframe
timeframe_exit_bars = {
    "1min": 10,
    "5min": 8,
    "15min": 6,
    "1hour": 4,
    "4hour": 3,
    "daily": 5
}
```

## Performance Optimization

### 1. From Optimization Plan

#### Phase 1: Dynamic Exits
```python
# Instead of fixed 4-bar exit:
use_dynamic_exits: bool = True

# Multi-target system:
targets = [
    (0.4, 1.5),  # Exit 40% at 1.5R
    (0.3, 2.5),  # Exit 30% at 2.5R
    (0.3, 4.0),  # Exit 30% at 4.0R
]
```

#### Phase 2: Market Regime Adaptation
```python
# Detect market regime
def get_market_regime():
    # Trending: ADX > 25
    # Ranging: ADX < 20
    # Transitioning: ADX 20-25
    pass

# Adjust parameters by regime
if market_regime == "trending":
    config.use_adx_filter = True
    config.adx_threshold = 25
elif market_regime == "ranging":
    config.use_volatility_filter = True
    config.regime_threshold = -0.2
```

### 2. Ehlers DSP Enhancements (NEW)

#### Market Mode Detection
```python
# From Rocket Science for Traders
def detect_market_mode(bars, config):
    """Detect if market is in Trend or Cycle mode"""
    
    # Method 1: Sinewave Indicator
    sine, lead_sine = calculate_sinewave(bars)
    lines_parallel = abs(sine - lead_sine) < 0.1
    
    # Method 2: ADX Threshold
    adx_value = calculate_adx(bars, 14)
    
    if lines_parallel or adx_value > config.trend_mode_adx_threshold:
        return "TREND"
    else:
        return "CYCLE"
```

#### Super Smoother Filter
```python
# Replace simple smoothing with Ehlers Super Smoother
def super_smoother(data, cutoff_period):
    """Low-lag smoothing filter"""
    a1 = np.exp(-1.414 * np.pi / cutoff_period)
    b1 = 2 * a1 * np.cos(1.414 * 180 / cutoff_period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3
    
    # Apply filter
    smoothed = np.zeros_like(data)
    for i in range(2, len(data)):
        smoothed[i] = c1 * (data[i] + data[i-1]) / 2 + c2 * smoothed[i-1] + c3 * smoothed[i-2]
    
    return smoothed
```

#### Adaptive Indicators
```python
# Make indicators adaptive to market cycle
def adaptive_rsi(data, use_adaptive=True):
    """RSI that adapts period to dominant cycle"""
    
    if use_adaptive:
        # Measure dominant cycle period
        period = measure_dominant_cycle(data)
        period = np.clip(period, 10, 48)  # Limit range
    else:
        period = 14  # Default
    
    return calculate_rsi(data, int(period))
```

#### Cycle-Based Targets
```python
# Set profit targets based on cycle amplitude
def calculate_cycle_targets(entry_price, cycle_amplitude):
    """Dynamic targets based on market cycles"""
    
    targets = {
        'target_1': entry_price + (cycle_amplitude * 0.5),   # Half cycle
        'target_2': entry_price + (cycle_amplitude * 0.75),  # 3/4 cycle
        'target_3': entry_price + (cycle_amplitude * 1.0),   # Full cycle
    }
    
    return targets
```

### 2. Walk-Forward Optimization

```python
# From optimization_plan.md
walk_forward_params = {
    "training_window": 2 * 365,  # 2 years
    "test_window": 6 * 30,       # 6 months
    "step_size": 30,             # Roll monthly
}
```

## Testing & Validation

### 1. Parameter Stability Testing

```python
# Test parameter ranges
def test_parameter_stability(param_name, base_value, test_range):
    results = []
    for multiplier in [0.5, 0.75, 1.0, 1.25, 1.5]:
        test_value = base_value * multiplier
        performance = run_backtest(param_name=test_value)
        results.append((test_value, performance))
    
    # Look for stable regions, not peaks
    return find_stable_region(results)
```

### 2. Cross-Market Validation

```python
# Test on different instruments
test_symbols = {
    "trending": ["RELIANCE", "TCS"],
    "volatile": ["TATAMOTORS", "YESBANK"],
    "stable": ["ITC", "HINDUNILVR"]
}

# Parameters should work across categories
```

### 3. Monte Carlo Simulation

```python
# Randomize trade order to test robustness
def monte_carlo_test(trades, iterations=1000):
    results = []
    for _ in range(iterations):
        shuffled = random.shuffle(trades)
        equity_curve = calculate_equity(shuffled)
        results.append(calculate_metrics(equity_curve))
    
    return analyze_distribution(results)
```

## Best Practices

### ✅ DO:
1. **Start with defaults** - They're battle-tested
2. **Change one parameter at a time**
3. **Use round numbers** (1.5, 2.0, not 1.47)
4. **Test on out-of-sample data**
5. **Validate across multiple markets**
6. **Focus on robustness over performance**

### ❌ DON'T:
1. **Over-optimize on historical data**
2. **Use more than 10 parameters**
3. **Make tiny adjustments** (<10% changes)
4. **Ignore transaction costs**
5. **Forget about market regime changes**
6. **Chase perfect win rates**

## Quick Start Fine-Tuning

### For Beginners:
```python
# Start with these safe adjustments:
config = TradingConfig(
    neighbors_count=8,        # Keep default
    max_bars_back=2000,      # Keep default
    use_volatility_filter=True,
    use_regime_filter=True,
    regime_threshold=-0.2,   # Slightly more selective
    use_adx_filter=True,     # Enable for trends
    adx_threshold=25         # Strong trends only
)
```

### For Trending Markets:
```python
config = TradingConfig(
    neighbors_count=6,       # More responsive
    use_adx_filter=True,
    adx_threshold=25,
    use_kernel_smoothing=True,
    use_dynamic_exits=True
)
```

### For Ranging Markets:
```python
config = TradingConfig(
    neighbors_count=10,      # More stable
    use_volatility_filter=True,
    use_regime_filter=True,
    regime_threshold=-0.3,   # More selective
    use_adx_filter=True,
    adx_threshold=20        # Filter out trends
)
```

## Monitoring & Adjustment

### Key Metrics to Track:
1. **Win Rate**: Target 50-65% (not higher)
2. **Profit Factor**: Target > 1.5
3. **Average R-Multiple**: Target > 1.2R
4. **Maximum Drawdown**: Keep < 20%
5. **Trade Frequency**: 5-10 per 1000 bars

### When to Re-tune:
- Performance degrades for 2+ months
- Market regime change detected
- Major volatility shift
- New market or timeframe

## Conclusion

Fine-tuning the Lorentzian Classification system is about finding the right balance between responsiveness and stability. Start with the defaults, make small adjustments based on your specific market and timeframe, and always validate changes with proper testing. Remember that the goal is not to maximize historical performance but to create a robust system that works across different market conditions.

The most important parameters to focus on are:
1. Risk management settings (position sizing, stops)
2. Filter thresholds (regime, ADX)
3. ML neighbors count
4. Trading time windows

Always prioritize risk management over return optimization, and remember that a simpler, more robust system will outperform a complex, over-optimized one in live trading.