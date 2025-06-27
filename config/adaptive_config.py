"""
Adaptive Configuration - Stock-specific settings based on market analysis
========================================================================

Automatically adjusts targets, stops, and filters based on:
- Stock volatility characteristics
- Historical price movements
- Timeframe-specific patterns
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from data.data_types import Settings, FilterSettings


@dataclass
class AdaptiveConfig:
    """
    Configuration that adapts to stock characteristics
    """
    
    # Base settings (Pine Script defaults)
    source: str = "close"
    neighbors_count: int = 8
    max_bars_back: int = 2000
    feature_count: int = 5
    color_compression: int = 1
    
    # Base features
    features: Dict[str, Tuple[str, int, int]] = field(default_factory=lambda: {
        "f1": ("RSI", 14, 1),
        "f2": ("WT", 10, 11), 
        "f3": ("CCI", 20, 1),
        "f4": ("ADX", 20, 2),
        "f5": ("RSI", 9, 1)
    })
    
    # ML thresholds (adaptive)
    ml_min_confidence: float = 3.0  # Minimum for entry
    ml_high_confidence: float = 5.0  # For full position
    
    # FILTERS - Less restrictive than original
    use_volatility_filter: bool = True
    use_regime_filter: bool = False  # DISABLED - too restrictive
    use_adx_filter: bool = False
    use_kernel_filter: bool = True
    use_ema_filter: bool = False
    use_sma_filter: bool = False
    
    # Filter parameters
    regime_threshold: float = 0.0  # More permissive
    adx_threshold: int = 20
    kernel_lookback: int = 8
    kernel_relative_weight: float = 8.0
    kernel_regression_level: int = 25
    kernel_lag: int = 2
    use_kernel_smoothing: bool = False
    
    # Risk management (will be adapted per stock)
    stop_loss_percent: float = 0.3
    take_profit_targets: List[float] = field(default_factory=lambda: [0.15, 0.25, 0.35])
    target_sizes: List[float] = field(default_factory=lambda: [50, 30, 20])
    
    # Exit management
    use_trailing_stop: bool = True
    trailing_activation: float = 0.15  # Activate after first target
    trailing_distance: float = 0.1
    max_holding_bars: int = 15  # 75 minutes for 5-min
    
    # Time filters
    avoid_first_minutes: int = 15
    avoid_last_minutes: int = 15
    market_open_time: str = "09:15"
    market_close_time: str = "15:30"
    
    # Position sizing
    initial_capital: float = 100000
    base_position_size: float = 10.0  # % of capital
    commission_percent: float = 0.03
    slippage_percent: float = 0.05
    
    # Data settings
    symbol: str = ""
    timeframe: str = "5minute"
    lookback_days: int = 90
    
    def adapt_to_stock(self, stock_stats: Dict):
        """
        Adapt configuration based on stock statistics
        
        Args:
            stock_stats: Statistics from SmartDataManager.analyze_price_movement()
        """
        if not stock_stats:
            return
        
        # Get key metrics
        avg_range = stock_stats.get('avg_range_pct', 0.15)
        mfe_50 = stock_stats.get('mfe_long_50_pct', 0.2)
        mfe_70 = stock_stats.get('mfe_long_70_pct', 0.3)
        mfe_90 = stock_stats.get('mfe_long_90_pct', 0.5)
        mae_50 = stock_stats.get('mae_long_50_pct', 0.2)
        
        # Adapt stop loss based on typical adverse movement
        self.stop_loss_percent = min(
            round(mae_50 * 1.2, 2),  # 20% buffer beyond typical MAE
            0.5  # Maximum 0.5% stop
        )
        
        # Adapt targets based on favorable movement statistics
        self.take_profit_targets = [
            round(mfe_50 * 0.7, 2),   # Conservative: 70% of median MFE
            round(mfe_70 * 0.8, 2),   # Normal: 80% of 70th percentile
            round(mfe_90 * 0.7, 2)    # Stretch: 70% of 90th percentile
        ]
        
        # Ensure minimum targets
        self.take_profit_targets = [
            max(t, 0.1) for t in self.take_profit_targets
        ]
        
        # Adapt holding time based on volatility
        if avg_range > 0.2:  # High volatility
            self.max_holding_bars = 10  # Quicker exits
        elif avg_range < 0.15:  # Low volatility  
            self.max_holding_bars = 20  # More time
        
        # Adapt ML confidence based on volatility
        if avg_range > 0.2:
            # High volatility - be more selective
            self.ml_min_confidence = 4.0
            self.ml_high_confidence = 6.0
        elif avg_range < 0.15:
            # Low volatility - can be less selective
            self.ml_min_confidence = 2.0
            self.ml_high_confidence = 4.0
    
    def get_volatility_profile(self, avg_range_pct: float) -> str:
        """Classify stock volatility"""
        if avg_range_pct >= 0.2:
            return "high"
        elif avg_range_pct >= 0.15:
            return "medium"
        else:
            return "low"
    
    def get_settings(self) -> Settings:
        """Convert to Settings object for ML model"""
        return Settings(
            source=self.source,
            neighbors_count=self.neighbors_count,
            max_bars_back=self.max_bars_back,
            feature_count=self.feature_count,
            color_compression=self.color_compression,
            show_exits=False,
            use_dynamic_exits=False
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
Adaptive Configuration for {self.symbol or 'Stock'}
================================================

ML SETTINGS:
- Min Confidence: {self.ml_min_confidence}
- High Confidence: {self.ml_high_confidence}
- Neighbors: {self.neighbors_count}

ACTIVE FILTERS:
- Volatility: {'ON' if self.use_volatility_filter else 'OFF'}
- Regime: {'OFF (disabled)' if not self.use_regime_filter else 'ON'}
- Kernel: {'ON' if self.use_kernel_filter else 'OFF'}

RISK MANAGEMENT:
- Stop Loss: {self.stop_loss_percent}%
- Targets: {self.take_profit_targets}% (sizes: {self.target_sizes}%)
- Max Hold: {self.max_holding_bars} bars

POSITION SIZING:
- Base Size: {self.base_position_size}% of capital
- ML >= {self.ml_high_confidence}: 100% position
- ML >= {self.ml_min_confidence}: 50% position
"""


