# Filter Tracking Bug Fix Documentation

## Issue Found
The comprehensive test was showing 0.0% filter pass rate because of a key mismatch bug.

## Root Cause
```python
# Enhanced bar processor returns:
result.filter_states = {
    "volatility": True/False,
    "regime": True/False,
    "adx": True/False
}

# But comprehensive test was looking for:
if filter_name in results['filter_states']:  # This never matched!
    results['filter_states'][f"{filter_name}_passes"] += 1

# Because results['filter_states'] had keys like:
# "volatility_passes", "regime_passes", etc.
```

## Fix Applied
Changed the filter tracking logic in `test_zerodha_comprehensive.py`:

```python
# OLD (Broken):
if passed and filter_name in results['filter_states']:
    results['filter_states'][f"{filter_name}_passes"] += 1

# NEW (Fixed):
key = f"{filter_name}_passes"
if passed and key in results['filter_states']:
    results['filter_states'][key] += 1
```

## Additional Fixes
1. Removed 'kernel_passes' from filter_states initialization (not tracked by bar processor)
2. Removed 'kernel' from filter calculation loops
3. Created test script `test_filter_fix.py` to verify the fix

## To Verify Fix
Run the comprehensive test again:
```bash
python test_zerodha_comprehensive.py
```

Expected: Filter pass rates should now show actual percentages instead of 0.0%

## Impact
- Previous tests were correctly processing filters but not tracking stats
- Entry signals were still generated correctly (that's why we saw 3 entries)
- Now filter statistics will be accurately reported
