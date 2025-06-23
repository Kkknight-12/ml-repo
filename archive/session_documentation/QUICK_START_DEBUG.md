# QUICK START: Debug Filter Issue

## The Problem
Comprehensive test showing 0% filter pass rate while generating entry signals (filters must be working)

## Quick Commands to Run
```bash
cd /Users/knight/Desktop/projects/mcp-testing/lorentzian_classifier

# 1. Quick filter comparison test
python test_filter_comparison.py

# 2. Test debug logging (small dataset)
python test_debug_processor.py

# 3. Run comprehensive test with debug output
python test_zerodha_comprehensive.py > debug_output.txt 2>&1

# 4. Check the output
tail -n 50 debug_output.txt
```

## What to Look For

### In `test_filter_comparison.py` output:
- Should show ~40% volatility, ~35% regime pass rates for both tests
- If one shows 0%, there's a bug in that specific test

### In `debug_output.txt`:
Look for patterns like:
```
Bar X | FILTER RESULTS:
  - Volatility Filter: true (Enabled: true)
  - Regime Filter: false (Enabled: true)  
  - ADX Filter: true (Enabled: false)
```

### If All Filters Show 0%:
1. Check if `result.filter_states` is None
2. Check if warmup period is too long (skipping good bars)
3. Check if enhanced processor is returning filter states

## Key Files
- `scanner/enhanced_bar_processor_debug.py` - Debug version
- `test_zerodha_comprehensive.py` - Main test (updated)
- `DEBUG_LOGGING_IMPLEMENTATION.md` - Full details

## Next Steps Based on Results
1. **If filter comparison shows different rates**: Bug in comprehensive test tracking
2. **If both show 0%**: Issue with enhanced filter calculations
3. **If debug shows filter states are None**: Bar processor issue

Good luck! 🚀
