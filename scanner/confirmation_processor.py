"""
Confirmation Processor
=====================

Integrates all confirmation filters with the signal generation system.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass

from scanner.mode_aware_processor import ModeAwareBarProcessor, ModeAwareBarResult
from indicators.confirmation.volume_filter import VolumeConfirmationFilter
from indicators.confirmation.momentum_filter import MomentumConfirmationFilter
from indicators.confirmation.support_resistance_filter import SupportResistanceFilter


@dataclass
class ConfirmationResult(ModeAwareBarResult):
    """Extended result with confirmation data"""
    # Volume confirmation
    volume_confirmed: bool = False
    volume_ratio: float = 0.0
    volume_confidence: float = 0.0
    
    # Momentum confirmation
    momentum_confirmed: bool = False
    momentum_score: float = 0.0
    momentum_confidence: float = 0.0
    
    # S/R confirmation
    sr_confirmed: bool = False
    sr_score: float = 0.0
    sr_distance: float = 0.0
    
    # Overall confirmation
    confirmed_signal: int = 0  # Final confirmed signal
    confirmation_score: float = 0.0
    confirmation_count: int = 0


class ConfirmationProcessor(ModeAwareBarProcessor):
    """
    Extends mode-aware processor with confirmation filters.
    
    Signal flow:
    1. ML prediction -> Raw signal
    2. Mode filter -> Mode-filtered signal
    3. Confirmation filters -> Confirmed signal
    """
    
    def __init__(self, config, symbol: str, timeframe: str,
                 require_volume: bool = True,
                 require_momentum: bool = True,
                 require_sr: bool = False,
                 min_confirmations: int = 2):
        """
        Initialize confirmation processor.
        
        Args:
            config: Trading configuration
            symbol: Trading symbol
            timeframe: Timeframe
            require_volume: Require volume confirmation
            require_momentum: Require momentum confirmation
            require_sr: Require S/R confirmation
            min_confirmations: Minimum confirmations needed
        """
        super().__init__(config, symbol, timeframe)
        
        # Confirmation requirements
        self.require_volume = require_volume
        self.require_momentum = require_momentum
        self.require_sr = require_sr
        self.min_confirmations = min_confirmations
        
        # Initialize filters
        self.volume_filter = VolumeConfirmationFilter(
            lookback_period=20,
            min_volume_ratio=1.5,
            spike_threshold=2.0
        )
        
        self.momentum_filter = MomentumConfirmationFilter(
            rsi_period=14,
            rsi_overbought=70,
            rsi_oversold=30
        )
        
        self.sr_filter = SupportResistanceFilter(
            lookback_period=100,
            min_touches=2,
            tolerance_percent=0.3
        )
        
    def process_bar(self, open_price: float, high: float, low: float, 
                   close: float, volume: float) -> Optional[ConfirmationResult]:
        """
        Process bar with full confirmation pipeline.
        
        Returns:
            ConfirmationResult with all analysis data
        """
        # Get mode-filtered result first
        mode_result = super().process_bar(open_price, high, low, close, volume)
        
        if not mode_result:
            return None
            
        # Create confirmation result
        result = ConfirmationResult(
            **mode_result.__dict__  # Copy all mode result fields
        )
        
        # Update confirmation filters with new data
        self.volume_filter.update(volume, close)
        self.momentum_filter.update(close)
        self.sr_filter.update(high, low, close)
        
        # Only check confirmations if we have a mode-filtered signal
        if mode_result.mode_filtered_signal != 0:
            # Run confirmation checks
            confirmations = self._check_confirmations(
                mode_result.mode_filtered_signal,
                close,
                volume
            )
            
            # Update result with confirmation data
            result.volume_confirmed = confirmations['volume']['confirmed']
            result.volume_ratio = confirmations['volume']['ratio']
            result.volume_confidence = confirmations['volume']['confidence']
            
            result.momentum_confirmed = confirmations['momentum']['confirmed']
            result.momentum_score = confirmations['momentum']['score']
            result.momentum_confidence = confirmations['momentum']['confidence']
            
            result.sr_confirmed = confirmations['sr']['confirmed']
            result.sr_score = confirmations['sr']['score']
            result.sr_distance = confirmations['sr']['distance']
            
            # Calculate overall confirmation
            confirmation_count = sum([
                result.volume_confirmed,
                result.momentum_confirmed,
                result.sr_confirmed
            ])
            
            result.confirmation_count = confirmation_count
            
            # Calculate confirmation score (weighted average)
            weights = {
                'volume': 0.4 if self.require_volume else 0.2,
                'momentum': 0.4 if self.require_momentum else 0.2,
                'sr': 0.2 if self.require_sr else 0.1
            }
            
            # Normalize weights
            total_weight = sum(weights.values())
            weights = {k: v/total_weight for k, v in weights.items()}
            
            result.confirmation_score = (
                weights['volume'] * result.volume_confidence +
                weights['momentum'] * result.momentum_confidence +
                weights['sr'] * result.sr_score
            )
            
            # Determine if signal is confirmed
            required_confirmations = []
            if self.require_volume:
                required_confirmations.append(result.volume_confirmed)
            if self.require_momentum:
                required_confirmations.append(result.momentum_confirmed)
            if self.require_sr:
                required_confirmations.append(result.sr_confirmed)
            
            # Signal is confirmed if:
            # 1. All required confirmations pass, OR
            # 2. Minimum confirmations met with high score
            all_required = all(required_confirmations) if required_confirmations else True
            min_met = confirmation_count >= self.min_confirmations and result.confirmation_score >= 0.6
            
            if all_required or min_met:
                result.confirmed_signal = mode_result.mode_filtered_signal
            else:
                result.confirmed_signal = 0
        
        return result
    
    def _check_confirmations(self, signal_direction: int, 
                           close: float, volume: float) -> Dict:
        """Run all confirmation checks"""
        confirmations = {
            'volume': {'confirmed': False, 'ratio': 0.0, 'confidence': 0.0},
            'momentum': {'confirmed': False, 'score': 0.0, 'confidence': 0.0},
            'sr': {'confirmed': False, 'score': 0.0, 'distance': 0.0}
        }
        
        # Volume confirmation
        volume_stats = self.volume_filter.update(volume, close)
        confirmations['volume']['confirmed'] = volume_stats.is_confirmed
        confirmations['volume']['ratio'] = volume_stats.volume_ratio
        confirmations['volume']['confidence'] = volume_stats.confidence
        
        # Momentum confirmation
        momentum_confirmed, momentum_confidence = self.momentum_filter.check_signal_momentum(
            signal_direction
        )
        momentum_stats = self.momentum_filter.update(close)
        confirmations['momentum']['confirmed'] = momentum_confirmed
        confirmations['momentum']['score'] = momentum_stats.momentum_score
        confirmations['momentum']['confidence'] = momentum_confidence
        
        # S/R confirmation
        sr_validation = self.sr_filter.validate_signal(close, signal_direction)
        confirmations['sr']['confirmed'] = sr_validation.is_valid
        confirmations['sr']['score'] = sr_validation.validation_score
        confirmations['sr']['distance'] = min(
            sr_validation.distance_to_support,
            sr_validation.distance_to_resistance
        )
        
        return confirmations
    
    def get_confirmation_stats(self) -> Dict:
        """Get detailed confirmation statistics"""
        mode_stats = self.get_mode_statistics()
        
        return {
            **mode_stats,
            'volume_profile': self.volume_filter.get_volume_profile(),
            'sr_levels': self.sr_filter.get_levels_summary(),
            'filters_active': {
                'volume': self.require_volume,
                'momentum': self.require_momentum,
                'sr': self.require_sr
            },
            'min_confirmations': self.min_confirmations
        }