"""
⚠️ DEPRECATED - DO NOT USE ⚠️
==============================

This configuration is DEPRECATED due to critical issues:
- ML predictions differ 79% from standard config
- Only generates 2 trades in 180 days (vs 47 with standard)
- Features incompatible with trained ML model
- Kernel smoothing blocks valid trades
- All changes combined break the system

USE INSTEAD: FixedOptimizedTradingConfig from config.fixed_optimized_settings

DEPRECATED: Optimized Settings for Lorentzian Classification Trading System
===========================================================================

Based on analysis of current performance and best practices from:
- Current test results (75% win rate but small wins ~3.7%)
- AI Trading Knowledge Base (85% win rate in prime window)
- Quantitative Trading principles (risk-first approach)
- Trading Warrior methodology (momentum + quality filters)
- Rocket Science for Traders (Ehlers DSP techniques)

Key issues addressed:
1. Small average wins despite high win rate
2. Fixed 5-bar exits (not adaptive)
3. Low trade frequency
4. Poor risk-reward ratio
5. No market mode detection (trend vs cycle)
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple
from data.data_types import Settings, FilterSettings
from config.constants import DEFAULT_FEATURES
import warnings

@dataclass
class OptimizedTradingConfig:
    """
    ⚠️ DEPRECATED - DO NOT USE ⚠️
    
    Use FixedOptimizedTradingConfig from config.fixed_optimized_settings instead.
    This config generates only 2 trades in 180 days due to incompatible changes.
    """
    
    def __post_init__(self):
        """Issue deprecation warning when instantiated"""
        warnings.warn(
            "OptimizedTradingConfig is DEPRECATED and generates only 2 trades in 180 days! "
            "Use FixedOptimizedTradingConfig from config.fixed_optimized_settings instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
    # ===== CORE ML PARAMETERS (Minimal changes for stability) =====
    
    # Keep default - well tested
    source: str = 'close'
    
    # CHANGE: Reduce to 6 for more responsive signals
    # Rationale: Current system misses opportunities, need more signals
    neighbors_count: int = 6  # Changed from 8
    
    # Keep default - optimal for 5min timeframe
    max_bars_back: int = 2000
    
    # Keep default - 5 features is optimal
    feature_count: int = 5
    
    # Keep defaults for display
    color_compression: int = 1
    show_exits: bool = True  # Changed to True for monitoring
    
    # CRITICAL CHANGE: Enable dynamic exits
    # Rationale: Fixed 5-bar exit is leaving money on table
    use_dynamic_exits: bool = True  # Changed from False
    
    # ===== FEATURE ENGINEERING (Optimize for momentum) =====
    
    # CHANGE: Adjusted for better momentum detection
    features: Dict[str, Tuple[str, int, int]] = field(default_factory=lambda: {
        "f1": ("RSI", 9, 1),    # Faster RSI for momentum (was 14)
        "f2": ("WT", 10, 11),   # Keep WaveTrend - good for reversals
        "f3": ("ADX", 14, 2),   # Faster ADX for trend strength (was 20)
        "f4": ("CCI", 14, 1),   # Faster CCI (was 20)
        "f5": ("RSI", 21, 1)    # Slower RSI for divergences (was 9)
    })
    
    # ===== FILTERS (More selective for quality) =====
    
    # Keep volatility filter
    use_volatility_filter: bool = True
    
    # Keep regime filter but adjust threshold
    use_regime_filter: bool = True
    
    # CHANGE: Lower threshold for more selective entries
    # Rationale: Quality over quantity
    regime_threshold: float = -0.2  # Changed from -0.1
    
    # CHANGE: Enable ADX filter for trend confirmation
    # Rationale: Trade only in trending markets
    use_adx_filter: bool = True  # Changed from False
    
    # CHANGE: Higher ADX threshold for stronger trends
    # Rationale: Momentum works better in strong trends
    adx_threshold: int = 25  # Changed from 20
    
    # ===== TREND FILTERS (Add confirmation) =====
    
    # CHANGE: Enable both EMA and SMA filters
    # Rationale: Dual confirmation reduces false signals
    use_ema_filter: bool = True  # Changed from False
    ema_period: int = 20  # Fast EMA for trend
    
    use_sma_filter: bool = True  # Changed from False  
    sma_period: int = 50  # Slower SMA for major trend
    
    # ===== KERNEL SETTINGS (Fine-tune for responsiveness) =====
    
    use_kernel_filter: bool = True
    show_kernel_estimate: bool = True
    
    # CHANGE: Enable smoothing to reduce whipsaws
    # Rationale: Too many false signals in current system
    use_kernel_smoothing: bool = True  # Changed from False
    
    # CHANGE: Shorter lookback for faster response
    # Rationale: Current system is too slow to react
    kernel_lookback: int = 6  # Changed from 8
    
    # Keep other kernel settings
    kernel_relative_weight: float = 8.0
    kernel_regression_level: int = 25
    kernel_lag: int = 2
    
    # ===== DISPLAY SETTINGS =====
    show_bar_colors: bool = True
    show_bar_predictions: bool = True
    use_atr_offset: bool = False
    bar_predictions_offset: float = 0.0
    
    # ===== RISK MANAGEMENT (New parameters) =====
    
    # Position sizing
    risk_per_trade: float = 0.015  # 1.5% risk per trade
    max_positions: int = 3  # Maximum concurrent positions
    
    # Stop loss settings (ATR-based)
    stop_loss_atr_multiplier: float = 1.5  # Tighter stops
    
    # Profit targets (multiple exits)
    target_1_ratio: float = 1.5  # First target at 1.5R
    target_1_percent: float = 0.5  # Exit 50% at first target
    target_2_ratio: float = 3.0  # Second target at 3R
    target_2_percent: float = 0.3  # Exit 30% at second target
    # Remaining 20% with trailing stop
    
    # ===== TIME-BASED SETTINGS (New parameters) =====
    
    # Trading windows (Indian market)
    no_trade_before_hour: float = 9.5  # 9:30 AM (market open + 15 min)
    prime_window_start: float = 10.0  # 10:00 AM
    prime_window_end: float = 14.0  # 2:00 PM
    no_trade_after_hour: float = 14.75  # 2:45 PM
    
    # Time-based position limits
    max_trades_per_day: int = 5  # Increased from implied 2
    
    # ===== SIGNAL QUALITY THRESHOLDS (New parameters) =====
    
    # Minimum ML prediction strength
    min_prediction_strength: float = 3.0  # Require stronger signals
    
    # Pattern quality score
    min_pattern_score: float = 6.0  # Minimum quality score
    high_conviction_score: float = 8.0  # High conviction trades get larger size
    
    # ===== EHLERS DSP ENHANCEMENTS (New from Rocket Science) =====
    
    # Market mode detection
    use_market_mode_detection: bool = True  # Enable trend/cycle detection
    trend_mode_adx_threshold: int = 25  # ADX > 25 = trend mode
    
    # Signal filtering
    use_ehlers_smoothing: bool = True  # Use Super Smoother instead of SMA
    super_smoother_cutoff: int = 10  # Cutoff period for Super Smoother
    
    # Cycle measurement
    use_cycle_measurement: bool = True  # Measure dominant cycle period
    min_cycle_period: int = 10  # Minimum tradable cycle
    max_cycle_period: int = 48  # Maximum tradable cycle
    
    # Signal-to-Noise Ratio
    min_snr_threshold: float = 6.0  # Minimum SNR for cycle trades (in dB)
    
    # Adaptive features
    use_adaptive_indicators: bool = True  # Adapt indicator periods to cycle
    
    # ===== METHODS =====
    
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
    
    def adjust_for_market_conditions(self, volatility_percentile: float, trend_strength: float):
        """Dynamic adjustment based on market conditions"""
        
        # High volatility adjustments
        if volatility_percentile > 80:
            self.stop_loss_atr_multiplier = 2.0  # Wider stops
            self.risk_per_trade = 0.01  # Reduce risk
            self.min_prediction_strength = 4.0  # Require stronger signals
        
        # Low volatility adjustments  
        elif volatility_percentile < 20:
            self.stop_loss_atr_multiplier = 1.2  # Tighter stops
            self.kernel_lookback = 5  # More responsive
            self.min_pattern_score = 5.0  # Accept more signals
        
        # Strong trend adjustments
        if trend_strength > 30:  # ADX > 30
            self.use_dynamic_exits = True
            self.target_2_ratio = 4.0  # Let winners run
            self.neighbors_count = 5  # More responsive
        
        # Ranging market adjustments
        elif trend_strength < 20:  # ADX < 20
            self.regime_threshold = -0.3  # More selective
            self.min_prediction_strength = 4.0  # Higher conviction required
            self.target_1_ratio = 1.2  # Quick profits
    
    def get_position_size_multiplier(self, pattern_score: float) -> float:
        """Adjust position size based on pattern quality"""
        if pattern_score >= self.high_conviction_score:
            return 1.5  # 50% larger position
        elif pattern_score >= self.min_pattern_score:
            return 1.0  # Normal position
        else:
            return 0.0  # No trade


# ===== CONFIGURATION PRESETS =====

def get_conservative_config() -> OptimizedTradingConfig:
    """Conservative settings for beginners or small accounts
    ⚠️ DEPRECATED - Returns deprecated OptimizedTradingConfig
    """
    config = OptimizedTradingConfig()
    config.risk_per_trade = 0.01  # 1% risk
    config.neighbors_count = 8  # More stable
    config.min_prediction_strength = 4.0  # Higher conviction
    config.min_pattern_score = 7.0  # Quality over quantity
    config.max_positions = 2  # Fewer positions
    return config


def get_aggressive_config() -> OptimizedTradingConfig:
    """Aggressive settings for experienced traders"""
    config = OptimizedTradingConfig()
    config.risk_per_trade = 0.02  # 2% risk
    config.neighbors_count = 5  # More responsive
    config.min_prediction_strength = 2.0  # More signals
    config.min_pattern_score = 5.0  # More opportunities
    config.max_positions = 5  # More positions
    config.use_kernel_smoothing = False  # Less filtering
    return config


def get_scalping_config() -> OptimizedTradingConfig:
    """Settings optimized for quick scalps"""
    config = OptimizedTradingConfig()
    config.neighbors_count = 4  # Very responsive
    config.kernel_lookback = 5  # Short lookback
    config.target_1_ratio = 1.2  # Quick profits
    config.target_1_percent = 0.8  # Exit 80% quickly
    config.stop_loss_atr_multiplier = 1.0  # Tight stops
    config.features["f1"] = ("RSI", 7, 1)  # Faster RSI
    config.features["f3"] = ("CCI", 10, 1)  # Faster CCI
    return config


def get_swing_trading_config() -> OptimizedTradingConfig:
    """Settings for longer-term swing trades"""
    config = OptimizedTradingConfig()
    config.neighbors_count = 10  # More stable
    config.max_bars_back = 3000  # More history
    config.kernel_lookback = 10  # Longer lookback
    config.target_2_ratio = 5.0  # Let winners run
    config.use_dynamic_exits = True  # Essential for swings
    config.ema_period = 50  # Slower EMA
    config.sma_period = 200  # Major trend
    return config


def get_ehlers_cycle_config() -> OptimizedTradingConfig:
    """Settings optimized for Ehlers cycle trading"""
    config = OptimizedTradingConfig()
    
    # Core ML - adaptive to cycles
    config.neighbors_count = 5  # Responsive to cycles
    config.use_dynamic_exits = True  # Must adapt to cycle phase
    
    # Features - focus on cycle indicators
    config.features["f1"] = ("RSI", 14, 1)  # Will be made adaptive
    config.features["f2"] = ("WT", 10, 11)  # Excellent for cycles
    config.features["f3"] = ("CCI", 20, 1)  # Will be made adaptive
    config.features["f4"] = ("ADX", 14, 2)  # For mode detection
    config.features["f5"] = ("RSI", 21, 1)  # Divergence detection
    
    # Filters - cycle-focused
    config.use_volatility_filter = True
    config.use_regime_filter = True
    config.regime_threshold = -0.15  # Balanced
    config.use_adx_filter = True
    config.adx_threshold = 20  # Lower for cycle mode
    
    # Ehlers enhancements - all enabled
    config.use_market_mode_detection = True
    config.use_ehlers_smoothing = True
    config.use_cycle_measurement = True
    config.use_adaptive_indicators = True
    config.min_snr_threshold = 6.0  # Quality cycles only
    
    # Risk management - cycle-aware
    config.stop_loss_atr_multiplier = 1.2  # Tighter for cycles
    config.target_1_ratio = 1.5  # Quick profit at cycle peak
    config.target_2_ratio = 2.5  # Full cycle swing
    
    # Time windows - all day for cycles
    config.no_trade_before_hour = 9.25  # Early start OK
    config.no_trade_after_hour = 15.25  # Late end OK
    
    return config


# ===== MAIN OPTIMIZED CONFIG =====

# Create the optimized configuration instance
optimized_config = OptimizedTradingConfig()

# Summary of key changes:
"""
CHANGES MADE AND RATIONALE:

