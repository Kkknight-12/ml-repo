# Deprecation and Migration Guide - June 26, 2025

## Overview
Migrated from old `backtest_framework` to `backtest_framework_enhanced` to ensure all fixes are properly applied.

## Files Deprecated

### 1. `backtest_framework.py` → `DEPRECATED_backtest_framework.py`
- Old backtesting framework without multi-target exit support
- Does not use the enhanced bar processor with our ML fixes

### 2. `test_timeframe_optimization.py` → `DEPRECATED_test_timeframe_optimization.py`
- Used only the old backtest framework
- Needs rewriting if timeframe optimization is needed

### 3. Previously deprecated files:
- `ml/lorentzian_knn_fixed.py` → `ml/DEPRECATED_lorentzian_knn_fixed.py`
- `scanner/signal_generator.py` → `scanner/DEPRECATED_signal_generator.py`

## Files Updated

### 1. `analyze_trading_performance.py`
- Changed from `BacktestEngine` to `EnhancedBacktestEngine`
- Now uses the enhanced framework with all ML fixes

### 2. `test_multi_target_exits.py`
- Updated imports to use only `EnhancedBacktestEngine`
- Already had both imports, cleaned up to use only enhanced

### 3. `test_multi_target_simple.py`
- Updated to use `EnhancedBacktestEngine` consistently
- Removed dependency on old framework

### 4. `diagnose_trade_quality.py`
- Updated imports to use enhanced framework
- Now properly uses fixed ML implementation

### 5. `backtest_framework_enhanced.py`
- Made standalone (no longer inherits from old BacktestEngine)
- Added `BacktestMetrics` and `TradeResult` classes directly
- Added missing `__init__` and `_get_historical_data` methods

## Migration Steps for Other Files

If you have other files using the old framework:

1. Update imports:
   ```python
   # Old
   from backtest_framework import BacktestEngine
   
   # New
   from backtest_framework_enhanced import EnhancedBacktestEngine
   ```

2. Update class instantiation:
   ```python
   # Old
   engine = BacktestEngine()
   
   # New
   engine = EnhancedBacktestEngine()
   ```

3. The API is mostly the same, but enhanced version:
   - Properly implements multi-target exits
   - Uses enhanced bar processor with ML fixes
   - Tracks partial trades

## Why This Migration is Important

The old `backtest_framework` was not using:
1. The fixed ML prediction logic (feature array timing fix)
2. The corrected filter settings (ADX disabled)
3. The enhanced bar processor
4. Multi-target exit functionality

This explains why the win rate was still showing 36.2% - the old framework wasn't using our fixes!

## Next Steps

Run `analyze_trading_performance.py` again to see the improved results with:
- Non-zero ML predictions (86.4% of bars)
- Proper filter effectiveness
- Improved win rate (target >45%)