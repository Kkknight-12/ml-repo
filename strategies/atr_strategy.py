"""
ATR-Based Exit Strategy
======================

Dynamic strategy using Average True Range for stops and targets.
"""

from typing import Dict
from .base_strategy import BaseExitStrategy


class ATRStrategy(BaseExitStrategy):
    """ATR-based exit strategy - dynamic stops and targets"""
    
    def __init__(self):
        super().__init__("atr")
    
    @property
    def config(self) -> Dict:
        """ATR configuration with dynamic parameters"""
        return {
            'use_atr_stops': True,
            'atr_stop_multiplier': 2.0,
            'atr_profit_multipliers': [1.5, 3.0, 5.0],
            'target_sizes': [50, 30, 20],
            'use_trailing_stop': False,  # Disabled for now
            'atr_trailing_multiplier': 1.5,
            'max_holding_bars': 200  # Increased from 78
        }