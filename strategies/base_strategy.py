"""
Base Strategy Class
==================

Abstract base class for all exit strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from scanner.smart_exit_manager import SmartExitManager


class BaseExitStrategy(ABC):
    """Base class for all exit strategies"""
    
    def __init__(self, name: str):
        self.name = name
        self._exit_manager = None
    
    @property
    @abstractmethod
    def config(self) -> Dict:
        """Return the exit configuration for this strategy"""
        pass
    
    @property
    def exit_manager(self) -> SmartExitManager:
        """Get or create the exit manager"""
        if self._exit_manager is None:
            use_atr = self.config.get('use_atr_stops', False)
            self._exit_manager = SmartExitManager(
                self.config.copy(), 
                use_atr_stops=use_atr
            )
        return self._exit_manager
    
    def get_description(self) -> str:
        """Get a formatted description of the strategy"""
        config = self.config
        desc = f"\n{self.name.upper()} Strategy Configuration\n"
        desc += "="*50 + "\n"
        
        if 'use_atr_stops' in config and config['use_atr_stops']:
            desc += f"Stop Loss: {config.get('atr_stop_multiplier', 2.0)}x ATR\n"
            desc += f"Targets: {config.get('atr_profit_multipliers', [])} x ATR\n"
        else:
            desc += f"Stop Loss: {config.get('stop_loss_percent', 0)}%\n"
            desc += f"Targets: {config.get('take_profit_targets', [])}%\n"
        
        desc += f"Position Sizes: {config.get('target_sizes', [])}%\n"
        desc += f"Trailing Stop: {config.get('use_trailing_stop', False)}\n"
        desc += f"Max Hold: {config.get('max_holding_bars', 0)} bars\n"
        
        return desc
    
    def reset(self):
        """Reset the exit manager"""
        self._exit_manager = None