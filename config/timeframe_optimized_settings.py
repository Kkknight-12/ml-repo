"""
Timeframe-Optimized Settings for Lorentzian Classification System

This module provides optimized parameter sets for different trading timeframes.
Each configuration is tuned based on the characteristics of that specific timeframe.

Key principles:
- Shorter timeframes: Faster exits, tighter stops, fewer neighbors for responsiveness
- Longer timeframes: Wider stops, more neighbors for stability, higher confidence thresholds
- Filter settings: ADX more useful on longer timeframes, volatility filters on shorter
- Target ratios: Scale with timeframe to capture appropriate move sizes
"""

from typing import Dict, Any

# Base configuration template
BASE_CONFIG = {
    # ML Model Parameters
    "ml_model": {
        "neighbors_count": 8,
        "max_bars_back": 2000,
        "feature_count": 5,
        "color_compression": 1,
        "use_dynamic_exits": True,
        "prediction_confidence_threshold": 0.5
    },
    
    # Feature Engineering
    "features": {
        "rsi_length": 14,
        "wt_length": 10,
        "cci_length": 20,
        "adx_length": 20,
        "rsi_source": "close",
        "feature_weights": {
            "rsi": 1.0,
            "wt": 1.0,
            "cci": 1.0,
            "adx": 1.0,
            "price_relative": 1.0
        }
    },
    
    # Kernel Settings
    "kernel": {
        "use_kernel_filter": True,
        "use_kernel_smoothing": False,
        "kernel_lookback": 3,
        "kernel_weight": 8,
        "kernel_regression_bandwidth": 8,
        "use_rational_quadratic": True,
        "lag": 2
    },
    
    # Filter Settings
    "filters": {
        "use_volatility_filter": True,
        "use_regime_filter": True,
        "use_adx_filter": True,
        "regime_threshold": -0.1,
        "adx_threshold": 20,
        "volatility_lookback": 20,
        "filter_combination": "any"  # "any" or "all"
    },
    
    # Exit Strategy
    "exit_strategy": {
        "take_profit_atr_multiplier": 1.0,
        "stop_loss_atr_multiplier": 1.0,
        "use_trailing_stop": False,
        "trailing_stop_activation": 1.5,
        "trailing_stop_distance": 0.5
    },
    
    # Risk Management
    "risk_management": {
        "position_size_pct": 10.0,
        "max_positions": 3,
        "risk_per_trade_pct": 2.0,
        "use_kelly_criterion": False
    }
}


# 1-Minute Timeframe Configuration
# Optimized for: Scalping, quick in-and-out trades
CONFIG_1MIN = {
    **BASE_CONFIG,
    "ml_model": {
        **BASE_CONFIG["ml_model"],
        "neighbors_count": 5,  # Fewer neighbors for faster response
        "prediction_confidence_threshold": 0.45  # Lower threshold for more signals
    },
    "features": {
        **BASE_CONFIG["features"],
        "rsi_length": 9,  # Faster RSI
        "wt_length": 7,   # Faster Wave Trend
        "cci_length": 14, # Faster CCI
        "adx_length": 14, # Faster ADX
    },
    "kernel": {
        **BASE_CONFIG["kernel"],
        "kernel_lookback": 2,  # Shorter lookback
        "kernel_weight": 6,    # Lower weight for responsiveness
        "lag": 1              # Minimal lag
    },
    "filters": {
        **BASE_CONFIG["filters"],
        "use_adx_filter": False,  # ADX less reliable on 1-min
        "use_volatility_filter": True,  # Volatility important for scalping
        "volatility_lookback": 10,  # Shorter lookback
        "filter_combination": "any"
    },
    "exit_strategy": {
        **BASE_CONFIG["exit_strategy"],
        "take_profit_atr_multiplier": 0.5,  # Very tight targets
        "stop_loss_atr_multiplier": 0.3,    # Very tight stops
        "use_trailing_stop": True,          # Trail aggressively
        "trailing_stop_activation": 0.5,     # Activate early
        "trailing_stop_distance": 0.2       # Tight trailing
    }
}


