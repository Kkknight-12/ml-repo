"""
Fixed Regime Filter Implementation
==================================

This implements the EXACT Pine Script regime filter logic without modifications.
The issue was that we were using EMA which doesn't match Pine Script's custom recursive formula.
"""
import math
from typing import Optional, Dict
from .stateful_ta import StatefulEMA, StatefulIndicator
from .enhanced_indicators import get_indicator_manager


class StatefulRegimeFilter(StatefulIndicator):
    """
    Stateful implementation of Pine Script's regime filter
    Uses exact recursive formulas from Pine Script
    """
    
    def __init__(self):
        super().__init__(200)  # 200 bar EMA for slope
        
        # State variables (var in Pine Script)
        self.value1: float = 0.0
        self.value2: float = 0.0
        self.klmf: float = 0.0
        self.prev_ohlc4: Optional[float] = None
        self.prev_klmf: Optional[float] = None
        
        # EMA for exponential average of slope
        self.slope_ema = StatefulEMA(200)
        
    def update(self, ohlc4: float, high: float, low: float) -> float:
        """
        Update regime filter and return normalized slope decline
        
        Args:
            ohlc4: Current OHLC4 value
            high: Current high
            low: Current low
            
        Returns:
            Normalized slope decline value
        """
        if any(v is None or math.isnan(v) for v in [ohlc4, high, low]):
            return 0.0
            
        self.bars_processed += 1
        
        # Initialize KLMF on first bar (Pine Script's nz() handles this)
        if self.bars_processed == 1:
            self.klmf = ohlc4
            self.prev_ohlc4 = ohlc4
            self.prev_klmf = ohlc4
            return 0.0  # No slope on first bar
        
        # Calculate source change
        src_change = 0.0
        if self.prev_ohlc4 is not None:
            src_change = ohlc4 - self.prev_ohlc4
        
        # Update value1: 0.2 * (src - src[1]) + 0.8 * value1[1]
        self.value1 = 0.2 * src_change + 0.8 * self.value1
        
        # Update value2: 0.1 * (high - low) + 0.8 * value2[1]
        high_low_range = high - low
        self.value2 = 0.1 * high_low_range + 0.8 * self.value2
        
        # Calculate omega and alpha
        omega = 0.0
        if self.value2 != 0:
            omega = abs(self.value1 / self.value2)
        
        # Pine Script formula for alpha
        alpha = (-omega * omega + math.sqrt(omega ** 4 + 16 * omega ** 2)) / 8
        
        # Update KLMF: alpha * src + (1 - alpha) * klmf[1]
        self.klmf = alpha * ohlc4 + (1 - alpha) * self.klmf
        
        # Calculate absolute curve slope
        abs_curve_slope = 0.0
        if self.prev_klmf is not None:
            abs_curve_slope = abs(self.klmf - self.prev_klmf)
        
        # Update exponential average of absolute curve slope
        exp_avg_slope = self.slope_ema.update(abs_curve_slope)
        
        # Calculate normalized slope decline
        normalized_slope_decline = 0.0
        if exp_avg_slope > 0:
            normalized_slope_decline = (abs_curve_slope - exp_avg_slope) / exp_avg_slope
        
        # Debug logging for specific bars to track the issue
        if self.bars_processed in [10, 20, 30, 40, 50, 100, 150] or self.bars_processed % 50 == 0:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"REGIME DEBUG Bar {self.bars_processed}: "
                       f"value1={self.value1:.6f}, value2={self.value2:.6f}, "
                       f"omega={omega:.6f}, alpha={alpha:.6f}, klmf={self.klmf:.2f}, "
                       f"abs_slope={abs_curve_slope:.6f}, exp_avg={exp_avg_slope:.6f}, "
                       f"normalized_decline={normalized_slope_decline:.6f}, "
                       f"threshold=-0.1, passes={normalized_slope_decline >= -0.1}")
        
        # Update previous values
        self.prev_ohlc4 = ohlc4
        self.prev_klmf = self.klmf
        
        return normalized_slope_decline
        
    def reset(self):
        """Reset to initial state"""
        super().reset()
        self.value1 = 0.0
        self.value2 = 0.0
        self.klmf = 0.0
        self.prev_ohlc4 = None
        self.prev_klmf = None
        self.slope_ema.reset()


def fixed_regime_filter(ohlc4: float, high: float, low: float, 
                       threshold: float, use_regime_filter: bool,
                       symbol: str, timeframe: str) -> bool:
    """
    Fixed regime filter that uses exact Pine Script logic
    
    Args:
        ohlc4: Current OHLC4 value
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
    manager = get_indicator_manager()
    key = f"regime_filter_{symbol}_{timeframe}"
    
    indicators = manager.indicators.setdefault(symbol, {}).setdefault(timeframe, {})
    if key not in indicators:
        indicators[key] = StatefulRegimeFilter()
    
    regime_filter = indicators[key]
    
    # Update and get normalized slope decline
    normalized_slope_decline = regime_filter.update(ohlc4, high, low)
    
    # Return true if slope decline is above threshold
    return normalized_slope_decline >= threshold
