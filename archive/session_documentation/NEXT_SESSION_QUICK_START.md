# 🚀 QUICK START FOR NEXT SESSION

## 📂 Project Location
```bash
cd /Users/knight/Desktop/projects/mcp-testing/lorentzian_classifier/
```

## 🧹 First Steps (If Needed)
```bash
# Clear Python cache if seeing old errors
find . -type d -name __pycache__ -exec rm -rf {} +
find . -name "*.pyc" -delete
```

## 🧪 Key Test Commands
```bash
# Test ML predictions (should show -8 to +8 range)
python test_ml_fix_final.py

# Test crossover functions
python test_crossover_functions.py

# Test compatibility
python test_compatibility.py

# Debug entry signals
python test_enhanced_current_conditions.py
```

## 📊 Current Status Summary

### ✅ What's Working:
- ML predictions: -8 to +8 range ✅
- All filters working correctly ✅
- Pine Script logic converted ✅
- Backward compatibility maintained ✅

### ⚠️ What Needs Attention:
- **Entry Signals = 0** (need balanced test data)
- Real market data testing pending
- Performance optimization needed

## 🎯 Next Session Focus

### Priority 1: Fix Entry Signals
```python
# Problem: Test data only generates bearish signals
# Solution: Create balanced data with trend changes

# Quick test with balanced data:
python generate_balanced_test_data.py  # TODO: Create this
python test_ml_fix_final.py
```

### Priority 2: Real Data Testing
```python
# Fetch real market data
python fetch_pinescript_style_data.py

# Test with ICICI Bank daily
python test_icici_daily.py
```

## 📝 Key Files to Review

### Documentation:
- `SESSION_CONTEXT.md` - Complete project state
- `README_SINGLE_SOURCE_OF_TRUTH.md` - Main reference
- `PHASE_5_PLAN.md` - Next phase details

### Core Files:
- `scanner/bar_processor.py` - Main engine
- `scanner/signal_generator.py` - Entry logic
- `ml/lorentzian_knn.py` - ML algorithm

## 💡 Remember

1. **Entry signals need signal transitions**
   - Current: All signals = -1 (bearish)
   - Need: Mix of -1, 0, 1 signals

2. **ML predictions are separate from signals**
   - Prediction: Raw ML output (-8 to +8)
   - Signal: After filters (-1, 0, 1)
   - Entry: When signal changes

3. **Test with real data next**
   - Synthetic data may not capture market dynamics
   - Use Zerodha API for real historical data

## 🔗 Quick Links

- Pine Script files: `/original pine scripts/`
- Test scripts: Root directory
- Documentation: Root directory (*.md files)

---

**Ready to continue? Start with fixing entry signal generation!**
