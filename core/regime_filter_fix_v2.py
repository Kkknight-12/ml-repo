"""
Fixed Regime Filter Implementation V2
=====================================

This implements the EXACT Pine Script regime filter logic.
The key insight is that Pine Script's ta.ema() handles initialization differently
and we need to match that behavior exactly.
"""
import math
from typing import Optional, Dict, List
from .stateful_ta import StatefulIndicator


class PineScriptEMA:
    """
    EMA that matches Pine Script's ta.ema() behavior exactly
    """
    def __init__(self, period: int):
        self.period = period
        self.alpha = 2.0 / (period + 1)
        self.value: Optional[float] = None
        self.values: List[float] = []  # Store all values for debugging
    
    def update(self, value: float) -> float:
        """Update EMA with new value"""
        if self.value is None:
            # First value - Pine Script initializes EMA to the first value
            self.value = value
        else:
            # EMA formula: alpha * value + (1 - alpha) * previous_ema
            self.value = self.alpha * value + (1 - self.alpha) * self.value
        
        self.values.append(self.value)
        return self.value
    
    def reset(self):
        """Reset to initial state"""
        self.value = None
        self.values.clear()


class StatefulRegimeFilterV2(StatefulIndicator):
    """
    Stateful implementation of Pine Script's regime filter
    This version more accurately matches Pine Script's behavior
    """
    
    def __init__(self):
        super().__init__(200)  # 200 bar EMA for slope
        
        # State variables (var in Pine Script)
        self.value1: float = 0.0
        self.value2: float = 0.0
        self.klmf: float = 0.0
        self.prev_src: Optional[float] = None
        self.prev_klmf: Optional[float] = None
        
        # EMA for exponential average of slope - matches ta.ema()
        self.slope_ema = PineScriptEMA(200)
        
        # Debug tracking
        self.debug_values = []
        
    def update(self, src: float, high: float, low: float) -> float:
        """
        Update regime filter and return normalized slope decline
        
        Args:
            src: Current source value (usually OHLC4)
            high: Current high
            low: Current low
            
        Returns:
            Normalized slope decline value
        """
        if any(v is None or math.isnan(v) for v in [src, high, low]):
            return 0.0
            
        self.bars_processed += 1
        
        # Calculate source change
        src_change = 0.0
        if self.prev_src is not None:
            src_change = src - self.prev_src
        
        # Update value1: 0.2 * (src - src[1]) + 0.8 * nz(value1[1])
        # nz() returns 0 if value is None/NaN
        self.value1 = 0.2 * src_change + 0.8 * self.value1
        
        # Update value2: 0.1 * (high - low) + 0.8 * nz(value2[1])
        high_low_range = high - low
        self.value2 = 0.1 * high_low_range + 0.8 * self.value2
        
        # Calculate omega and alpha
        omega = 0.0
        if self.value2 != 0:
            omega = abs(self.value1 / self.value2)
        
        # Pine Script formula for alpha
        alpha = (-omega * omega + math.sqrt(omega ** 4 + 16 * omega ** 2)) / 8
        
        # Update KLMF: alpha * src + (1 - alpha) * nz(klmf[1])
        # On first bar, klmf[1] is 0 (nz behavior)
        if self.bars_processed == 1:
            self.klmf = alpha * src  # First bar: no previous klmf
        else:
            self.klmf = alpha * src + (1 - alpha) * self.klmf
        
        # Calculate absolute curve slope
        abs_curve_slope = 0.0
        if self.prev_klmf is not None:
            abs_curve_slope = abs(self.klmf - self.prev_klmf)
        
        # Update exponential average of absolute curve slope
        # Pine Script: exponentialAverageAbsCurveSlope = 1.0 * ta.ema(absCurveSlope, 200)
        exp_avg_slope = self.slope_ema.update(abs_curve_slope)
        
        # Calculate normalized slope decline
        normalized_slope_decline = 0.0
        if exp_avg_slope > 0:
            normalized_slope_decline = (abs_curve_slope - exp_avg_slope) / exp_avg_slope
        
        # Debug logging for specific bars
        if self.bars_processed in [1, 10, 20, 30, 40, 50, 100, 150, 200] or self.bars_processed % 50 == 0:
            debug_info = {
                'bar': self.bars_processed,
                'src': src,
                'value1': self.value1,
                'value2': self.value2,
                'omega': omega,
                'alpha': alpha,
                'klmf': self.klmf,
                'abs_slope': abs_curve_slope,
                'exp_avg': exp_avg_slope,
                'nsd': normalized_slope_decline
            }
            self.debug_values.append(debug_info)
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"REGIME V2 Bar {self.bars_processed}: "
                       f"v1={self.value1:.6f}, v2={self.value2:.6f}, "
                       f"omega={omega:.6f}, alpha={alpha:.6f}, klmf={self.klmf:.2f}, "
                       f"slope={abs_curve_slope:.6f}, avg={exp_avg_slope:.6f}, "
                       f"NSD={normalized_slope_decline:.6f}")
        
        # Update previous values
        self.prev_src = src
        self.prev_klmf = self.klmf
        
        return normalized_slope_decline
        
    def reset(self):
        """Reset to initial state"""
        super().reset()
        self.value1 = 0.0
        self.value2 = 0.0
        self.klmf = 0.0
        self.prev_src = None
        self.prev_klmf = None
        self.slope_ema.reset()
        self.debug_values.clear()


def fixed_regime_filter_v2(src: float, high: float, low: float, 
                          threshold: float, use_regime_filter: bool,
                          symbol: str, timeframe: str) -> bool:
    """
    Fixed regime filter V2 that uses exact Pine Script logic
    
    Args:
        src: Current source value (usually OHLC4)
        high: Current high
        low: Current low
        threshold: Threshold for trend detection
        use_regime_filter: Whether to use the filter
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        True if market is trending (normalized slope decline >= threshold)
    """
    if not use_regime_filter:
        return True
    
    # Get or create stateful regime filter
    from .enhanced_indicators import get_indicator_manager
    manager = get_indicator_manager()
    key = f"regime_filter_v2_{symbol}_{timeframe}"
    
    indicators = manager.indicators.setdefault(symbol, {}).setdefault(timeframe, {})
    if key not in indicators:
        indicators[key] = StatefulRegimeFilterV2()
    
    regime_filter = indicators[key]
    
    # Update and get normalized slope decline
    normalized_slope_decline = regime_filter.update(src, high, low)
    
    # Return true if slope decline is above threshold
    return normalized_slope_decline >= threshold