"""
Strategy Factory
===============

Factory for creating exit strategy instances.
"""

from typing import Dict, List
from .conservative_strategy import ConservativeStrategy
from .scalping_strategy import ScalpingStrategy
from .adaptive_strategy import AdaptiveStrategy
from .atr_strategy import ATRStrategy
from .base_strategy import BaseExitStrategy


class StrategyFactory:
    """Factory for creating exit strategies"""
    
    _strategies = {
        'conservative': ConservativeStrategy,
        'scalping': ScalpingStrategy,
        'adaptive': AdaptiveStrategy,
        'atr': ATRStrategy
    }
    
    @classmethod
    def create_strategy(cls, name: str) -> BaseExitStrategy:
        """Create a strategy by name"""
        if name not in cls._strategies:
            raise ValueError(f"Unknown strategy: {name}")
        return cls._strategies[name]()
    
    @classmethod
    def get_all_strategies(cls) -> Dict[str, BaseExitStrategy]:
        """Get all available strategies"""
        return {name: cls.create_strategy(name) for name in cls._strategies}
    
    @classmethod
    def get_strategy_names(cls) -> List[str]:
        """Get list of available strategy names"""
        return list(cls._strategies.keys())