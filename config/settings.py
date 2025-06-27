"""
Settings module - Mimics Pine Script input.* functions
All defaults match the original Pine Script exactly
"""
from dataclasses import dataclass, field
from typing import Dict, Tuple
from data.data_types import Settings, FilterSettings
from config.constants import *


@dataclass
class TradingConfig:
    """Complete configuration matching Pine Script inputs"""

    # General Settings
    source: str = 'close'
    neighbors_count: int = 8
    max_bars_back: int = 2000
    feature_count: int = 5
    color_compression: int = 1
    show_exits: bool = False
    use_dynamic_exits: bool = False

    scan_interval: str = "5minute"  # For intraday scanning

    # Feature Engineering (f1-f5 configurations)
    features: Dict[str, Tuple[str, int, int]] = field(default_factory=lambda: DEFAULT_FEATURES.copy())

    # Filters
    use_volatility_filter: bool = True
    use_regime_filter: bool = True
    use_adx_filter: bool = False
    regime_threshold: float = -0.1
    adx_threshold: int = 20

    # EMA/SMA Filters
    use_ema_filter: bool = USE_EMA_FILTER
    ema_period: int = EMA_PERIOD
    use_sma_filter: bool = USE_SMA_FILTER
    sma_period: int = SMA_PERIOD

    # Kernel Settings
    use_kernel_filter: bool = USE_KERNEL_FILTER
    show_kernel_estimate: bool = SHOW_KERNEL_ESTIMATE
    use_kernel_smoothing: bool = USE_KERNEL_SMOOTHING
    kernel_lookback: int = KERNEL_LOOKBACK
    kernel_relative_weight: float = KERNEL_RELATIVE_WEIGHT
    kernel_regression_level: int = KERNEL_REGRESSION_LEVEL
    kernel_lag: int = KERNEL_LAG

    # Display Settings
    show_bar_colors: bool = SHOW_BAR_COLORS
    show_bar_predictions: bool = SHOW_BAR_PREDICTIONS
    use_atr_offset: bool = USE_ATR_OFFSET
    bar_predictions_offset: float = BAR_PREDICTIONS_OFFSET

    # Trade Stats
    show_trade_stats: bool = SHOW_TRADE_STATS
    use_worst_case: bool = USE_WORST_CASE
    
    # Phase 3 settings (with rollback safety)
    use_flexible_ml: bool = False  # Feature flag for flexible ML
    enable_phase3_features: bool = False  # Enable new indicators
    flexible_ml_rollout_pct: float = 0.0  # Gradual rollout (0-100%)

    def get_settings(self) -> Settings:
        """Convert to Settings object for ML model"""
        return Settings(
            source=self.source,
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


# Global config instance (like Pine Script's inputs are global)
config = TradingConfig()