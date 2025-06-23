"""
Indicator State Manager
======================

Manages stateful indicator instances per symbol/timeframe combination.
This ensures each symbol maintains its own independent indicator state,
just like Pine Script does automatically.
"""
from typing import Dict, Optional, Tuple
from .stateful_ta import (
    StatefulEMA, StatefulSMA, StatefulRMA, StatefulRSI, StatefulATR,
    StatefulCCI, StatefulDMI, StatefulStdev, StatefulWaveTrend,
    StatefulChange, StatefulCrossover, StatefulCrossunder, StatefulBarsSince
)


class IndicatorStateManager:
    """
    Manages stateful indicator instances for different symbols and timeframes.
    
    Key features:
    - Each symbol/timeframe combination gets its own indicator instances
    - Indicators maintain state across bar updates
    - Automatic instance creation on first access
    - Memory efficient - only creates indicators that are actually used
    """
    
    def __init__(self):
        # Nested dict: {symbol: {timeframe: {indicator_key: indicator_instance}}}
        self.indicators: Dict[str, Dict[str, Dict[str, object]]] = {}
        
    def _get_key(self, symbol: str, timeframe: str, indicator_type: str, *params) -> Tuple[str, str, str]:
        """Generate unique key for indicator instance"""
        # Create parameter string from all parameters
        param_str = "_".join(str(p) for p in params)
        indicator_key = f"{indicator_type}_{param_str}" if param_str else indicator_type
        return symbol, timeframe, indicator_key
        
    def _get_or_create(self, symbol: str, timeframe: str, indicator_key: str, 
                      creator_func) -> object:
        """Get existing indicator or create new one"""
        # Ensure nested structure exists
        if symbol not in self.indicators:
            self.indicators[symbol] = {}
        if timeframe not in self.indicators[symbol]:
            self.indicators[symbol][timeframe] = {}
            
        # Get or create indicator
        if indicator_key not in self.indicators[symbol][timeframe]:
            self.indicators[symbol][timeframe][indicator_key] = creator_func()
            
        return self.indicators[symbol][timeframe][indicator_key]
        
    # EMA Management
    def get_or_create_ema(self, symbol: str, timeframe: str, period: int) -> StatefulEMA:
        """Get or create EMA instance for symbol/timeframe"""
        sym, tf, key = self._get_key(symbol, timeframe, "ema", period)
        return self._get_or_create(sym, tf, key, lambda: StatefulEMA(period))
        
    # SMA Management
    def get_or_create_sma(self, symbol: str, timeframe: str, period: int) -> StatefulSMA:
        """Get or create SMA instance for symbol/timeframe"""
        sym, tf, key = self._get_key(symbol, timeframe, "sma", period)
        return self._get_or_create(sym, tf, key, lambda: StatefulSMA(period))
        
    # RMA Management
    def get_or_create_rma(self, symbol: str, timeframe: str, period: int) -> StatefulRMA:
        """Get or create RMA instance for symbol/timeframe"""
        sym, tf, key = self._get_key(symbol, timeframe, "rma", period)
        return self._get_or_create(sym, tf, key, lambda: StatefulRMA(period))
        
    # RSI Management
    def get_or_create_rsi(self, symbol: str, timeframe: str, period: int) -> StatefulRSI:
        """Get or create RSI instance for symbol/timeframe"""
        sym, tf, key = self._get_key(symbol, timeframe, "rsi", period)
        return self._get_or_create(sym, tf, key, lambda: StatefulRSI(period))
        
    # ATR Management
    def get_or_create_atr(self, symbol: str, timeframe: str, period: int) -> StatefulATR:
        """Get or create ATR instance for symbol/timeframe"""
        sym, tf, key = self._get_key(symbol, timeframe, "atr", period)
        return self._get_or_create(sym, tf, key, lambda: StatefulATR(period))
        
    # CCI Management
    def get_or_create_cci(self, symbol: str, timeframe: str, period: int) -> StatefulCCI:
        """Get or create CCI instance for symbol/timeframe"""
        sym, tf, key = self._get_key(symbol, timeframe, "cci", period)
        return self._get_or_create(sym, tf, key, lambda: StatefulCCI(period))
        
    # DMI Management
    def get_or_create_dmi(self, symbol: str, timeframe: str, 
                         di_length: int, adx_length: int) -> StatefulDMI:
        """Get or create DMI instance for symbol/timeframe"""
        sym, tf, key = self._get_key(symbol, timeframe, "dmi", di_length, adx_length)
        return self._get_or_create(sym, tf, key, lambda: StatefulDMI(di_length, adx_length))
        
    # Standard Deviation Management
    def get_or_create_stdev(self, symbol: str, timeframe: str, period: int) -> StatefulStdev:
        """Get or create Standard Deviation instance for symbol/timeframe"""
        sym, tf, key = self._get_key(symbol, timeframe, "stdev", period)
        return self._get_or_create(sym, tf, key, lambda: StatefulStdev(period))
        
    # WaveTrend Management
    def get_or_create_wavetrend(self, symbol: str, timeframe: str, 
                                n1: int, n2: int) -> StatefulWaveTrend:
        """Get or create WaveTrend instance for symbol/timeframe"""
        sym, tf, key = self._get_key(symbol, timeframe, "wt", n1, n2)
        return self._get_or_create(sym, tf, key, lambda: StatefulWaveTrend(n1, n2))
        
    # Change Tracking
    def get_or_create_change(self, symbol: str, timeframe: str, 
                            series_name: str = "default") -> StatefulChange:
        """Get or create Change tracker for symbol/timeframe"""
        sym, tf, key = self._get_key(symbol, timeframe, "change", series_name)
        return self._get_or_create(sym, tf, key, lambda: StatefulChange())
        
    # Crossover Detection
    def get_or_create_crossover(self, symbol: str, timeframe: str,
                               series1_name: str, series2_name: str) -> StatefulCrossover:
        """Get or create Crossover detector for symbol/timeframe"""
        sym, tf, key = self._get_key(symbol, timeframe, "crossover", series1_name, series2_name)
        return self._get_or_create(sym, tf, key, lambda: StatefulCrossover())
        
    # Crossunder Detection
    def get_or_create_crossunder(self, symbol: str, timeframe: str,
                                series1_name: str, series2_name: str) -> StatefulCrossunder:
        """Get or create Crossunder detector for symbol/timeframe"""
        sym, tf, key = self._get_key(symbol, timeframe, "crossunder", series1_name, series2_name)
        return self._get_or_create(sym, tf, key, lambda: StatefulCrossunder())
        
    # Bars Since
    def get_or_create_barssince(self, symbol: str, timeframe: str,
                               condition_name: str) -> StatefulBarsSince:
        """Get or create BarsSince counter for symbol/timeframe"""
        sym, tf, key = self._get_key(symbol, timeframe, "barssince", condition_name)
        return self._get_or_create(sym, tf, key, lambda: StatefulBarsSince())
        
    # Management Methods
    def reset_symbol(self, symbol: str):
        """Reset all indicators for a specific symbol"""
        if symbol in self.indicators:
            for timeframe in self.indicators[symbol]:
                for indicator in self.indicators[symbol][timeframe].values():
                    if hasattr(indicator, 'reset'):
                        indicator.reset()
                        
    def reset_all(self):
        """Reset all indicators for all symbols"""
        for symbol in self.indicators:
            self.reset_symbol(symbol)
            
    def clear_symbol(self, symbol: str):
        """Remove all indicators for a specific symbol (free memory)"""
        if symbol in self.indicators:
            del self.indicators[symbol]
            
    def clear_all(self):
        """Remove all indicators (free all memory)"""
        self.indicators.clear()
        
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about managed indicators"""
        stats = {
            'total_symbols': len(self.indicators),
            'total_indicators': 0,
            'by_type': {}
        }
        
        for symbol in self.indicators:
            for timeframe in self.indicators[symbol]:
                for key, indicator in self.indicators[symbol][timeframe].items():
                    stats['total_indicators'] += 1
                    
                    # Extract indicator type from key
                    indicator_type = key.split('_')[0]
                    if indicator_type not in stats['by_type']:
                        stats['by_type'][indicator_type] = 0
                    stats['by_type'][indicator_type] += 1
                    
        return stats
