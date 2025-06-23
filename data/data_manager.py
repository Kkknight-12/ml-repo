"""
Data Manager - Bridges Zerodha data with Bar Processor
Handles real-time and historical data processing
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
from collections import defaultdict

from data.zerodha_client import ZerodhaClient
from scanner.bar_processor import BarProcessor, BarResult
from config.settings import TradingConfig

logger = logging.getLogger(__name__)


class DataManager:
    """
    Manages data flow between Zerodha and trading system
    Maintains bar processors for multiple stocks
    """

    def __init__(self, config: TradingConfig, zerodha_client: ZerodhaClient):
        """
        Initialize data manager

        Args:
            config: Trading configuration
            zerodha_client: Initialized Zerodha client
        """
        self.config = config
        self.zerodha = zerodha_client

        # Bar processors for each symbol
        self.processors: Dict[str, BarProcessor] = {}

        # Current day's OHLCV data for each symbol
        self.current_candles: Dict[str, Dict] = defaultdict(dict)

        # Callback for signals
        self.on_signal_callback: Optional[Callable] = None

        # Track last update time for each symbol
        self.last_update_time: Dict[str, datetime] = {}
        
        # API call counter
        self.api_call_counter = {
            'quotes': 0,
            'historical': 0,
            'total': 0
        }

    def initialize_symbol(self, symbol: str) -> BarProcessor:
        """
        Initialize bar processor for a symbol

        Args:
            symbol: Trading symbol

        Returns:
            Initialized BarProcessor
        """
        if symbol not in self.processors:
            # Create processor with symbol and timeframe for stateful indicators
            processor = BarProcessor(
                self.config,
                symbol=symbol,
                timeframe=self.config.scan_interval,
                use_enhanced=True  # Use enhanced stateful indicators
            )
            self.processors[symbol] = processor
            logger.info(f"Initialized processor for {symbol} with enhanced indicators")

            # Load historical data to warm up
            self._load_historical_data(symbol, processor)

        return self.processors[symbol]

    def _load_historical_data(self, symbol: str, processor: BarProcessor):
        """
        Load historical data to warm up the processor

        Args:
            symbol: Trading symbol
            processor: Bar processor instance
        """
        try:
            print(f"Loading historical data for {symbol}...")
            
            # Fetch historical data
            # For intraday: 5minute candles for last 30 days
            # For daily: day candles for last 100 days

            if self.config.scan_interval == "5minute":
                historical = self.zerodha.get_historical_data(
                    # symbol, "5minute", days=30
                    symbol, "5minute", days=5 # Change to days=5
                )
                self.api_call_counter['historical'] += 1
                self.api_call_counter['total'] += 1
            else:
                historical = self.zerodha.get_historical_data(
                    symbol, "day", days=100
                )
                self.api_call_counter['historical'] += 1
                self.api_call_counter['total'] += 1

            # Process historical bars
            processed = 0
            total_bars = len(historical) if historical else 0
            
            # Note: Enhanced indicators handle state automatically
            # No need to set total_bars with stateful implementation
            logger.info(f"Processing {total_bars} historical bars for {symbol}")
            
            for candle in historical:
                result = processor.process_bar(
                    candle['open'],
                    candle['high'],
                    candle['low'],
                    candle['close'],
                    candle.get('volume', 0)
                )
                processed += 1
                
                # Show progress every 100 bars
                if processed % 100 == 0:
                    print(f"  {symbol}: {processed}/{total_bars} bars processed...")

            logger.info(f"Loaded {processed} historical bars for {symbol}, indicators now stateful")
            print(f"✓ {symbol} ready! ({processed} bars loaded, indicators warmed up)")

        except Exception as e:
            logger.error(f"Failed to load historical data for {symbol}: {str(e)}")
            print(f"❌ Error loading {symbol}: {str(e)}")

    def process_tick(self, tick_data: Dict):
        """
        Process real-time tick data

        Args:
            tick_data: Tick data from Zerodha WebSocket
        """
        try:
            # Extract symbol from token
            symbol = self._get_symbol_from_token(tick_data.get('instrument_token'))
            if not symbol:
                return

            # Initialize processor if needed
            if symbol not in self.processors:
                self.initialize_symbol(symbol)

            # Update current candle
            self._update_current_candle(symbol, tick_data)

            # Check if candle is complete (for intraday)
            if self._is_candle_complete(symbol):
                # Process completed candle
                candle = self.current_candles[symbol]
                processor = self.processors[symbol]

                result = processor.process_bar(
                    candle['open'],
                    candle['high'],
                    candle['low'],
                    candle['close'],
                    candle['volume']
                )

                # Check for signals
                self._check_signals(symbol, result)

                # Reset candle
                self._reset_candle(symbol)

        except Exception as e:
            logger.error(f"Error processing tick: {str(e)}")

    def process_quote(self, symbol: str, quote_data: Dict):
        """
        Process quote data (alternative to tick for less frequent updates)

        Args:
            symbol: Trading symbol
            quote_data: Quote data from API
        """
        try:
            if symbol not in self.processors:
                self.initialize_symbol(symbol)

            processor = self.processors[symbol]

            # Create bar from quote
            result = processor.process_bar(
                quote_data['open'],
                quote_data['high'],
                quote_data['low'],
                quote_data['last_price'],  # Use last_price as close
                quote_data['volume']
            )

            # Check for signals
            self._check_signals(symbol, result)

        except Exception as e:
            logger.error(f"Error processing quote for {symbol}: {str(e)}")

    def _update_current_candle(self, symbol: str, tick_data: Dict):
        """Update current candle with tick data"""
        ltp = tick_data.get('last_price', 0)
        volume = tick_data.get('volume', 0)
        timestamp = tick_data.get('timestamp', datetime.now())

        if symbol not in self.current_candles or not self.current_candles[symbol]:
            # Initialize new candle
            self.current_candles[symbol] = {
                'open': ltp,
                'high': ltp,
                'low': ltp,
                'close': ltp,
                'volume': volume,
                'start_time': timestamp
            }
        else:
            # Update existing candle
            candle = self.current_candles[symbol]
            candle['high'] = max(candle['high'], ltp)
            candle['low'] = min(candle['low'], ltp)
            candle['close'] = ltp
            candle['volume'] = volume

    def _is_candle_complete(self, symbol: str) -> bool:
        """Check if current candle is complete"""
        if symbol not in self.current_candles:
            return False

        candle = self.current_candles[symbol]
        if 'start_time' not in candle:
            return False

        # For 5-minute candles
        if self.config.scan_interval == "5minute":
            current_time = datetime.now()
            start_time = candle['start_time']

            # Check if 5 minutes have passed
            time_diff = (current_time - start_time).total_seconds()
            return time_diff >= 300  # 5 minutes

        # For daily candles, return False (process at end of day)
        return False

    def _reset_candle(self, symbol: str):
        """Reset candle data for symbol"""
        self.current_candles[symbol] = {}

    def _check_signals(self, symbol: str, result: BarResult):
        """Check for trading signals and trigger callback"""
        if result.start_long_trade or result.start_short_trade:
            signal_data = {
                'symbol': symbol,
                'type': 'BUY' if result.start_long_trade else 'SELL',
                'price': result.close,
                'prediction': result.prediction,
                'strength': result.prediction_strength,
                'filters': result.filter_states,
                'timestamp': datetime.now()
            }

            logger.info(f"Signal generated for {symbol}: {signal_data['type']} at {signal_data['price']}")

            # Trigger callback
            if self.on_signal_callback:
                self.on_signal_callback(signal_data)

    def _get_symbol_from_token(self, token: int) -> Optional[str]:
        """Get symbol from instrument token"""
        # Reverse lookup from symbol_token_map
        for symbol, inst_token in self.zerodha.symbol_token_map.items():
            if inst_token == token:
                return symbol
        return None

    def scan_all_symbols(self, symbols: List[str]):
        """
        Scan all symbols for signals (used for periodic scanning)

        Args:
            symbols: List of symbols to scan
        """
        logger.info(f"Scanning {len(symbols)} symbols...")
        print(f"\nScanning {len(symbols)} stocks...")

        # Get quotes for all symbols
        quotes = self.zerodha.get_quote(symbols)
        self.api_call_counter['quotes'] += 1
        self.api_call_counter['total'] += 1

        # Process each quote
        signals_found = 0
        for i, (symbol, quote) in enumerate(quotes.items()):
            if quote:
                print(f"\n[{i+1}/{len(symbols)}] Processing {symbol}...")
                self.process_quote(symbol, quote)

                # Check if signal was generated
                if symbol in self.processors:
                    processor = self.processors[symbol]
                    if hasattr(processor, 'last_signal_generated'):
                        signals_found += 1

        logger.info(f"Scan complete. Found {signals_found} signals.")

    def get_processor_stats(self, symbol: str) -> Dict:
        """Get statistics for a symbol's processor"""
        if symbol not in self.processors:
            return {}

        processor = self.processors[symbol]
        ml_model = processor.ml_model

        return {
            'symbol': symbol,
            'bars_processed': processor.bars.bar_index,
            'current_signal': ml_model.signal,
            'last_prediction': ml_model.prediction,
            'neighbors_used': len(ml_model.predictions),
            'prediction_strength': ml_model.get_prediction_strength()
        }

    def set_signal_callback(self, callback: Callable):
        """Set callback function for signals"""
        self.on_signal_callback = callback

    def get_api_call_stats(self) -> Dict[str, int]:
        """Get API call statistics"""
        return self.api_call_counter.copy()
    
    def reset_api_counter(self):
        """Reset API call counter"""
        self.api_call_counter = {
            'quotes': 0,
            'historical': 0,
            'total': 0
        }