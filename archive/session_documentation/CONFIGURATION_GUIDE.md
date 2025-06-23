# Configuration Guide for Different Timeframes

## Overview
The Lorentzian Classification algorithm was originally designed for 4H-12H timeframes. When using it on different timeframes, parameter adjustments may be necessary.

## Recommended Parameter Ranges

### Regime Filter Threshold
- **Range**: -0.5 to 0.5 (as per solution document)
- **Default**: -0.1
- **Adjustment Guide**:
  - More negative (-0.3 to -0.5): For trending markets, more restrictive
  - Near zero (-0.1 to 0.1): Balanced between trending and ranging
  - More positive (0.1 to 0.5): For ranging markets, less restrictive

### ADX Filter Threshold
- **Range**: 10-30
- **Default**: 20
- **Adjustment Guide**:
  - 10-15: For ranging markets (more signals)
  - 20-25: For moderate trends (balanced)
  - 25-30: For strong trends only (fewer signals)

### Timeframe-Specific Recommendations

#### 1-Day Timeframe (Daily Bars)
```python
config = TradingConfig(
    neighbors_count=8,           # Default is good
    max_bars_back=2000,         # 2000 days = ~8 years of data
    regime_threshold=-0.1,      # Default works well
    adx_threshold=20,           # Default for daily trends
    use_kernel_smoothing=False, # Less smoothing needed
    kernel_lookback=8,          # 8 days lookback
)
```

#### 4-Hour Timeframe (Original Design)
```python
config = TradingConfig(
    neighbors_count=8,           # Optimal for this timeframe
    max_bars_back=2000,         # 2000 * 4H = ~333 days
    regime_threshold=-0.1,      # Original default
    adx_threshold=20,           # Original default
    use_kernel_smoothing=False, # As designed
    kernel_lookback=8,          # 32 hours lookback
)
```

#### 5-Minute Timeframe (Intraday)
```python
config = TradingConfig(
    neighbors_count=5,           # Reduce for faster adaptation
    max_bars_back=1000,         # 1000 * 5min = ~3.5 days
    regime_threshold=0.0,       # More neutral for choppy intraday
    adx_threshold=15,           # Lower for intraday ranging
    use_kernel_smoothing=True,  # Smooth out noise
    kernel_lookback=12,         # 1 hour lookback
    ema_period=50,              # Shorter MA for intraday
    sma_period=50,              # Shorter MA for intraday
)
```

#### 1-Minute Timeframe (Scalping)
```python
config = TradingConfig(
    neighbors_count=3,           # Very responsive
    max_bars_back=500,          # 500 minutes = ~8 hours
    regime_threshold=0.2,       # Favor ranging detection
    adx_threshold=12,           # Very low for micro-trends
    use_kernel_smoothing=True,  # Essential for noise
    kernel_lookback=20,         # 20 minutes lookback
    ema_period=20,              # Very short MA
    sma_period=20,              # Very short MA
)
```

## General Guidelines

### Data Requirements
- **Minimum bars**: 500 (as per solution document)
- **Recommended**: 1000+ bars for stable predictions
- **Training warmup**: First 20-50 bars used for initialization

### Filter Usage
1. **Start simple**: Begin with fewer filters enabled
2. **Test incrementally**: Enable one filter at a time
3. **Monitor results**: Track signal frequency and quality

### Common Issues and Solutions

#### No Signals Generated
1. Check ML predictions are non-zero
2. Reduce filter restrictions:
   - Increase regime_threshold (toward 0.5)
   - Decrease adx_threshold (toward 10)
   - Disable kernel_filter temporarily
3. Ensure sufficient historical data

#### Too Many Signals
1. Tighten filter restrictions:
   - Decrease regime_threshold (toward -0.5)
   - Increase adx_threshold (toward 25)
   - Enable all filters
2. Increase neighbors_count for more consensus

#### Choppy/Whipsaw Signals
1. Enable kernel_smoothing
2. Increase kernel_lookback
3. Use EMA/SMA filters
4. Check for early_signal_flips

## Dynamic Adjustment Formula

For custom timeframes, use this formula as a starting point:

```python
# Base values (4H timeframe)
base_timeframe_minutes = 240  # 4 hours
base_max_bars = 2000
base_kernel_lookback = 8

# Your timeframe
your_timeframe_minutes = 5  # Example: 5 minutes

# Scaling factor
scale = your_timeframe_minutes / base_timeframe_minutes

# Adjusted values
adjusted_max_bars = int(base_max_bars * (1/scale) * 0.5)  # 0.5 to reduce memory
adjusted_kernel_lookback = max(3, int(base_kernel_lookback / scale))
```

## Testing Approach

1. **Baseline Test**: Run with default parameters
2. **Measure Performance**: Track prediction rate, signal rate
3. **Adjust Gradually**: Change one parameter at a time
4. **Document Results**: Keep notes on what works

Remember: The algorithm needs time to adapt to each timeframe's characteristics. Allow at least 500-1000 bars of warmup before evaluating performance.
