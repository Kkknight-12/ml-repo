# Pine Script to Python TA Function Mapping

## Quick Reference for Stateful Implementation

### 1. ta.ema() - Exponential Moving Average
**Pine Script**: `ta.ema(source, length)`
**Current Python**: `pine_ema(values, length)` - Recalculates all
**Required**: 
```python
class StatefulEMA:
    alpha = 2 / (length + 1)
    value = alpha * current + (1 - alpha) * previous
```

### 2. ta.sma() - Simple Moving Average  
**Pine Script**: `ta.sma(source, length)`
**Current Python**: `pine_sma(values, length)` - Recalculates all
**Required**:
```python
class StatefulSMA:
    # Maintain rolling window of length values
    # Add new, remove old, calculate mean
```

### 3. ta.rsi() - Relative Strength Index
**Pine Script**: `ta.rsi(source, length)`
**Current Python**: `calculate_rsi(values, length)` - Recalculates all
**Required**:
```python
class StatefulRSI:
    # Maintain avg_gain and avg_loss using RMA
    # Update incrementally with new price change
```

### 4. ta.rma() - Relative Moving Average (Wilder's)
**Pine Script**: `ta.rma(source, length)`
**Current Python**: `pine_rma(values, length)` - Recalculates all
**Required**:
```python
class StatefulRMA:
    alpha = 1 / length
    value = alpha * current + (1 - alpha) * previous
```

### 5. ta.atr() - Average True Range
**Pine Script**: `ta.atr(length)`
**Current Python**: `pine_atr(high, low, close, length)` - Recalculates all
**Required**:
```python
class StatefulATR:
    # Calculate TR for current bar
    # Maintain RMA of TR values
```

### 6. ta.cci() - Commodity Channel Index
**Pine Script**: `ta.cci(source, length)`
**Current Python**: `calculate_cci(close, high, low, length)` - Recalculates all
**Required**:
```python
class StatefulCCI:
    # Maintain SMA of typical price
    # Maintain mean deviation
```

### 7. ta.dmi() - Directional Movement Index
**Pine Script**: `[diplus, diminus, adx] = ta.dmi(diLength, adxSmoothing)`
**Current Python**: `dmi(high, low, close, length_di, length_adx)` - Recalculates all
**Required**:
```python
class StatefulDMI:
    # Maintain smoothed +DM, -DM, TR
    # Calculate DI+, DI-, DX, ADX incrementally
```

### 8. ta.stdev() - Standard Deviation
**Pine Script**: `ta.stdev(source, length)`
**Current Python**: `pine_stdev(values, length)` - Recalculates all
**Required**:
```python
class StatefulStdev:
    # Maintain sum and sum of squares
    # Calculate incrementally
```

### 9. ta.change() - Bar-to-bar change
**Pine Script**: `ta.change(source, length)`
**Current Python**: `change(series, lookback)` - Stateless OK
**Note**: This can remain stateless, just needs previous value

### 10. ta.crossover() - Crossover detection
**Pine Script**: `ta.crossover(source1, source2)`
**Current Python**: `crossover_value(s1_curr, s1_prev, s2_curr, s2_prev)` - Stateless OK
**Note**: Just comparison, can remain stateless

### 11. ta.crossunder() - Crossunder detection
**Pine Script**: `ta.crossunder(source1, source2)`
**Current Python**: `crossunder_value(s1_curr, s1_prev, s2_curr, s2_prev)` - Stateless OK
**Note**: Just comparison, can remain stateless

### 12. ta.barssince() - Bars since condition
**Pine Script**: `ta.barssince(condition)`
**Current Python**: `barssince(condition_series)` - Needs state
**Required**:
```python
class StatefulBarsSince:
    # Maintain counter
    # Reset when condition true
    # Increment otherwise
```

## Usage Pattern Change

### Current (Wrong):
```python
# Calculate from full history
rsi_value = calculate_rsi(close_values, 14)
ema_value = pine_ema(close_values, 20)
```

### New (Correct):
```python
# Get or create stateful indicator
rsi = state_manager.get_or_create_rsi("rsi_14", 14)
ema = state_manager.get_or_create_ema("ema_20", 20)

# Update with current value only
rsi_value = rsi.update(current_close, previous_close)
ema_value = ema.update(current_close)
```

## Key Principles

1. **One instance per indicator/period combination**
2. **Update incrementally, never recalculate**
3. **Maintain minimal state required**
4. **Call on every bar for consistency**
5. **Handle initialization carefully**

## Testing Strategy

For each indicator:
1. Initialize with first value
2. Update with series: [1, 2, 3, 4, 5...]
3. Compare output with Pine Script
4. Verify state persistence
5. Test with real market data
