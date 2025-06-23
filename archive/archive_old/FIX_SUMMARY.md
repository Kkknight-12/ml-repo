# Quick Reference - Bar Index Fix

## 🔴 THE PROBLEM
Pine Script: `maxBarsBackIndex = last_bar_index - 2000` (knows total bars)
Python: `max_bars_back_index = bar_index - 2000` (was using current bar) ❌

## 🟢 THE FIX
```python
# BarProcessor now accepts total_bars
processor = BarProcessor(config, total_bars=len(data))
```

## 📍 CRITICAL INSIGHT
ML was starting at bar 0 with NO training data! Should start after 2000 bars.

## 📝 PENDING
- Update all test files to pass total_bars
- Update main.py demo
- Test the fix with real data

## 🎯 EXPECTED RESULT
More signals, better quality predictions, no stuck states!

---
*Pine Script has complete context, Python needs it explicitly.*