"""
Pine Script Style History Referencing for Python
Provides [] operator for accessing historical values like Pine Script
"""
from typing import Any, Optional, Union, List, Dict
from collections import deque
import numpy as np
import pandas as pd
from dataclasses import dataclass


class HistoryBuffer:
    """
    Pine Script style history referencing for Python
    Mimics Pine Script's [] operator for accessing historical values
    """
    
    def __init__(self, max_history: int = 500):
        """
        Initialize history buffer
        
        Args:
            max_history: Maximum bars to keep in history (default 500)
        """
        self._buffer = deque(maxlen=max_history)
        self._current_value = None
        
    def update(self, value: Any) -> None:
        """
        Update buffer with new value (called on each new bar)
        
        Args:
            value: New value to add (can be float, array, list, etc.)
        """
        # Store current value in history before updating
        if self._current_value is not None:
            self._buffer.append(self._current_value)
        
        # Deep copy if array/list to avoid reference issues
        if isinstance(value, (list, np.ndarray)):
            self._current_value = value.copy()
        elif isinstance(value, pd.Series):
            self._current_value = value.copy()
        else:
            self._current_value = value
    
    def __getitem__(self, index: int) -> Any:
        """
        Get historical value using [] operator
        Pine Script style: close[0] = current, close[1] = previous
        
        Args:
            index: Number of bars back (0 = current, 1 = previous, etc.)
            
        Returns:
            Historical value or None if not enough history
        """
        if index == 0:
            return self._current_value
        
        # For historical values
        if index > 0 and index <= len(self._buffer):
            # -1 for previous, -2 for 2 bars back, etc.
            return self._buffer[-index]
        
        return None
    
    @property
    def current(self) -> Any:
        """Get current value (same as [0])"""
        return self._current_value
    
    def get(self, index: int, default: Any = None) -> Any:
        """
        Get historical value with default
        
        Args:
            index: Bars back
            default: Default value if history not available
            
        Returns:
            Historical value or default
        """
        value = self[index]
        return default if value is None else value
    
    def history(self, length: int) -> List[Any]:
        """
        Get multiple historical values
        
        Args:
            length: Number of historical values to retrieve
            
        Returns:
            List of historical values (newest to oldest)
        """
        result = []
        for i in range(length):
            value = self[i]
            if value is not None:
                result.append(value)
            else:
                break
        return result
    
    def __len__(self) -> int:
        """Return available history length"""
        return len(self._buffer) + (1 if self._current_value is not None else 0)


class PineScriptSeries:
    """
    Wrapper for any series data with Pine Script style history access
    Use this for close, open, high, low, volume, indicators, etc.
    """
    
    def __init__(self, name: str = "series", max_history: int = 500):
        self.name = name
        self._history = HistoryBuffer(max_history)
        
    def update(self, value: Union[float, int, None]) -> None:
        """Update series with new value"""
        self._history.update(value)
        
    def __getitem__(self, index: int) -> Any:
        """Access history using [] operator like Pine Script"""
        return self._history[index]
    
    @property
    def value(self) -> Any:
        """Get current value"""
        return self._history.current
    
    def __repr__(self) -> str:
        return f"PineScriptSeries({self.name}={self.value})"


class PineArray:
    """
    Pine Script style array with history referencing
    Mimics array.new<float>() with [] operator support
    """
    
    def __init__(self, size: int = 1, max_history: int = 500):
        self._size = size
        self._data = np.zeros(size)
        self._history = HistoryBuffer(max_history)
        # Auto-update history on each bar
        self._history.update(self._data.copy())
        
    def set(self, index: int, value: float) -> None:
        """
        Set array element value (like array.set())
        
        Args:
            index: Array index
            value: Value to set
        """
        if 0 <= index < self._size:
            self._data[index] = value
        
    def get(self, index: int) -> float:
        """
        Get array element value (like array.get())
        
        Args:
            index: Array index
            
        Returns:
            Element value
        """
        if 0 <= index < self._size:
            return self._data[index]
        return 0.0
    
    def push(self, value: float) -> None:
        """Add value to end (like array.push())"""
        self._data = np.append(self._data, value)
        self._size += 1
        
    def pop(self) -> float:
        """Remove and return last element (like array.pop())"""
        if self._size > 0:
            value = self._data[-1]
            self._data = self._data[:-1]
            self._size -= 1
            return value
        return 0.0
        
    def new_bar(self) -> None:
        """Call this when new bar starts to update history"""
        self._history.update(self._data.copy())
        
    def __getitem__(self, bars_back: int) -> Optional[np.ndarray]:
        """
        Get historical array instance
        
        Args:
            bars_back: Number of bars back (0 = current, 1 = previous bar)
            
        Returns:
            Historical array or None
        """
        return self._history[bars_back]
    
    @property
    def current(self) -> np.ndarray:
        """Get current array"""
        return self._data
    
    def __len__(self) -> int:
        """Array size"""
        return self._size


