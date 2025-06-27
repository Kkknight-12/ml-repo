#!/usr/bin/env python3
"""
5-Minute EXACT Pine Script Settings
===================================

Exact configuration matching TradingView Pine Script for 5-minute timeframe
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from data.data_types import Settings, FilterSettings

@dataclass
class FiveMinExactConfig:
    """
    Exact Pine Script configuration for 5-minute trading
    """
    
    # GENERAL SETTINGS - EXACT FROM PINE SCRIPT
    source: str = "close"
    neighbors_count: int = 8
    max_bars_back: int = 2000
    color_compression: int = 1
    show_default_exits: bool = False  # ❌ unchecked
    use_dynamic_exits: bool = False   # ❌ unchecked
    show_trade_stats: bool = True     # ✅ checked
    use_worst_case: bool = False      # ❌ unchecked
    
    # FEATURE ENGINEERING - EXACT FROM PINE SCRIPT
    feature_count: int = 5
    features: Dict[str, Tuple[str, int, int]] = field(default_factory=lambda: {
        "f1": ("RSI", 14, 1),
        "f2": ("WT", 10, 11),
        "f3": ("CCI", 20, 1),
        "f4": ("ADX", 20, 2),
        "f5": ("RSI", 9, 1)
    })
    
    # FILTERS - EXACT FROM PINE SCRIPT
    use_volatility_filter: bool = True   # ✅ checked
    use_regime_filter: bool = True       # ✅ checked
    regime_threshold: float = -0.1
    use_adx_filter: bool = False         # ❌ unchecked
    adx_threshold: int = 20
    use_ema_filter: bool = False         # ❌ unchecked
    ema_period: int = 200
    use_sma_filter: bool = False         # ❌ unchecked
    sma_period: int = 200
    
    # KERNEL SETTINGS - EXACT FROM PINE SCRIPT
    use_kernel_filter: bool = True       # Trade with Kernel ✅
    show_kernel_estimate: bool = True    # ✅ checked
    kernel_lookback: int = 8
    kernel_relative_weight: float = 8.0
    kernel_regression_level: int = 25
    use_kernel_smoothing: bool = False   # ❌ unchecked
    kernel_lag: int = 2
    
    # DISPLAY SETTINGS (from Pine defaults)
    show_bar_colors: bool = True
    show_bar_predictions: bool = True
    use_atr_offset: bool = False
    bar_predictions_offset: float = 0.0
    
    # Risk Management - OPTIMIZED FOR 5-MIN
    # Based on test_5min_optimization results
    stop_loss_percent: float = 0.75      # Balanced approach
    take_profit_percent: float = 0.5     # Quick profit target
    
    # Multi-target exits (optional)
    use_multi_targets: bool = True
    target_1_percent: float = 0.3
    target_1_size: float = 50.0
    target_2_percent: float = 0.5
    target_2_size: float = 30.0
    target_3_percent: float = 0.75
    target_3_size: float = 20.0
    
    # Trailing stop for 5-min
    use_trailing_stop: bool = True
    trailing_activation_percent: float = 0.3
    trailing_distance_percent: float = 0.2
    
    # Time-based exit
    fixed_exit_bars: int = 15  # 75 minutes max hold time
    
    # Time filters for 5-min
    avoid_first_minutes: int = 30
    avoid_last_minutes: int = 30
    market_open_time: str = "09:15"
    market_close_time: str = "15:30"
    
    # Position sizing
    initial_capital: float = 100000
    position_size_percent: float = 10.0
    commission_percent: float = 0.03
    slippage_percent: float = 0.05
    
    # Backtesting
    lookback_days: int = 90  # 3 months for 5-min data
    
    # Symbol and timeframe
    symbol: str = "RELIANCE"
    timeframe: str = "5minute"
    
    def get_settings(self) -> Settings:
        """Convert to Settings object for ML model"""
        return Settings(
            source=self.source,
            neighbors_count=self.neighbors_count,
            max_bars_back=self.max_bars_back,
            feature_count=self.feature_count,
            color_compression=self.color_compression,
            show_exits=self.show_default_exits,
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
    
    def get_description(self) -> str:
        """Get configuration description"""
        return f"""
5-Minute EXACT Pine Script Configuration
========================================

GENERAL SETTINGS:
- Source: {self.source}
- Neighbors Count: {self.neighbors_count}
- Max Bars Back: {self.max_bars_back}
- Dynamic Exits: {'ON' if self.use_dynamic_exits else 'OFF'}

FEATURES:
- F1: RSI(14,1)
- F2: WT(10,11)
- F3: CCI(20,1)
- F4: ADX(20,2)
- F5: RSI(9,1)

ACTIVE FILTERS:
- Volatility Filter: {'ON ✅' if self.use_volatility_filter else 'OFF'}
- Regime Filter: {'ON ✅' if self.use_regime_filter else 'OFF'} (threshold: {self.regime_threshold})
- ADX Filter: {'ON' if self.use_adx_filter else 'OFF ❌'}
- EMA Filter: {'ON' if self.use_ema_filter else 'OFF ❌'}
- SMA Filter: {'ON' if self.use_sma_filter else 'OFF ❌'}

KERNEL SETTINGS:
- Trade with Kernel: {'ON ✅' if self.use_kernel_filter else 'OFF'}
- Lookback: {self.kernel_lookback}
- Relative Weight: {self.kernel_relative_weight}
- Regression Level: {self.kernel_regression_level}
- Smoothing: {'ON' if self.use_kernel_smoothing else 'OFF ❌'}

RISK MANAGEMENT:
- Stop Loss: {self.stop_loss_percent}%
- Take Profit: {self.take_profit_percent}%
"""


# Create the exact configuration
FIVEMIN_EXACT = FiveMinExactConfig()

# Also create variations for testing
FIVEMIN_EXACT_TIGHT = FiveMinExactConfig(
    stop_loss_percent=0.5,
    take_profit_percent=0.3
)

FIVEMIN_EXACT_WIDE = FiveMinExactConfig(
    stop_loss_percent=1.0,
    take_profit_percent=0.75
)