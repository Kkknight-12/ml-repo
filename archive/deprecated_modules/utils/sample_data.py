"""
Sample data generation utilities for testing
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_sample_data(num_bars=1000, trend_strength=0.1, volatility=0.02, 
                        start_price=100.0, start_date=None):
    """
    Generate sample OHLCV data for testing
    
    Args:
        num_bars: Number of bars to generate
        trend_strength: Trend component (0.1 = 10% over period)
        volatility: Random noise level
        start_price: Starting price
        start_date: Starting date (default: 2024-01-01)
    
    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume
    """
    if start_date is None:
        start_date = datetime(2024, 1, 1)
    
    # Generate timestamps
    timestamps = [start_date + timedelta(minutes=5*i) for i in range(num_bars)]
    
    # Generate price data with trend and noise
    prices = []
    current_price = start_price
    
    for i in range(num_bars):
        # Add trend component
        trend = (trend_strength / num_bars) * start_price
        
        # Add cyclical component for more realistic movement
        cycle = 2 * np.sin(i * 0.1) * volatility * start_price
        
        # Add random noise
        noise = np.random.normal(0, volatility * start_price)
        
        # Update price
        current_price = current_price + trend + cycle + noise
        current_price = max(current_price, start_price * 0.5)  # Prevent negative
        
        prices.append(current_price)
    
    # Create OHLC data
    data = []
    for i, (timestamp, close_price) in enumerate(zip(timestamps, prices)):
        if i == 0:
            open_price = start_price
        else:
            open_price = prices[i-1]
        
        # Create realistic high/low
        daily_range = abs(np.random.normal(0, volatility * close_price))
        high = max(open_price, close_price) + daily_range * 0.5
        low = min(open_price, close_price) - daily_range * 0.5
        
        # Random volume
        volume = np.random.randint(100000, 500000)
        
        data.append({
            'timestamp': timestamp,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close_price, 2),
            'volume': volume
        })
    
    return pd.DataFrame(data)


def generate_trending_data(num_bars=1000, direction='up', volatility=0.01, 
                          start_price=100.0):
    """
    Generate data with a clear trend for testing
    
    Args:
        num_bars: Number of bars
        direction: 'up' or 'down'
        volatility: Noise level
        start_price: Starting price
    
    Returns:
        DataFrame with OHLCV data
    """
    trend_strength = 0.3 if direction == 'up' else -0.3
    return generate_sample_data(
        num_bars=num_bars,
        trend_strength=trend_strength,
        volatility=volatility,
        start_price=start_price
    )


def generate_ranging_data(num_bars=1000, range_size=0.1, volatility=0.02,
                         center_price=100.0):
    """
    Generate sideways/ranging market data
    
    Args:
        num_bars: Number of bars
        range_size: Size of the range (0.1 = 10%)
        volatility: Noise level
        center_price: Center of the range
    
    Returns:
        DataFrame with OHLCV data
    """
    timestamps = [datetime(2024, 1, 1) + timedelta(minutes=5*i) for i in range(num_bars)]
    
    # Generate prices that oscillate in a range
    prices = []
    for i in range(num_bars):
        # Sine wave for ranging
        position = np.sin(i * 0.05) * range_size * center_price
        noise = np.random.normal(0, volatility * center_price)
        price = center_price + position + noise
        prices.append(price)
    
    # Create OHLC
    data = []
    for i, (timestamp, close_price) in enumerate(zip(timestamps, prices)):
        if i == 0:
            open_price = center_price
        else:
            open_price = prices[i-1]
        
        daily_range = abs(np.random.normal(0, volatility * close_price))
        high = max(open_price, close_price) + daily_range * 0.3
        low = min(open_price, close_price) - daily_range * 0.3
        
        volume = np.random.randint(100000, 500000)
        
        data.append({
            'timestamp': timestamp,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close_price, 2),
            'volume': volume
        })
    
    return pd.DataFrame(data)
