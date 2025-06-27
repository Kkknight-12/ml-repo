#!/usr/bin/env python3
"""
Relaxed Trading Configuration
=============================

Less restrictive entry conditions for reasonable trade frequency
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RelaxedTradingConfig:
    """
    Configuration with relaxed entry conditions
    
    Key changes:
    1. No "different signal" requirement (handled in signal generator)
    2. Optional ML threshold
    3. More permissive filter settings
    4. Standard risk management maintained
    """
    
    # Core settings
    symbol: str = "RELIANCE"
    timeframe: str = "5minute"
    max_bars_back: int = 2000
    
    # k-NN settings
    neighbors_count: int = 8
    feature_count: int = 4
    
    # ML settings - optional threshold
    ml_prediction_threshold: float = 0.0  # Set to 0 to disable
    
    # Filter settings - more permissive
    use_volatility_filter: bool = False  # Disabled for more entries
    use_regime_filter: bool = True
    use_adx_filter: bool = False  # Pine Script default
    adx_threshold: float = 20.0
    
    # Entry settings (handled by relaxed signal generator)
    entry_cooldown_bars: int = 10  # Minimum bars between entries
    
    # Exit settings
    use_dynamic_exits: bool = True
    fixed_exit_bars: int = 5  # Changed from 4 to 5 for better exits
    
    # Risk management - standard
    stop_loss_percent: float = 1.0
    initial_capital: float = 100000
    position_size_percent: float = 10.0
    
    # Multi-target exits (if enabled)
    use_multi_targets: bool = True
    target_1_r_multiple: float = 1.5
    target_1_percent: float = 50.0
    target_2_r_multiple: float = 3.0
    target_2_percent: float = 30.0
    target_3_percent: float = 20.0  # Trailing
    
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
            'target_3_percent': self.target_3_percent,
            'lookback_days': self.lookback_days,
            'commission_percent': self.commission_percent,
            'slippage_percent': self.slippage_percent
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RelaxedTradingConfig':
        """Create from dictionary"""
        return cls(**data)
    
    def get_description(self) -> str:
        """Get configuration description"""
        return f"""
Relaxed Trading Configuration
=============================
Symbol: {self.symbol}
Timeframe: {self.timeframe}

Entry Conditions:
- ML Threshold: {self.ml_prediction_threshold if self.ml_prediction_threshold > 0 else 'Disabled'}
- Entry Cooldown: {self.entry_cooldown_bars} bars
- Volatility Filter: {'Enabled' if self.use_volatility_filter else 'Disabled'}
- Regime Filter: {'Enabled' if self.use_regime_filter else 'Disabled'}
- ADX Filter: {'Enabled' if self.use_adx_filter else 'Disabled'}

Risk Management:
- Stop Loss: {self.stop_loss_percent}%
- Position Size: {self.position_size_percent}% of capital

Multi-Target Exits: {'Enabled' if self.use_multi_targets else 'Disabled'}
- Target 1: {self.target_1_r_multiple}R @ {self.target_1_percent}%
- Target 2: {self.target_2_r_multiple}R @ {self.target_2_percent}%
- Target 3: Trailing @ {self.target_3_percent}%
"""


# Preset configurations
RELAXED_NO_THRESHOLD = RelaxedTradingConfig(
    ml_prediction_threshold=0.0,
    use_volatility_filter=False,
    use_adx_filter=False
)

RELAXED_WITH_THRESHOLD = RelaxedTradingConfig(
    ml_prediction_threshold=2.0,  # Lower than original 3.0
    use_volatility_filter=False,
    use_adx_filter=False
)

RELAXED_SIMPLE = RelaxedTradingConfig(
    ml_prediction_threshold=0.0,
    use_volatility_filter=False,
    use_regime_filter=False,
    use_adx_filter=False,
    use_multi_targets=False
)