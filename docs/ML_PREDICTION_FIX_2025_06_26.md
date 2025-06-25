# ML Prediction Fix - June 26, 2025

## Problem Identified
The Lorentzian k-NN model was returning 0.00 predictions throughout the entire backtest, causing the system to trade on random noise. This resulted in a terrible 36.2% win rate (below break-even).

## Root Cause Analysis

### Initial Hypothesis (Incorrect)
Initially thought the training labels were generated incorrectly using kernel signals instead of simple price comparison. This was **wrong**.

### Actual Root Cause
The feature arrays were being updated BEFORE ML predictions were made. This caused the k-NN algorithm to compare current features with themselves (just added to the array), resulting in:
- Distance of 0 or very small values for i=0
- Most neighbors being rejected due to distance comparisons
- Empty predictions array → 0.00 ML predictions

### Debug Evidence
```
🔍 DEBUG: First ML prediction at bar 2000
   Training data size: 1997
   size_loop: 1996
   Current predictions array: []
   Current distances array: []
   i=0: distance=0.0701, last_distance=-1.0000, i%4=0
   i=1: distance=0.4582, last_distance=-1.0000, i%4=1
```

## Solution Implemented

### Code Change in enhanced_bar_processor.py
Moved feature array updates to AFTER ML predictions:

```python
# BEFORE (incorrect order):
feature_series = self._calculate_features_stateful(high, low, close)
self._update_feature_arrays(feature_series)  # Too early!
# ... ML prediction happens here ...

# AFTER (correct order):
feature_series = self._calculate_features_stateful(high, low, close)
# ... ML prediction happens here ...
self._update_feature_arrays(feature_series)  # After prediction!
```

This ensures ML predictions compare current features only with historical features, not with themselves.

## Verification of Training Logic

### Pine Script Training Labels
```pinescript
y_train_series := src[4] < src[0] ? direction.short : 
                 src[4] > src[0] ? direction.long : direction.neutral
```

### Our Python Implementation
```python
if src_4bars_ago < src_current:
    y_train_series = self.label.short
elif src_4bars_ago > src_current:
    y_train_series = self.label.long
else:
    y_train_series = self.label.neutral
```

**Confirmed: Our training label logic is CORRECT and matches Pine Script exactly.**

## Results After Fix

### Before Fix
- ML predictions: Always 0.00
- Win rate: 36.2% (random trading)
- No meaningful predictions

### After Fix
- ML predictions now generating non-zero values:
  - `ML Prediction (raw): -6.00` at bar 2499
  - `ML Prediction (raw): 1.00` at bar 2599
  - `ML Prediction (raw): -8.00` at bar 2699
- Win rate: Still 36.2% but now with actual ML predictions
- Most predictions still 0.00 (needs further optimization)

## Next Steps

1. **Optimize k-NN parameters**
   - Adjust neighbors_count
   - Tune distance thresholds
   - Review i%4 filtering logic

2. **Fix filter effectiveness**
   - All filters currently passing 100%
   - Need to calibrate thresholds

3. **Improve ML prediction quality**
   - Add more diverse features
   - Adjust training window
   - Fine-tune for different timeframes

## Key Learnings

1. **Always verify execution order** - Feature updates must happen after predictions
2. **Pine Script i%4 behavior** - When i%4 == 0, it evaluates to false (skip)
3. **Training labels are correct** - Simple price comparison, not kernel signals
4. **Debug systematically** - Check array sizes, distances, and predictions at each step

## Files Modified
- `/scanner/enhanced_bar_processor.py` - Fixed feature array update timing
- `/debug_ml_zero_predictions.py` - Created for debugging
- `/debug_knn_logic.py` - Created for step-by-step k-NN debugging
- `/CRITICAL_ML_ISSUE.md` - Documentation for future reference