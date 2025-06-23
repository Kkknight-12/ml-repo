# Next Session Instructions - Sliding Window Fix Applied

## ✅ Changes Implemented in This Session

### 1. **Sliding Window Implementation**
- Removed `total_bars` dependency from all code
- ML now uses relative positioning: `if len(y_train_array) >= max_bars_back`
- Works identically for backtest and live trading

### 2. **Updated Files**:
- `test_pinescript_style.py` - Removed total_bars parameter
- `lorentzian_knn.py` - Documentation updated
- `README_SINGLE_SOURCE_OF_TRUTH.md` - Added implementation details

### 3. **Created Verification Scripts**:
- `verify_sliding_window.py` - Tests sliding window with different scenarios
- `quick_ml_test.py` - Quick ML prediction verification

## 🎯 Next Session Tasks

### Priority 1: Run Verification
```bash
# Test sliding window implementation
python verify_sliding_window.py

# Quick ML prediction test
python quick_ml_test.py

# Full test with real data
python test_pinescript_style.py
```

### Priority 2: Debug ML Predictions
If still getting zero predictions:

1. **Check Feature Calculations**:
   - Add debug prints in `indicators.py`
   - Verify normalization is working
   - Check for NaN/None values

2. **Verify Training Labels**:
   ```python
   # In lorentzian_knn.py
   print(f"Training labels: {self.y_train_array[-10:]}")
   print(f"Label distribution: long={long_count}, short={short_count}, neutral={neutral_count}")
   ```

3. **Debug Distance Calculations**:
   ```python
   # In get_lorentzian_distance()
   print(f"Distance at i={i}: {distance}")
   ```

### Priority 3: Feature Analysis
Create a script to analyze feature values:
```python
# analyze_features.py
# - Print raw feature values before normalization
# - Check historical min/max tracking
# - Verify each indicator calculation
```

## 🔍 What to Look For

### In verify_sliding_window.py output:
- ML should start at `max_bars_back + 3-4` (for training label lookback)
- Should work with any dataset size ✅
- Real-time simulation should show correct behavior ✅

### In quick_ml_test.py output:
- Look for non-zero predictions after ML starts
- Check prediction range (should be -8 to +8)
- Verify distribution of positive/negative predictions

### In test_pinescript_style.py output:
- ML predictions should appear after correct bar
- Some filters should pass (not all blocked)
- Should generate some signals (buy/sell)

## 🚨 If Still Not Working

### Possible Issues:
1. **Feature calculations wrong** - Debug each indicator
2. **Data quality issues** - Not enough price movement
3. **Normalization broken** - Check min/max tracking
4. **Distance always too small** - Debug Lorentzian calculation

### Emergency Debug Steps:
1. Create minimal test with synthetic data
2. Use only 1 feature (RSI) to simplify
3. Print every calculation step
4. Compare with Pine Script values if possible

## 📊 Expected Behavior

After sliding window fix:
- ML starts at bar `max_bars_back + 3-4` (e.g., 103, 503, 1003)
- The 3-4 bar delay is for training label lookback (src[4] vs src[0]) 
- Predictions in range -8 to +8 ✅
- Some signals generated (with filters adjusted)
- Works same way for any data size ✅

**Note**: The slight delay is EXPECTED and matches Pine Script behavior!

## 💡 Key Insights

1. **Pine Script Dual Nature**: Same code handles both historical and real-time
2. **Sliding Window**: No pre-calculation needed, just relative positioning
3. **Stateless Design**: Each bar evaluated independently within window

---

**Session Status**: Sliding window implementation complete ✅
**Next Focus**: Verify implementation and debug ML predictions
**Priority**: Get non-zero ML predictions working!
