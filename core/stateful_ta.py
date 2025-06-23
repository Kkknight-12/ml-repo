"""
Stateful Technical Analysis Functions
=====================================

CRITICAL: Pine Script's ta.* functions are inherently stateful - they maintain running 
calculations across bars. This module provides stateful Python implementations that 
match Pine Script's behavior.

Each indicator maintains its own state and updates incrementally, avoiding the 
recalculation of entire history on each bar.
"""
from typing import Optional, List, Tuple, Dict
from collections import deque
import math
from .pine_functions import nz  # For Pine Script compatibility


class StatefulIndicator:
    """Base class for all stateful indicators"""
    
    def __init__(self, period: int):
        self.period = period
        self.is_initialized = False
        self.bars_processed = 0
        
    def update(self, value: float) -> float:
        """Update indicator with new value and return current result"""
        raise NotImplementedError("Subclasses must implement update()")
        
    def reset(self):
        """Reset the indicator to initial state"""
        self.is_initialized = False
        self.bars_processed = 0


class StatefulEMA(StatefulIndicator):
    """
    Stateful Exponential Moving Average
    Maintains state like Pine Script's ta.ema()
    """
    
    def __init__(self, period: int):
        super().__init__(period)
        self.alpha = 2.0 / (period + 1)
        self.value: Optional[float] = None
        
    def update(self, current_price: float) -> float:
        """Update EMA with new price"""
        if current_price is None or math.isnan(current_price):
            return self.value if self.value is not None else 0.0
            
        self.bars_processed += 1
        
        if self.value is None:
            # First value - initialize with current price
            self.value = current_price
            self.is_initialized = True
        else:
            # EMA formula: α * current + (1-α) * previous
            self.value = self.alpha * current_price + (1 - self.alpha) * self.value
            
        return self.value
        
    def reset(self):
        super().reset()
        self.value = None


class StatefulSMA(StatefulIndicator):
    """
    Stateful Simple Moving Average
    Maintains a rolling window like Pine Script's ta.sma()
    """
    
    def __init__(self, period: int):
        super().__init__(period)
        self.values = deque(maxlen=period)
        self.sum = 0.0
        
    def update(self, current_price: float) -> float:
        """Update SMA with new price"""
        if current_price is None or math.isnan(current_price):
            return self.sum / len(self.values) if self.values else 0.0
            
        self.bars_processed += 1
        
        # If at capacity, subtract the oldest value
        if len(self.values) == self.period:
            self.sum -= self.values[0]
            
        # Add new value
        self.values.append(current_price)
        self.sum += current_price
        
        # Calculate average
        if len(self.values) > 0:
            self.is_initialized = len(self.values) >= self.period
            return self.sum / len(self.values)
        return 0.0
        
    def reset(self):
        super().reset()
        self.values.clear()
        self.sum = 0.0


class StatefulRMA(StatefulIndicator):
    """
    Stateful Relative Moving Average (Wilder's Smoothing)
    Used internally by RSI, ATR, and other indicators
    """
    
    def __init__(self, period: int):
        super().__init__(period)
        self.alpha = 1.0 / period
        self.value: Optional[float] = None
        self.initial_values = []
        
    def update(self, current_value: float) -> float:
        """Update RMA with new value"""
        if current_value is None or math.isnan(current_value):
            return self.value if self.value is not None else 0.0
            
        self.bars_processed += 1
        
        if self.value is None:
            # Accumulate initial values for SMA
            self.initial_values.append(current_value)
            
            if len(self.initial_values) >= self.period:
                # Initialize with SMA
                self.value = sum(self.initial_values) / len(self.initial_values)
                self.is_initialized = True
                self.initial_values = []  # Clear initial values
            else:
                # Return simple average until we have enough data
                return sum(self.initial_values) / len(self.initial_values)
        else:
            # RMA formula: (previous * (period - 1) + current) / period
            self.value = (self.value * (self.period - 1) + current_value) / self.period
            
        return self.value
        
    def reset(self):
        super().reset()
        self.value = None
        self.initial_values = []


