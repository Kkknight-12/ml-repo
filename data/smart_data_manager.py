"""
Smart Data Manager - Reusable component for efficient market data management
============================================================================

Features:
- Intelligent caching with SQLite
- Automatic incremental updates
- Data quality analysis
- Multi-stock batch operations
- Support for multiple timeframes
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from data.cache_manager import MarketDataCache
from data.zerodha_client import ZerodhaClient

logger = logging.getLogger(__name__)


class SmartDataManager:
    """
    Intelligent data manager that handles caching, fetching, and analysis
    """
    
    def __init__(self, cache_dir: str = "data_cache", use_cache: bool = True):
        """Initialize with cache manager and Zerodha client"""
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        self.cache = MarketDataCache(cache_dir)
        self.kite_client = None
        self._initialize_zerodha()
        
    def _initialize_zerodha(self) -> bool:
        """Initialize Zerodha connection if credentials available"""
        try:
            # Check for saved session
            if os.path.exists('.kite_session.json'):
                with open('.kite_session.json', 'r') as f:
                    session_data = json.load(f)
                    access_token = session_data.get('access_token')
                    
                if access_token:
                    os.environ['KITE_ACCESS_TOKEN'] = access_token
                    # Initialize with caching enabled
                    self.kite_client = ZerodhaClient(use_cache=self.use_cache, cache_dir=self.cache_dir)
                    logger.info("Zerodha client initialized with smart caching")
                    return True
            
            logger.warning("No Zerodha credentials found - will use cached data only")
            return False
            
        except ImportError:
            logger.warning("KiteConnect not installed - will use cached data only")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Zerodha: {e}")
            return False
    
    def get_data(self, symbol: str, days: int = 90, 
                 interval: str = "5minute") -> Optional[pd.DataFrame]:
        """
        Get data with intelligent caching
        
        Args:
            symbol: Stock symbol
            days: Number of days to fetch
            interval: Timeframe (5minute, day, etc.)
            
        Returns:
            DataFrame with OHLCV data
        """
        # If we have Zerodha client, use its smart caching
        if self.kite_client:
            try:
                # This will automatically:
                # 1. Check cache for existing data
                # 2. Fetch only missing data from API
                # 3. Merge and return complete dataset
                data = self.kite_client.get_historical_data(
                    symbol=symbol,
                    interval=interval,
                    days=days
                )
                
                if data:
                    df = pd.DataFrame(data)
                    df['date'] = pd.to_datetime(df['date'])
                    # Remove timezone info for consistency
                    if df['date'].dt.tz is not None:
                        df['date'] = df['date'].dt.tz_localize(None)
                    df = df.sort_values('date').reset_index(drop=True)
                    
                    # Set date as index for consistency
                    df.set_index('date', inplace=True)
                    
                    logger.info(f"Got {len(df)} bars for {symbol} ({interval})")
                    return df
                    
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
        
        # Fallback to direct cache access if no Zerodha client
        logger.info(f"Using cache-only mode for {symbol}")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get cached data
        df = self.cache.get_cached_data(symbol, start_date, end_date, interval)
        
        if df is not None and len(df) > 0:
            logger.info(f"Found {len(df)} cached bars for {symbol} ({interval})")
            # Remove timezone info for consistency
            if df['date'].dt.tz is not None:
                df['date'] = df['date'].dt.tz_localize(None)
            # Set date as index
            df.set_index('date', inplace=True)
            return df
        
        logger.warning(f"No data available for {symbol}")
        return None
    
    def get_multi_stock_data(self, symbols: List[str], 
                            days: int = 90,
                            interval: str = "5minute") -> Dict[str, pd.DataFrame]:
        """
        Get data for multiple stocks efficiently
        
        Args:
            symbols: List of stock symbols
            days: Number of days to fetch
            interval: Timeframe
            
        Returns:
            Dictionary of symbol -> DataFrame
        """
        results = {}
        
        for symbol in symbols:
            logger.info(f"Fetching data for {symbol}...")
            df = self.get_data(symbol, days, interval)
            if df is not None:
                results[symbol] = df
            else:
                logger.warning(f"Failed to get data for {symbol}")
        
        return results
    
    def analyze_price_movement(self, df: pd.DataFrame, 
                              holding_periods: List[int] = [1, 5, 10, 20]) -> Dict:
        """
        Analyze historical price movements for risk/reward calibration
        
        Args:
            df: DataFrame with OHLCV data
            holding_periods: List of bar periods to analyze
            
        Returns:
            Dictionary with movement statistics
        """
        if df is None or len(df) < max(holding_periods) + 1:
            return {}
        
        stats = {}
        
        # Ensure we have the required columns
        if 'close' not in df.columns and 'close' in df.index.names:
            df = df.reset_index()
        
        for period in holding_periods:
            # Calculate forward returns
            df[f'return_{period}'] = df['close'].shift(-period) / df['close'] - 1
            
            # Maximum favorable excursion (MFE) - best possible outcome
            mfe_list = []
            # Maximum adverse excursion (MAE) - worst possible outcome  
            mae_list = []
            
            for i in range(len(df) - period):
                # Get price range over next 'period' bars
                future_highs = df['high'].iloc[i+1:i+period+1]
                future_lows = df['low'].iloc[i+1:i+period+1]
                entry_price = df['close'].iloc[i]
                
                # MFE for long position
                max_high = future_highs.max()
                mfe = (max_high - entry_price) / entry_price
                mfe_list.append(mfe)
                
                # MAE for long position
                min_low = future_lows.min()
                mae = (min_low - entry_price) / entry_price
                mae_list.append(mae)
            
            # Calculate statistics
            stats[f'period_{period}'] = {
                'avg_return': df[f'return_{period}'].mean() * 100,
                'std_return': df[f'return_{period}'].std() * 100,
                'mfe_mean': np.mean(mfe_list) * 100,
                'mfe_50': np.percentile(mfe_list, 50) * 100,
                'mfe_70': np.percentile(mfe_list, 70) * 100,
                'mfe_90': np.percentile(mfe_list, 90) * 100,
                'mae_mean': np.mean(mae_list) * 100,
                'mae_50': np.percentile(mae_list, 50) * 100,
                'mae_30': np.percentile(mae_list, 30) * 100,
                'mae_10': np.percentile(mae_list, 10) * 100,
            }
        
        # Add general statistics
        stats['general'] = {
            'total_bars': len(df),
            'avg_range_pct': ((df['high'] - df['low']) / df['close']).mean() * 100,
            'avg_volume': df['volume'].mean() if 'volume' in df.columns else 0
        }
        
        # For adaptive configuration
        stats['avg_range_pct'] = stats['general']['avg_range_pct']
        stats['mfe_long_50_pct'] = stats['period_5']['mfe_50'] if 'period_5' in stats else 0.2
        stats['mfe_long_70_pct'] = stats['period_5']['mfe_70'] if 'period_5' in stats else 0.3
        stats['mfe_long_90_pct'] = stats['period_5']['mfe_90'] if 'period_5' in stats else 0.5
        stats['mae_long_50_pct'] = abs(stats['period_5']['mae_50']) if 'period_5' in stats else 0.2
        
        return stats
    
    def get_cache_info(self) -> pd.DataFrame:
        """Get information about cached data"""
        return self.cache.get_cache_info()
    
    def clear_cache(self, symbol: Optional[str] = None, interval: Optional[str] = None):
        """Clear cache for specific symbol/interval or all"""
        if symbol:
            logger.warning(f"Clearing cache for {symbol} {interval or 'all intervals'}")
            # This would need to be implemented in cache_manager
        else:
            logger.warning("Clearing entire cache")
            # This would need to be implemented in cache_manager
    
    def _estimate_bars(self, start_date: datetime, end_date: datetime, 
                      interval: str) -> int:
        """Estimate expected number of bars for a date range"""
        days = (end_date - start_date).days
        
        if interval == "day":
            # Roughly 250 trading days per year
            return int(days * 250 / 365)
        elif interval == "5minute":
            # 75 bars per day (375 minutes / 5)
            trading_days = int(days * 250 / 365)
            return trading_days * 75
        elif interval == "15minute":
            # 25 bars per day
            trading_days = int(days * 250 / 365)
            return trading_days * 25
        elif interval == "60minute":
            # 6-7 bars per day
            trading_days = int(days * 250 / 365)
            return trading_days * 6
        else:
            # Default estimate
            return days