"""
Phase 2 Optimized Settings
=========================

Final configuration after completing Phase 2 signal enhancement.
Includes mode filtering and confirmation filters with optimal parameters.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class Phase2OptimizedConfig:
    """
    Optimized configuration for Phase 2 enhanced system.
    
    Key improvements:
    1. Market mode filtering (100% trend signal removal)
    2. Volume confirmation with relaxed parameters
    3. Balanced signal quality vs quantity
    """
    
    # ML Settings
    ml_threshold: float = 3.0  # Keep high for quality
    
    # Mode Detection Settings
    use_mode_filtering: bool = True
    allow_trend_trades: bool = False  # Filter all trend signals
    min_mode_confidence: float = 0.3
    trend_threshold: float = 0.1
    
    # Confirmation Filter Settings
    use_confirmation_filters: bool = True
    require_volume: bool = True
    require_momentum: bool = False  # Too restrictive when combined
    require_sr: bool = False  # Not needed for 5min
    min_confirmations: int = 1
    
    # Volume Filter Parameters (Relaxed)
    volume_min_ratio: float = 1.2  # Down from 1.5
    volume_spike_threshold: float = 1.8  # Down from 2.0
    volume_lookback: int = 20
    
    # Exit Strategy (from Phase 1)
    exit_strategy: str = 'scalping'  # Best performer from Phase 1
    
    # Scalping Exit Parameters
    scalping_config: Dict = None
    
    def __post_init__(self):
        if self.scalping_config is None:
            self.scalping_config = {
                'stop_loss_percent': 0.5,
                'take_profit_targets': [0.5, 0.75, 1.0],
                'target_sizes': [50, 30, 20],
                'use_trailing_stop': False,
                'max_holding_bars': 100,  # ~8 hours for 5min
                'use_time_exit': True
            }
    
    def get_summary(self) -> Dict:
        """Get configuration summary"""
        return {
            'phase': 'Phase 2 Complete',
            'ml_threshold': self.ml_threshold,
            'mode_filtering': self.use_mode_filtering,
            'confirmation': 'Volume Only (Relaxed)',
            'exit_strategy': self.exit_strategy,
            'expected_signals': '200-250 per month',
            'signal_reduction': '~80% from raw',
            'improvements': [
                'Mode filtering: 25% reduction, 100% trend removal',
                'Volume confirmation: Additional 55% reduction',
                'Total quality improvement expected'
            ]
        }


def get_phase2_config() -> Phase2OptimizedConfig:
    """Get the optimal Phase 2 configuration"""
    return Phase2OptimizedConfig()


def get_confirmation_processor_params() -> Dict:
    """Get parameters for ConfirmationProcessor initialization"""
    config = get_phase2_config()
    
    return {
        'require_volume': config.require_volume,
        'require_momentum': config.require_momentum,
        'require_sr': config.require_sr,
        'min_confirmations': config.min_confirmations,
        # Include relaxed parameters
        'volume_params': {
            'min_volume_ratio': config.volume_min_ratio,
            'spike_threshold': config.volume_spike_threshold,
            'lookback_period': config.volume_lookback
        }
    }


def compare_with_phase1() -> Dict:
    """Compare Phase 2 with Phase 1 results"""
    return {
        'Phase 1': {
            'approach': 'ML + Exit Optimization',
            'best_strategy': 'Scalping',
            'return': '184.78%',
            'win_rate': '54.3%',
            'signals': 'All ML signals used'
        },
        'Phase 2': {
            'approach': 'ML + Mode Filter + Volume Confirmation',
            'best_strategy': 'Scalping (retained)',
            'expected_improvement': 'Higher win rate, fewer false signals',
            'signal_quality': 'Much higher',
            'signals': '~20% of original signals'
        }
    }