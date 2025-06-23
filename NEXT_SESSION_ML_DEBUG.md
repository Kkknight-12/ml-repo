# Next Session Instructions - Phase 4 ML Debug

## 🔴 CRITICAL FINDING - ML Predictions = 0

### Test Output Analysis:
```
Bar 1000: ML Prediction: 0.0 (Neutral ⚪)
Bar 1500: ML Prediction: 0.0 (Neutral ⚪)
Filters: Vol=✗ Regime=✗ ADX=✓ Kernel=✗
```

### Root Problem:
**ML predictions are returning 0** - This means:
- Either no neighbors are being selected
- Or all training labels are neutral
- Or feature calculations are wrong

## 🎯 Debug Priority Order

### 1. Check Training Labels First
```python
# In lorentzian_knn.py update_training_data():
def update_training_data(self, src_current: float, src_4bars_ago: float) -> None:
    if src_4bars_ago < src_current:
        label = self.label.short
    elif src_4bars_ago > src_current:
        label = self.label.long
    else:
        label = self.label.neutral
    
    # ADD DEBUG:
    if len(self.y_train_array) % 100 == 0:  # Every 100 bars
        print(f"Training labels last 10: {self.y_train_array[-10:]}")
        print(f"Long: {self.y_train_array.count(1)}, "
              f"Short: {self.y_train_array.count(-1)}, "
              f"Neutral: {self.y_train_array.count(0)}")
    
    self.y_train_array.append(label)
```

### 2. Debug Neighbor Selection
```python
# In lorentzian_knn.py predict():
def predict(...):
    # ... existing code ...
    
    # ADD DEBUG before the loop:
    print(f"\n=== ML Debug Bar {bar_index} ===")
    print(f"Max bars back index: {max_bars_back_index}")
    print(f"Size loop: {size_loop}")
    
    # Inside the loop where neighbors are added:
    if d >= last_distance and i % 4 == 0:
        # ADD DEBUG:
        if len(self.predictions) < 5:  # First few neighbors
            print(f"  Neighbor {i}: distance={d:.4f}, label={self.y_train_array[i]}")
    
    # After the loop:
    print(f"Total neighbors selected: {len(self.predictions)}")
    print(f"Predictions array: {self.predictions}")
    print(f"Final prediction sum: {self.prediction}")
```

### 3. Check Feature Values
```python
# In bar_processor.py _calculate_features():
def _calculate_features(self) -> FeatureSeries:
    # ... existing calculations ...
    
    # ADD DEBUG:
    if self.bars.bar_index % 100 == 0:  # Every 100 bars
        print(f"\nFeatures at bar {self.bars.bar_index}:")
        print(f"  F1 (RSI): {f1:.4f}")
        print(f"  F2 (WT): {f2:.4f}")
        print(f"  F3 (CCI): {f3:.4f}")
        print(f"  F4 (ADX): {f4:.4f}")
        print(f"  F5 (RSI): {f5:.4f}")
    
    return FeatureSeries(f1=f1, f2=f2, f3=f3, f4=f4, f5=f5)
```

## 🔍 Quick Debug Script

Create `debug_ml_zero.py`:
```python
#!/usr/bin/env python3
"""Quick debug for ML predictions returning 0"""

import pandas as pd
from config.settings import TradingConfig
from scanner.bar_processor import BarProcessor

# Load data
df = pd.read_csv("pinescript_style_ICICIBANK_2000bars.csv")
print(f"Loaded {len(df)} bars")

# Minimal config
config = TradingConfig(
    max_bars_back=500,  # Smaller for faster debug
    use_volatility_filter=False,  # Disable all filters
    use_regime_filter=False,
    use_adx_filter=False,
    use_kernel_filter=False,
    use_ema_filter=False,
    use_sma_filter=False
)

# Process with debug
processor = BarProcessor(config, total_bars=len(df))

# Process first 600 bars to see ML start
for i in range(600):
    bar = df.iloc[i]
    result = processor.process_bar(
        bar['open'], bar['high'], bar['low'], 
        bar['close'], bar['volume']
    )
    
    # Check when ML starts
    if i == 499:
        print(f"\n=== ML Should Start Next Bar ===")
    
    if i >= 500 and result.prediction != 0:
        print(f"First non-zero prediction at bar {i}: {result.prediction}")
        break
    elif i >= 500 and i % 10 == 0:
        print(f"Bar {i}: Still 0 prediction")

# Final analysis
ml = processor.ml_model
print(f"\nFinal ML state:")
print(f"Training labels count: {len(ml.y_train_array)}")
print(f"Unique labels: {set(ml.y_train_array)}")
```

## 📊 Expected vs Actual

### Expected (Pine Script):
- Training labels: Mix of 1, -1, 0
- Neighbors: 8 selected
- Predictions: Sum of neighbor labels (-8 to +8)

### Actual (Python):
- Training labels: ??? (need to check)
- Neighbors: ??? (need to check)
- Predictions: 0 (problem!)

## 💡 Most Likely Issues

1. **Price Not Moving**: If close prices are similar, all labels could be neutral
2. **Wrong Comparison**: Check if we're comparing prices correctly (4 bars apart)
3. **Integer Division**: Python 3 division might cause issues
4. **Feature Normalization**: All features might be normalizing to same value

## 🚀 Action Plan

1. Run the debug script first
2. Add debug logging to core files
3. Focus on training label distribution
4. Check if ICICIBANK data has price movements
5. Verify 4-bar price comparison logic

---

**Priority**: Figure out why ML predictions are 0
**Ignore**: Filters for now (they're secondary)
**Focus**: Training labels and neighbor selection