# 5-Minute Timeframe Configuration
# Optimized for: Short-term trading, intraday momentum
CONFIG_5MIN = {
    **BASE_CONFIG,
    "ml_model": {
        **BASE_CONFIG["ml_model"],
        "neighbors_count": 6,  # Balanced neighbor count
        "prediction_confidence_threshold": 0.48
    },
    "features": {
        **BASE_CONFIG["features"],
        "rsi_length": 12,
        "wt_length": 9,
        "cci_length": 18,
        "adx_length": 18,
    },
    "kernel": {
        **BASE_CONFIG["kernel"],
        "kernel_lookback": 3,
        "kernel_weight": 7,
        "lag": 2
    },
    "filters": {
        **BASE_CONFIG["filters"],
        "use_adx_filter": True,
        "adx_threshold": 18,  # Slightly lower threshold
        "volatility_lookback": 15,
        "filter_combination": "any"
    },
    "exit_strategy": {
        **BASE_CONFIG["exit_strategy"],
        "take_profit_atr_multiplier": 0.8,
        "stop_loss_atr_multiplier": 0.5,
        "use_trailing_stop": True,
        "trailing_stop_activation": 1.0,
        "trailing_stop_distance": 0.3
    }
}


# 15-Minute Timeframe Configuration
# Optimized for: Intraday swing trading
CONFIG_15MIN = {
    **BASE_CONFIG,
    "ml_model": {
        **BASE_CONFIG["ml_model"],
        "neighbors_count": 8,  # Standard neighbor count
        "prediction_confidence_threshold": 0.5
    },
    "features": {
        **BASE_CONFIG["features"],
        # Using default lengths from BASE_CONFIG
    },
    "kernel": {
        **BASE_CONFIG["kernel"],
        # Using default settings from BASE_CONFIG
    },
    "filters": {
        **BASE_CONFIG["filters"],
        "use_adx_filter": True,
        "adx_threshold": 20,
        "filter_combination": "any"
    },
    "exit_strategy": {
        **BASE_CONFIG["exit_strategy"],
        "take_profit_atr_multiplier": 1.2,
        "stop_loss_atr_multiplier": 0.8,
        "use_trailing_stop": True,
        "trailing_stop_activation": 1.5,
        "trailing_stop_distance": 0.5
    }
}


# 30-Minute Timeframe Configuration
# Optimized for: Intraday position trading
CONFIG_30MIN = {
    **BASE_CONFIG,
    "ml_model": {
        **BASE_CONFIG["ml_model"],
        "neighbors_count": 10,  # More neighbors for stability
        "prediction_confidence_threshold": 0.52
    },
    "features": {
        **BASE_CONFIG["features"],
        "rsi_length": 16,
        "wt_length": 12,
        "cci_length": 22,
        "adx_length": 22,
    },
    "kernel": {
        **BASE_CONFIG["kernel"],
        "kernel_lookback": 4,
        "kernel_weight": 9,
        "kernel_regression_bandwidth": 10,
    },
    "filters": {
        **BASE_CONFIG["filters"],
        "use_adx_filter": True,
        "adx_threshold": 22,
        "regime_threshold": -0.05,  # Less strict regime filter
        "filter_combination": "all"  # More conservative
    },
    "exit_strategy": {
        **BASE_CONFIG["exit_strategy"],
        "take_profit_atr_multiplier": 1.5,
        "stop_loss_atr_multiplier": 1.0,
        "use_trailing_stop": True,
        "trailing_stop_activation": 2.0,
        "trailing_stop_distance": 0.7
    }
}


# 60-Minute (1 Hour) Timeframe Configuration
# Optimized for: Swing trading, multi-day positions
CONFIG_60MIN = {
    **BASE_CONFIG,
    "ml_model": {
        **BASE_CONFIG["ml_model"],
        "neighbors_count": 12,  # More neighbors for better confirmation
        "prediction_confidence_threshold": 0.55
    },
    "features": {
        **BASE_CONFIG["features"],
        "rsi_length": 18,
        "wt_length": 14,
        "cci_length": 25,
        "adx_length": 25,
    },
    "kernel": {
        **BASE_CONFIG["kernel"],
        "kernel_lookback": 5,
        "kernel_weight": 10,
        "kernel_regression_bandwidth": 12,
        "lag": 3
    },
    "filters": {
        **BASE_CONFIG["filters"],
        "use_adx_filter": True,
        "adx_threshold": 25,
        "regime_threshold": 0.0,  # Neutral regime filter
        "volatility_lookback": 30,
        "filter_combination": "all"
    },
    "exit_strategy": {
        **BASE_CONFIG["exit_strategy"],
        "take_profit_atr_multiplier": 2.0,
        "stop_loss_atr_multiplier": 1.2,
        "use_trailing_stop": True,
        "trailing_stop_activation": 2.5,
        "trailing_stop_distance": 1.0
    },
    "risk_management": {
        **BASE_CONFIG["risk_management"],
        "position_size_pct": 15.0,  # Larger positions for longer timeframe
        "max_positions": 5,
        "risk_per_trade_pct": 2.5,
    }
}


