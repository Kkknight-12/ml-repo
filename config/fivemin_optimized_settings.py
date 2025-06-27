#!/usr/bin/env python3
"""
5-Minute Optimized Trading Configuration
========================================

Fine-tuned settings specifically for 5-minute timeframe based on optimization results
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from data.data_types import Settings, FilterSettings
from config.constants import DEFAULT_FEATURES


@dataclass
class FiveMinOptimizedConfig:
    """
    Optimized configuration for 5-minute trading
    
    Key optimizations:
    1. Tight stops and targets for small 5-min moves
    2. Original restrictive entry conditions (quality over quantity)
    3. Quick exits to capture small profits
    """
    
    # Core settings - SAME AS ORIGINAL
    symbol: str = "RELIANCE"
    timeframe: str = "5minute"
    max_bars_back: int = 2000
    neighbors_count: int = 8
    feature_count: int = 5  # Using all 5 features like Pine Script
    
    # Feature configuration (matching Pine Script)
    features: Dict[str, Tuple[str, int, int]] = field(default_factory=lambda: DEFAULT_FEATURES.copy())
    
    # Entry filters - KEEP RESTRICTIVE (Original Pine Script)
    use_volatility_filter: bool = True
    use_regime_filter: bool = True
    use_adx_filter: bool = False  # Pine Script default
    regime_threshold: float = -0.1
    adx_threshold: int = 20
    
    # ML settings - No threshold (trust the filters)
    ml_prediction_threshold: float = 0.0
    
    # EMA/SMA Filter settings (from Pine Script defaults)
    use_ema_filter: bool = False
    ema_period: int = 200
    use_sma_filter: bool = False
    sma_period: int = 200
    
    # Kernel settings (from Pine Script defaults)
    use_kernel_filter: bool = True
    show_kernel_estimate: bool = True
    use_kernel_smoothing: bool = False
    kernel_lookback: int = 8
    kernel_relative_weight: float = 8.0
    kernel_regression_level: int = 25
    kernel_lag: int = 2
    
    # Display settings
    show_bar_colors: bool = True
    show_bar_predictions: bool = True
    use_atr_offset: bool = False
    bar_predictions_offset: float = 0.0
    
    # Trade stats
    show_trade_stats: bool = True
    use_worst_case: bool = False
    
    # Color compression
    color_compression: int = 1
    
    # Exit settings - OPTIMIZED FOR 5-MIN
    use_dynamic_exits: bool = True
    show_exits: bool = False
    
    # BALANCED STRATEGY (Best performer)
    stop_loss_percent: float = 0.75      # Tighter stop for 5-min
    take_profit_percent: float = 0.5     # Quick profit target
    
    # Alternative: SCALPING STRATEGY
    # stop_loss_percent: float = 0.5     # Very tight stop
    # take_profit_percent: float = 0.3   # Very quick profit
    
    # Time-based exit
    fixed_exit_bars: int = 15  # 75 minutes max hold time
    
    # Multi-target exits for 5-min (optional)
    use_multi_targets: bool = True
    target_1_percent: float = 0.3        # Quick 0.3% scalp
    target_1_size: float = 50.0          # Take half off
    target_2_percent: float = 0.5        # Full target
    target_2_size: float = 30.0          # Take more off
    target_3_percent: float = 0.75       # Runner
    target_3_size: float = 20.0          # Let rest run
    
    # Trailing stop for 5-min
    use_trailing_stop: bool = True
    trailing_activation_percent: float = 0.3   # Activate after 0.3%
    trailing_distance_percent: float = 0.2     # Trail by 0.2%
    
    # Risk management
    initial_capital: float = 100000
    position_size_percent: float = 10.0
    max_positions: int = 1
    
    # Time filters for 5-min (avoid noise)
    avoid_first_minutes: int = 30        # Skip first 30 min
    avoid_last_minutes: int = 30         # Skip last 30 min
    
    # Indian market hours (9:15 AM - 3:30 PM)
    market_open_time: str = "09:15"
    market_close_time: str = "15:30"
    
    # Backtesting
    lookback_days: int = 90  # 3 months for 5-min data
    commission_percent: float = 0.03
    slippage_percent: float = 0.05
    
    def get_settings(self) -> Settings:
        """Convert to Settings object for ML model"""
        return Settings(
            source='close',
            neighbors_count=self.neighbors_count,
            max_bars_back=self.max_bars_back,
            feature_count=self.feature_count,
            color_compression=self.color_compression,
            show_exits=self.show_exits,
            use_dynamic_exits=self.use_dynamic_exits
        )
    
    def get_filter_settings(self) -> FilterSettings:
        """Convert to FilterSettings object"""
        return FilterSettings(
            use_volatility_filter=self.use_volatility_filter,
            use_regime_filter=self.use_regime_filter,
            use_adx_filter=self.use_adx_filter,
            regime_threshold=self.regime_threshold,
            adx_threshold=self.adx_threshold
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'max_bars_back': self.max_bars_back,
            'neighbors_count': self.neighbors_count,
            'feature_count': self.feature_count,
            'use_volatility_filter': self.use_volatility_filter,
            'use_regime_filter': self.use_regime_filter,
            'use_adx_filter': self.use_adx_filter,
            'regime_threshold': self.regime_threshold,
            'adx_threshold': self.adx_threshold,
            'ml_prediction_threshold': self.ml_prediction_threshold,
            'use_dynamic_exits': self.use_dynamic_exits,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent,
            'fixed_exit_bars': self.fixed_exit_bars,
            'use_multi_targets': self.use_multi_targets,
            'use_trailing_stop': self.use_trailing_stop,
            'initial_capital': self.initial_capital,
            'position_size_percent': self.position_size_percent,
            'commission_percent': self.commission_percent,
            'slippage_percent': self.slippage_percent
        }
    
    def get_description(self) -> str:
        """Get configuration description"""
        return f"""
