# Filter Test Results Template

**Test Date**: [DATE]
**Tester**: [NAME]

## Test Configuration Summary

| Config | Vol Filter | Regime Filter | ADX Filter | Regime Threshold | ADX Threshold |
|--------|------------|---------------|------------|------------------|----------------|
| ALL_OFF | ❌ | ❌ | ❌ | -0.1 | 20 |
| VOLATILITY_ONLY | ✅ | ❌ | ❌ | -0.1 | 20 |
| REGIME_ONLY | ❌ | ✅ | ❌ | -0.1 | 20 |
| ADX_ONLY | ❌ | ❌ | ✅ | -0.1 | 20 |
| PINE_DEFAULTS | ✅ | ✅ | ❌ | -0.1 | 20 |
| VOL_REGIME | ✅ | ✅ | ❌ | -0.1 | 20 |
| ADJUSTED_THRESHOLDS | ✅ | ✅ | ✅ | 0.0 | 15 |

---

## Test 1: ALL_OFF (Baseline)

**Configuration**: ALL_OFF
**Purpose**: Verify ML system works without filters

### Results:
- **ML Predictions**: [ ] Working / [ ] Not Working
- **Prediction Range**: ___ to ___
- **Signal Transitions**: ___
- **Entry Signals**: ___
- **Filter Pass Rates**:
  - Volatility: ___%
  - Regime: ___%
  - ADX: ___%
  - Combined: ___%

### Sample Output:
```
[Paste relevant output here]
```

**Conclusion**: [ ] ML Working / [ ] ML Not Working

---

## Test 2: VOLATILITY_ONLY

**Configuration**: VOLATILITY_ONLY
**Purpose**: Test if volatility filter is too restrictive

### Results:
- **ML Predictions**: [ ] Working / [ ] Not Working
- **Prediction Range**: ___ to ___
- **Signal Transitions**: ___
- **Entry Signals**: ___
- **Filter Pass Rates**:
  - Volatility: ___%
  - Regime: 100% (OFF)
  - ADX: 100% (OFF)
  - Combined: ___%

### Sample Output:
```
[Paste relevant output here]
```

**Conclusion**: [ ] Reasonable / [ ] Too Restrictive / [ ] Needs Adjustment

---

## Test 3: REGIME_ONLY

**Configuration**: REGIME_ONLY
**Purpose**: Test if regime filter is too restrictive

### Results:
- **ML Predictions**: [ ] Working / [ ] Not Working
- **Prediction Range**: ___ to ___
- **Signal Transitions**: ___
- **Entry Signals**: ___
- **Filter Pass Rates**:
  - Volatility: 100% (OFF)
  - Regime: ___%
  - ADX: 100% (OFF)
  - Combined: ___%

### Sample Output:
```
[Paste relevant output here]
```

**Conclusion**: [ ] Reasonable / [ ] Too Restrictive / [ ] Needs Adjustment

---

## Test 4: ADX_ONLY

**Configuration**: ADX_ONLY
**Purpose**: Test if ADX filter blocks signals

### Results:
- **ML Predictions**: [ ] Working / [ ] Not Working
- **Prediction Range**: ___ to ___
- **Signal Transitions**: ___
- **Entry Signals**: ___
- **Filter Pass Rates**:
  - Volatility: 100% (OFF)
  - Regime: 100% (OFF)
  - ADX: ___%
  - Combined: ___%

### Sample Output:
```
[Paste relevant output here]
```

**Conclusion**: [ ] Reasonable / [ ] Too Restrictive / [ ] Needs Adjustment

---

## Test 5: PINE_DEFAULTS

**Configuration**: PINE_DEFAULTS
**Purpose**: Test with exact Pine Script defaults

### Results:
- **ML Predictions**: [ ] Working / [ ] Not Working
- **Prediction Range**: ___ to ___
- **Signal Transitions**: ___
- **Entry Signals**: ___
- **Filter Pass Rates**:
  - Volatility: ___%
  - Regime: ___%
  - ADX: 100% (OFF)
  - Combined: ___%

### Sample Output:
```
[Paste relevant output here]
```

**Conclusion**: [ ] Working / [ ] Too Restrictive for Daily

---

## Test 6: VOL_REGIME

**Configuration**: VOL_REGIME
**Purpose**: Test combination of volatility and regime

### Results:
- **ML Predictions**: [ ] Working / [ ] Not Working
- **Prediction Range**: ___ to ___
- **Signal Transitions**: ___
- **Entry Signals**: ___
- **Filter Pass Rates**:
  - Volatility: ___%
  - Regime: ___%
  - ADX: 100% (OFF)
  - Combined: ___%

### Sample Output:
```
[Paste relevant output here]
```

**Conclusion**: [ ] Reasonable / [ ] Too Restrictive

---

## Test 7: ADJUSTED_THRESHOLDS

**Configuration**: ADJUSTED_THRESHOLDS
**Purpose**: Test with relaxed thresholds for daily data

### Results:
- **ML Predictions**: [ ] Working / [ ] Not Working
- **Prediction Range**: ___ to ___
- **Signal Transitions**: ___
- **Entry Signals**: ___
- **Filter Pass Rates**:
  - Volatility: ___%
  - Regime: ___%
  - ADX: ___%
  - Combined: ___%

### Sample Output:
```
[Paste relevant output here]
```

**Conclusion**: [ ] Better Results / [ ] Still Too Restrictive

---

## Summary & Recommendations

### Most Restrictive Filter:
[ ] Volatility
[ ] Regime
[ ] ADX
[ ] Combination Effect

### Recommended Configuration for Daily Data:
[ ] ALL_OFF
[ ] VOLATILITY_ONLY
[ ] REGIME_ONLY
[ ] PINE_DEFAULTS
[ ] ADJUSTED_THRESHOLDS
[ ] Custom: _____________

### Specific Threshold Adjustments Needed:
- Regime Threshold: Change from -0.1 to ___
- ADX Threshold: Change from 20 to ___
- Other: _______________

### Final Notes:
[Add any observations or recommendations]

---

**Test Completed By**: _______________
**Date**: _______________
**Time Taken**: _______________