class StatefulRSI(StatefulIndicator):
    """
    Stateful Relative Strength Index
    Maintains separate gain/loss averages like Pine Script's ta.rsi()
    """
    
    def __init__(self, period: int):
        super().__init__(period)
        self.avg_gain_rma = StatefulRMA(period)
        self.avg_loss_rma = StatefulRMA(period)
        self.previous_close: Optional[float] = None
        
    def update(self, current_close: float) -> float:
        """Update RSI with new close price"""
        if current_close is None or math.isnan(current_close):
            return 50.0  # Neutral RSI
            
        self.bars_processed += 1
        
        if self.previous_close is None:
            # First bar - can't calculate change yet
            self.previous_close = current_close
            return 50.0  # Neutral RSI
            
        # Calculate price change
        change = current_close - self.previous_close
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        
        # Update averages
        avg_gain = self.avg_gain_rma.update(gain)
        avg_loss = self.avg_loss_rma.update(loss)
        
        # Calculate RSI
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
            
        # Update previous close for next calculation
        self.previous_close = current_close
        
        self.is_initialized = self.avg_gain_rma.is_initialized and self.avg_loss_rma.is_initialized
        
        return rsi
        
    def reset(self):
        super().reset()
        self.avg_gain_rma.reset()
        self.avg_loss_rma.reset()
        self.previous_close = None


class StatefulATR(StatefulIndicator):
    """
    Stateful Average True Range
    Maintains TR calculation and RMA like Pine Script's ta.atr()
    """
    
    def __init__(self, period: int):
        super().__init__(period)
        self.tr_rma = StatefulRMA(period)
        self.previous_close: Optional[float] = None
        
    def update(self, high: float, low: float, close: float) -> float:
        """Update ATR with new OHLC data"""
        if any(v is None or math.isnan(v) for v in [high, low, close]):
            return 0.0
            
        self.bars_processed += 1
        
        # Calculate True Range
        if self.previous_close is None:
            # First bar - use high-low range
            tr = high - low
        else:
            # TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr = max(
                high - low,
                abs(high - self.previous_close),
                abs(low - self.previous_close)
            )
            
        # Update ATR (RMA of TR)
        atr = self.tr_rma.update(tr)
        
        # Store close for next calculation
        self.previous_close = close
        
        self.is_initialized = self.tr_rma.is_initialized
        
        return atr
        
    def reset(self):
        super().reset()
        self.tr_rma.reset()
        self.previous_close = None


class StatefulCCI(StatefulIndicator):
    """
    Stateful Commodity Channel Index
    Maintains typical price window and calculations
    """
    
    def __init__(self, period: int):
        super().__init__(period)
        self.typical_prices = deque(maxlen=period)
        self.sma = StatefulSMA(period)
        
    def update(self, high: float, low: float, close: float) -> float:
        """Update CCI with new OHLC data"""
        if any(v is None or math.isnan(v) for v in [high, low, close]):
            return 0.0
            
        self.bars_processed += 1
        
        # Calculate typical price (hlc3)
        typical_price = (high + low + close) / 3.0
        
        # Update collections
        self.typical_prices.append(typical_price)
        sma_tp = self.sma.update(typical_price)
        
        # Calculate mean deviation
        if len(self.typical_prices) == 0:
            return 0.0
            
        deviations = [abs(tp - sma_tp) for tp in self.typical_prices]
        mean_deviation = sum(deviations) / len(deviations)
        
        # Calculate CCI
        if mean_deviation == 0:
            return 0.0
            
        cci = (typical_price - sma_tp) / (0.015 * mean_deviation)
        
        self.is_initialized = self.sma.is_initialized
        
        return cci
        
    def reset(self):
        super().reset()
        self.typical_prices.clear()
        self.sma.reset()


