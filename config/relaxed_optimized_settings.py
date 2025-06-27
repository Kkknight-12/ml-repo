#!/usr/bin/env python3
"""
Relaxed + Optimized Trading Configuration
=========================================

Combines relaxed entry conditions with optimized exit strategy
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RelaxedOptimizedConfig:
    """
    Best of both worlds:
    - Relaxed entry conditions for more trades
    - Optimized exits for better risk/reward
    """
    
    # Core settings
    symbol: str = "RELIANCE"
    timeframe: str = "5minute"
    max_bars_back: int = 2000
    
    # k-NN settings
    neighbors_count: int = 8
    feature_count: int = 4
    
    # ML settings - moderate threshold
    ml_prediction_threshold: float = 2.0  # Lower than original 3.0
    
    # Filter settings - relaxed
    use_volatility_filter: bool = False
    use_regime_filter: bool = True
    use_adx_filter: bool = False
    adx_threshold: float = 20.0
    
    # Entry settings
    entry_cooldown_bars: int = 10
    
    # Exit settings - OPTIMIZED
    use_dynamic_exits: bool = True
    fixed_exit_bars: int = 10  # Increased from 5 to give trades more time
    
    # Risk management - IMPROVED
    stop_loss_percent: float = 1.5  # Increased from 1.0% to reduce premature stops
    initial_capital: float = 100000
    position_size_percent: float = 10.0
    
    # Multi-target exits - KEY IMPROVEMENT
    use_multi_targets: bool = True
    target_1_r_multiple: float = 0.5   # Quick profit at 0.75% (0.5 * 1.5% stop)
    target_1_percent: float = 40.0     # Take 40% off
    target_2_r_multiple: float = 1.0   # Second target at 1.5%
    target_2_percent: float = 30.0     # Take another 30% off
    target_3_r_multiple: float = 2.0   # Final target at 3.0%
    target_3_percent: float = 30.0     # Let the rest run with trailing stop
    
    # Trailing stop (after target 1)
    use_trailing_stop: bool = True
    trailing_stop_activation: float = 0.75  # Activate after 0.75% profit
    trailing_stop_distance: float = 0.5     # Trail by 0.5%
    
    # Momentum-based exits
    use_momentum_exits: bool = True
    momentum_exit_threshold: float = -2.0  # Exit if momentum turns strongly negative
    
    # Time-based filters
    avoid_first_30_minutes: bool = True   # Skip volatile opening
    avoid_last_30_minutes: bool = True     # Skip closing volatility
    
    # Backtesting
    lookback_days: int = 180
    commission_percent: float = 0.03
    slippage_percent: float = 0.05
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'max_bars_back': self.max_bars_back,
            'neighbors_count': self.neighbors_count,
            'feature_count': self.feature_count,
            'ml_prediction_threshold': self.ml_prediction_threshold,
            'use_volatility_filter': self.use_volatility_filter,
            'use_regime_filter': self.use_regime_filter,
            'use_adx_filter': self.use_adx_filter,
            'adx_threshold': self.adx_threshold,
            'entry_cooldown_bars': self.entry_cooldown_bars,
            'use_dynamic_exits': self.use_dynamic_exits,
            'fixed_exit_bars': self.fixed_exit_bars,
            'stop_loss_percent': self.stop_loss_percent,
            'initial_capital': self.initial_capital,
            'position_size_percent': self.position_size_percent,
            'use_multi_targets': self.use_multi_targets,
            'target_1_r_multiple': self.target_1_r_multiple,
            'target_1_percent': self.target_1_percent,
            'target_2_r_multiple': self.target_2_r_multiple,
            'target_2_percent': self.target_2_percent,
            'target_3_r_multiple': self.target_3_r_multiple,
            'target_3_percent': self.target_3_percent,
            'use_trailing_stop': self.use_trailing_stop,
            'trailing_stop_activation': self.trailing_stop_activation,
            'trailing_stop_distance': self.trailing_stop_distance,
            'use_momentum_exits': self.use_momentum_exits,
            'momentum_exit_threshold': self.momentum_exit_threshold,
            'avoid_first_30_minutes': self.avoid_first_30_minutes,
            'avoid_last_30_minutes': self.avoid_last_30_minutes,
            'lookback_days': self.lookback_days,
            'commission_percent': self.commission_percent,
            'slippage_percent': self.slippage_percent
        }
    
    def get_description(self) -> str:
        """Get configuration description"""
        return f"""
Relaxed + Optimized Configuration
=================================
Symbol: {self.symbol}
Timeframe: {self.timeframe}

Entry Conditions (Relaxed):
- ML Threshold: {self.ml_prediction_threshold}
- Entry Cooldown: {self.entry_cooldown_bars} bars
- Filters: Minimal (regime only)

Exit Strategy (Optimized):
- Stop Loss: {self.stop_loss_percent}% (wider)
- Target 1: {self.target_1_r_multiple * self.stop_loss_percent:.1f}% @ {self.target_1_percent}%
- Target 2: {self.target_2_r_multiple * self.stop_loss_percent:.1f}% @ {self.target_2_percent}%
- Target 3: {self.target_3_r_multiple * self.stop_loss_percent:.1f}% @ {self.target_3_percent}%
- Trailing Stop: {self.trailing_stop_distance}% after {self.trailing_stop_activation}%
- Max Hold: {self.fixed_exit_bars} bars

Expected Improvements:
- More trades (relaxed entries)
- Better risk/reward (multi-targets)
- Capture more profit (trailing stops)
- Reduce time exits (longer hold time)
"""


# Preset configurations
RELAXED_OPTIMIZED_V1 = RelaxedOptimizedConfig()

RELAXED_OPTIMIZED_AGGRESSIVE = RelaxedOptimizedConfig(
    ml_prediction_threshold=0.0,  # No ML threshold
    target_1_r_multiple=0.3,      # Quick 0.45% target
    target_1_percent=50.0,        # Take half off quickly
    stop_loss_percent=2.0         # Wider stop for volatile moves
)

RELAXED_OPTIMIZED_CONSERVATIVE = RelaxedOptimizedConfig(
    ml_prediction_threshold=3.0,  # Higher ML threshold
    target_1_r_multiple=0.7,      # Wait for 1.05% before first exit
    stop_loss_percent=1.0,        # Tighter stop
    position_size_percent=5.0     # Smaller position size
)