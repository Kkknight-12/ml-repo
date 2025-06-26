#!/usr/bin/env python3
"""
ML-Optimized Enhanced Bar Processor
===================================

Enhanced bar processor that uses ML prediction threshold for better win rate.
This is a minimal modification to use the ML-optimized signal generator.
"""

from typing import Optional
from config.settings import TradingConfig
from .enhanced_bar_processor import EnhancedBarProcessor
from .signal_generator_ml_optimized import MLOptimizedSignalGenerator
from data.data_types import Label


class MLOptimizedBarProcessor(EnhancedBarProcessor):
    """
    Bar processor with ML threshold optimization
    
    Key enhancement: Uses ML prediction threshold for entries
    """
    
    def __init__(self, config: TradingConfig, symbol: str, timeframe: str = "5min", debug_mode: bool = False):
        """Initialize with ML-optimized signal generator"""
        super().__init__(config, symbol, timeframe, debug_mode)
        
        # Replace signal generator with ML-optimized version
        ml_threshold = getattr(config, 'ml_prediction_threshold', 3.0)
        self.signal_generator = MLOptimizedSignalGenerator(self.label, ml_threshold)
        
        # Store threshold for logging
        self.ml_threshold = ml_threshold
        
        if debug_mode:
            print(f"📊 Using ML-Optimized Signal Generator with threshold: {ml_threshold}")
    
    def process_bar(self, open_price: float, high: float, low: float, 
                    close: float, volume: float) -> 'ProcessingResult':
        """
        Process bar with ML threshold check
        
        Override to pass ML prediction to signal generator
        """
        # Call parent process_bar to get all calculations
        result = super().process_bar(open_price, high, low, close, volume)
        
        # If we're past warmup and have ML prediction, recheck entry signals
        if self.bars_processed >= self.settings.max_bars_back:
            # Get current ML prediction
            ml_prediction = self.ml_model.prediction
            
            # Re-evaluate entry signals with ML threshold
            # Get current states
            signal = self.ml_model.signal
            bar_index = self.bars_processed - 1
            
            # Get filter states
            filter_states = self._apply_filters_stateful(high, low, close)
            
            # Calculate trend filters
            is_ema_uptrend, is_ema_downtrend = self._calculate_ema_trend_stateful(close)
            is_sma_uptrend, is_sma_downtrend = self._calculate_sma_trend_stateful(close)
            
            # Calculate kernel filters
            is_bullish_kernel = self._calculate_kernel_bullish()
            is_bearish_kernel = self._calculate_kernel_bearish()
            
            # Check entry with ML threshold
            # First check ML threshold
            if abs(ml_prediction) < self.ml_threshold:
                start_long, start_short = False, False
                if self.debug_mode and signal != 0:
                    print(f"  ⚠️ ML Threshold Filter: Signal blocked (|{ml_prediction:.2f}| < {self.ml_threshold})")
            else:
                # ML threshold passed, now check other conditions
                if hasattr(self.signal_generator, 'check_entry_conditions_relaxed'):
                    # Use relaxed conditions (no volatility filter)
                    start_long, start_short = self.signal_generator.check_entry_conditions_relaxed(
                        signal, self.signal_history[1:], ml_prediction,  # Exclude current signal
                        is_bullish_kernel, is_bearish_kernel,
                        volatility_filter=filter_states.get('volatility', True),
                        regime_filter=filter_states.get('regime', True),
                        adx_filter=filter_states.get('adx', True)
                    )
                else:
                    # For standard signal generator, check entry normally
                    # but we already know ML threshold passed
                    start_long, start_short = self.signal_generator.check_entry_conditions(
                        signal, self.signal_history[1:],
                        is_bullish_kernel, is_bearish_kernel,
                        is_ema_uptrend, is_ema_downtrend, 
                        is_sma_uptrend, is_sma_downtrend
                    )
            
            # Update result with ML-filtered entries
            result.start_long_trade = start_long
            result.start_short_trade = start_short
            
            # Log ML threshold filtering
            if self.debug_mode and (result.signal != 0):
                if abs(ml_prediction) < self.ml_threshold:
                    print(f"  ⚠️ ML Threshold Filter: Signal blocked (|{ml_prediction:.2f}| < {self.ml_threshold})")
                elif start_long or start_short:
                    strength = self.signal_generator.get_entry_strength(ml_prediction)
                    print(f"  ✅ ML Entry: {strength} strength (|{ml_prediction:.2f}| >= {self.ml_threshold})")
        
        return result


def create_ml_optimized_processor(config: TradingConfig, symbol: str, 
                                 timeframe: str = "5minute", debug: bool = False):
    """
    Factory function to create ML-optimized processor
    
    Args:
        config: Trading configuration (should have ml_prediction_threshold)
        symbol: Trading symbol
        timeframe: Timeframe
        debug: Enable debug mode
        
    Returns:
        MLOptimizedBarProcessor instance
    """
    return MLOptimizedBarProcessor(config, symbol, timeframe, debug)


# Example usage
if __name__ == "__main__":
    from config.ml_optimized_settings import MLOptimizedTradingConfig
    
    # Create processor with ML optimization
    config = MLOptimizedTradingConfig()
    processor = create_ml_optimized_processor(config, "RELIANCE", debug=True)
    
    print(f"ML-Optimized Processor created with threshold: {processor.ml_threshold}")