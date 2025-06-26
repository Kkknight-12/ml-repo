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
        
        Simply checks ML threshold after normal processing
        """
        # Call parent process_bar to get all calculations
        result = super().process_bar(open_price, high, low, close, volume)
        
        # Apply ML threshold filter to entries
        if self.bars_processed >= self.settings.max_bars_back:
            ml_prediction = result.prediction
            
            # Check ML threshold
            if abs(ml_prediction) < self.ml_threshold:
                # Block entries if ML prediction is too weak
                if result.start_long_trade or result.start_short_trade:
                    if self.debug_mode:
                        print(f"  ⚠️ ML Threshold blocked entry: |{ml_prediction:.2f}| < {self.ml_threshold}")
                    result.start_long_trade = False
                    result.start_short_trade = False
            else:
                # Log successful entries
                if self.debug_mode and (result.start_long_trade or result.start_short_trade):
                    strength = self.signal_generator.get_entry_strength(ml_prediction)
                    print(f"  ✅ ML Entry allowed: {strength} strength (|{ml_prediction:.2f}| >= {self.ml_threshold})")
        
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