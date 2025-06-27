"""
Conservative Exit Strategy
=========================

Low risk strategy with tight stops and higher profit targets.
"""

from typing import Dict
from .base_strategy import BaseExitStrategy


class ConservativeStrategy(BaseExitStrategy):
    """Conservative exit strategy - 1% stop, 2% target"""
    
    def __init__(self):
        super().__init__("conservative")
    
    @property
    def config(self) -> Dict:
        """Conservative configuration with fixed parameters"""
        return {
            'stop_loss_percent': 1.0,
            'take_profit_targets': [2.0],
            'target_sizes': [100],
            'use_trailing_stop': False,
            'max_holding_bars': 200  # Increased from 78
        }