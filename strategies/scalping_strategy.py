"""
Scalping Exit Strategy
=====================

High frequency strategy with small targets and tight stops.
"""

from typing import Dict
from .base_strategy import BaseExitStrategy


class ScalpingStrategy(BaseExitStrategy):
    """Scalping exit strategy - 0.5% stop, 0.5/0.75/1% targets"""
    
    def __init__(self):
        super().__init__("scalping")
    
    @property
    def config(self) -> Dict:
        """Scalping configuration with multiple small targets"""
        return {
            'stop_loss_percent': 0.5,
            'take_profit_targets': [0.5, 0.75, 1.0],
            'target_sizes': [50, 30, 20],
            'use_trailing_stop': False,  # Disabled for now
            'trailing_activation': 0.5,
            'trailing_distance': 0.25,
            'max_holding_bars': 100  # Increased from 20!
        }