@dataclass
class OHLCVBar:
    """Single bar data"""
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    

class PineScriptData:
    """
    Complete Pine Script style data management
    Handles OHLCV and custom series with history
    """
    
    def __init__(self, max_history: int = 2000):
        """Initialize with Pine Script style series"""
        self.max_history = max_history
        
        # Built-in series
        self.open = PineScriptSeries("open", max_history)
        self.high = PineScriptSeries("high", max_history)
        self.low = PineScriptSeries("low", max_history)
        self.close = PineScriptSeries("close", max_history)
        self.volume = PineScriptSeries("volume", max_history)
        
        # Calculated series
        self.hlc3 = PineScriptSeries("hlc3", max_history)
        self.ohlc4 = PineScriptSeries("ohlc4", max_history)
        self.hl2 = PineScriptSeries("hl2", max_history)
        
        # Custom series storage
        self.custom_series: Dict[str, PineScriptSeries] = {}
        
        # Arrays storage
        self.arrays: Dict[str, PineArray] = {}
        
        # Bar counter
        self.bar_index = 0
        
    def update_bar(self, bar: OHLCVBar) -> None:
        """
        Update all series with new bar data
        
        Args:
            bar: OHLCV bar data
        """
        # Update basic series
        self.open.update(bar.open)
        self.high.update(bar.high)
        self.low.update(bar.low)
        self.close.update(bar.close)
        self.volume.update(bar.volume)
        
        # Calculate and update derived series
        hlc3_value = (bar.high + bar.low + bar.close) / 3
        ohlc4_value = (bar.open + bar.high + bar.low + bar.close) / 4
        hl2_value = (bar.high + bar.low) / 2
        
        self.hlc3.update(hlc3_value)
        self.ohlc4.update(ohlc4_value)
        self.hl2.update(hl2_value)
        
        # Update all arrays to save history
        for array in self.arrays.values():
            array.new_bar()
            
        # Increment bar index
        self.bar_index += 1
        
    def create_series(self, name: str) -> PineScriptSeries:
        """Create custom series"""
        if name not in self.custom_series:
            self.custom_series[name] = PineScriptSeries(name, self.max_history)
        return self.custom_series[name]
        
    def create_array(self, name: str, size: int = 1) -> PineArray:
        """Create custom array"""
        if name not in self.arrays:
            self.arrays[name] = PineArray(size, self.max_history)
        return self.arrays[name]
        
    def get_series(self, name: str) -> Optional[PineScriptSeries]:
        """Get series by name"""
        # Check built-in series
        if hasattr(self, name):
            attr = getattr(self, name)
            if isinstance(attr, PineScriptSeries):
                return attr
        
        # Check custom series
        return self.custom_series.get(name)


# Helper function for backward compatibility
def lookback(values: List[float], index: int) -> Optional[float]:
    """
    Simple lookback function for lists
    
    Args:
        values: List of values (newest at end)
        index: Bars back (0 = current/last, 1 = previous, etc.)
        
    Returns:
        Historical value or None
    """
    if not values or index < 0:
        return None
        
    if index == 0 and values:
        return values[-1]  # Current/last value
        
    if index > 0 and index < len(values):
        return values[-(index + 1)]  # Historical value
        
    return None


# Convenience function for creating series
def create_series(name: str = "series", max_history: int = 500) -> PineScriptSeries:
    """Create a Pine Script style series"""
    return PineScriptSeries(name, max_history)


# Example usage
if __name__ == "__main__":
    # Example 1: Simple series usage
    print("=== Example 1: Pine Script Series ===")
    close = create_series("close")
    
    # Simulate 5 bars
    for i, price in enumerate([100, 102, 101, 103, 104]):
        close.update(price)
        print(f"\nBar {i}: close = {price}")
        
        if i > 0:
            print(f"  close[0] = {close[0]} (current)")
            print(f"  close[1] = {close[1]} (previous)")
            
        if i > 1:
            print(f"  close[2] = {close[2]} (2 bars ago)")
    
    # Example 2: Complete data management
    print("\n\n=== Example 2: Full OHLCV Data ===")
    data = PineScriptData()
    
    bars = [
        OHLCVBar(100, 102, 99, 101, 1000),
        OHLCVBar(101, 103, 100, 102, 1200),
        OHLCVBar(102, 104, 101, 103, 1100),
    ]
    
    for i, bar in enumerate(bars):
        data.update_bar(bar)
        print(f"\nBar {i}:")
        print(f"  close[0] = {data.close[0]}")
        print(f"  high[0] = {data.high[0]}")
        print(f"  hlc3[0] = {data.hlc3[0]}")
        
        if i > 0:
            print(f"  close[1] = {data.close[1]}")
            print(f"  volume[1] = {data.volume[1]}")
