# Lorentzian Classification Implementation Guide

## Pine Script to Python Conversion

### Core Algorithm
The Lorentzian Classification algorithm uses k-Nearest Neighbors with Lorentzian distance metric to predict price movements.

#### Key Components:
1. **Feature Engineering**: 5 technical indicators (RSI, WT, CCI, ADX)
2. **Distance Calculation**: Lorentzian distance between feature vectors
3. **Classification**: k-NN voting with nearest neighbors
4. **Signal Generation**: Buy/sell based on prediction + filters

### Critical Implementation Details

#### 1. Array Management
Pine Script uses persistent arrays that maintain state across bars. Python implementation uses:
```python
# PersistentArray class in bar_data.py
self.feature_arrays[f"f{i}_array"] = PersistentArray(max_size=2000)
```

#### 2. State Persistence
- All indicators maintain internal state
- Bar index tracked consistently
- Arrays roll forward automatically

#### 3. Warmup Period
- Requires 2000 bars before ML predictions
- During warmup: `ml_model.prediction = 0.0`
- Prevents premature signals

## Common Issues and Fixes

### 1. Zerodha Authentication Error
**Problem**: "Incorrect api_key or access_token"
**Solution**: 
```python
# Read from .kite_session.json
with open('.kite_session.json', 'r') as f:
    session_data = json.load(f)
    access_token = session_data.get('access_token')
os.environ['KITE_ACCESS_TOKEN'] = access_token
```

### 2. Historical Data API
**Problem**: Wrong parameters for get_historical_data
**Solution**:
```python
# Correct usage
df = kite_client.get_historical_data(
    symbol=symbol,
    interval="5minute", 
    days=60  # Not from_date/to_date
)
```

### 3. Signal Mismatch with Pine Script
**Problem**: Python signals don't match TradingView
**Reasons**:
- Different data sources (Zerodha vs TradingView)
- Calculation precision differences
- State initialization variations

### 4. Memory Limits
**Problem**: Large arrays cause memory issues
**Solution**: Implemented memory limits in `config/memory_limits.py`

## Testing and Validation

### 1. Unit Tests
```bash
python -m pytest tests/test_ml_algorithm.py
python -m pytest tests/test_enhanced_indicators.py
```

### 2. Signal Validation
```bash
python test_zerodha_comprehensive.py
# Generates detailed comparison CSVs
```

### 3. Live Market Testing
```bash
python test_live_market.py --symbol RELIANCE
# Tests with real-time data (market hours only)
```

## Performance Optimization

### 1. Data Caching
- 24-hour cache for historical data
- Reduces API calls by 90%
- Automatic cache invalidation

### 2. Computation Efficiency
- Vectorized operations where possible
- Minimal redundant calculations
- Efficient array operations

### 3. Parameter Tuning
See `config/optimized_settings.py` for:
- Optimized ML parameters
- Market-specific adjustments
- Risk management settings

## Integration Examples

### Basic Signal Generation
```python
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig

config = TradingConfig()
processor = EnhancedBarProcessor(config, "RELIANCE", "5minute")

# Process bars
for _, bar in df.iterrows():
    result = processor.process_bar(
        bar['open'], bar['high'], 
        bar['low'], bar['close'], 
        bar['volume']
    )
    
    if result.start_long_trade:
        print(f"BUY signal at {bar['close']}")
```

### With Risk Management
```python
from config.optimized_settings import OptimizedTradingConfig

config = OptimizedTradingConfig()
# Includes multi-target exits, ATR stops, position sizing
```

## Debugging Tips

### 1. Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Check ML Predictions
```python
print(f"Prediction: {processor.ml_model.prediction}")
print(f"Signal: {processor.ml_model.signal}")
```

### 3. Verify Array States
```python
# Check feature arrays
for i in range(5):
    array = processor.feature_arrays[f"f{i}_array"]
    print(f"Feature {i}: {array.get(0)}")
```

## Best Practices

### DO:
- ✅ Always check warmup period before trading
- ✅ Use cached data for backtesting
- ✅ Validate signals with known test cases
- ✅ Monitor memory usage with large datasets
- ✅ Use optimized settings for production

### DON'T:
- ❌ Skip the 2000-bar warmup
- ❌ Modify core algorithm logic
- ❌ Ignore risk management rules
- ❌ Trade without stop losses
- ❌ Over-optimize on historical data

## Troubleshooting Checklist

1. **No signals generated?**
   - Check warmup period (need 2000 bars)
   - Verify filter settings
   - Check prediction threshold

2. **Wrong signal direction?**
   - Verify feature calculations
   - Check array indexing
   - Compare with Pine Script debug

3. **Performance issues?**
   - Enable data caching
   - Reduce max_bars_back if possible
   - Use optimized numpy operations

4. **API errors?**
   - Regenerate auth token
   - Check rate limits
   - Verify network connection

---
*For fine-tuning parameters, see [SYSTEM_FINE_TUNING_GUIDE.md](SYSTEM_FINE_TUNING_GUIDE.md)*