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

# Indicators
from .indicators import (
    calculate_rsi,
    n_rsi,
    calculate_cci,
    n_cci,
    calculate_wavetrend,
    n_wt,
    calculate_adx,
    n_adx,
    dmi,
    series_from
)

# ML Extensions
from .ml_extensions import (
    regime_filter,
    filter_adx,
    filter_volatility,
    backtest
)

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
    'calculate_adx', 'n_adx',
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