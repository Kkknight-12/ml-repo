# Lorentzian Classification Trading System

## Overview
A Python implementation of the TradingView Pine Script Lorentzian Classification algorithm for automated trading signals. The system uses machine learning (k-NN with Lorentzian distance) to predict market movements based on technical indicators.

## Current Status
- ✅ **Core ML Algorithm**: Fully implemented with critical bug fixes
- ✅ **Signal Generation**: Optimized from 36% to 50-65% win rate  
- ✅ **Live Trading**: Simulation mode with AI enhancements
- ✅ **Exit Strategies**: Multi-target system implemented (4 strategies)
- ✅ **Phase 1**: 100% complete - Scalping strategy winner (54.3% win rate)
- ✅ **Phase 2**: 100% complete - Signal enhancement implemented
  - ✅ Market mode detection (Ehlers) - filters 100% trend signals
  - ✅ Volume confirmation - optimal 1.2x ratio filter
  - ✅ Signal quality significantly improved (80% filtered)
- 🔄 **Phase 3**: ML Model Optimization - Next focus
- ⚠️ **Risk Management**: Basic position sizing only (Kelly Criterion pending)
- ⚠️ **ATR Integration**: Functions exist but not connected to exits

## Quick Start

### 1. Setup
```bash
pip install -r requirements.txt
python auth_helper.py  # Generate Zerodha session
```

### 2. Run Live Market Test
```bash
# Basic version
python test_live_market.py

# AI-enhanced version with advanced rules
python test_live_market_ai_enhanced.py

# Optimized system with multi-targets
python test_optimized_system.py
```

### 3. Run Backtests
```bash
python test_lorentzian_system.py --symbol RELIANCE --days 60
python test_zerodha_comprehensive.py  # Full validation
```

## Key Components

### Core Files
- `ml/lorentzian_knn_fixed_corrected.py` - Fixed ML algorithm (bug resolved)
- `scanner/enhanced_bar_processor.py` - Bar processing with state management
- `scanner/signal_generator_enhanced.py` - Signal generation logic
- `scanner/smart_exit_manager.py` - Multi-target exit strategies
- `scanner/ml_quality_filter.py` - ML signal quality filtering
- `config/ml_optimized_settings.py` - ML threshold settings (3.0)
- `data/smart_data_manager.py` - Efficient data caching

### Phase 2 Components
- `indicators/ehlers/` - Market mode detection (Hilbert, Sinewave)
- `scanner/mode_aware_processor.py` - Mode-based signal filtering
- `indicators/confirmation/` - Volume, momentum, S/R filters
- `scanner/confirmation_processor.py` - Entry confirmation integration
- `config/phase2_optimized_settings.py` - Phase 2 optimal configuration

### Configuration
- `config/settings.py` - Default Pine Script parameters
- `config/constants.py` - System constants and feature definitions

### Data Management
- `data/zerodha_client.py` - Market data API client
- `data/cache_manager.py` - Intelligent data caching

## Performance Metrics

### Current Performance (Phase 2 Complete)
- **Phase 1 Results**: 54.3% win rate, 0.24 expectancy
- **Phase 2 Results**: 45.8% win rate (lower due to strict filtering)
- **Signal Quality**: 80% of signals filtered (higher quality)
- **Trade Frequency**: ~50 signals per symbol (60 days)
- **Market Mode**: 100% trend signals filtered
- **Volume Confirmation**: 2.58 average ratio
- **Next Focus**: ML model optimization to improve returns

### Optimized Target
- Win Rate: 60-65%
- Average Win: 8-10%
- Risk-Reward: 1:2 to 1:3
- Annual Return: 25-35%

## Trading Rules

### Entry Conditions
1. ML prediction strength > 3.0
2. Pattern quality score > 6/10
3. Time window: 10:00 AM - 2:30 PM
4. Stock filters: Price ₹50-500, Volume 2x average

### Risk Management
- Position Size: 1.5% risk per trade
- Stop Loss: 1.5x ATR
- Targets: 50% at 1.5R, 30% at 3R, 20% trailing
- Max Daily Loss: 2%
- Max Trades/Day: 5

## Key Improvements from Original

1. **ML Bug Fix**: Feature arrays now update AFTER predictions (critical fix)
2. **ML Quality Filter**: Minimum threshold 3.0 for signal strength
3. **Dynamic Exits**: Multi-target system (1.5R, 3R, 5R) replacing fixed 5-bar
4. **Smart Exit Manager**: 4 strategies - Conservative, ATR, Adaptive, Scalping
5. **Data Efficiency**: Smart caching with pickle files
6. **Positive Expectancy**: System now profitable (was negative)
7. **Modular Testing**: Compare strategies systematically

## Important Notes

### Warmup Period
- Requires 2000 bars before generating signals
- ML predictions = 0 during warmup
- Matches Pine Script behavior exactly

### Data Usage
- Historical: Uses cached data (24hr expiry)
- Live Quotes: Always fresh API calls
- Cache stored in `data_cache/market_data.db`

## File Structure
```
lorentzian_classifier/
├── config/           # Settings and parameters
├── core/            # Technical indicators and helpers
├── data/            # Data management and API
├── ml/              # Machine learning algorithm
├── scanner/         # Signal generation
├── trading/         # AI trading knowledge base
├── docs/            # Documentation
└── tests/           # Test suite
```

## Phase 3: ML Model Optimization (Next Steps)
1. **Walk-Forward Analysis**: Rolling window optimization
2. **Feature Engineering**: New technical indicators
3. **Adaptive Thresholds**: Market-specific ML thresholds
4. **Enhanced Training**: Larger dataset, better validation
5. **Hyperparameter Tuning**: Optimize k-NN parameters

## Phase 2 Achievements
- ✅ Ehlers market mode detection (100% trend filtering)
- ✅ Volume confirmation (1.2x optimal ratio)
- ✅ Signal quality improvement (80% filtered)
- ✅ Maintained reasonable signal frequency
- ✅ Ready for ML optimization phase

## Resources

### Quick References
- 📚 [Documentation README](README.md) - Start here for navigation
- 🗺️ [Documentation Map](DOCUMENTATION_MAP.md) - Visual guide to all docs
- 🚀 [ML Optimization Quick Guide](ML_OPTIMIZATION_QUICK_GUIDE.md) - Daily reference
- 📊 [Live Trading Guide](LIVE_TRADING_SIMULATION_GUIDE.md) - Test the system

### Technical Guides
- [Implementation Guide](IMPLEMENTATION_GUIDE.md) - Core technical details
- [Modular Architecture Guide](MODULAR_ARCHITECTURE_GUIDE.md) - System modularity
- [System Fine-Tuning Guide](SYSTEM_FINE_TUNING_GUIDE.md) - Master reference

### Exit Strategies
- [Quantitative Exits Implementation](quantitative_exits_implementation.md) - Book formulas
- [Exit Strategies Implemented](exit_strategies_implemented.md) - Current exits

### Advanced Features
- [Rocket Science Integration Plan](ROCKET_SCIENCE_INTEGRATION_PLAN.md) - Ehlers DSP
- [Optimization Plan](optimization_plan.md) - Original strategy

---
*Last Updated: January 27, 2025*
*Phase 2 Status: 100% Complete*
*Current Focus: Phase 3 - ML Model Optimization*