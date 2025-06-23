"""
Zerodha Kite API Client Wrapper
Handles authentication, data fetching, and streaming
"""
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dotenv import load_dotenv
import pandas as pd

# Import our cache manager
from .cache_manager import MarketDataCache

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from kiteconnect import KiteConnect, KiteTicker

    KITE_AVAILABLE = True
except ImportError:
    logger.warning("KiteConnect not installed. Install with: pip install kiteconnect")
    KITE_AVAILABLE = False
    KiteConnect = None
    KiteTicker = None


class ZerodhaClient:
    """
    Wrapper for Zerodha Kite API
    Handles authentication and data operations
    """

    def __init__(self, use_cache: bool = True, cache_dir: str = "data_cache"):
        """
        Initialize Zerodha client with credentials from environment
        
        Args:
            use_cache: Whether to use local SQLite cache for data
            cache_dir: Directory to store SQLite database
        """
        self.api_key = os.getenv('KITE_API_KEY')
        self.api_secret = os.getenv('KITE_API_SECRET')
        self.user_id = os.getenv('KITE_USER_ID')
        self.access_token = os.getenv('KITE_ACCESS_TOKEN')
        
        # Initialize cache
        self.use_cache = use_cache
        self.cache = MarketDataCache(cache_dir) if use_cache else None

        if not KITE_AVAILABLE:
            raise ImportError("KiteConnect not installed. Run: pip install kiteconnect")

        if not self.api_key:
            raise ValueError("KITE_API_KEY not found in environment variables")

        # Initialize KiteConnect
        self.kite = KiteConnect(api_key=self.api_key)

        # Set access token if available
        if self.access_token:
            self.kite.set_access_token(self.access_token)
            logger.info("Using existing access token")

        # WebSocket client for streaming
        self.kws = None
        self.subscribed_tokens = []

        # Symbol to token mapping
        self.symbol_token_map = {}

    def generate_login_url(self) -> str:
        """
        Generate login URL for user authentication

        Returns:
            Login URL string
        """
        return self.kite.login_url()

    def complete_login(self, request_token: str) -> str:
        """
        Complete login process with request token

        Args:
            request_token: Token received after login redirect

        Returns:
            Access token for future requests
        """
        try:
            data = self.kite.generate_session(
                request_token=request_token,
                api_secret=self.api_secret
            )

            access_token = data["access_token"]
            self.access_token = access_token
            self.kite.set_access_token(access_token)

            # Save to .env file
            self._update_env_file('KITE_ACCESS_TOKEN', access_token)

            logger.info(f"Login successful for user: {data.get('user_id')}")
            return access_token

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise

    def get_instruments(self, exchange: str = "NSE") -> List[Dict]:
        """
        Get all instruments for an exchange

        Args:
            exchange: Exchange name (NSE, BSE, etc.)

        Returns:
            List of instrument dictionaries
        """
        try:
            instruments = self.kite.instruments(exchange)

            # Build symbol to token mapping
            for inst in instruments:
                symbol = inst['tradingsymbol']
                self.symbol_token_map[symbol] = inst['instrument_token']

            logger.info(f"Loaded {len(instruments)} instruments from {exchange}")
            return instruments

        except Exception as e:
            logger.error(f"Failed to get instruments: {str(e)}")
            return []

    def get_quote(self, symbols: List[str]) -> Dict:
        """
        Get current market quotes for symbols

        Args:
            symbols: List of trading symbols

        Returns:
            Dictionary of quotes
        """
        try:
            # Convert symbols to NSE:SYMBOL format
            formatted_symbols = [f"NSE:{symbol}" for symbol in symbols]
            quotes = self.kite.quote(formatted_symbols)

            # Simplify the response
            simplified_quotes = {}
            for key, data in quotes.items():
                symbol = key.split(':')[1] if ':' in key else key
                simplified_quotes[symbol] = {
                    'last_price': data.get('last_price', 0),
                    'open': data.get('ohlc', {}).get('open', 0),
                    'high': data.get('ohlc', {}).get('high', 0),
                    'low': data.get('ohlc', {}).get('low', 0),
                    'close': data.get('ohlc', {}).get('close', 0),
                    'volume': data.get('volume', 0),
                    'change': data.get('change', 0),
                    'change_percent': data.get('change', 0) / data.get('ohlc', {}).get('close', 1) * 100 if data.get(
                        'ohlc', {}).get('close', 0) > 0 else 0
                }

            return simplified_quotes

        except Exception as e:
            logger.error(f"Failed to get quotes: {str(e)}")
            return {}

    def get_historical_data(self, symbol: str, interval: str, days: int = 30) -> List[Dict]:
        """
        Get historical data for a symbol with caching support

        Args:
            symbol: Trading symbol
            interval: Candle interval (minute, 3minute, 5minute, 15minute, 30minute, 60minute, day)
            days: Number of days of history

        Returns:
            List of candle dictionaries
        """
        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        
        # If cache is enabled, use merge_and_get_data
        if self.use_cache and self.cache:
            logger.info(f"Using cache for {symbol} data")
            
            # Define fetch function for cache manager
            def fetch_missing_data(sym: str, start: datetime, end: datetime, intv: str) -> pd.DataFrame:
                """Fetch data from Zerodha API and convert to DataFrame"""
                try:
                    # Get instrument token
                    if sym not in self.symbol_token_map:
                        self.get_instruments()
                    
                    instrument_token = self.symbol_token_map.get(sym)
                    if not instrument_token:
                        logger.error(f"Instrument token not found for {sym}")
                        return pd.DataFrame()
                    
                    # Fetch data in chunks (Zerodha has 2000 bar limit)
                    all_data = []
                    current_end = end
                    
                    while current_end > start:
                        # Calculate chunk start (max 2000 bars back)
                        if intv == "day":
                            chunk_start = max(start, current_end - timedelta(days=2000))
                        elif intv == "minute":
                            chunk_start = max(start, current_end - timedelta(minutes=2000))
                        elif intv == "3minute":
                            chunk_start = max(start, current_end - timedelta(minutes=6000))
                        elif intv == "5minute":
                            chunk_start = max(start, current_end - timedelta(minutes=10000))
                        elif intv == "15minute":
                            chunk_start = max(start, current_end - timedelta(minutes=30000))
                        elif intv == "30minute":
                            chunk_start = max(start, current_end - timedelta(minutes=60000))
                        elif intv == "60minute":
                            chunk_start = max(start, current_end - timedelta(hours=2000))
                        else:
                            chunk_start = max(start, current_end - timedelta(days=100))
                        
                        # Fetch chunk
                        logger.info(f"Fetching chunk from {chunk_start} to {current_end}")
                        chunk_data = self.kite.historical_data(
                            instrument_token=instrument_token,
                            from_date=chunk_start,
                            to_date=current_end,
                            interval=intv
                        )
                        
                        if chunk_data:
                            all_data.extend(chunk_data)
                            # Move to next chunk
                            current_end = chunk_start - timedelta(seconds=1)
                        else:
                            break
                        
                        # Add small delay to respect rate limits
                        time.sleep(0.3)
                    
                    # Convert to DataFrame
                    if all_data:
                        df = pd.DataFrame(all_data)
                        df['date'] = pd.to_datetime(df['date'])
                        return df
                    
                    return pd.DataFrame()
                    
                except Exception as e:
                    logger.error(f"Failed to fetch data: {str(e)}")
                    return pd.DataFrame()
            
            # Get data from cache (will fetch missing data automatically)
            df = self.cache.merge_and_get_data(
                symbol=symbol,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                fetch_function=fetch_missing_data
            )
            
            # Convert DataFrame back to list of dicts for compatibility
            if not df.empty:
                return df.to_dict('records')
            return []
        
        # Original implementation without cache
        try:
            # Get instrument token
            if symbol not in self.symbol_token_map:
                self.get_instruments()

            instrument_token = self.symbol_token_map.get(symbol)
            if not instrument_token:
                logger.error(f"Instrument token not found for {symbol}")
                return []

            # Fetch historical data
            data = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )

            logger.info(f"Fetched {len(data)} candles for {symbol}")
            return data

        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {str(e)}")
            return []

    def start_websocket(self, on_tick: Callable, on_connect: Callable = None,
                        on_close: Callable = None, on_error: Callable = None):
        """
        Start WebSocket for real-time data streaming

        Args:
            on_tick: Callback for tick data
            on_connect: Callback for connection established
            on_close: Callback for connection closed
            on_error: Callback for errors
        """
        try:
            # Initialize KiteTicker
            self.kws = KiteTicker(self.api_key, self.access_token)

            # Assign callbacks
            self.kws.on_ticks = on_tick
            self.kws.on_connect = on_connect or self._on_connect
            self.kws.on_close = on_close or self._on_close
            self.kws.on_error = on_error or self._on_error

            # Connect
            self.kws.connect(threaded=True)
            logger.info("WebSocket connection initiated")

        except Exception as e:
            logger.error(f"Failed to start WebSocket: {str(e)}")
            raise

    def subscribe_symbols(self, symbols: List[str], mode: str = "full"):
        """
        Subscribe to real-time data for symbols

        Args:
            symbols: List of trading symbols
            mode: Subscription mode (ltp, quote, full)
        """
        if not self.kws:
            logger.error("WebSocket not initialized")
            return

        # Get tokens for symbols
        tokens = []
        for symbol in symbols:
            if symbol in self.symbol_token_map:
                tokens.append(self.symbol_token_map[symbol])
            else:
                logger.warning(f"Token not found for {symbol}")

        if tokens:
            # Subscribe
            self.kws.subscribe(tokens)

            # Set mode
            if mode == "full":
                self.kws.set_mode(self.kws.MODE_FULL, tokens)
            elif mode == "quote":
                self.kws.set_mode(self.kws.MODE_QUOTE, tokens)
            else:
                self.kws.set_mode(self.kws.MODE_LTP, tokens)

            self.subscribed_tokens.extend(tokens)
            logger.info(f"Subscribed to {len(tokens)} symbols in {mode} mode")

    def unsubscribe_symbols(self, symbols: List[str]):
        """Unsubscribe from real-time data for symbols"""
        if not self.kws:
            return

        tokens = []
        for symbol in symbols:
            if symbol in self.symbol_token_map:
                token = self.symbol_token_map[symbol]
                if token in self.subscribed_tokens:
                    tokens.append(token)
                    self.subscribed_tokens.remove(token)

        if tokens:
            self.kws.unsubscribe(tokens)
            logger.info(f"Unsubscribed from {len(tokens)} symbols")

    def stop_websocket(self):
        """Stop WebSocket connection"""
        if self.kws:
            self.kws.stop()
            logger.info("WebSocket connection stopped")

    def _on_connect(self, ws, response):
        """Default WebSocket connect callback"""
        logger.info("WebSocket connected")

    def _on_close(self, ws, code, reason):
        """Default WebSocket close callback"""
        logger.info(f"WebSocket closed: {code} - {reason}")

    def _on_error(self, ws, code, reason):
        """Default WebSocket error callback"""
        logger.error(f"WebSocket error: {code} - {reason}")

    def _update_env_file(self, key: str, value: str):
        """Update .env file with new value"""
        try:
            # Read existing content
            env_path = '.env'
            lines = []

            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()

            # Update or add the key
            updated = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    updated = True
                    break

            if not updated:
                lines.append(f"{key}={value}\n")

            # Write back
            with open(env_path, 'w') as f:
                f.writelines(lines)

        except Exception as e:
            logger.error(f"Failed to update .env file: {str(e)}")

    def get_margins(self) -> Dict:
        """Get account margins"""
        try:
            return self.kite.margins()
        except Exception as e:
            logger.error(f"Failed to get margins: {str(e)}")
            return {}

    def get_positions(self) -> Dict:
        """Get current positions"""
        try:
            return self.kite.positions()
        except Exception as e:
            logger.error(f"Failed to get positions: {str(e)}")
            return {"net": [], "day": []}

    def get_api_limits(self):
        """
        Get API usage information
        Note: Zerodha doesn't provide exact credits, but we can check limits
        """
        try:
            # Get profile to check if API is working
            profile = self.kite.profile()
            
            print("\n=== Zerodha API Status ===")
            print(f"✓ API Active: Yes")
            print(f"User: {profile.get('user_name', 'N/A')}")
            print(f"Email: {profile.get('email', 'N/A')}")
            
            # Check data subscriptions
            print(f"\nData Subscriptions:")
            exchanges = profile.get('exchanges', [])
            print(f"Exchanges: {', '.join(exchanges)}")
            
            # Order types allowed
            order_types = profile.get('order_types', [])
            print(f"\nOrder Types: {', '.join(order_types)}")
            
            # Products allowed
            products = profile.get('products', [])
            print(f"Products: {', '.join(products)}")
            
            print("\n=== API Limits (Zerodha Standard) ===")
            print("Quote API: 1 request/second")
            print("Order API: 10 requests/second")  
            print("Historical API: 3 requests/second")
            print("WebSocket: 3000 instruments max")
            print("\nNote: No daily limit, only rate limits apply")
            
            return True
            
        except Exception as e:
            print(f"❌ API Error: {str(e)}")
            return False

    def check_historical_access(self):
        """Check if historical data API is accessible"""
        try:
            # Try fetching 1 day data
            print("\nChecking Historical Data API access...")
            test_data = self.get_historical_data("RELIANCE", "day", days=1)
            if test_data:
                print("✓ Historical Data API: Active")
                print(f"  Test data fetched: {len(test_data)} candles")
                return True
            else:
                print("⚠️ Historical Data API: No data returned")
                return False
        except Exception as e:
            if "Insufficient" in str(e) or "subscription" in str(e).lower():
                print("❌ Historical Data API: Not subscribed (₹2000/month required)")
            else:
                print(f"❌ Historical Data API Error: {str(e)}")
            return False

    def get_api_usage_summary(self):
        """Display a summary of API usage and limits"""
        print("\n" + "=" * 60)
        print("ZERODHA API USAGE SUMMARY")
        print("=" * 60)
        
        # Check API status
        self.get_api_limits()
        
        # Check historical data access
        self.check_historical_access()
        
        print("\n" + "=" * 60)
        print("\nTip: Run this periodically to monitor your API status")
        print("=" * 60)
    
    def get_cache_info(self) -> pd.DataFrame:
        """Get information about cached data"""
        if self.cache:
            return self.cache.get_cache_info()
        else:
            logger.warning("Cache is not enabled")
            return pd.DataFrame()
    
    def clear_cache(self, symbol: Optional[str] = None, interval: Optional[str] = None):
        """Clear cached data for a symbol or all data"""
        if self.cache:
            self.cache.clear_cache(symbol, interval)
            logger.info(f"Cache cleared for symbol={symbol}, interval={interval}")
        else:
            logger.warning("Cache is not enabled")