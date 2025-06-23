# Next Session Instructions - Phase 4

## 📍 Current Status
- **Phase 1**: ✅ Complete - Critical Bar Index Fixes
- **Phase 2**: ✅ Complete - Validation & Testing  
- **Phase 3**: ✅ Complete - Array History & NA Handling
- **Phase 4**: ⏳ Pending - Kernel & Advanced Features
- **Phase 5**: ⏳ Pending - Performance & Production

## 🎯 Phase 4 Tasks to Complete

### 1. Kernel Regression Validation
- Compare `kernel_functions.py` output with Pine Script
- Test both rational_quadratic and gaussian kernels
- Verify crossover detection logic
- Check smoothing behavior (use_kernel_smoothing parameter)

### 2. Dynamic Exit Logic
```python
# Current: Simplified exit after 4 bars
# Need: Full implementation of kernel-based exits
- endLongTradeDynamic
- endShortTradeDynamic
- Kernel crossover detection
- Multi-timeframe considerations
```

### 3. Streaming Mode Updates
```python
# Add to BarProcessor:
def update_bar_count(self):
    self.total_bars += 1
    self.max_bars_back_index = self._calculate_max_bars_back_index()
```

### 4. Missing Pine Script Functions
- Implement `ta.crossover()` and `ta.crossunder()`
- Check if any other Pine Script built-ins are needed
- Ensure exact behavior match

### 5. Stop Loss/Take Profit
- Add SL/TP calculation methods
- ATR-based stops
- Percentage-based targets
- Risk-reward ratios

## 📂 Key Files to Work On
1. `core/kernel_functions.py` - Validate accuracy
2. `scanner/signal_generator.py` - Dynamic exit logic
3. `scanner/bar_processor.py` - Streaming updates
4. `utils/risk_management.py` - Create new file for SL/TP

## 🧪 Testing Approach
1. Create `tests/test_kernel_validation.py`
2. Compare outputs with Pine Script CSV exports
3. Test with live streaming data
4. Validate exit conditions

## 💡 Important Notes
- All NA handling is complete (Phase 3)
- Array history not needed (confirmed)
- Focus on accuracy over performance
- Keep Pine Script logic exact

## 🚀 Quick Start Commands
```bash
# Navigate to project
cd /Users/knight/Desktop/projects/mcp-testing/lorentzian_classifier

# Run quick validation
python test_phase3_quick.py  # Should pass

# Start Phase 4 work
# Create kernel validation test first
```

## 📊 Expected Outcomes
After Phase 4:
- Kernel values match Pine Script ±1%
- Dynamic exits working correctly
- Streaming mode handles growing data
- All Pine Script features available
- Ready for Phase 5 optimization

## ⚠️ Reminders
- Don't break existing functionality
- Test each change incrementally
- Document any Pine Script discrepancies
- Keep bar-by-bar processing intact

---

**Start with kernel validation to ensure accuracy before adding new features.**
