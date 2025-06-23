"""
Enhanced Bar Data with Pine Script style history referencing
Replacement for bar_data.py with [] operator support
"""
from typing import Optional, List, Union
from core.history_referencing import PineScriptData, OHLCVBar, lookback


class EnhancedBarData:
    """
    Bar data manager with Pine Script style history referencing
    Drop-in replacement for BarData with [] operator support
    """
    
    def __init__(self, max_bars: int = 2500):
        """Initialize with Pine Script data structure"""
        self.max_bars = max_bars
        self.data = PineScriptData(max_bars)
        
        # For backward compatibility
        self.bar_index = 0
        
        # Legacy lists (for compatibility)
        self._open_list: List[float] = []
        self._high_list: List[float] = []
        self._low_list: List[float] = []
        self._close_list: List[float] = []
        self._volume_list: List[float] = []
        
    def add_bar(self, open_price: float, high: float, low: float, 
                close: float, volume: float = 0.0) -> None:
        """
        Add new bar data
        
        Args:
            open_price: Opening price
            high: High price
            low: Low price  
            close: Closing price
            volume: Volume (default 0)
        """
        # Create bar
        bar = OHLCVBar(open_price, high, low, close, volume)
        
        # Update Pine Script data
        self.data.update_bar(bar)
        
        # Update legacy lists (for compatibility)
        self._open_list.append(open_price)
        self._high_list.append(high)
        self._low_list.append(low)
        self._close_list.append(close)
        self._volume_list.append(volume)
        
        # Limit list sizes
        if len(self._close_list) > self.max_bars:
            self._open_list.pop(0)
            self._high_list.pop(0)
            self._low_list.pop(0)
            self._close_list.pop(0)
            self._volume_list.pop(0)
        
        # Update bar index
        self.bar_index = self.data.bar_index
    
    # Pine Script style access
    @property
    def open(self):
        """Access open series with [] operator"""
        return self.data.open
        
    @property
    def high(self):
        """Access high series with [] operator"""
        return self.data.high
        
    @property
    def low(self):
        """Access low series with [] operator"""
        return self.data.low
        
    @property
    def close(self):
        """Access close series with [] operator"""
        return self.data.close
        
    @property
    def volume(self):
        """Access volume series with [] operator"""
        return self.data.volume
        
    @property
    def hlc3(self):
        """Access hlc3 series with [] operator"""
        return self.data.hlc3
        
    @property
    def ohlc4(self):
        """Access ohlc4 series with [] operator"""
        return self.data.ohlc4
        
    @property
    def hl2(self):
        """Access hl2 series with [] operator"""
        return self.data.hl2
    
    # Legacy compatibility methods
    def get_open(self, bars_back: int = 0) -> Optional[float]:
        """Get open price N bars back (legacy method)"""
        return self.open[bars_back]
    
    def get_high(self, bars_back: int = 0) -> Optional[float]:
        """Get high price N bars back (legacy method)"""
        return self.high[bars_back]
        
    def get_low(self, bars_back: int = 0) -> Optional[float]:
        """Get low price N bars back (legacy method)"""
        return self.low[bars_back]
        
    def get_close(self, bars_back: int = 0) -> Optional[float]:
        """Get close price N bars back (legacy method)"""
        return self.close[bars_back]
        
    def get_volume(self, bars_back: int = 0) -> Optional[float]:
        """Get volume N bars back (legacy method)"""
        return self.volume[bars_back]
        
    def get_hlc3(self, bars_back: int = 0) -> Optional[float]:
        """Get HLC3 N bars back (legacy method)"""
        return self.hlc3[bars_back]
        
    def get_ohlc4(self, bars_back: int = 0) -> Optional[float]:
        """Get OHLC4 N bars back (legacy method)"""
        return self.ohlc4[bars_back]
        
    def get_hl2(self, bars_back: int = 0) -> Optional[float]:
        """Get HL2 N bars back (legacy method)"""
        return self.hl2[bars_back]
    
    def __len__(self) -> int:
        """Number of bars stored"""
        return len(self._close_list)
    
    # Create custom series
    def create_series(self, name: str):
        """Create custom series for indicators"""
        return self.data.create_series(name)
        
    def create_array(self, name: str, size: int = 1):
        """Create custom array"""
        return self.data.create_array(name, size)


# Convenience function for backward compatibility
def pine_lookback(values: List[float], index: int) -> Optional[float]:
    """
    Pine Script style lookback for lists
    
    Args:
        values: List of values (oldest to newest)
        index: Bars back (0 = current, 1 = previous)
        
    Returns:
        Historical value or None
    """
    return lookback(values, index)


# Example usage
if __name__ == "__main__":
    print("=== Enhanced Bar Data Example ===\n")
    
    # Create enhanced bar data
    bars = EnhancedBarData()
    
    # Add some test bars
    test_data = [
        (100, 102, 99, 101, 1000),
        (101, 103, 100, 102, 1200),
        (102, 104, 101, 103, 1100),
        (103, 105, 102, 104, 1300),
    ]
    
    for i, (o, h, l, c, v) in enumerate(test_data):
        bars.add_bar(o, h, l, c, v)
        print(f"Bar {i}:")
        
        # Pine Script style access
        print(f"  close[0] = {bars.close[0]} (current)")
        if i > 0:
            print(f"  close[1] = {bars.close[1]} (previous)")
            print(f"  high[1] = {bars.high[1]}")
            print(f"  volume[1] = {bars.volume[1]}")
            
        # Legacy method (still works)
        print(f"  get_close(0) = {bars.get_close(0)}")
        
        # Calculated values
        print(f"  hlc3[0] = {bars.hlc3[0]}")
        print()
