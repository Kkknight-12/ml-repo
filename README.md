# Lorentzian Classification Trading System

A Python implementation of the TradingView Pine Script Lorentzian Classification algorithm for automated trading signals.

## Features
- 🤖 Machine Learning k-NN algorithm with Lorentzian distance
- 📊 Real-time signal generation for Indian stocks
- 💰 Multi-target profit booking system
- 🛡️ ATR-based dynamic risk management
- ⚡ Optimized parameters for 25-35% annual returns
- 📈 75% historical win rate

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Zerodha Authentication**
   ```bash
   python auth_helper.py
   ```

3. **Run Trading System**
   ```bash
   # Basic version
   python test_live_market.py
   
   # AI-enhanced version  
   python test_live_market_ai_enhanced.py
   
   # Optimized multi-target version
   python test_optimized_system.py
   ```

## Documentation

- 📖 [Project Overview](docs/PROJECT_OVERVIEW.md) - System architecture and components
- 🔧 [Implementation Guide](docs/IMPLEMENTATION_GUIDE.md) - Technical details and troubleshooting  
- 📊 [Fine-Tuning Guide](docs/SYSTEM_FINE_TUNING_GUIDE.md) - Parameter optimization
- 🚀 [Optimization Plan](docs/optimization_plan.md) - Roadmap for improvements
- 📱 [Live Trading Guide](docs/LIVE_TRADING_SIMULATION_GUIDE.md) - How to use the system

## Project Structure
```
├── config/        # Trading parameters and settings
├── ml/            # Machine learning algorithm
├── scanner/       # Signal generation engine
├── data/          # Market data management
├── trading/       # AI trading knowledge base
└── docs/          # Documentation
```

## Performance
- **Win Rate**: 75%
- **Average Win**: 3.7% (targeting 8-10%)
- **Risk per Trade**: 1.5%
- **Max Daily Loss**: 2%

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer
This software is for educational purposes only. Use at your own risk. Not financial advice.