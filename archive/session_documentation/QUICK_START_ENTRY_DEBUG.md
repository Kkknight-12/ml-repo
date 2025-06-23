# 🚨 QUICK START - Entry Signal Debug

## THE ISSUE
**Entry Signals = 0** (should be ~16)
- ML predictions: ✅ Working (-8 to +8)
- Signals: ❌ Stuck at -1 (no transitions)
- Cause: Biased test data + low filter pass rate

## IMMEDIATE NEXT STEPS

### 1. Run Debug Script (5 seconds)
```bash
cd /Users/knight/Desktop/projects/mcp-testing/lorentzian_classifier/
python debug_signal_transitions.py
```
This tests with balanced data (up→sideways→down→up trends)

### 2. Check Output For:
- Do signals transition? (Should see -1→0→1 changes)
- Which filter config works best?
- Are entries generated with balanced data?

### 3. If Still No Entries:
```bash
# Try with minimal filters
python test_neutral_signal.py

# Check real data (if available)
python test_icici_daily.py
```

## KEY FILES
- **CURRENT_SESSION_CONTEXT.md** - Full context
- **ENTRY_SIGNAL_ISSUE_ANALYSIS.md** - Detailed analysis
- **debug_signal_transitions.py** - Main debug script

## WHAT WE KNOW
- Signal comparison logic: ✅ Correct
- ML predictions: ✅ Working
- Test files: ✅ All using EnhancedBarProcessor
- Issue: Signals stuck at -1, need transitions for entries

## DON'T WASTE TIME ON
- Signal comparison logic (already verified correct)
- ML prediction issues (working fine)
- Migrating to EnhancedBarProcessor (already done)

## FOCUS ON
Getting signal TRANSITIONS with better test data!
