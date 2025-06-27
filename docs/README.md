# Lorentzian Classification System Documentation

## 📚 Documentation Structure

This documentation is organized by phases and purpose to help you navigate efficiently.

## 🚀 Quick Start
1. **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)** - Start here for system overview
2. **[ML_OPTIMIZATION_QUICK_GUIDE.md](ML_OPTIMIZATION_QUICK_GUIDE.md)** - Quick implementation reference
3. **[LIVE_TRADING_SIMULATION_GUIDE.md](LIVE_TRADING_SIMULATION_GUIDE.md)** - Test with live data

## 📖 Core Documentation

### Phase 1: Foundation & Optimization
- **[PHASE1_OPTIMIZATION_RESULTS.md](PHASE1_OPTIMIZATION_RESULTS.md)** - Journey from 36% to 50%+ win rate
- **[ML_PREDICTION_FIX_2025_06_26.md](ML_PREDICTION_FIX_2025_06_26.md)** - Critical ML bug fix details
- **[optimization_plan.md](optimization_plan.md)** - Original optimization strategy

### Phase 2: Exit Strategies & Risk Management
- **[quantitative_exits_implementation.md](quantitative_exits_implementation.md)** - Exit formulas from trading books
- **[exit_strategies_implemented.md](exit_strategies_implemented.md)** - Current exit strategy implementations
- **[trading_knowledge_update.md](trading_knowledge_update.md)** - Book-based trading rules

### Phase 3: Advanced Features (In Progress)
- **[ROCKET_SCIENCE_INTEGRATION_PLAN.md](ROCKET_SCIENCE_INTEGRATION_PLAN.md)** - Ehlers DSP techniques
- **[SYSTEM_FINE_TUNING_GUIDE.md](SYSTEM_FINE_TUNING_GUIDE.md)** - Comprehensive tuning reference

### Phase 4: Implementation & Testing
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Technical implementation details
- **[MODULAR_ARCHITECTURE_GUIDE.md](MODULAR_ARCHITECTURE_GUIDE.md)** - System modularity guide

## 📊 Key Metrics & Performance

### Current System Performance
- **Win Rate**: 50-65% (optimized from 36%)
- **Average Win**: 6-8% (improved from 3.7%)
- **Risk/Reward**: 2:1 minimum
- **Expectancy**: Must be positive
- **CAR/MaxDD**: Target > 1.0

### Critical Formulas
```python
# Expectancy (must be positive)
Expectancy = (% Winners * Avg Win) - (% Losers * Avg Loss)

# CAR/MaxDD (primary optimization metric)
CAR/MaxDD = Annualized Return / Maximum Drawdown

# Position Sizing
Position Size = (Account * Risk%) / (Entry - Stop Loss)
```

## 🔄 System Evolution

### Completed Optimizations
1. ✅ Fixed ML prediction bug (feature array timing)
2. ✅ Implemented multi-target exits
3. ✅ Added ATR-based dynamic stops
4. ✅ Integrated book-based exit strategies
5. ✅ Created modular architecture

### In Progress
1. 🔄 Ehlers market mode detection
2. 🔄 Adaptive indicator implementation
3. 🔄 Full system backtesting

## 📁 Document Categories

### Essential Daily References
- [ML_OPTIMIZATION_QUICK_GUIDE.md](ML_OPTIMIZATION_QUICK_GUIDE.md)
- [LIVE_TRADING_SIMULATION_GUIDE.md](LIVE_TRADING_SIMULATION_GUIDE.md)
- [exit_strategies_implemented.md](exit_strategies_implemented.md)

### Technical References
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)
- [MODULAR_ARCHITECTURE_GUIDE.md](MODULAR_ARCHITECTURE_GUIDE.md)
- [quantitative_exits_implementation.md](quantitative_exits_implementation.md)

### Historical/Research
- [PHASE1_OPTIMIZATION_RESULTS.md](PHASE1_OPTIMIZATION_RESULTS.md)
- [ML_PREDICTION_FIX_2025_06_26.md](ML_PREDICTION_FIX_2025_06_26.md)

### Future Development
- [ROCKET_SCIENCE_INTEGRATION_PLAN.md](ROCKET_SCIENCE_INTEGRATION_PLAN.md)
- [SYSTEM_FINE_TUNING_GUIDE.md](SYSTEM_FINE_TUNING_GUIDE.md)

## 🎯 Navigation by Goal

### "I want to understand the system"
1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)
2. [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)

### "I want to run live tests"
1. [ML_OPTIMIZATION_QUICK_GUIDE.md](ML_OPTIMIZATION_QUICK_GUIDE.md)
2. [LIVE_TRADING_SIMULATION_GUIDE.md](LIVE_TRADING_SIMULATION_GUIDE.md)

### "I want to optimize performance"
1. [SYSTEM_FINE_TUNING_GUIDE.md](SYSTEM_FINE_TUNING_GUIDE.md)
2. [PHASE1_OPTIMIZATION_RESULTS.md](PHASE1_OPTIMIZATION_RESULTS.md)

### "I want to understand exits"
1. [quantitative_exits_implementation.md](quantitative_exits_implementation.md)
2. [exit_strategies_implemented.md](exit_strategies_implemented.md)

## 🔗 Cross-References

- **Optimization Journey**: [ML_PREDICTION_FIX](ML_PREDICTION_FIX_2025_06_26.md) → [PHASE1_RESULTS](PHASE1_OPTIMIZATION_RESULTS.md) → [QUICK_GUIDE](ML_OPTIMIZATION_QUICK_GUIDE.md)
- **Exit Strategies**: [quantitative_exits](quantitative_exits_implementation.md) → [exit_strategies](exit_strategies_implemented.md) → [trading_knowledge](trading_knowledge_update.md)
- **Advanced Features**: [ROCKET_SCIENCE](ROCKET_SCIENCE_INTEGRATION_PLAN.md) → [FINE_TUNING](SYSTEM_FINE_TUNING_GUIDE.md)

## 📝 Notes
- All documents are interconnected - use cross-references to dive deeper
- Phase 1-2 are complete and tested
- Phase 3-4 are in active development
- Check archived docs only for historical context

---
*Last Updated: 2025-06-26*