class StatefulDMI(StatefulIndicator):
    """
    Stateful Directional Movement Index
    Maintains DI+, DI-, and ADX calculations
    """
    
    def __init__(self, di_length: int, adx_length: int):
        super().__init__(di_length)
        self.adx_length = adx_length
        
        # RMA for smoothing
        self.smooth_tr = StatefulRMA(di_length)
        self.smooth_plus_dm = StatefulRMA(di_length)
        self.smooth_minus_dm = StatefulRMA(di_length)
        
        # For ADX calculation
        self.dx_values = deque(maxlen=adx_length)
        self.adx_rma = StatefulRMA(adx_length)
        
        # Previous values
        self.prev_high: Optional[float] = None
        self.prev_low: Optional[float] = None
        self.prev_close: Optional[float] = None
        
    def update(self, high: float, low: float, close: float) -> Tuple[float, float, float]:
        """Update DMI with new OHLC data, returns (DI+, DI-, ADX)"""
        if any(v is None or math.isnan(v) for v in [high, low, close]):
            return 0.0, 0.0, 0.0
            
        self.bars_processed += 1
        
        # First bar - store values and return zeros
        if self.prev_high is None:
            self.prev_high = high
            self.prev_low = low
            self.prev_close = close
            return 0.0, 0.0, 0.0
            
        # Calculate True Range
        tr = max(
            high - low,
            abs(high - self.prev_close),
            abs(low - self.prev_close)
        )
        
        # Calculate Directional Movement
        high_diff = high - self.prev_high
        low_diff = self.prev_low - low
        
        plus_dm = max(high_diff, 0) if high_diff > low_diff else 0
        minus_dm = max(low_diff, 0) if low_diff > high_diff else 0
        
        # Update smoothed values
        smooth_tr_val = self.smooth_tr.update(tr)
        smooth_plus_dm_val = self.smooth_plus_dm.update(plus_dm)
        smooth_minus_dm_val = self.smooth_minus_dm.update(minus_dm)
        
        # Calculate DI+ and DI-
        di_plus = (smooth_plus_dm_val / smooth_tr_val * 100) if smooth_tr_val > 0 else 0
        di_minus = (smooth_minus_dm_val / smooth_tr_val * 100) if smooth_tr_val > 0 else 0
        
        # Calculate DX
        di_sum = di_plus + di_minus
        if di_sum == 0:
            dx = 0
        else:
            dx = abs(di_plus - di_minus) / di_sum * 100
            
        # Update ADX
        adx = self.adx_rma.update(dx)
        
        # Update previous values
        self.prev_high = high
        self.prev_low = low
        self.prev_close = close
        
        self.is_initialized = (self.smooth_tr.is_initialized and 
                             self.smooth_plus_dm.is_initialized and 
                             self.smooth_minus_dm.is_initialized and
                             self.bars_processed >= self.adx_length)
        
        return di_plus, di_minus, adx
        
    def reset(self):
        super().reset()
        self.smooth_tr.reset()
        self.smooth_plus_dm.reset()
        self.smooth_minus_dm.reset()
        self.dx_values.clear()
        self.adx_rma.reset()
        self.prev_high = None
        self.prev_low = None
        self.prev_close = None


class StatefulStdev(StatefulIndicator):
    """
    Stateful Standard Deviation
    Maintains running calculation
    """
    
    def __init__(self, period: int):
        super().__init__(period)
        self.values = deque(maxlen=period)
        self.sma = StatefulSMA(period)
        
    def update(self, value: float) -> float:
        """Update standard deviation with new value"""
        if value is None or math.isnan(value):
            return 0.0
            
        self.bars_processed += 1
        
        # Update collections
        self.values.append(value)
        mean = self.sma.update(value)
        
        # Calculate standard deviation
        if len(self.values) < 2:
            return 0.0
            
        variance = sum((x - mean) ** 2 for x in self.values) / len(self.values)
        stdev = math.sqrt(variance)
        
        self.is_initialized = len(self.values) >= self.period
        
        return stdev
        
    def reset(self):
        super().reset()
        self.values.clear()
        self.sma.reset()


