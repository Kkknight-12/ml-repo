# Array Conversion Example: Training Labels

## Pine Script Original
```pinescript
// Training label array declaration
var y_train_array = array.new_int(0)

// Update training labels (looks 4 bars back)
y_train_series = src[4] < src[0] ? direction.short : 
                src[4] > src[0] ? direction.long : direction.neutral
array.push(y_train_array, y_train_series)
```

## Python Implementation
```python
class LorentzianKNN:
    def __init__(self):
        # Equivalent to: var y_train_array = array.new_int(0)
        self.y_train_array: List[int] = []
    
    def update_training_data(self, src_current: float, src_4bars_ago: float):
        """
        Pine Script:
        y_train_series = src[4] < src[0] ? direction.short :
                        src[4] > src[0] ? direction.long : direction.neutral
        """
        if src_4bars_ago < src_current:
            label = self.label.short  # -1
        elif src_4bars_ago > src_current:
            label = self.label.long   # 1
        else:
            label = self.label.neutral # 0
        
        # Equivalent to: array.push(y_train_array, y_train_series)
        self.y_train_array.append(label)
```

## Key Differences Handled

### 1. Array Declaration
- **Pine**: `var array.new_int(0)` - Creates empty integer array once
- **Python**: `self.y_train_array: List[int] = []` - Creates empty list in __init__

### 2. Historical Price Access
- **Pine**: `src[4]` - Automatic historical referencing
- **Python**: Explicit parameter `src_4bars_ago` passed from bar processor

```python
# In bar_processor.py
if len(self.close_values) > 4:
    self.ml_model.update_training_data(
        close,                  # Current close (src[0])
        self.close_values[4]    # 4 bars ago (src[4])
    )
```

### 3. Array Growth
- **Pine**: `array.push()` adds to end of array
- **Python**: `list.append()` adds to end of list

Both maintain chronological order with oldest labels first.

## ML Algorithm Usage
```python
def predict(self, ...):
    # Access training labels in chronological order
    for i in range(size_loop + 1):
        # Get label for this historical point
        if i < len(self.y_train_array):
            self.predictions.append(float(self.y_train_array[i]))
```

## Memory Management
Unlike Pine Script which has automatic limits, Python implementation must manually manage array size if needed. Currently, `y_train_array` grows unbounded, but this matches Pine Script behavior for training labels.