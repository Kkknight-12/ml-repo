"""
Scanner module - Bar processing and signal generation
"""

# from .bar_processor import BarProcessor, BarResult
# from .signal_generator import SignalGenerator
#
# __all__ = ['BarProcessor', 'BarResult', 'SignalGenerator']
# """
# Scanner module - Bar processing and signal generation
# """

# Import both BarResult and EnhancedBarProcessor from enhanced_bar_processor
from .enhanced_bar_processor import EnhancedBarProcessor as BarProcessor, BarResult
from .signal_generator import SignalGenerator

__all__ = ['BarProcessor', 'BarResult', 'SignalGenerator']