# Update Guide: Regular BarProcessor → EnhancedBarProcessor

## Why Update?
EnhancedBarProcessor has correct Pine Script style array history referencing logic.

## Changes for Each Test File:

### 1. test_ml_fix_final.py
```python
# OLD:
from scanner.bar_processor import BarProcessor
processor = BarProcessor(config)

# NEW:
from scanner.enhanced_bar_processor import EnhancedBarProcessor
processor = EnhancedBarProcessor(config, "TEST_SYMBOL", "5minute")
```

### 2. test_enhanced_current_conditions.py
```python
# OLD:
from scanner.bar_processor import BarProcessor
processor = BarProcessor(config)

# NEW:
from scanner.enhanced_bar_processor import EnhancedBarProcessor
processor = EnhancedBarProcessor(config, "TEST", "5minute")
```

### 3. test_all_fixes.py
```python
# OLD:
from scanner.bar_processor import BarProcessor
processor = BarProcessor(config)

# NEW:
from scanner.enhanced_bar_processor import EnhancedBarProcessor
processor = EnhancedBarProcessor(config, "TEST", "5minute")

# Also update the historical reference test:
# OLD:
if len(processor.close_values) >= 5:
    current = processor.close_values[-1]
    four_bars_ago = processor.close_values[-5]

# NEW (Pine Script style):
if len(processor.bars) >= 5:
    current = processor.bars.close[0]
    four_bars_ago = processor.bars.close[4]
```

### 4. Other Test Files
The following already use EnhancedBarProcessor or compatibility layer:
- ✅ test_icici_daily.py (already using Enhanced)
- ✅ test_compatibility.py (tests both)
- ✅ example_parameter_passing.py (uses create_processor)

## Quick Script to Update All Files:

```bash
# Run this to see which files need updating:
grep -l "from scanner.bar_processor import BarProcessor" *.py

# Files to update:
# - test_ml_fix_final.py
# - test_enhanced_current_conditions.py
# - test_all_fixes.py
```

## Benefits After Update:
1. Pine Script style: `processor.bars.close[0]`
2. Custom series: `processor.ml_predictions[0]`
3. Symbol tracking: `processor.symbol`
4. Timeframe aware: `processor.timeframe`
5. Better debugging with enhanced output
