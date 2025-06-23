# 📊 PHASE 2: Validation & Testing Plan

## Available Test Data

### 5-Minute Data:
1. `NSE_ICICIBANK, 5.csv` - 300 bars ✅ (already tested)
2. `NSE_HDFCBANK, 5.csv` - ? bars
3. `NSE_RELIANCE, 5.csv` - ? bars
4. `NSE_TCS, 5.csv` - ? bars

### Daily Data:
1. `NSE_ICICIBANK, 1D.csv` - ? bars

## Validation Tasks

### Task 1: Multi-Stock 5-Minute Validation
- [ ] Test HDFCBANK 5-minute data
- [ ] Test RELIANCE 5-minute data
- [ ] Test TCS 5-minute data
- [ ] Compare signal patterns across stocks

### Task 2: Daily vs Intraday Comparison
- [ ] Test ICICIBANK daily data
- [ ] Compare daily signals with 5-minute aggregated signals
- [ ] Verify indicator calculations on different timeframes

### Task 3: Signal Quality Analysis
- [ ] Count total signals per stock
- [ ] Analyze signal distribution (buy/sell ratio)
- [ ] Check signal timing accuracy
- [ ] Measure prediction strength patterns

### Task 4: Cross-Stock Correlation
- [ ] Check if signals appear simultaneously across stocks
- [ ] Analyze market-wide patterns
- [ ] Identify stock-specific behaviors

### Task 5: Edge Case Testing
- [ ] Test with incomplete data
- [ ] Test with gap periods
- [ ] Test with extreme price movements

## Validation Metrics to Track

### Per Stock:
1. **Signal Count**: Total, Buy, Sell
2. **Signal Quality**: Average prediction strength
3. **Filter Performance**: Pass rates for each filter
4. **Kernel Accuracy**: Difference from Pine Script
5. **ML Performance**: When predictions start

### Aggregate:
1. **Cross-stock correlation**: Similar signals across stocks
2. **Time-based patterns**: Signal clustering
3. **Filter effectiveness**: Which filters block most signals
4. **Overall accuracy**: Match with Pine Script

## Expected Outcomes

### Good Signs ✅:
- Balanced buy/sell ratios (0.5 - 2.0)
- Kernel accuracy < 1% difference
- Signals during volatile periods
- Different patterns per stock

### Warning Signs ⚠️:
- Too many signals (>20% of bars)
- All buy or all sell signals
- Kernel difference > 5%
- No signals at all

### Red Flags 🚨:
- Crashes or errors
- Signals on every bar
- Completely different from Pine Script
- Same signals across all stocks

## Deliverables

1. **Validation Report** (`PHASE_2_VALIDATION_REPORT.md`)
   - Summary statistics for each stock
   - Key findings and issues
   - Recommendations for Phase 3/4

2. **Comparison Matrix** (`validation_results.csv`)
   - Stock-by-stock metrics
   - Easy comparison format

3. **Issue List** (`validation_issues.md`)
   - Specific problems found
   - Priority ranking
   - Suggested fixes

---

**Ready to start validation!**