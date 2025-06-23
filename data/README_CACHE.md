# Market Data Caching System

## Overview

The Market Data Cache uses SQLite to store historical market data locally, avoiding repeated API calls to Zerodha. This is especially useful when backtesting strategies over long periods or fetching data for multiple stocks.

## Features

- **Local SQLite Database**: No external database needed - just a local file
- **Automatic Data Merging**: When fetching overlapping date ranges, the system automatically merges data
- **Incremental Updates**: Only fetches missing data from the API
- **Multi-Symbol Support**: Cache data for multiple symbols and timeframes
- **Zero Configuration**: Works out of the box with sensible defaults

## Usage

### Basic Usage

```python
from data.zerodha_client import ZerodhaClient

# Initialize with cache enabled (default)
client = ZerodhaClient(use_cache=True, cache_dir="data_cache")

# Fetch data - first time hits API, subsequent calls use cache
data = client.get_historical_data("ICICIBANK", "day", days=3000)
```

### Without Cache

```python
# Disable cache if needed
client = ZerodhaClient(use_cache=False)
```

### Cache Management

```python
# Check what's in the cache
cache_info = client.get_cache_info()
print(cache_info)

# Clear cache for specific symbol/interval
client.clear_cache(symbol="ICICIBANK", interval="day")

# Clear entire cache
client.clear_cache()
```

## How It Works

1. **First Request**: When you request data, the system checks the local cache
2. **Cache Miss**: If data isn't cached, it fetches from Zerodha API in chunks (respecting 2000 bar limit)
3. **Cache Hit**: If data exists, it identifies missing ranges and only fetches those
4. **Merge & Return**: New data is merged with cached data and returned as a single dataset

## Database Schema

The SQLite database contains two tables:

### market_data
- `symbol`: Stock symbol (e.g., "ICICIBANK")
- `date`: Timestamp of the bar
- `open`, `high`, `low`, `close`: OHLC data
- `volume`: Trade volume
- `interval`: Timeframe (e.g., "day", "5minute")

### cache_metadata
- Tracks date ranges and record counts for each symbol/interval combination
- Used to quickly identify missing data ranges

## Example: Fetching 20-30 Years of Data

```python
# Fetch 20 years of daily data
data = client.get_historical_data("RELIANCE", "day", days=7300)  # ~20 years

# The first fetch will take time as it downloads from API
# Subsequent fetches are instant!

# Later, fetch 30 years (will only fetch the missing 10 years)
data = client.get_historical_data("RELIANCE", "day", days=10950)  # ~30 years
```

## Performance

- **First Fetch**: Limited by Zerodha API rate limits (3 requests/second)
- **Cached Fetch**: Near-instant (milliseconds)
- **Storage**: ~1-2 MB per year of daily data per symbol

## Tips

1. **Pre-cache Data**: Run initial fetches during off-market hours
2. **Batch Symbols**: Cache multiple symbols in one session
3. **Long-term Storage**: SQLite databases are portable - backup your cache directory
4. **Update Strategy**: Fetch recent data periodically to keep cache current

## Troubleshooting

- **Cache Location**: Default is `./data_cache/market_data.db`
- **Permissions**: Ensure write permissions for cache directory
- **Disk Space**: Monitor available disk space for large datasets
- **Rate Limits**: Respect Zerodha's 3 requests/second limit for historical data