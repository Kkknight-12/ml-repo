"""
Live Scanner - Scans multiple stocks in real-time
Main application for live trading signals
"""
import os
import sys
import time
import logging
import threading
from datetime import datetime
from typing import List, Dict, Optional

from config.settings import TradingConfig
from data.zerodha_client import ZerodhaClient
from data.data_manager import DataManager
from utils.notifications import NotificationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiveScanner:
    """
    Main scanner application
    Coordinates data fetching, processing, and notifications
    """

    def __init__(self, config: TradingConfig = None):
        """Initialize scanner with configuration"""
        self.config = config or TradingConfig()

        # Initialize components
        self.zerodha = None
        self.data_manager = None
        self.notifier = NotificationManager()

        # Stock lists
        # self.nifty_50 = self._load_stock_list('NIFTY_50_SYMBOLS')
        # self.volatile_stocks = self._load_stock_list('VOLATILE_STOCKS')
        self.primary_stocks = self._load_stock_list('PRIMARY_SCAN')
        self.momentum_stocks = self._load_stock_list('MOMENTUM_SCAN')
        self.active_symbols = []

        # Scanner state
        self.is_running = False
        self.scan_thread = None
        self.websocket_connected = False

        # Signal tracking
        self.active_signals: Dict[str, Dict] = {}
        self.signal_history: List[Dict] = []

    def _load_stock_list(self, env_key: str) -> List[str]:
        """Load stock list from environment"""
        stock_list = os.getenv(env_key, '')
        return [s.strip() for s in stock_list.split(',') if s.strip()]

    def initialize(self) -> bool:
        """
        Initialize Zerodha connection and components

        Returns:
            True if successful, False otherwise
        """
        try:
            # Initialize Zerodha client
            self.zerodha = ZerodhaClient()

            # Check if we have access token
            if not self.zerodha.access_token:
                logger.error("No access token found. Please login first.")
                print(f"\nLogin URL: {self.zerodha.generate_login_url()}")
                return False

            # Test connection
            margins = self.zerodha.get_margins()
            if margins:
                logger.info(
                    f"Connected to Zerodha. Available balance: {margins.get('equity', {}).get('available', {}).get('live_balance', 0)}")

            # Initialize data manager
            self.data_manager = DataManager(self.config, self.zerodha)
            self.data_manager.set_signal_callback(self._on_signal)

            # Load instruments
            self.zerodha.get_instruments()

            # Prepare symbol list
            # self.active_symbols = self.nifty_50 + self.volatile_stocks
            self.active_symbols = self.primary_stocks + self.momentum_stocks
            logger.info(f"Initialized with {len(self.active_symbols)} symbols")

            return True

        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            return False

    def start_scanning(self, mode: str = "periodic"):
        """
        Start scanning stocks

        Args:
            mode: 'periodic' for API polling or 'stream' for WebSocket
        """
        if self.is_running:
            logger.warning("Scanner already running")
            return

        self.is_running = True
        logger.info(f"Starting scanner in {mode} mode")

        if mode == "stream":
            self._start_streaming()
        else:
            self._start_periodic_scanning()

    def _start_periodic_scanning(self):
        """Start periodic API-based scanning"""

        def scan_loop():
            scan_interval = int(os.getenv('SCAN_INTERVAL_SECONDS', '5'))

            while self.is_running:
                try:
                    # Scan all symbols
                    self.data_manager.scan_all_symbols(self.active_symbols)

                    # Display status
                    self._display_status()

                    # Wait for next scan
                    time.sleep(scan_interval)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Scan error: {str(e)}")
                    time.sleep(scan_interval)

        # Start scan thread
        self.scan_thread = threading.Thread(target=scan_loop)
        self.scan_thread.daemon = True
        self.scan_thread.start()

    def _start_streaming(self):
        """Start WebSocket streaming"""
        try:
            # Define callbacks
            def on_ticks(ws, ticks):
                for tick in ticks:
                    self.data_manager.process_tick(tick)

            def on_connect(ws, response):
                logger.info("WebSocket connected")
                self.websocket_connected = True

                # Subscribe to symbols
                self.zerodha.subscribe_symbols(self.active_symbols[:50])  # Limit to 50

            def on_close(ws, code, reason):
                logger.info(f"WebSocket closed: {code} - {reason}")
                self.websocket_connected = False

            def on_error(ws, code, reason):
                logger.error(f"WebSocket error: {code} - {reason}")

            # Start WebSocket
            self.zerodha.start_websocket(
                on_tick=on_ticks,
                on_connect=on_connect,
                on_close=on_close,
                on_error=on_error
            )

            # Keep main thread alive
            while self.is_running:
                time.sleep(1)
                self._display_status()

        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")

    def stop_scanning(self):
        """Stop scanning"""
        logger.info("Stopping scanner...")
        self.is_running = False

        if self.websocket_connected:
            self.zerodha.stop_websocket()

        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_thread.join(timeout=5)

        logger.info("Scanner stopped")

    def _on_signal(self, signal_data: Dict):
        """Handle trading signal"""
        symbol = signal_data['symbol']
        signal_type = signal_data['type']

        # Store signal
        self.active_signals[symbol] = signal_data
        self.signal_history.append(signal_data)

        # Create notification message
        message = (
            f"🚨 {signal_type} Signal - {symbol}\n"
            f"Price: ₹{signal_data['price']:.2f}\n"
            f"Prediction: {signal_data['prediction']:.2f}\n"
            f"Strength: {signal_data['strength']:.1%}"
        )

        # Send notification
        self.notifier.send_notification(
            title=f"{signal_type} Signal: {symbol}",
            message=message,
            sound=True
        )

        # Log signal
        logger.info(f"Signal: {symbol} {signal_type} @ {signal_data['price']}")

        # Print to console
        self._print_signal(signal_data)

    def _print_signal(self, signal_data: Dict):
        """Print signal to console with formatting"""
        symbol = signal_data['symbol']
        signal_type = signal_data['type']

        # Color codes
        GREEN = '\033[92m'
        RED = '\033[91m'
        RESET = '\033[0m'

        color = GREEN if signal_type == 'BUY' else RED

        print(f"\n{'=' * 60}")
        print(f"{color}{'🟢' if signal_type == 'BUY' else '🔴'} {signal_type} SIGNAL - {symbol}{RESET}")
        print(f"{'=' * 60}")
        print(f"Time: {signal_data['timestamp'].strftime('%H:%M:%S')}")
        print(f"Price: ₹{signal_data['price']:.2f}")
        print(f"ML Prediction: {signal_data['prediction']:.2f}")
        print(f"Signal Strength: {signal_data['strength']:.1%}")
        print(f"Filters Passed: {sum(1 for v in signal_data['filters'].values() if v)}/{len(signal_data['filters'])}")
        print(f"{'=' * 60}\n")

    def _display_status(self):
        """Display current scanner status"""
        # Clear screen (optional)
        # os.system('clear' if os.name == 'posix' else 'cls')

        # Get current time
        current_time = datetime.now().strftime('%H:%M:%S')

        # Count active processors
        active_processors = len(self.data_manager.processors)

        # Display status line
        status = f"[{current_time}] Scanning {len(self.active_symbols)} symbols | "
        status += f"Active: {active_processors} | "
        status += f"Signals Today: {len(self.signal_history)} | "
        
        # Add API call info if available
        if hasattr(self.data_manager, 'api_call_counter'):
            api_calls = self.data_manager.api_call_counter
            status += f"API Calls: {api_calls['total']} (Q:{api_calls['quotes']}/H:{api_calls['historical']})"

        # Print without newline, overwrite previous
        print(f"\r{status}", end='', flush=True)

    def get_active_signals(self) -> List[Dict]:
        """Get list of active signals"""
        return list(self.active_signals.values())

    def get_signal_history(self) -> List[Dict]:
        """Get signal history"""
        return self.signal_history

    def get_processor_stats(self) -> Dict[str, Dict]:
        """Get statistics for all processors"""
        stats = {}
        for symbol in self.data_manager.processors:
            stats[symbol] = self.data_manager.get_processor_stats(symbol)
        return stats


