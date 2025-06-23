"""
Core module - Technical indicators and ML helpers
"""

# Math helpers
from .math_helpers import (
    tanh,
    normalize_deriv,
    dual_pole_filter,
    pine_ema,
    pine_sma,
    pine_rma,
    pine_stdev,
    pine_atr
)

# Normalization
from .normalization import (
    normalizer,
    rescale,
    tanh_transform
)

# Enhanced Indicators (indicators.py was archived)
from .enhanced_indicators import (
    enhanced_rsi as calculate_rsi,
    enhanced_n_rsi as n_rsi,
    enhanced_cci as calculate_cci,
    enhanced_n_cci as n_cci,
    enhanced_wavetrend as calculate_wavetrend,
    enhanced_n_wt as n_wt,
    enhanced_dmi as dmi,
    enhanced_n_adx as n_adx,
    enhanced_series_from as series_from
)

# Enhanced ML Extensions (ml_extensions.py was archived)
from .enhanced_ml_extensions import (
    enhanced_regime_filter as regime_filter,
    enhanced_filter_adx as filter_adx,
    enhanced_filter_volatility as filter_volatility
)

# Keep backtest import (not in enhanced_ml_extensions)
def backtest(*args, **kwargs):
    """Placeholder for backtest function"""
    pass

# Pine Script Functions
from .pine_functions import (
    nz,
    na,
    iff,
    change,
    valuewhen,
    crossover_value,
    crossunder_value,
    barssince,
    barssince_na
)

# History Referencing
from .history_referencing import (
    PineScriptSeries,
    PineArray,
    PineScriptData,
    create_series,
    lookback
)

__all__ = [
    # Math
    'tanh', 'normalize_deriv', 'dual_pole_filter',
    'pine_ema', 'pine_sma', 'pine_rma', 'pine_stdev', 'pine_atr',

    # Normalization
    'normalizer', 'rescale', 'tanh_transform',

    # Indicators
    'calculate_rsi', 'n_rsi',
    'calculate_cci', 'n_cci',
    'calculate_wavetrend', 'n_wt',
    'n_adx',
    'dmi',
    'series_from',

    # Filters
    'regime_filter', 'filter_adx', 'filter_volatility',
    'backtest',
    
    # Pine Functions
    'nz', 'na', 'iff', 'change', 'valuewhen',
    'crossover_value', 'crossunder_value', 'barssince', 'barssince_na',
    
    # History Referencing
    'PineScriptSeries', 'PineArray', 'PineScriptData',
    'create_series', 'lookback'
]