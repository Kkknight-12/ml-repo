# Pine Script to Python Conversion Guide

## Critical Principles for Accurate Conversion

### 1. **State Persistence is Critical**
- Pine Script's `var` keyword creates persistent variables that Python must replicate with instance variables
- Feature arrays grow indefinitely while prediction arrays use fixed-size sliding windows
- Always maintain state between bars - never reset unless explicitly required
- Example pattern:
```python
class LorentzianClassifier:
    def __init__(self):
        # Persistent state variables
        self.f1_array = []  # Unlimited growth
        self.predictions = deque(maxlen=8)  # Fixed size
        self.last_signal = 0  # Maintain between bars
```

### 2. **Warmup Period Handling**
- Pine Script naturally handles warmup through bar_index checks
- Python must explicitly track bar count and block signals during warmup
- Warmup period: First 25-2000 bars (configurable) where ML predictions are disabled
- Continue processing and accumulating data during warmup, just don't generate signals
- Implementation:
```python
if self.bar_count < self.config.max_bars_back:
    # Still in warmup - accumulate data but no signals
    return ProcessResult(signal=self.last_signal, prediction=0)
```

### 3. **Filter Cascade and Signal Quality**
- Filters are applied in sequence: pre-filters → ML prediction → post-filters
- Any filter can block a signal - all must pass for entry
- Kernel filter is particularly critical for timing entry signals
- Signal persistence using `nz(signal[1])` improves quality by 15-20%
- Correct order:
  1. Data quality filters (volatility, regime) - return last signal if fail
  2. ML prediction
  3. Directional filters (kernel, EMA/SMA) - modify signal
  4. Entry signal generation (all conditions must align)

### 4. **Array Management Patterns**
- Feature arrays: Unlimited growth with simple append operations
- Prediction/distance arrays: Fixed-size FIFO using deque(maxlen=n)
- 4-bar chronological spacing is critical for neighbor diversity
- 75th percentile distance threshold for dynamic adaptation
```python
# Neighbor selection with 4-bar spacing
for i in range(0, len(self.y_train_array), 4):
    if i >= self.config.max_bars_back:
        break
    # Calculate distance and select neighbors
```

### 5. **Mathematical Precision**
- Lorentzian distance: `log(1 + abs(difference))` - handles volatility better than Euclidean
- KLMF regime filter has unique alpha formula requiring careful implementation:
```python
omega = abs(value1 / value2) if value2 != 0 else 2.0
alpha = (-omega**2 + np.sqrt(omega**4 + 16*omega**2)) / 8
klmf = alpha * price + (1 - alpha) * self.klmf_prev
```
- Kernel regression calculations must match Pine Script exactly
- Handle division by zero and NaN propagation explicitly

### 6. **Execution Model Differences**
- Pine Script: Automatic bar-by-bar with implicit state management
- Python: Manual iteration with explicit state tracking
- Historical access: Pine's `close[n]` vs Python's manual indexing
- Must process bars chronologically and maintain temporal relationships
- Pine Script series access:
```pinescript
close[1]  // Previous bar's close
```
- Python equivalent:
```python
self.close_history[-2] if len(self.close_history) > 1 else 0
```

### 7. **Common Pitfalls to Avoid**
- ❌ Premature returns when data insufficient (maintain last valid signal instead)
- ❌ Applying filters after ML prediction (apply before to save computation)
- ❌ Missing the 4-bar spacing pattern in neighbor selection
- ❌ Not handling Pine's three-valued logic (true/false/na)
- ❌ Resetting state inappropriately between bars
- ❌ Using wrong array indexing (Pine's [0] is current, [1] is previous)

### 8. **Signal Generation Logic**

**Long Entry Requirements (ALL must be true):**
1. `isNewBuySignal`: ML prediction = 1 AND signal changed from previous
2. `isBullish`: Kernel filter indicates bullish conditions
3. `isEmaUptrend`: Price > EMA (if filter enabled)
4. `isSmaUptrend`: Price > SMA (if filter enabled)

**Short Entry Requirements (ALL must be true):**
1. `isNewSellSignal`: ML prediction = -1 AND signal changed from previous
2. `isBearish`: Kernel filter indicates bearish conditions
3. `isEmaDowntrend`: Price < EMA (if filter enabled)
4. `isSmaDowntrend`: Price < SMA (if filter enabled)

### 9. **Critical Functions to Implement**
```python
def nz(value, replacement=0):
    """Pine Script nz() equivalent"""
    return replacement if pd.isna(value) or value is None else value

def na(value):
    """Pine Script na() equivalent"""
    return pd.isna(value) or value is None

def crossover(series1, series2):
    """True when series1 crosses above series2"""
    if len(series1) < 2 or len(series2) < 2:
        return False
    return series1[-1] > series2[-1] and series1[-2] <= series2[-2]

def crossunder(series1, series2):
    """True when series1 crosses below series2"""
    if len(series1) < 2 or len(series2) < 2:
        return False
    return series1[-1] < series2[-1] and series1[-2] >= series2[-2]
```

### 10. **Debugging Strategy**
1. Start with all filters disabled except core ML
2. Verify ML predictions match Pine Script
3. Enable filters one by one, comparing outputs
4. Log extensively at each stage
5. Compare bar-by-bar with Pine Script exports
6. Check array sizes and state persistence

## Key Insight
The fundamental challenge in Pine Script to Python conversion is that Pine Script is a domain-specific language designed for financial time series analysis, with many implicit behaviors around state management, series handling, and execution flow. Successful conversion requires explicitly implementing all these implicit behaviors while maintaining the exact mathematical and logical flow of the original algorithm.