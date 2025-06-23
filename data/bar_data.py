"""
Bar data structure - Mimics Pine Script's bar access
Provides same interface as Pine Script: close, high, low, open, hlc3, ohlc4
"""
from typing import List, Optional
import numpy as np


class BarData:
    """
    Handles bar data similar to Pine Script
    Supports array indexing: close[0] is current, close[1] is previous
    """

    def __init__(self, max_bars: int = 5000):
        """Initialize empty bar data arrays"""
        self.max_bars = max_bars

        # Price arrays - stored newest first (index 0 = current bar)
        self._open: List[float] = []
        self._high: List[float] = []
        self._low: List[float] = []
        self._close: List[float] = []
        self._volume: List[float] = []

        # Bar index (mimics Pine Script's bar_index)
        self._bar_index = -1

    def add_bar(self, open_price: float, high: float, low: float,
                close: float, volume: float = 0.0):
        """Add new bar data (like Pine Script getting new bar)"""
        # Insert at beginning (index 0 is always current bar)
        self._open.insert(0, open_price)
        self._high.insert(0, high)
        self._low.insert(0, low)
        self._close.insert(0, close)
        self._volume.insert(0, volume)

        # Increment bar index
        self._bar_index += 1

        # Trim arrays if too long
        if len(self._close) > self.max_bars:
            self._open.pop()
            self._high.pop()
            self._low.pop()
            self._close.pop()
            self._volume.pop()

    @property
    def close(self) -> float:
        """Current close price"""
        return self._close[0] if self._close else 0.0

    @property
    def open(self) -> float:
        """Current open price"""
        return self._open[0] if self._open else 0.0

    @property
    def high(self) -> float:
        """Current high price"""
        return self._high[0] if self._high else 0.0

    @property
    def low(self) -> float:
        """Current low price"""
        return self._low[0] if self._low else 0.0

    @property
    def volume(self) -> float:
        """Current volume"""
        return self._volume[0] if self._volume else 0.0

    @property
    def hlc3(self) -> float:
        """(high + low + close) / 3"""
        return (self.high + self.low + self.close) / 3.0

    @property
    def ohlc4(self) -> float:
        """(open + high + low + close) / 4"""
        return (self.open + self.high + self.low + self.close) / 4.0

    @property
    def hl2(self) -> float:
        """(high + low) / 2"""
        return (self.high + self.low) / 2.0

    @property
    def bar_index(self) -> int:
        """Current bar index (like Pine Script)"""
        return self._bar_index

    @property
    def last_bar_index(self) -> int:
        """Alias for bar_index"""
        return self._bar_index

    def get_close(self, index: int = 0) -> float:
        """Get close at index (0 = current, 1 = previous, etc.)"""
        if 0 <= index < len(self._close):
            return self._close[index]
        return 0.0

    def get_open(self, index: int = 0) -> float:
        """Get open at index"""
        if 0 <= index < len(self._open):
            return self._open[index]
        return 0.0

    def get_high(self, index: int = 0) -> float:
        """Get high at index"""
        if 0 <= index < len(self._high):
            return self._high[index]
        return 0.0

    def get_low(self, index: int = 0) -> float:
        """Get low at index"""
        if 0 <= index < len(self._low):
            return self._low[index]
        return 0.0

    def get_hlc3(self, index: int = 0) -> float:
        """Get hlc3 at index"""
        h = self.get_high(index)
        l = self.get_low(index)
        c = self.get_close(index)
        return (h + l + c) / 3.0

    def get_ohlc4(self, index: int = 0) -> float:
        """Get ohlc4 at index"""
        o = self.get_open(index)
        h = self.get_high(index)
        l = self.get_low(index)
        c = self.get_close(index)
        return (o + h + l + c) / 4.0

    def __len__(self) -> int:
        """Number of bars stored"""
        return len(self._close)