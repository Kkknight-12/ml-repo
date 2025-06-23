"""
Constants from Pine Script - No modifications
These are the exact values used in the original script
"""

# Feature options - exact from Pine Script input.string options
FEATURE_OPTIONS = ["RSI", "WT", "CCI", "ADX"]

# Default feature selections
DEFAULT_FEATURES = {
    "f1": ("RSI", 14, 1),
    "f2": ("WT", 10, 11),
    "f3": ("CCI", 20, 1),
    "f4": ("ADX", 20, 2),
    "f5": ("RSI", 9, 1)
}

# Trade settings
PREDICTION_LENGTH = 4  # Hardcoded 4 bars ahead prediction

# Colors for ML prediction (we'll use these for terminal output)
COLOR_COMPRESSION_FACTOR = 1

# Display settings defaults
SHOW_BAR_COLORS = True
SHOW_BAR_PREDICTIONS = True
USE_ATR_OFFSET = False
BAR_PREDICTIONS_OFFSET = 0.0

# Filter defaults (from Pine Script)
USE_EMA_FILTER = False
EMA_PERIOD = 200
USE_SMA_FILTER = False
SMA_PERIOD = 200

# Kernel settings defaults
USE_KERNEL_FILTER = True
SHOW_KERNEL_ESTIMATE = True
USE_KERNEL_SMOOTHING = False
KERNEL_LOOKBACK = 8
KERNEL_RELATIVE_WEIGHT = 8.0
KERNEL_REGRESSION_LEVEL = 25
KERNEL_LAG = 2

# Trade stats display
SHOW_TRADE_STATS = True
USE_WORST_CASE = False