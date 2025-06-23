# Original Pine Script Source Code

This folder contains the original Pine Script source code for reference during Python conversion.

## Files:

### 1. **Lorentzian Classification.txt**
The main indicator script containing:
- Core ML algorithm (Lorentzian KNN)
- Signal generation logic
- Entry/exit conditions
- Default parameter values

### 2. **MLExtensions.txt**
Machine Learning extension library containing:
- Normalization functions (normalize, rescale)
- Technical indicators (n_rsi, n_wt, n_cci, n_adx)
- Filter functions (volatility, regime, ADX)
- Helper functions

### 3. **KernelFunctions.txt**
Kernel regression library containing:
- Rational Quadratic kernel
- Gaussian kernel
- Nadaraya-Watson estimator implementation

## Important Default Values:

```pinescript
// From main script:
useVolatilityFilter = true
useRegimeFilter = true
useAdxFilter = false      // ← Important: OFF by default
useEmaFilter = false
useSmaFilter = false
useKernelFilter = true
useKernelSmoothing = false

// ML Parameters:
neighborsCount = 8
maxBarsBack = 2000
featureCount = 5
```

## Key Logic Patterns:

### Two-Layer Filtering:
1. **ML Signal Layer**: `filter_all = volatility AND regime AND adx`
2. **Entry Signal Layer**: `isNewBuySignal AND isBullish AND trends`

### Continuous Learning:
- No train/test split
- Uses ALL available data
- Learns and predicts simultaneously

## Usage:

Always refer to these files when:
- Verifying calculation logic
- Checking default values
- Understanding signal flow
- Debugging discrepancies

---

**Note**: These are the authoritative source for how the algorithm should work.
