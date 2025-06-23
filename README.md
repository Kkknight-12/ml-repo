# Lorentzian Classification - Python Implementation

A Python implementation of the popular Pine Script Lorentzian Classification trading strategy with machine learning capabilities.

## 🚀 Overview

This project converts the Pine Script Lorentzian Classification strategy to Python, maintaining exact compatibility with the original Pine Script behavior. The strategy uses machine learning with k-nearest neighbors and Lorentzian distance metrics to predict market movements.

### Key Features

- ✅ **Machine Learning Based**: Uses k-NN with Lorentzian distance for market prediction
- ✅ **Multiple Technical Indicators**: RSI, CCI, WaveTrend, ADX integration
- ✅ **Advanced Filtering**: Volatility, regime, and ADX filters
- ✅ **Kernel Regression**: Optional kernel smoothing for signals
- ✅ **Risk Management**: Automatic stop-loss and take-profit calculation
- ✅ **Real-time Compatible**: Works with live market data via Zerodha API

## 📋 Prerequisites

- Python 3.8 or higher
- Zerodha Kite Connect account (for live data)
- Basic understanding of technical analysis

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/lorentzian-classifier.git
cd lorentzian-classifier
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Zerodha credentials (for live data):
```bash
cp config/credentials.example.py config/credentials.py
# Edit config/credentials.py with your API keys
```

## 🎯 Quick Start

### Basic Usage

```python
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor

# Initialize configuration
config = TradingConfig()

# Create processor
processor = EnhancedBarProcessor(config, "RELIANCE", "5min")

# Process a bar
result = processor.process_bar(
    open_price=2500.0,
    high=2510.0,
    low=2495.0,
    close=2505.0,
    volume=1000000
)

if result.start_long_trade:
    print(f"Long entry signal at {result.close}")
    print(f"Stop Loss: {result.stop_loss}")
    print(f"Take Profit: {result.take_profit}")
```

### Running Tests

```bash
# Test with CSV data
python test_comprehensive_fix_verification.py

# Test with live Zerodha data
python test_zerodha_comprehensive.py
```

## 📊 Configuration

The strategy can be customized via `TradingConfig`:

```python
config = TradingConfig(
    # ML Settings
    neighbors_count=8,           # Number of neighbors for k-NN
    max_bars_back=2000,         # Historical lookback
    
    # Filters
    use_volatility_filter=True,  # Enable volatility filter
    use_regime_filter=True,      # Enable regime filter
    use_adx_filter=False,        # ADX filter (off by default)
    
    # Kernel Settings
    use_kernel_filter=True,      # Enable kernel regression
    kernel_lookback=8,           # Kernel lookback period
    
    # Risk Management
    use_dynamic_exits=False      # Dynamic exit signals
)
```

## 📈 Strategy Components

### 1. Machine Learning Core
- **Algorithm**: k-Nearest Neighbors with Lorentzian distance
- **Features**: Normalized RSI, CCI, WaveTrend, ADX
- **Prediction**: Directional bias (-8 to +8 range)

### 2. Filter System
- **Volatility Filter**: Ensures sufficient market movement
- **Regime Filter**: Confirms trend direction
- **ADX Filter**: Optional trend strength filter

### 3. Signal Generation
- Entry signals when ML prediction aligns with filters
- Exit signals based on:
  - Signal reversal
  - Dynamic kernel crossovers
  - Fixed bar holding periods

## 🧪 Performance Metrics

Expected behavior with default settings:
- **Regime Filter Pass Rate**: ~35%
- **Entry Frequency**: 5-10 entries per 1000 bars
- **ML Prediction Range**: -8 to +8
- **Typical Win Rate**: 40-60% (market dependent)

## 📁 Project Structure

```
lorentzian_classifier/
├── config/                 # Configuration files
│   ├── settings.py        # Main settings
│   └── credentials.py     # API credentials (create from example)
├── core/                  # Core functionality
│   ├── enhanced_indicators.py    # Stateful indicators
│   ├── regime_filter_fix_v2.py  # Regime filter
│   └── kernel_functions.py       # Kernel regression
├── ml/                    # Machine learning
│   └── lorentzian_knn_fixed.py  # k-NN implementation
├── scanner/               # Bar processing
│   ├── enhanced_bar_processor.py # Main processor
│   └── signal_generator.py       # Signal logic
├── pine_script/           # Original Pine Script
├── solution/              # Conversion documentation
└── tests/                 # Test files
```

## 🔍 Debugging

For detailed debugging, use the debug processor:

```python
from scanner.enhanced_bar_processor_debug import EnhancedBarProcessorDebug

processor = EnhancedBarProcessorDebug(config, "RELIANCE", "5min")
# This provides extensive Pine Script-style logging
```

## ⚠️ Important Notes

1. **No Train/Test Split**: Like Pine Script, the system learns continuously
2. **Stateful Indicators**: All indicators maintain state across bars
3. **Persistent Arrays**: ML arrays never reset (Pine Script `var` behavior)
4. **Modulo 4 Sampling**: Temporal sampling for diverse neighbors

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📚 Documentation

- [Analysis Guide](ANALYSIS_GUIDE.md) - Detailed code analysis guide
- [Pine Script Notes](solution/pine_script_conversion_notes.md) - Conversion details
- [ML Algorithm](solution/ml_algorithm_explanation.md) - ML implementation details

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Original Pine Script strategy by [jdehorty](https://www.tradingview.com/u/jdehorty/)
- Inspired by machine learning research in quantitative finance
- Built with Pine Script to Python conversion best practices

## ⚡ Performance Tips

1. Use `enhanced_bar_processor.py` for production (not debug version)
2. Ensure sufficient historical data (minimum 100 bars)
3. Adjust filters based on market conditions
4. Monitor regime filter pass rates

## 🐛 Known Issues

- Regime filter pass rates vary with market conditions (adaptive behavior)
- Requires minimum 20 bars for ML predictions to start
- ADX filter is disabled by default (Pine Script compatibility)

## 📞 Support

For issues and questions:
1. Check the [Analysis Guide](ANALYSIS_GUIDE.md)
2. Review closed issues on GitHub
3. Open a new issue with details

---

**Disclaimer**: This is a trading strategy implementation. Use at your own risk. Past performance does not guarantee future results.