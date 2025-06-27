"""
Adaptive Exit Strategy
=====================

Flexible strategy with wider stops and multiple profit targets.
"""

from typing import Dict
from .base_strategy import BaseExitStrategy


class AdaptiveStrategy(BaseExitStrategy):
    """Adaptive exit strategy - 2% stop, 1/2/3% targets"""
    
    def __init__(self):
        super().__init__("adaptive")
    
    @property
    def config(self) -> Dict:
        """Adaptive configuration with wider risk tolerance"""
        return {
            'stop_loss_percent': 2.0,
            'take_profit_targets': [1.0, 2.0, 3.0],
            'target_sizes': [40, 40, 20],
            'use_trailing_stop': False,  # Disabled for now
            'trailing_activation': 1.0,
            'trailing_distance': 0.5,
            'max_holding_bars': 200  # Increased from 40
        }