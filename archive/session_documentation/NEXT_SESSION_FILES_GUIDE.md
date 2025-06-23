# 📂 Context Files for Next Session

## Primary Files to Read (In Order):

### 1. Quick Start (30 seconds)
**File**: `QUICK_START_ENTRY_DEBUG.md`
- Immediate commands to run
- What to look for
- Skip what's already done

### 2. Current Context (2 minutes)
**File**: `CURRENT_SESSION_CONTEXT.md`
- Complete session state
- What we discovered
- Next steps detailed

### 3. Issue Analysis (If Needed)
**File**: `ENTRY_SIGNAL_ISSUE_ANALYSIS.md`
- Deep dive into why entries = 0
- Code snippets showing the issue
- Multiple solution approaches

## Debug Scripts Ready to Run:

1. **debug_signal_transitions.py**
   - Tests with 4 market phases (up→sideways→down→up)
   - Multiple filter configurations
   - Should show signal transitions

2. **test_neutral_signal.py**
   - Tests neutral signal initialization
   - Simpler test case
   - Shows if signal stuck from start

3. **verify_enhanced_processor.py**
   - Confirms EnhancedBarProcessor features
   - Shows Pine Script style access working

## Key Understanding:

**The Problem**: 
- Signals stuck at -1 (never change)
- No transitions = No entries

**The Cause**:
- Test data too bearish (312 neg vs 83 pos)
- Filters too restrictive (14.9% pass)

**The Solution**:
- Need balanced data with trend changes
- Or real market data
- Or adjust filter thresholds

## Don't Waste Time On:
- ✅ Signal comparison logic (verified correct)
- ✅ ML predictions (working fine)
- ✅ Bar processor migration (complete)
- ✅ Array indexing (Pine Script style working)

## Focus Only On:
Getting signal TRANSITIONS!

---
**Start Here**: Run `python debug_signal_transitions.py`
