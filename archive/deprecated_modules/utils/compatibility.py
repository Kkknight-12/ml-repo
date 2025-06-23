"""
Compatibility layer for smooth transition between old and new features
"""
from typing import Union, Optional
from scanner.bar_processor import BarProcessor
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from data.bar_data import BarData
from data.enhanced_bar_data import EnhancedBarData
from config.settings import TradingConfig


def create_processor(config: TradingConfig, 
                    symbol: str = "UNKNOWN",
                    timeframe: str = "5minute",
                    use_enhanced: bool = True) -> Union[BarProcessor, EnhancedBarProcessor]:
    """
    Create appropriate bar processor based on requirements
    
    Args:
        config: Trading configuration
        symbol: Trading symbol (e.g., "ICICIBANK")
        timeframe: Timeframe string (e.g., "day", "5minute")
        use_enhanced: Whether to use enhanced features
        
    Returns:
        BarProcessor or EnhancedBarProcessor instance
    """
    if use_enhanced:
        return EnhancedBarProcessor(config, symbol, timeframe)
    else:
        # Old processor doesn't support symbol/timeframe in constructor
        # But we can add them as attributes for consistency
        processor = BarProcessor(config)
        processor.symbol = symbol
        processor.timeframe = timeframe
        return processor


def create_bar_data(max_bars: int = 2500, 
                   use_enhanced: bool = True) -> Union[BarData, EnhancedBarData]:
    """
    Create appropriate bar data structure
    
    Args:
        max_bars: Maximum bars to store
        use_enhanced: Whether to use enhanced features
        
    Returns:
        BarData or EnhancedBarData instance
    """
    if use_enhanced:
        return EnhancedBarData(max_bars)
    else:
        return BarData(max_bars)


# Migration helpers
def migrate_to_enhanced(old_processor: BarProcessor, 
                       symbol: str = "UNKNOWN",
                       timeframe: str = "5minute") -> EnhancedBarProcessor:
    """
    Migrate from old BarProcessor to EnhancedBarProcessor
    
    Args:
        old_processor: Existing BarProcessor instance
        symbol: Trading symbol
        timeframe: Timeframe string
        
    Returns:
        New EnhancedBarProcessor with same config
    """
    # Create enhanced processor with same config
    enhanced = EnhancedBarProcessor(old_processor.config, symbol, timeframe)
    
    # Copy state if needed
    enhanced.signal_history = old_processor.signal_history.copy()
    enhanced.entry_history = old_processor.entry_history.copy()
    enhanced.bars_processed = old_processor.bars_processed
    
    # Note: Historical bar data needs to be re-processed
    
    return enhanced


# Backward compatibility functions
def process_bars_compatible(processor: Union[BarProcessor, EnhancedBarProcessor],
                           data: list,
                           show_progress: bool = True) -> list:
    """
    Process bars with either processor type
    
    Args:
        processor: Bar processor instance
        data: List of (open, high, low, close, volume) tuples
        show_progress: Whether to show progress
        
    Returns:
        List of BarResult objects
    """
    results = []
    
    for i, (o, h, l, c, v) in enumerate(data):
        result = processor.process_bar(o, h, l, c, v)
        if result:
            results.append(result)
        
        if show_progress and i % 100 == 0 and i > 0:
            if hasattr(processor, 'symbol'):
                print(f"Processed {i} bars for {processor.symbol}")
            else:
                print(f"Processed {i} bars")
    
    return results


# Test script helper
def setup_test_environment(symbol: str = "ICICIBANK",
                          timeframe: str = "day",
                          use_enhanced: bool = True) -> dict:
    """
    Setup complete test environment
    
    Args:
        symbol: Trading symbol
        timeframe: Timeframe string
        use_enhanced: Whether to use enhanced features
        
    Returns:
        Dictionary with configured components
    """
    # Create configuration based on timeframe
    if timeframe == "day":
        config = TradingConfig(
            neighbors_count=8,
            max_bars_back=2000,
            regime_threshold=-0.1,
            adx_threshold=20,
            kernel_lookback=8
        )
    elif timeframe == "5minute":
        config = TradingConfig(
            neighbors_count=5,
            max_bars_back=1000,
            regime_threshold=0.0,
            adx_threshold=15,
            kernel_lookback=12,
            use_kernel_smoothing=True
        )
    else:
        config = TradingConfig()  # Default
    
    # Create components
    processor = create_processor(config, symbol, timeframe, use_enhanced)
    bar_data = create_bar_data(config.max_bars_back, use_enhanced)
    
    return {
        "config": config,
        "processor": processor,
        "bar_data": bar_data,
        "symbol": symbol,
        "timeframe": timeframe,
        "use_enhanced": use_enhanced
    }
