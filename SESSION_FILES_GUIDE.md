# 📚 Session Progress Files Guide

## 🔴 Current Issue
ML predictions return 0 when filters are ON (but work when filters are OFF)

## 📋 Essential Reading Order

### 1. Quick Start (Read First!)
- `QUICK_START_DEBUG.md` - Start here for immediate action

### 2. Issue Details
- `PHASE_4B_DEBUG_SUMMARY.md` - Detailed issue analysis
- `NEXT_SESSION_DEBUG_ML_ZERO.md` - Step-by-step debug instructions

### 3. Progress Tracking
- `README_SINGLE_SOURCE_OF_TRUTH.md` - Main documentation (see sections 6 & 7)
- `PHASE_4_PROGRESS.md` - Full phase 4 progress (95% complete)
- `PHASE_4_QUICK_STATUS.md` - Quick status check

## 🛠️ Debug Scripts Created

```bash
# Compare filter configurations
python debug_ml_with_filters.py

# Deep dive ML algorithm
python debug_ml_internals.py

# Try potential fixes
python test_with_fixes.py
```

## 📂 Key Code Files to Debug

```
ml/lorentzian_knn.py         # ML prediction logic
scanner/bar_processor.py     # Main processing (check filter interaction)
core/ml_extensions.py        # Filter implementations
original pine scripts/       # Reference for correct behavior
```

## 🎯 Success Criteria

1. Get ML predictions != 0 with filters ON
2. Generate at least 1 buy/sell signal
3. Understand why filters affect ML

## 💡 Quick Debug Command

```bash
# Add this to bar_processor.py after prediction calculation:
print(f"DEBUG Bar {bar_index}: Raw Prediction={prediction}, Filter All={filter_all}, Signal={signal}")
```

## 📊 What We Know

✅ **Working**:
- ML algorithm (verified with filters OFF)
- Sliding window implementation
- Training label generation
- Feature calculations

❌ **Not Working**:
- ML predictions when filters are ON
- Signal generation (due to 0 predictions)

## 🚀 Next Steps

1. Run debug scripts
2. Find which filter causes issue
3. Fix the problematic code
4. Verify signals generate

---

**Remember**: The ML algorithm is correct! The issue is in how filters interact with ML. Focus on that interaction point.