def main():
    """Main entry point for live scanner"""
    print("=== Lorentzian Classification Live Scanner ===\n")

    # Create scanner
    scanner = LiveScanner()

    # Initialize
    if not scanner.initialize():
        print("\nInitialization failed. Please check your credentials.")
        return

    print("\nScanner initialized successfully!")
    print(f"Monitoring {len(scanner.active_symbols)} symbols")
    print("\nStarting scan... Press Ctrl+C to stop.\n")

    try:
        # Start scanning
        scanner.start_scanning(mode="periodic")

        # Keep running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nStopping scanner...")
        scanner.stop_scanning()

        # Display summary
        print("\n=== Session Summary ===")
        print(f"Total signals generated: {len(scanner.signal_history)}")
        
        # Show API usage summary
        if hasattr(scanner.data_manager, 'get_api_call_stats'):
            api_stats = scanner.data_manager.get_api_call_stats()
            print(f"\nAPI Calls Made:")
            print(f"  Total: {api_stats['total']}")
            print(f"  Quotes: {api_stats['quotes']}")
            print(f"  Historical: {api_stats['historical']}")

        if scanner.signal_history:
            print("\nRecent signals:")
            for signal in scanner.signal_history[-5:]:
                print(f"  {signal['timestamp'].strftime('%H:%M')} - "
                      f"{signal['symbol']} {signal['type']} @ ₹{signal['price']:.2f}")

        print("\nGoodbye!")


if __name__ == "__main__":
    main()