# Daily Timeframe Configuration
# Optimized for: Position trading, long-term trends
CONFIG_DAILY = {
    **BASE_CONFIG,
    "ml_model": {
        **BASE_CONFIG["ml_model"],
        "neighbors_count": 15,  # Maximum neighbors for high confidence
        "prediction_confidence_threshold": 0.6,  # High confidence required
        "max_bars_back": 3000  # More historical data
    },
    "features": {
        **BASE_CONFIG["features"],
        "rsi_length": 21,
        "wt_length": 21,
        "cci_length": 30,
        "adx_length": 30,
        "feature_weights": {
            "rsi": 0.8,          # Slightly less weight on oscillators
            "wt": 0.8,
            "cci": 0.8,
            "adx": 1.2,          # More weight on trend strength
            "price_relative": 1.2 # More weight on price action
        }
    },
    "kernel": {
        **BASE_CONFIG["kernel"],
        "kernel_lookback": 7,
        "kernel_weight": 12,
        "kernel_regression_bandwidth": 15,
        "lag": 5
    },
    "filters": {
        **BASE_CONFIG["filters"],
        "use_adx_filter": True,
        "adx_threshold": 30,  # Strong trends only
        "regime_threshold": 0.1,  # Bullish regime preference
        "volatility_lookback": 50,
        "filter_combination": "all"  # Most conservative
    },
    "exit_strategy": {
        **BASE_CONFIG["exit_strategy"],
        "take_profit_atr_multiplier": 3.0,  # Wide targets for big moves
        "stop_loss_atr_multiplier": 1.5,    # Wider stops
        "use_trailing_stop": True,
        "trailing_stop_activation": 3.0,     # Let profits run
        "trailing_stop_distance": 1.5       # Give room to breathe
    },
    "risk_management": {
        **BASE_CONFIG["risk_management"],
        "position_size_pct": 20.0,  # Larger positions
        "max_positions": 10,        # More diversification
        "risk_per_trade_pct": 3.0,  # Can risk more per trade
        "use_kelly_criterion": True  # Consider Kelly for position sizing
    }
}


# Configuration mapping by timeframe
TIMEFRAME_CONFIGS = {
    "1min": CONFIG_1MIN,
    "1m": CONFIG_1MIN,
    "5min": CONFIG_5MIN,
    "5m": CONFIG_5MIN,
    "15min": CONFIG_15MIN,
    "15m": CONFIG_15MIN,
    "30min": CONFIG_30MIN,
    "30m": CONFIG_30MIN,
    "60min": CONFIG_60MIN,
    "60m": CONFIG_60MIN,
    "1h": CONFIG_60MIN,
    "daily": CONFIG_DAILY,
    "1d": CONFIG_DAILY,
    "1D": CONFIG_DAILY,
}


def get_config_for_timeframe(timeframe: str) -> Dict[str, Any]:
    """
    Get the optimized configuration for a specific timeframe.
    
    Args:
        timeframe: Timeframe string (e.g., "5min", "1h", "daily")
    
    Returns:
        Configuration dictionary for the timeframe
    """
    config = TIMEFRAME_CONFIGS.get(timeframe.lower())
    if config is None:
        print(f"Warning: No optimized config for timeframe '{timeframe}', using base config")
        return BASE_CONFIG
    return config


