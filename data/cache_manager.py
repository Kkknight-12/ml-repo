"""
Market Data Cache Manager using SQLite
Stores historical data locally to avoid repeated API calls
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os
import logging

logger = logging.getLogger(__name__)


class MarketDataCache:
    """
    Manages local caching of market data using SQLite database
    
    Features:
    - Automatic data merging when fetching overlapping periods
    - Incremental updates (only fetch missing data)
    - Support for multiple timeframes
    - No external database needed (SQLite is file-based)
    """
    
    def __init__(self, cache_dir: str = "data_cache"):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory to store the SQLite database
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        self.db_path = os.path.join(cache_dir, "market_data.db")
        self._init_database()
        
    def _init_database(self):
        """Create database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    symbol TEXT NOT NULL,
                    date TIMESTAMP NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER,
                    interval TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, date, interval)
                )
            """)
            
            # Create indexes for faster queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_date 
                ON market_data(symbol, date, interval)
            """)
            
            # Metadata table to track data ranges
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    first_date TIMESTAMP,
                    last_date TIMESTAMP,
                    total_records INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, interval)
                )
            """)
            
            conn.commit()
    
    def get_cached_data(self, symbol: str, from_date: datetime, 
                       to_date: datetime, interval: str = "day") -> Optional[pd.DataFrame]:
        """
        Get data from cache for the specified date range
        
        Args:
            symbol: Stock symbol
            from_date: Start date
            to_date: End date
            interval: Time interval (day, 5minute, etc.)
            
        Returns:
            DataFrame with cached data or None if no data found
        """
        query = """
            SELECT date, open, high, low, close, volume
            FROM market_data
            WHERE symbol = ? AND interval = ?
                AND date >= ? AND date <= ?
            ORDER BY date
        """
        
        # Convert datetime objects to strings for SQLite
        from_date_str = from_date.strftime('%Y-%m-%d %H:%M:%S') if isinstance(from_date, datetime) else str(from_date)
        to_date_str = to_date.strftime('%Y-%m-%d %H:%M:%S') if isinstance(to_date, datetime) else str(to_date)
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(
                query, 
                conn,
                params=(symbol, interval, from_date_str, to_date_str),
                parse_dates=['date']
            )
        
        if df.empty:
            return None
            
        logger.info(f"Loaded {len(df)} cached records for {symbol} ({interval})")
        return df
    
    def save_data(self, symbol: str, data: pd.DataFrame, interval: str = "day"):
        """
        Save data to cache, handling duplicates and merging
        
        Args:
            symbol: Stock symbol
            data: DataFrame with columns [date, open, high, low, close, volume]
            interval: Time interval
        """
        if data.empty:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            # Prepare data for insertion
            data_to_insert = data.copy()
            data_to_insert['symbol'] = symbol
            data_to_insert['interval'] = interval
            
            # Insert data, replacing duplicates
            # Convert date to string format for SQLite
            data_to_insert['date'] = data_to_insert['date'].astype(str)
            
            # Insert with REPLACE to handle duplicates
            for _, row in data_to_insert.iterrows():
                conn.execute("""
                    INSERT OR REPLACE INTO market_data 
                    (symbol, date, interval, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (row['symbol'], row['date'], row['interval'], 
                      row['open'], row['high'], row['low'], row['close'], row['volume']))
            
            # Update metadata
            self._update_metadata(conn, symbol, interval)
            
        logger.info(f"Saved {len(data)} records for {symbol} ({interval}) to cache")
    
    def get_missing_date_ranges(self, symbol: str, from_date: datetime,
                               to_date: datetime, interval: str = "day") -> List[tuple]:
        """
        Identify missing date ranges in cached data
        
        Returns:
            List of (start_date, end_date) tuples for missing data
        """
        # Get metadata
        metadata = self._get_metadata(symbol, interval)
        
        if not metadata:
            # No cached data, need everything
            return [(from_date, to_date)]
        
        cached_first_date = metadata['first_date']
        cached_last_date = metadata['last_date']
        
        missing_ranges = []
        
        # Ensure both dates have the same timezone awareness for comparison
        # If cached dates have timezone info, ensure from_date/to_date also have it
        if cached_first_date.tzinfo is not None and from_date.tzinfo is None:
            # Make from_date/to_date timezone-aware (assume same timezone as cached data)
            from_date = from_date.replace(tzinfo=cached_first_date.tzinfo)
            to_date = to_date.replace(tzinfo=cached_first_date.tzinfo)
        elif cached_first_date.tzinfo is None and from_date.tzinfo is not None:
            # Make from_date/to_date timezone-naive
            from_date = from_date.replace(tzinfo=None)
            to_date = to_date.replace(tzinfo=None)
        
        # Check if we need data before cached range
        if from_date < cached_first_date:
            missing_ranges.append((from_date, cached_first_date - timedelta(days=1)))
        
        # Check if we need data after cached range
        if to_date > cached_last_date:
            missing_ranges.append((cached_last_date + timedelta(days=1), to_date))
        
        # For now, we assume no gaps in the middle
        # Could be enhanced to detect and fill gaps
        
        return missing_ranges
    
    def merge_and_get_data(self, symbol: str, from_date: datetime,
                          to_date: datetime, interval: str,
                          fetch_function) -> pd.DataFrame:
        """
        Smart data fetching with caching
        
        1. Check what's in cache
        2. Identify missing ranges
        3. Fetch only missing data
        4. Merge and return complete dataset
        
        Args:
            fetch_function: Function to fetch data from API
                           Should accept (symbol, from_date, to_date, interval)
        """
        # Check cache first
        cached_data = self.get_cached_data(symbol, from_date, to_date, interval)
        
        # Identify missing ranges
        missing_ranges = self.get_missing_date_ranges(symbol, from_date, to_date, interval)
        
        if not missing_ranges:
            # All data is cached
            logger.info(f"All data for {symbol} is already cached - no API calls needed")
            return cached_data if cached_data is not None else pd.DataFrame()
        
        # Fetch missing data
        all_new_data = []
        for start_date, end_date in missing_ranges:
            logger.info(f"Fetching missing data for {symbol} from {start_date.date()} to {end_date.date()}")
            new_data = fetch_function(symbol, start_date, end_date, interval)
            if not new_data.empty:
                logger.info(f"Received {len(new_data)} records from API")
                all_new_data.append(new_data)
                self.save_data(symbol, new_data, interval)
            else:
                logger.warning(f"No data received from API for {symbol} {start_date.date()} to {end_date.date()}")
        
        # Combine all data
        if all_new_data:
            new_df = pd.concat(all_new_data, ignore_index=True)
            if cached_data is not None:
                # Ensure both DataFrames have consistent timezone handling
                # Convert both to timezone-naive for consistency
                if pd.api.types.is_datetime64_any_dtype(cached_data['date']):
                    cached_data['date'] = pd.to_datetime(cached_data['date']).dt.tz_localize(None)
                if pd.api.types.is_datetime64_any_dtype(new_df['date']):
                    new_df['date'] = pd.to_datetime(new_df['date']).dt.tz_localize(None)
                
                # Merge cached and new data
                combined = pd.concat([cached_data, new_df], ignore_index=True)
                # Remove duplicates, keeping last (most recent)
                combined = combined.drop_duplicates(subset=['date'], keep='last')
                combined = combined.sort_values('date').reset_index(drop=True)
                return combined
            else:
                return new_df
        else:
            return cached_data if cached_data is not None else pd.DataFrame()
    
    def _get_metadata(self, symbol: str, interval: str) -> Optional[Dict]:
        """Get cache metadata for a symbol"""
        query = """
            SELECT first_date, last_date, total_records, last_updated
            FROM cache_metadata
            WHERE symbol = ? AND interval = ?
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, (symbol, interval))
            row = cursor.fetchone()
            
        if row:
            return {
                'first_date': pd.to_datetime(row[0]),
                'last_date': pd.to_datetime(row[1]),
                'total_records': row[2],
                'last_updated': pd.to_datetime(row[3])
            }
        return None
    
    def _update_metadata(self, conn: sqlite3.Connection, symbol: str, interval: str):
        """Update cache metadata after data insertion"""
        # Get date range and count
        query = """
            SELECT MIN(date), MAX(date), COUNT(*)
            FROM market_data
            WHERE symbol = ? AND interval = ?
        """
        cursor = conn.execute(query, (symbol, interval))
        first_date, last_date, count = cursor.fetchone()
        
        # Update or insert metadata
        conn.execute("""
            INSERT OR REPLACE INTO cache_metadata 
            (symbol, interval, first_date, last_date, total_records, last_updated)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (symbol, interval, first_date, last_date, count))
        
        conn.commit()
    
    def get_cache_info(self) -> pd.DataFrame:
        """Get information about cached data"""
        query = """
            SELECT symbol, interval, first_date, last_date, 
                   total_records, last_updated
            FROM cache_metadata
            ORDER BY symbol, interval
        """
        
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn, parse_dates=['first_date', 'last_date', 'last_updated'])
    
    def clear_cache(self, symbol: Optional[str] = None, interval: Optional[str] = None):
        """
        Clear cached data
        
        Args:
            symbol: Clear only this symbol (None = all symbols)
            interval: Clear only this interval (None = all intervals)
        """
        with sqlite3.connect(self.db_path) as conn:
            if symbol and interval:
                conn.execute("DELETE FROM market_data WHERE symbol = ? AND interval = ?", 
                           (symbol, interval))
                conn.execute("DELETE FROM cache_metadata WHERE symbol = ? AND interval = ?",
                           (symbol, interval))
            elif symbol:
                conn.execute("DELETE FROM market_data WHERE symbol = ?", (symbol,))
                conn.execute("DELETE FROM cache_metadata WHERE symbol = ?", (symbol,))
            else:
                conn.execute("DELETE FROM market_data")
                conn.execute("DELETE FROM cache_metadata")
            
            conn.commit()
            
        logger.info(f"Cleared cache for symbol={symbol}, interval={interval}")