class StatefulWaveTrend(StatefulIndicator):
    """
    Stateful WaveTrend Oscillator
    Complex indicator with multiple EMAs
    """
    
    def __init__(self, n1: int, n2: int):
        super().__init__(n1)
        self.n2 = n2
        
        # EMAs for calculation
        self.ema1 = StatefulEMA(n1)
        self.ema2 = StatefulEMA(n1)
        self.tci_ema = StatefulEMA(n2)
        self.wt2_sma = StatefulSMA(4)
        
        # Track hlc3 for diff calculation
        self.current_hlc3: Optional[float] = None
        
    def update(self, high: float, low: float, close: float) -> Tuple[float, float]:
        """Update WaveTrend with new OHLC data, returns (wt1, wt2)"""
        if any(v is None or math.isnan(v) for v in [high, low, close]):
            return 0.0, 0.0
            
        self.bars_processed += 1
        
        # Calculate HLC3
        hlc3 = (high + low + close) / 3.0
        self.current_hlc3 = hlc3
        
        # Step 1: EMA of HLC3
        ema1_val = self.ema1.update(hlc3)
        
        # Step 2: EMA of absolute difference
        diff = abs(hlc3 - ema1_val)
        ema2_val = self.ema2.update(diff)
        
        # Step 3: Calculate CI (Chande Index)
        if ema2_val == 0:
            ci = 0.0
        else:
            ci = (hlc3 - ema1_val) / (0.015 * ema2_val)
            
        # Step 4: WT1 = EMA of CI (TCI)
        wt1 = self.tci_ema.update(ci)
        
        # Step 5: WT2 = SMA of WT1
        wt2 = self.wt2_sma.update(wt1)
        
        self.is_initialized = (self.ema1.is_initialized and 
                             self.ema2.is_initialized and 
                             self.tci_ema.is_initialized)
        
        return wt1, wt2
        
    def reset(self):
        super().reset()
        self.ema1.reset()
        self.ema2.reset()
        self.tci_ema.reset()
        self.wt2_sma.reset()
        self.current_hlc3 = None


# Utility functions for state tracking
class StatefulChange:
    """Track price changes between bars"""
    
    def __init__(self):
        self.previous_value: Optional[float] = None
        
    def update(self, current_value: float) -> float:
        """Calculate change from previous value"""
        if current_value is None or math.isnan(current_value):
            return 0.0
            
        if self.previous_value is None:
            self.previous_value = current_value
            return 0.0
            
        change = current_value - self.previous_value
        self.previous_value = current_value
        return change
        
    def reset(self):
        self.previous_value = None


class StatefulCrossover:
    """Track crossover events between two series"""
    
    def __init__(self):
        self.prev_series1: Optional[float] = None
        self.prev_series2: Optional[float] = None
        
    def update(self, series1: float, series2: float) -> bool:
        """Check if series1 crossed over series2"""
        if any(v is None or math.isnan(v) for v in [series1, series2]):
            return False
            
        # Need at least one previous value
        if self.prev_series1 is None or self.prev_series2 is None:
            self.prev_series1 = series1
            self.prev_series2 = series2
            return False
            
        # Crossover: prev1 <= prev2 and curr1 > curr2
        crossover = (self.prev_series1 <= self.prev_series2 and 
                    series1 > series2)
        
        # Update previous values
        self.prev_series1 = series1
        self.prev_series2 = series2
        
        return crossover
        
    def reset(self):
        self.prev_series1 = None
        self.prev_series2 = None


class StatefulCrossunder:
    """Track crossunder events between two series"""
    
    def __init__(self):
        self.prev_series1: Optional[float] = None
        self.prev_series2: Optional[float] = None
        
    def update(self, series1: float, series2: float) -> bool:
        """Check if series1 crossed under series2"""
        if any(v is None or math.isnan(v) for v in [series1, series2]):
            return False
            
        # Need at least one previous value
        if self.prev_series1 is None or self.prev_series2 is None:
            self.prev_series1 = series1
            self.prev_series2 = series2
            return False
            
        # Crossunder: prev1 >= prev2 and curr1 < curr2
        crossunder = (self.prev_series1 >= self.prev_series2 and 
                     series1 < series2)
        
        # Update previous values
        self.prev_series1 = series1
        self.prev_series2 = series2
        
        return crossunder
        
    def reset(self):
        self.prev_series1 = None
        self.prev_series2 = None


class StatefulBarsSince:
    """Track bars since a condition was true"""
    
    def __init__(self):
        self.bars_count = 0
        self.condition_met = False
        
    def update(self, condition: bool) -> int:
        """Update counter based on condition"""
        if condition:
            # Reset counter when condition is true
            self.bars_count = 0
            self.condition_met = True
        else:
            # Increment counter if condition has been met before
            if self.condition_met:
                self.bars_count += 1
                
        return self.bars_count
        
    def reset(self):
        self.bars_count = 0
        self.condition_met = False
