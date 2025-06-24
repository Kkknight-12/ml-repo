"""
Memory limits configuration for persistent arrays
================================================

This module defines memory limits to prevent arrays from growing 
indefinitely in production environments.
"""

# Maximum size for persistent arrays
# Pine Script typically limits arrays to 10,000 elements
MAX_ARRAY_SIZE = 10000

# Feature arrays limit (per feature)
# These store historical feature values for k-NN comparison
MAX_FEATURE_ARRAY_SIZE = 10000

# Training data array limit
# Stores historical labels for ML training
MAX_TRAINING_ARRAY_SIZE = 10000

# Prediction arrays limit (sliding window)
# These are already limited by neighbors_count (typically 8)
# But we add a safety limit
MAX_PREDICTIONS_ARRAY_SIZE = 100

# Bar data history limit
# For technical indicator calculations
MAX_BAR_HISTORY_SIZE = 5000

# Signal and entry history for flip detection
# Only needs recent history
MAX_SIGNAL_HISTORY_SIZE = 20
MAX_ENTRY_HISTORY_SIZE = 20

# Memory cleanup thresholds
# When to trigger cleanup (percentage of max size)
CLEANUP_THRESHOLD_PERCENT = 90  # Start cleanup at 90% full
CLEANUP_REMOVE_PERCENT = 10     # Remove oldest 10% of data

def should_cleanup(current_size: int, max_size: int) -> bool:
    """Check if array needs cleanup based on threshold"""
    return current_size >= (max_size * CLEANUP_THRESHOLD_PERCENT / 100)

def calculate_items_to_remove(current_size: int) -> int:
    """Calculate how many items to remove during cleanup"""
    return int(current_size * CLEANUP_REMOVE_PERCENT / 100)