"""
Filter Debug Module
==================
Adds comprehensive logging to understand filter behavior
"""
import logging
from typing import Tuple, Optional
from .enhanced_ml_extensions import enhanced_regime_filter, enhanced_filter_adx, enhanced_filter_volatility

# Create dedicated logger for filters
filter_logger = logging.getLogger('filters')
filter_logger.setLevel(logging.DEBUG)

# Create file handler
fh = logging.FileHandler('filter_debug.log')
fh.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)

# Add handler to logger
filter_logger.addHandler(fh)


def debug_volatility_filter(high: float, low: float, close: float,
                          min_length: int, max_length: int, 
                          use_filter: bool, symbol: str, timeframe: str) -> bool:
    """Debug wrapper for volatility filter"""
    result = enhanced_filter_volatility(high, low, close, min_length, max_length, 
                                      use_filter, symbol, timeframe)
    
    filter_logger.debug(f"VOLATILITY FILTER [{symbol}]: "
                       f"high={high:.2f}, low={low:.2f}, close={close:.2f}, "
                       f"use_filter={use_filter}, result={result}")
    
    return result


def debug_regime_filter(src: float, high: float, low: float, 
                       threshold: float, use_filter: bool,
                       symbol: str, timeframe: str) -> bool:
    """Debug wrapper for regime filter"""
    result = enhanced_regime_filter(src, high, low, threshold, use_filter, 
                                  symbol, timeframe)
    
    filter_logger.debug(f"REGIME FILTER [{symbol}]: "
                       f"src={src:.2f}, threshold={threshold}, "
                       f"use_filter={use_filter}, result={result}")
    
    return result


def debug_adx_filter(high: float, low: float, close: float,
                    length: int, threshold: int, use_filter: bool,
                    symbol: str, timeframe: str) -> bool:
    """Debug wrapper for ADX filter"""
    result = enhanced_filter_adx(high, low, close, length, threshold, 
                               use_filter, symbol, timeframe)
    
    filter_logger.debug(f"ADX FILTER [{symbol}]: "
                       f"close={close:.2f}, threshold={threshold}, "
                       f"use_filter={use_filter}, result={result}")
    
    return result


def get_filter_statistics() -> dict:
    """Read filter log and calculate statistics"""
    stats = {
        'volatility': {'total': 0, 'passed': 0},
        'regime': {'total': 0, 'passed': 0},
        'adx': {'total': 0, 'passed': 0}
    }
    
    try:
        with open('filter_debug.log', 'r') as f:
            for line in f:
                if 'VOLATILITY FILTER' in line:
                    stats['volatility']['total'] += 1
                    if 'result=True' in line:
                        stats['volatility']['passed'] += 1
                elif 'REGIME FILTER' in line:
                    stats['regime']['total'] += 1
                    if 'result=True' in line:
                        stats['regime']['passed'] += 1
                elif 'ADX FILTER' in line:
                    stats['adx']['total'] += 1
                    if 'result=True' in line:
                        stats['adx']['passed'] += 1
    except FileNotFoundError:
        pass
    
    # Calculate pass rates
    for filter_name in stats:
        total = stats[filter_name]['total']
        passed = stats[filter_name]['passed']
        stats[filter_name]['pass_rate'] = (passed / total * 100) if total > 0 else 0
    
    return stats