# Quantitative Exit Strategies Implementation Guide

## Overview
This document consolidates the exit strategies and formulas from **Quantitative Trading** (Howard B. Bandy) and **Rocket Science for Trading** (John Ehlers).

## Key Formulas and Principles

### 1. From Quantitative Trading (Howard B. Bandy)

#### Core Metrics
- **Expectancy Formula**: `(% Winners * Avg % Win) - (% Losers * Avg % Loss)`
  - Must be positive for any viable system
  - This is the average profit/loss per trade

- **CAR/MaxDD**: `Compounded Annual Return / Maximum System % Drawdown`
  - Crucial measure of return per unit of risk
  - Primary objective function for optimization

- **Profit Factor**: `Gross Profit / Gross Loss`
  - Measures dollars won for every dollar lost
  - Key measure of robustness

- **Risk Management Rules**:
  - Maximum risk per trade: 1-2% of account
  - Risk/Reward ratio: Minimum 2:1
  - Position sizing: Risk percentage of portfolio, not fixed dollar amounts

#### Exit Principles
- **"Good exits are noted as being able to salvage almost any system"** (Directive 3.4)
- Exits must be mathematically objective and unambiguous
- All systems eventually fail - continuous monitoring required

### 2. From Rocket Science for Trading (John Ehlers)

#### Risk Management Philosophy
- **Strategic Risk**: Identify market mode (Trend vs Cycle) first
- **Tactical Risk**: Use wider "disaster stops" rather than tight stops
- **ATR-Based Exits**: Community enhancement using Average True Range

#### Ehlers' Exit Approach
- Prefers wider stops to avoid premature exits
- "Disaster stops" only for catastrophic protection
- Community practitioners add ATR-based targets and stops

#### Market Mode Identification
- **Trend Mode**: Use trend-following exits
- **Cycle Mode**: Use mean-reversion exits
- Sinewave indicator identifies mode (parallel lines = trend)

## Implementation in Code

### 1. Conservative Exit (Quantitative Trading Based)
```python
# Based on 2:1 risk/reward principle from Quantitative Trading
exit_config_conservative = {
    'stop_loss_percent': 1.0,      # 1% risk per trade
    'take_profit_targets': [2.0],   # 2:1 risk/reward ratio
    'target_sizes': [100],          # Exit full position
    'use_trailing_stop': False,     # Keep it simple
    'max_holding_bars': 78          # Full trading day
}
```

### 2. ATR-Based Exit (Both Books)
```python
# Combines Quantitative Trading ratios with Ehlers' ATR enhancement
exit_config_atr = {
    'use_atr_stops': True,
    'atr_stop_multiplier': 2.0,     # 2x ATR for stop (wider per Ehlers)
    'atr_profit_multipliers': [1.5, 3.0, 5.0],  # Risk/reward ratios
    'target_sizes': [50, 30, 20],   # Gradual exits
    'use_trailing_stop': True,
    'atr_trailing_multiplier': 1.5,  # Tighter than initial stop
    'max_holding_bars': 78
}
```

### 3. Adaptive Exit (Ehlers Inspired)
```python
# Based on market mode and disaster stop philosophy
exit_config_adaptive = {
    'stop_loss_percent': 2.0,       # Wider "disaster stop"
    'take_profit_targets': [1.0, 2.0, 3.0],
    'target_sizes': [40, 40, 20],   # Gradual exits
    'use_trailing_stop': True,
    'trailing_activation': 1.0,
    'trailing_distance': 0.5,
    'max_holding_bars': 40
}
```

## Position Sizing Formula

From Quantitative Trading:
```python
def calculate_position_size(account_balance, risk_percent, entry_price, stop_loss):
    """
    Risk-based position sizing per Quantitative Trading
    
    Args:
        account_balance: Total account value
        risk_percent: Risk per trade (0.01-0.02 for 1-2%)
        entry_price: Entry price
        stop_loss: Stop loss price
    
    Returns:
        Number of shares to trade
    """
    risk_amount = account_balance * risk_percent
    risk_per_share = abs(entry_price - stop_loss)
    
    if risk_per_share == 0:
        return 0
    
    position_size = int(risk_amount / risk_per_share)
    return position_size
```

## ATR Stop Calculation

Based on community enhancements to Ehlers' work:
```python
def calculate_atr_stop(entry_price, atr, direction, multiplier=2.0):
    """
    ATR-based stop loss calculation
    
    Args:
        entry_price: Entry price
        atr: Current ATR value
        direction: 1 for long, -1 for short
        multiplier: ATR multiplier (typically 2.0)
    
    Returns:
        Stop loss price
    """
    stop_distance = atr * multiplier
    
    if direction == 1:  # Long
        return entry_price - stop_distance
    else:  # Short
        return entry_price + stop_distance
```

## Expectancy Calculation

Critical filter from Quantitative Trading:
```python
def calculate_expectancy(trades):
    """
    Calculate system expectancy - must be positive
    
    Args:
        trades: List of trade results (profit/loss percentages)
    
    Returns:
        Expectancy value
    """
    if not trades:
        return 0
    
    winners = [t for t in trades if t > 0]
    losers = [t for t in trades if t <= 0]
    
    win_rate = len(winners) / len(trades) if trades else 0
    avg_win = sum(winners) / len(winners) if winners else 0
    avg_loss = abs(sum(losers) / len(losers)) if losers else 0
    
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    return expectancy
```

## Key Implementation Notes

1. **Always Calculate Expectancy**: No system should trade without positive expectancy
2. **Use CAR/MaxDD**: Primary metric for system evaluation
3. **Risk 1-2% Maximum**: Never risk more than 2% per trade
4. **ATR for Volatility**: Adjust stops based on market volatility
5. **Market Mode Matters**: Different exits for trending vs cycling markets
6. **Monitor System Decay**: All systems fail - track performance metrics

## Testing Priority

1. **Test Conservative First**: Simple 2:1 risk/reward baseline
2. **Add ATR Adaptation**: Test volatility-based improvements
3. **Compare Metrics**: Focus on CAR/MaxDD and Expectancy
4. **Monitor Profit Factor**: Should be > 1.5 for robustness
5. **Track System Decay**: Watch for degrading performance