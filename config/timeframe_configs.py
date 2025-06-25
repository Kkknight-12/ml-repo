"""
Timeframe-Specific Trading Configurations
=========================================

Provides TradingConfig instances optimized for different timeframes.
Integrates with the existing config system while providing timeframe-specific optimizations.
"""

from typing import Dict, Optional
from datetime import datetime

from config.settings import TradingConfig
from config.fixed_optimized_settings import FixedOptimizedTradingConfig
from config.timeframe_optimized_settings import TIMEFRAME_CONFIGS, get_config_for_timeframe


class TimeframeTradingConfig(TradingConfig):
    """Trading configuration with timeframe-specific optimizations"""
    
    def __init__(self, timeframe: str = "5min"):
        super().__init__()
        self.timeframe = timeframe
        self._apply_timeframe_settings()
    
    def _apply_timeframe_settings(self):
        """Apply timeframe-specific settings"""
        tf_config = get_config_for_timeframe(self.timeframe)
        
        if not tf_config:
            print(f"⚠️  No specific config for {self.timeframe}, using defaults")
            return
        
        # ML Model settings
        ml_settings = tf_config["ml_model"]
        self.neighbors_count = ml_settings["neighbors_count"]
        self.max_bars_back = ml_settings["max_bars_back"]
        self.use_dynamic_exits = ml_settings["use_dynamic_exits"]
        self.min_prediction_strength = ml_settings["prediction_confidence_threshold"] * 10  # Scale to match our 0-10 range
        
        # Feature settings (map to our RSI-based features)
        feature_settings = tf_config["features"]
        # Note: We use RSI-based features, so we'll adapt the lengths
        # f1: RSI, f2: WT, f3: CCI, f4: ADX, f5: Price relative
        # These map roughly to the feature engineering in enhanced_bar_processor
        
        # Kernel settings
        kernel_settings = tf_config["kernel"]
        self.use_kernel_filter = kernel_settings["use_kernel_filter"]
        self.use_kernel_smoothing = kernel_settings["use_kernel_smoothing"]
        self.kernel_lookback = kernel_settings["kernel_lookback"]
        self.kernel_relative_weight = kernel_settings["kernel_weight"]
        self.kernel_regression_level = kernel_settings["kernel_regression_bandwidth"]
        self.kernel_lag = kernel_settings["lag"]
        
        # Filter settings
        filter_settings = tf_config["filters"]
        self.use_volatility_filter = filter_settings["use_volatility_filter"]
        self.use_regime_filter = filter_settings["use_regime_filter"]
        self.use_adx_filter = filter_settings["use_adx_filter"]
        self.regime_threshold = filter_settings["regime_threshold"]
        self.adx_threshold = filter_settings["adx_threshold"]
        
        # Exit strategy (these need to be added to our config if not present)
        exit_settings = tf_config["exit_strategy"]
        self.take_profit_atr_multiplier = exit_settings["take_profit_atr_multiplier"]
        self.stop_loss_atr_multiplier = exit_settings["stop_loss_atr_multiplier"]
        self.use_trailing_stop = exit_settings["use_trailing_stop"]
        self.trailing_stop_activation = exit_settings["trailing_stop_activation"]
        self.trailing_stop_distance = exit_settings["trailing_stop_distance"]
        
        # Risk management
        risk_settings = tf_config["risk_management"]
        self.position_size_pct = risk_settings["position_size_pct"]
        self.max_positions = risk_settings["max_positions"]
        self.risk_per_trade_pct = risk_settings["risk_per_trade_pct"]
        self.use_kelly_criterion = risk_settings["use_kelly_criterion"]
        
    def get_description(self) -> str:
        """Get description of this configuration"""
        descriptions = {
            "1min": "Scalping configuration with tight stops and quick exits",
            "5min": "Short-term trading with balanced risk/reward",
            "15min": "Intraday swing trading with wider targets",
            "30min": "Conservative intraday with trend following",
            "60min": "Swing trading with larger targets",
            "daily": "Position trading for multi-day moves"
        }
        return descriptions.get(self.timeframe, f"Custom {self.timeframe} configuration")


