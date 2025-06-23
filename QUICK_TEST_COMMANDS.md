# Quick Test Commands

## 1. Run Comprehensive Fix Test
```bash
cd /Users/knight/Desktop/projects/mcp-testing/lorentzian_classifier
python test_comprehensive_fix_verification.py
```

## 2. Run Original Test (for comparison)
```bash
python test_fixed_implementation.py
```

## 3. Check Test Results
```bash
cat test_results/comprehensive_fix_verification.json | python -m json.tool
```

## 4. Quick Debug Check
```python
# In Python REPL
from ml.lorentzian_knn_fixed import LorentzianKNNFixed
from config.settings import TradingConfig

# Check if imports work
config = TradingConfig()
model = LorentzianKNNFixed(config.get_settings(), config.get_label())
print(f"Initial neighbors: {model.get_neighbor_count()}")  # Should be 0
```

## 5. Monitor Live Output
```bash
# Run test with full logging
python test_comprehensive_fix_verification.py 2>&1 | tee test_output.log
```

## Expected Results Summary:
- **Regime Filter**: 30-40% pass rate ✅
- **ML Neighbors**: 8 neighbors reached ✅
- **Both fixes**: WORKING ✅

## If Issues:
1. Check `test_results/comprehensive_fix_verification.json`
2. Look for error patterns in logs
3. Verify Zerodha connection is active
