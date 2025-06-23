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

from .bar_processor import BarProcessor, BarResult
from .signal_generator import SignalGenerator

# Import live scanner if dependencies available
try:
    from .live_scanner import LiveScanner
    __all__ = ['BarProcessor', 'BarResult', 'SignalGenerator', 'LiveScanner']
except ImportError:
    __all__ = ['BarProcessor', 'BarResult', 'SignalGenerator']