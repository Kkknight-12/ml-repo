"""
Fixed Optimized Trading Configuration
=====================================

This fixes the issues with OptimizedTradingConfig that were causing
only 2 trades to be generated. The main issues were:
1. Different features causing ML predictions to differ 79% of the time
2. Kernel smoothing being enabled
3. Reduced neighbors count affecting ML quality

This config keeps the good improvements while fixing the problems.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple
from config.settings import TradingConfig


@dataclass
class FixedOptimizedTradingConfig(TradingConfig):
    """
    Fixed optimized configuration that maintains compatibility
    with the ML model while adding selective improvements.
    """
    
    # ===== ML SETTINGS (Keep mostly standard for compatibility) =====
    
    # KEEP standard features - changing these breaks ML predictions!
    features: Dict[str, Tuple[str, int, int]] = field(default_factory=lambda: {
        "f1": ("RSI", 14, 1),   # Keep standard
        "f2": ("WT", 10, 11),   # Keep standard
        "f3": ("CCI", 20, 1),   # Keep standard
        "f4": ("ADX", 20, 2),   # Keep standard
        "f5": ("RSI", 9, 1)     # Keep standard
    })
    
    # KEEP standard neighbors for consistent ML behavior
    neighbors_count: int = 8  # Keep at 8, not 6
    
    # CHANGE: Enable dynamic exits (this was good)
    use_dynamic_exits: bool = True
    
    # ===== FILTERS (Make more selective) =====
    
    # Keep volatility and regime filters
    use_volatility_filter: bool = True
    use_regime_filter: bool = True
    
    # CHANGE: Tighten regime threshold for better selectivity
    regime_threshold: float = -0.15  # Slightly tighter than -0.1
    
    # CHANGE: Disable ADX filter (matches Pine Script default)
    use_adx_filter: bool = False  # Pine Script default is False
    adx_threshold: int = 20  # Keep at 20 if ever enabled
    
    # KEEP trend filters disabled by default
    use_ema_filter: bool = False
    use_sma_filter: bool = False
    
    # ===== KERNEL SETTINGS (Keep standard) =====
    
    # KEEP kernel smoothing OFF - it was filtering out good trades
    use_kernel_smoothing: bool = False
    kernel_lookback: int = 8  # Keep standard
    
    # ===== EXIT STRATEGY (Multi-target improvements) =====
    
    # Target ratios for partial exits (R-multiples)
    target_1_ratio: float = 1.5   # Take 50% at 1.5R
    target_1_percent: float = 0.5
    
    target_2_ratio: float = 3.0   # Take 30% at 3R
    target_2_percent: float = 0.3
    
    # Remaining 20% rides with trailing stop
    trailing_stop_distance_ratio: float = 1.0
    
    # ===== RISK MANAGEMENT =====
    
    # Tighter stop loss for better risk management
    stop_loss_atr_multiplier: float = 1.5  # Tighter than default 2.0
    
    # ===== POSITION SIZING =====
    
    # Conservative position sizing
    position_size_percent: float = 2.0  # 2% risk per trade
    
    # ===== TIME FILTERS (Optional improvements) =====
    
    # Could add time-based filters later
    use_time_filter: bool = False
    no_trade_before: float = 9.5   # 9:30 AM
    no_trade_after: float = 15.0   # 3:00 PM
    prime_window_start: float = 10.5  # 10:30 AM
    prime_window_end: float = 14.5    # 2:30 PM


@dataclass 
class AggressiveOptimizedConfig(FixedOptimizedTradingConfig):
    """More aggressive version for higher returns (higher risk)"""
    
    # Slightly more aggressive ML threshold
    min_prediction_strength: float = 2.5  # vs 3.0 default
    
    # Looser filters for more trades
    regime_threshold: float = -0.1
    adx_threshold: int = 15
    
    # More aggressive targets
    target_1_ratio: float = 2.0   # Higher first target
    target_2_ratio: float = 4.0   # Much higher second target
    
    # Slightly wider stop
    stop_loss_atr_multiplier: float = 2.0
    
    # Larger position size
    position_size_percent: float = 3.0


@dataclass
class ConservativeOptimizedConfig(FixedOptimizedTradingConfig):
    """More conservative version for capital preservation"""
    
    # Stricter ML threshold
    min_prediction_strength: float = 4.0
    
    # Tighter filters
    regime_threshold: float = -0.2
    adx_threshold: int = 25
    
    # Conservative targets
    target_1_ratio: float = 1.2   # Quick first exit
    target_1_percent: float = 0.7  # Exit 70% quickly
    target_2_ratio: float = 2.0
    target_2_percent: float = 0.3
    
    # Tighter stop
    stop_loss_atr_multiplier: float = 1.2
    
    # Smaller position size
    position_size_percent: float = 1.0


# Recommendations for improving win rate:
"""
IMPROVING WIN RATE FROM 36.2% TO 50%+:

1. ML Model Quality:
   - The model needs retraining with more recent data
   - Consider adding volume-based features
   - Add market regime detection

2. Better Entry Filters:
   - Current filters (all passing) are not discriminating
   - Add momentum confirmation (e.g., price above VWAP)
   - Add volume surge detection
   - Check for support/resistance levels

3. Exit Optimization:
   - Stop losses are hitting 32% of trades
   - Consider volatility-based stops
   - Add time-based exits for non-performing trades
   - Implement trailing stops after 1R profit

4. Market Conditions:
   - Add market trend filter (bullish/bearish/sideways)
   - Avoid trading during high volatility events
   - Check correlation with Nifty direction

5. Position Sizing:
   - Reduce size during losing streaks
   - Increase size during winning streaks
   - Use Kelly Criterion for optimal sizing
"""