def get_timeframe_characteristics(timeframe: str) -> Dict[str, str]:
    """
    Get descriptive characteristics of a timeframe configuration.
    
    Args:
        timeframe: Timeframe string
    
    Returns:
        Dictionary describing the timeframe's trading characteristics
    """
    characteristics = {
        "1min": {
            "style": "Scalping",
            "description": "Ultra-fast entries and exits, minimal drawdown tolerance",
            "best_for": "High-frequency traders, news trading, momentum scalping",
            "risk_level": "High",
            "typical_holding": "Seconds to minutes"
        },
        "5min": {
            "style": "Short-term trading",
            "description": "Quick intraday moves, balanced risk-reward",
            "best_for": "Active day traders, momentum trading",
            "risk_level": "Medium-High",
            "typical_holding": "Minutes to hours"
        },
        "15min": {
            "style": "Intraday swing",
            "description": "Captures intraday swings with moderate stops",
            "best_for": "Day traders, intraday swing traders",
            "risk_level": "Medium",
            "typical_holding": "Hours within a day"
        },
        "30min": {
            "style": "Intraday position",
            "description": "Larger intraday moves, more selective entries",
            "best_for": "Position traders, part-time traders",
            "risk_level": "Medium",
            "typical_holding": "Multiple hours to 1-2 days"
        },
        "60min": {
            "style": "Swing trading",
            "description": "Multi-day swings, trend following",
            "best_for": "Swing traders, working professionals",
            "risk_level": "Medium-Low",
            "typical_holding": "Days to weeks"
        },
        "daily": {
            "style": "Position trading",
            "description": "Long-term trends, maximum profit potential",
            "best_for": "Position traders, investors",
            "risk_level": "Low",
            "typical_holding": "Weeks to months"
        }
    }
    
    # Normalize timeframe key
    timeframe_key = timeframe.lower()
    if timeframe_key in ["1m", "1min"]:
        timeframe_key = "1min"
    elif timeframe_key in ["5m", "5min"]:
        timeframe_key = "5min"
    elif timeframe_key in ["15m", "15min"]:
        timeframe_key = "15min"
    elif timeframe_key in ["30m", "30min"]:
        timeframe_key = "30min"
    elif timeframe_key in ["60m", "60min", "1h"]:
        timeframe_key = "60min"
    elif timeframe_key in ["1d", "daily"]:
        timeframe_key = "daily"
    
    return characteristics.get(timeframe_key, {
        "style": "Unknown",
        "description": "No specific characteristics defined",
        "best_for": "General trading",
        "risk_level": "Unknown",
        "typical_holding": "Variable"
    })


# Performance optimization tips by timeframe
OPTIMIZATION_TIPS = {
    "1min": [
        "Use limit orders to avoid slippage",
        "Monitor spread costs closely",
        "Consider commission impact on profitability",
        "Use co-located servers for minimal latency",
        "Focus on liquid instruments only"
    ],
    "5min": [
        "Balance between signal frequency and quality",
        "Use volatility-based position sizing",
        "Monitor for false breakouts",
        "Consider time-of-day filters",
        "Focus on high-volume periods"
    ],
    "15min": [
        "Use multiple timeframe confirmation",
        "Consider market structure (support/resistance)",
        "Add volume analysis for confirmation",
        "Use wider stops during news events",
        "Scale into positions"
    ],
    "30min": [
        "Focus on trend strength indicators",
        "Use higher timeframe bias",
        "Consider overnight risk",
        "Add fundamental filters for stocks",
        "Use options for risk management"
    ],
    "60min": [
        "Emphasize trend following",
        "Use weekly levels for targets",
        "Consider sector rotation",
        "Add market breadth indicators",
        "Use partial profit taking"
    ],
    "daily": [
        "Focus on major trend changes",
        "Use monthly/weekly levels",
        "Consider fundamental analysis",
        "Use portfolio-level risk management",
        "Consider hedging strategies"
    ]
}


def get_optimization_tips(timeframe: str) -> list:
    """Get optimization tips for a specific timeframe."""
    timeframe_key = timeframe.lower()
    for key in ["1min", "5min", "15min", "30min", "60min", "daily"]:
        if key in timeframe_key or timeframe_key in key:
            return OPTIMIZATION_TIPS.get(key, [])
    return ["Use general best practices for your timeframe"]


if __name__ == "__main__":
    # Example usage
    print("Available timeframe configurations:")
    for tf in ["1min", "5min", "15min", "30min", "60min", "daily"]:
        config = get_config_for_timeframe(tf)
        chars = get_timeframe_characteristics(tf)
        tips = get_optimization_tips(tf)
        
        print(f"\n{tf.upper()} Configuration:")
        print(f"  Style: {chars['style']}")
        print(f"  Description: {chars['description']}")
        print(f"  Neighbors: {config['ml_model']['neighbors_count']}")
        print(f"  Confidence Threshold: {config['ml_model']['prediction_confidence_threshold']}")
        print(f"  TP Multiplier: {config['exit_strategy']['take_profit_atr_multiplier']}")
        print(f"  SL Multiplier: {config['exit_strategy']['stop_loss_atr_multiplier']}")
        print(f"  Key Tips: {', '.join(tips[:2])}")