# Pre-configured profiles for different volatility levels
class VolatilityProfiles:
    """Pre-defined profiles for quick setup"""
    
    @staticmethod
    def get_high_volatility_config() -> AdaptiveConfig:
        """Config for high volatility stocks (LT, RELIANCE)"""
        config = AdaptiveConfig()
        config.stop_loss_percent = 0.4
        config.take_profit_targets = [0.25, 0.4, 0.6]
        config.ml_min_confidence = 4.0
        config.ml_high_confidence = 6.0
        config.max_holding_bars = 10
        return config
    
    @staticmethod
    def get_medium_volatility_config() -> AdaptiveConfig:
        """Config for medium volatility stocks (INFY, AXISBANK)"""
        config = AdaptiveConfig()
        config.stop_loss_percent = 0.3
        config.take_profit_targets = [0.15, 0.25, 0.35]
        config.ml_min_confidence = 3.0
        config.ml_high_confidence = 5.0
        config.max_holding_bars = 15
        return config
    
    @staticmethod
    def get_low_volatility_config() -> AdaptiveConfig:
        """Config for low volatility stocks (ITC, HINDUNILVR)"""
        config = AdaptiveConfig()
        config.stop_loss_percent = 0.25
        config.take_profit_targets = [0.1, 0.15, 0.25]
        config.ml_min_confidence = 2.0
        config.ml_high_confidence = 4.0
        config.max_holding_bars = 20
        return config


# Factory function
def create_adaptive_config(symbol: str, timeframe: str = "5minute", 
                          stock_stats: Optional[Dict] = None) -> AdaptiveConfig:
    """
    Create an adaptive configuration for a specific stock
    
    Args:
        symbol: Stock symbol
        timeframe: Trading timeframe
        stock_stats: Optional pre-calculated statistics
        
    Returns:
        AdaptiveConfig instance adapted to the stock
    """
    config = AdaptiveConfig()
    config.symbol = symbol
    config.timeframe = timeframe
    
    # If we have statistics, adapt to them
    if stock_stats:
        config.adapt_to_stock(stock_stats)
    else:
        # Use defaults based on known stocks
        known_profiles = {
            # High volatility
            'RELIANCE': VolatilityProfiles.get_high_volatility_config,
            'LT': VolatilityProfiles.get_high_volatility_config,
            
            # Medium volatility  
            'INFY': VolatilityProfiles.get_medium_volatility_config,
            'AXISBANK': VolatilityProfiles.get_medium_volatility_config,
            'KOTAKBANK': VolatilityProfiles.get_medium_volatility_config,
            'TCS': VolatilityProfiles.get_medium_volatility_config,
            
            # Low volatility
            'ITC': VolatilityProfiles.get_low_volatility_config,
            'HINDUNILVR': VolatilityProfiles.get_low_volatility_config,
            'ICICIBANK': VolatilityProfiles.get_low_volatility_config,
        }
        
        if symbol in known_profiles:
            # Use known profile
            config = known_profiles[symbol]()
            config.symbol = symbol
            config.timeframe = timeframe
    
    return config


# FUTURE ENHANCEMENTS TO TEST (from trading folder analysis)
# ==========================================================
# These will be tested incrementally after baseline performance is established

class FutureEnhancements:
    """
    Potential improvements to test one by one after core system validation
    """
    
    # 1. From Quantitative-Trading-Introduction
    POSITIVE_EXPECTANCY_FILTER = {
        'min_expectancy': 0.01,
        'require_data_validation': True,
        'description': 'Only trade systems with positive mathematical expectancy'
    }
    
    # 2. From rocket-science-for-trading (Ehlers)
    CYCLE_TREND_DETECTION = {
        'use_cycle_detection': True,
        'min_snr_ratio': 2.0,
        'smooth_data_first': True,
        'description': 'Detect market mode (trend vs cycle) and adapt accordingly'
    }
    
    # 3. From trading-warrior (Momentum Trading)
    VOLATILITY_CATALYST_FILTER = {
        'volatility_threshold': 10.0,  # Min % move on day
        'max_float_millions': 100.0,
        'prefer_low_float': True,
        'gap_threshold': 4.0,
        'description': 'Focus on high volatility, low float stocks with catalysts'
    }
    
    # 4. Time window optimization
    PRIME_TIME_FILTER = {
        'prime_trading_start': '11:30',
        'prime_trading_end': '13:30',
        'avoid_first_hour': True,
        'description': 'Trade only during statistically optimal time windows'
    }
    
    # 5. Advanced risk controls
    STRICT_RISK_MANAGEMENT = {
        'max_trades_per_day': 2,
        'require_profit_on_first_trade': True,
        'min_profit_loss_ratio': 2.0,
        'description': 'Strict psychological and risk controls'
    }