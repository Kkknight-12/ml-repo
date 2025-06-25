# Branch Strategy for Lorentzian Classification Optimization

## Current Branch Structure

### `main`
- Stable, working Lorentzian Classification system
- 75% win rate with 3.7% average wins
- All core functionality tested and working

### `feature/phase1-optimization` (CURRENT)
**Goal**: Increase average win from 3.7% to 7-10%

**Features**:
- ✅ Comprehensive backtesting framework
- ✅ Multi-target exit system
- ✅ ATR-based stop losses
- ✅ Modular architecture for A/B testing
- 🔄 Integration of optimized settings
- 🔄 Performance comparison tools

**Next Steps**:
1. Test multi-target exits on real data
2. Compare baseline vs optimized performance
3. Integrate best performing exit strategy

### `feature/phase2-enhancements` (PLANNED)
**Goal**: Add proven enhancements that increase profitability

**Planned Features**:
- Market mode detection (Ehlers trend vs cycle)
- Time window optimization (11:30-1:30 PM)
- Dynamic exits based on market conditions
- Basic correlation features (Nifty correlation)
- Volume surge detection

**Merge Criteria**: Only if Phase 1 achieves 6%+ average wins

### `feature/phase3-advanced-features` (FUTURE)
**Goal**: Add advanced ML and alternative data

**Planned Features**:
- XGBoost directional confirmation
- News sentiment integration
- Economic event calendar
- Inter-market analysis
- GMM clustering for market regimes

**Merge Criteria**: Only if simpler features prove profitable

## Branch Workflow

1. **Development**: All new features in feature branches
2. **Testing**: Comprehensive backtesting before merge
3. **Merge Criteria**: 
   - Must improve profit factor by >10%
   - OR increase average win by >20%
   - OR reduce drawdown by >15%
4. **Documentation**: Update metrics after each merge

## Git Commands Reference

```bash
# Switch between branches
git checkout feature/phase1-optimization
git checkout main

# Merge when ready (from main)
git merge feature/phase1-optimization

# Check branch status
git branch -a

# Delete branch after merge
git branch -d feature/phase1-optimization
```

## Current Status
- Working on: `feature/phase1-optimization`
- Phase 1 completion: 60%
- Ready to test multi-target exits