5-Minute Optimized Configuration
================================
Symbol: {self.symbol}
Timeframe: {self.timeframe}

Entry Strategy (Original Pine Script):
- All original filters active
- ~40-50 high-quality trades expected
- No ML threshold (filters do the work)

Exit Strategy (Optimized for 5-min):
- Stop Loss: {self.stop_loss_percent}%
- Take Profit: {self.take_profit_percent}%
- Risk/Reward: {self.take_profit_percent/self.stop_loss_percent:.2f}
- Max Hold: {self.fixed_exit_bars} bars ({self.fixed_exit_bars * 5} minutes)

Multi-Target Exits:
- Target 1: {self.target_1_percent}% @ {self.target_1_size}%
- Target 2: {self.target_2_percent}% @ {self.target_2_size}%
- Target 3: {self.target_3_percent}% @ {self.target_3_size}%

Trailing Stop:
- Activation: {self.trailing_activation_percent}%
- Trail Distance: {self.trailing_distance_percent}%

Expected Performance:
- Win Rate: ~47-50%
- Risk/Reward: ~1.0
- Low time exits (~58%)
"""


# Preset configurations
FIVEMIN_BALANCED = FiveMinOptimizedConfig(
    stop_loss_percent=0.75,
    take_profit_percent=0.5
)

FIVEMIN_SCALPING = FiveMinOptimizedConfig(
    stop_loss_percent=0.5,
    take_profit_percent=0.3,
    fixed_exit_bars=10  # 50 minutes max
)

FIVEMIN_CONSERVATIVE = FiveMinOptimizedConfig(
    stop_loss_percent=1.0,
    take_profit_percent=0.75,
    position_size_percent=5.0  # Smaller position
)

FIVEMIN_AGGRESSIVE = FiveMinOptimizedConfig(
    stop_loss_percent=0.5,
    take_profit_percent=1.0,  # 1:2 risk/reward
    use_multi_targets=False,  # All or nothing
    position_size_percent=15.0  # Larger position
)