class TimeframeOptimizedConfig(FixedOptimizedTradingConfig):
    """Optimized configuration with timeframe-specific adjustments"""
    
    def __init__(self, timeframe: str = "5min"):
        super().__init__()
        self.timeframe = timeframe
        self._apply_timeframe_optimizations()
    
    def _apply_timeframe_optimizations(self):
        """Apply timeframe-specific optimizations on top of base optimizations"""
        tf_config = get_config_for_timeframe(self.timeframe)
        
        if not tf_config:
            return
        
        # Apply specific overrides for the optimized config
        ml_settings = tf_config["ml_model"]
        self.neighbors_count = ml_settings["neighbors_count"]
        
        # Scale prediction strength based on timeframe
        # Shorter timeframes need lower thresholds
        base_threshold = ml_settings["prediction_confidence_threshold"]
        self.min_prediction_strength = base_threshold * 6  # Our scale is 0-10, theirs is 0-1
        
        # Exit strategy adjustments
        exit_settings = tf_config["exit_strategy"]
        
        # For multi-target system, scale the targets based on timeframe
        base_target = exit_settings["take_profit_atr_multiplier"]
        self.target_1_ratio = base_target * 0.6  # First target at 60% of full target
        self.target_2_ratio = base_target * 1.2  # Second target at 120% of full target
        self.target_3_ratio = base_target * 2.0  # Third target (trailing) at 200%
        
        # Stop loss from timeframe config
        self.stop_loss_atr_multiplier = exit_settings["stop_loss_atr_multiplier"]
        
        # Trailing stop settings
        self.use_trailing_stop = exit_settings["use_trailing_stop"]
        self.trailing_stop_activation_ratio = exit_settings["trailing_stop_activation"]
        self.trailing_stop_distance_ratio = exit_settings["trailing_stop_distance"]
        
        # Pattern quality thresholds based on timeframe
        # Shorter timeframes accept lower quality patterns
        if self.timeframe in ["1min", "1m"]:
            self.min_pattern_score = 5.0
        elif self.timeframe in ["5min", "5m"]:
            self.min_pattern_score = 6.0
        elif self.timeframe in ["15min", "15m"]:
            self.min_pattern_score = 7.0
        else:  # 30min, 60min, daily
            self.min_pattern_score = 8.0


def get_all_timeframe_configs() -> Dict[str, TradingConfig]:
    """Get all available timeframe configurations"""
    timeframes = ["1min", "5min", "15min", "30min", "60min", "daily"]
    configs = {}
    
    for tf in timeframes:
        configs[f"{tf}_base"] = TimeframeTradingConfig(tf)
        configs[f"{tf}_optimized"] = TimeframeOptimizedConfig(tf)
    
    return configs


def compare_timeframe_configs():
    """Print comparison of key parameters across timeframes"""
    timeframes = ["1min", "5min", "15min", "30min", "60min", "daily"]
    
    print("\n" + "="*80)
    print("TIMEFRAME CONFIGURATION COMPARISON")
    print("="*80)
    
    # Header
    print(f"{'Parameter':<30} " + " ".join(f"{tf:>8}" for tf in timeframes))
    print("-"*80)
    
    # Compare key parameters
    params_to_compare = [
        ("neighbors_count", "Neighbors"),
        ("min_prediction_strength", "Min Prediction"),
        ("stop_loss_atr_multiplier", "Stop Loss ATR"),
        ("target_1_ratio", "Target 1 Ratio"),
        ("target_2_ratio", "Target 2 Ratio"),
        ("use_adx_filter", "Use ADX Filter"),
        ("adx_threshold", "ADX Threshold"),
        ("min_pattern_score", "Min Pattern Score"),
    ]
    
    for param, display_name in params_to_compare:
        row = f"{display_name:<30}"
        for tf in timeframes:
            config = TimeframeOptimizedConfig(tf)
            value = getattr(config, param, "N/A")
            if isinstance(value, float):
                row += f" {value:>8.2f}"
            elif isinstance(value, bool):
                row += f" {'Yes' if value else 'No':>8}"
            else:
                row += f" {str(value):>8}"
        print(row)
    
    print("\n" + "="*80)


# Example usage
if __name__ == "__main__":
    # Test different timeframe configs
    print("Testing Timeframe Configurations")
    
    # Create configs for different timeframes
    config_1min = TimeframeTradingConfig("1min")
    config_5min = TimeframeTradingConfig("5min")
    config_daily = TimeframeTradingConfig("daily")
    
    print(f"\n1-Minute Config: {config_1min.get_description()}")
    print(f"  Neighbors: {config_1min.neighbors_count}")
    print(f"  Min Prediction: {config_1min.min_prediction_strength}")
    
    print(f"\n5-Minute Config: {config_5min.get_description()}")
    print(f"  Neighbors: {config_5min.neighbors_count}")
    print(f"  Min Prediction: {config_5min.min_prediction_strength}")
    
    print(f"\nDaily Config: {config_daily.get_description()}")
    print(f"  Neighbors: {config_daily.neighbors_count}")
    print(f"  Min Prediction: {config_daily.min_prediction_strength}")
    
    # Compare all configs
    compare_timeframe_configs()