1. RESPONSIVENESS (Address low trade frequency)
   - neighbors_count: 8 → 6 (more signals)
   - kernel_lookback: 8 → 6 (faster response)
   - Features: Faster indicators (RSI 14→9, ADX 20→14, CCI 20→14)

2. EXIT MANAGEMENT (Address small wins)
   - use_dynamic_exits: False → True (adaptive exits)
   - Multi-target system: 50% at 1.5R, 30% at 3R, 20% trailing
   - Stop loss: ATR-based with 1.5x multiplier

3. QUALITY FILTERS (Improve win rate)
   - use_adx_filter: False → True (trend confirmation)
   - adx_threshold: 20 → 25 (stronger trends only)
   - regime_threshold: -0.1 → -0.2 (more selective)
   - use_kernel_smoothing: False → True (reduce false signals)
   - Enable both EMA and SMA filters for dual confirmation

4. RISK MANAGEMENT (New framework)
   - Risk per trade: 1.5% (balanced approach)
   - Max positions: 3 (diversification)
   - Position sizing based on pattern quality

5. TIME WINDOWS (From AI Knowledge Base)
   - Prime window: 10:00 AM - 2:00 PM
   - No trades before 9:30 AM or after 2:45 PM
   - Max 5 trades per day

Expected improvements:
- More trades: 5-10 per 1000 bars (vs current 3.2)
- Larger wins: 8-10% average (vs current 3.7%)
- Better risk-reward: 1:2 to 1:3 average
- Maintained win rate: 65-70% (slight decrease is OK)
"""