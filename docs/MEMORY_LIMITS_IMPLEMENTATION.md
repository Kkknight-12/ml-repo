# Memory Limits Implementation

## Overview

This document describes the memory limit implementation for persistent arrays in the Lorentzian Classifier system. These limits prevent arrays from growing indefinitely in production environments, ensuring stable memory usage during long-running operations.

## Why Memory Limits Are Needed

In Pine Script, arrays have built-in size limits (typically 10,000 elements). In Python, arrays can grow indefinitely, which can lead to:
- Memory exhaustion in production
- Performance degradation over time
- System instability during extended runs

## Implementation Details

### 1. Configuration (`config/memory_limits.py`)

Defines maximum sizes for all persistent arrays:

```python
MAX_ARRAY_SIZE = 10000           # General limit matching Pine Script
MAX_FEATURE_ARRAY_SIZE = 10000   # Historical features for k-NN
MAX_TRAINING_ARRAY_SIZE = 10000  # ML training labels
MAX_PREDICTIONS_ARRAY_SIZE = 100  # Sliding window (safety limit)
MAX_BAR_HISTORY_SIZE = 5000      # OHLCV data history
MAX_SIGNAL_HISTORY_SIZE = 20     # Recent signals for flip detection
MAX_ENTRY_HISTORY_SIZE = 20      # Recent entries
```

### 2. Cleanup Strategy

Arrays are cleaned up using a threshold approach:
- **Trigger**: Cleanup starts when array reaches 90% of max size
- **Action**: Remove oldest 10% of data
- **Benefit**: Prevents frequent reallocation while maintaining limits

### 3. Affected Components

#### ML Model (`ml/lorentzian_knn_fixed_corrected.py`)
- **Training array** (`y_train_array`): Limited to 10,000 entries
- **Predictions array**: Limited to 100 (though typically only 8 needed)
- Cleanup removes oldest training data when limit exceeded

#### Bar Processor (`scanner/enhanced_bar_processor.py`)
- **Feature arrays**: Limited to 10,000 entries per feature
- **Bar history**: Limited to 5,000 bars
- **Signal/entry history**: Limited to 20 entries
- Uses batch cleanup when threshold reached

## Usage Example

```python
from config.memory_limits import MAX_TRAINING_ARRAY_SIZE, should_cleanup

# In update_training_data method
self.y_train_array.append(y_train_series)

# Check memory limit
if len(self.y_train_array) > MAX_TRAINING_ARRAY_SIZE:
    items_to_remove = calculate_items_to_remove(len(self.y_train_array))
    if items_to_remove > 0:
        self.y_train_array = self.y_train_array[items_to_remove:]
```

## Testing

Run `test_memory_limits.py` to verify:
1. Training arrays respect limits
2. Feature arrays respect limits
3. Cleanup functions work correctly
4. Signal/entry histories are limited

## Production Considerations

1. **Monitor Memory Usage**: Use system monitoring to track actual memory consumption
2. **Adjust Limits**: Based on available RAM and data characteristics
3. **Log Cleanups**: Consider logging when cleanup occurs for debugging
4. **Performance**: Cleanup is O(n) but infrequent due to threshold approach

## Pine Script Compatibility

These limits ensure Python behavior matches Pine Script:
- Pine Script arrays are limited to ~10,000 elements
- Our implementation uses the same limit
- Maintains compatibility while preventing memory issues

## Future Enhancements

1. **Configurable Limits**: Allow runtime configuration
2. **Adaptive Cleanup**: Adjust cleanup percentage based on memory pressure
3. **Metrics Collection**: Track cleanup frequency and impact
4. **Memory Profiling**: Integration with memory profilers