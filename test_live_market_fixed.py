#!/usr/bin/env python3
"""
Enhanced Live Market Test Script for Lorentzian Classification System
====================================================================

This refactored version incorporates advanced trading techniques from:
- Quantitative Trading Introduction (systematic approach, risk management)
- Trading Warrior (momentum patterns, tape reading concepts)
- AI Trading Knowledge Base (time windows, position sizing)

Features:
- Proper warmup verification before trading
- Advanced position sizing based on risk
- Time-based trading windows
- Partial profit booking at targets
- Pattern quality scoring
- Comprehensive risk management

Usage:
    python test_live_market_fixed.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time
import json
from typing import Dict, List, Tuple, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Core imports
from config.settings import TradingConfig
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from data.zerodha_client import ZerodhaClient
from utils.risk_management import calculate_trade_levels

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedLiveMarketTest:
    """
    Enhanced live market testing with advanced trading techniques
    """
    
    def __init__(self, test_symbols: List[str] = None, capital: float = 10000.0):
        """
        Initialize with symbols and capital
        
        Args:
            test_symbols: List of stock symbols to test
            capital: Trading capital (default: 10000)
        """
        self.logger = logger
        self.kite_client = None
        self.results = {}
        self.active_signals = {}
        self.trade_history = []
        self.capital = capital
        self.daily_trades = 0
        self.daily_pnl = 0.0
        
        # Risk Management Parameters (from Quantitative Trading)
        self.max_risk_per_trade = 0.02  # 2% max risk per trade
        self.max_daily_risk = 0.06  # 6% max daily risk
        self.max_positions = 3  # Maximum concurrent positions
        self.profit_target_ratio = 2.0  # Risk:Reward ratio
        
        # Time Windows (from AI Knowledge Base)
        self.market_open = 9.25  # 9:15 AM + 10 min buffer
        self.momentum_start = 9.5  # 9:30 AM - good momentum
        self.prime_start = 10.0  # 10:00 AM - prime momentum
        self.prime_end = 14.5  # 2:30 PM - avoid after this
        self.market_close = 15.5  # 3:30 PM
        
        # Pattern Quality Thresholds (from Trading Warrior)
        self.min_pattern_score = 6.0  # Minimum pattern quality
        self.high_conviction_score = 8.0  # High conviction trades
        
        # Default test symbols if none provided
        self.test_symbols = test_symbols or [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
            'HDFC', 'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK',
            'BAJFINANCE', 'LT', 'HINDUNILVR', 'ASIANPAINT', 'AXISBANK'
        ]
        
        # Pine Script default configuration with enhancements
        self.config = TradingConfig(
            # Core ML settings
            neighbors_count=8,
            max_bars_back=2000,
            feature_count=5,
            source='close',
            
            # Filter settings (all enabled for quality)
            use_volatility_filter=True,
            use_regime_filter=True,
            use_adx_filter=True,  # Enable ADX for trend strength
            regime_threshold=-0.1,
            adx_threshold=25,  # Higher threshold for stronger trends
            
            # Kernel settings
            use_kernel_filter=True,
            use_kernel_smoothing=False,
            kernel_lookback=8,
            kernel_relative_weight=8.0,
            kernel_regression_level=25,
            kernel_lag=2,
            
            # Trend filters for additional confirmation
            use_ema_filter=True,
            use_sma_filter=True,
            ema_period=20,
            sma_period=50,
            
            # Exit settings
            show_exits=True,
            use_dynamic_exits=True
        )
        
        # Initialize processors for each symbol
        self.processors = {}
        self.symbol_stats = {}  # Track per-symbol statistics
        
        self._print_configuration()
    
    def _print_configuration(self):
        """Print enhanced trading configuration"""
        print("\n" + "="*60)
        print("🚀 ENHANCED LIVE MARKET TEST - LORENTZIAN CLASSIFIER")
        print("="*60)
        print(f"\n💰 Capital & Risk Management:")
        print(f"   Trading Capital: ₹{self.capital:,.2f}")
        print(f"   Max Risk per Trade: {self.max_risk_per_trade*100:.1f}%")
        print(f"   Max Daily Risk: {self.max_daily_risk*100:.1f}%")
        print(f"   Max Concurrent Positions: {self.max_positions}")
        print(f"   Target Risk:Reward: 1:{self.profit_target_ratio}")
        
        print(f"\n⏰ Trading Time Windows:")
        print(f"   Market Open Buffer: {self._hour_to_time(self.market_open)}")
        print(f"   Momentum Window: {self._hour_to_time(self.momentum_start)} - {self._hour_to_time(self.prime_end)}")
        print(f"   Prime Window: {self._hour_to_time(self.prime_start)} - {self._hour_to_time(14.0)}")
        print(f"   Avoid After: {self._hour_to_time(self.prime_end)}")
        
        print(f"\n📊 Quality Filters:")
        print(f"   Minimum Pattern Score: {self.min_pattern_score}/10")
        print(f"   High Conviction Score: {self.high_conviction_score}/10")
        print(f"   All ML Filters: Enabled")
        print(f"   ADX Threshold: {self.config.adx_threshold}")
        
        print(f"\n📈 Testing Stocks:")
        print(f"   {', '.join(self.test_symbols[:5])}{'...' if len(self.test_symbols) > 5 else ''}")
        print(f"   Total: {len(self.test_symbols)} stocks")
    
    def _hour_to_time(self, hour: float) -> str:
        """Convert decimal hour to time string"""
        h = int(hour)
        m = int((hour - h) * 60)
        return f"{h:02d}:{m:02d}"
    
    def initialize_zerodha(self) -> bool:
        """Initialize Zerodha connection"""
        try:
            # Check if kiteconnect is available
            try:
                from kiteconnect import KiteConnect
            except ImportError:
                print("\n❌ KiteConnect not installed!")
                print("   Please install with: pip install kiteconnect")
                print("   Or use: pip install -r requirements.txt")
                return False
            
            # Check for saved session
            if os.path.exists('.kite_session.json'):
                with open('.kite_session.json', 'r') as f:
                    session_data = json.load(f)
                    access_token = session_data.get('access_token')
                
                # Set token in environment
                os.environ['KITE_ACCESS_TOKEN'] = access_token
                # Initialize with caching enabled
                self.kite_client = ZerodhaClient(use_cache=True, cache_dir="data_cache")
                
                # Test connection
                profile = self.kite_client.kite.profile()
                print(f"\n📡 Zerodha connected: {profile.get('user_name', 'Unknown')}")
                return True
            else:
                print("❌ No access token found. Run auth_helper.py first")
                return False
                
        except Exception as e:
            print(f"❌ Failed to initialize Zerodha: {e}")
            return False
    
    def fetch_historical_data(self, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for warmup (FIXED API CALL)
        
        Args:
            symbol: Stock symbol
            days: Number of days of historical data
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # FIXED: Use correct API parameters
            data = self.kite_client.get_historical_data(
                symbol=symbol,
                interval='5minute',
                days=days
            )
            
            if data:
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                return df
            else:
                self.logger.warning(f"No historical data found for {symbol}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None
    
    def warmup_processor(self, symbol: str) -> bool:
        """
        Warmup processor with historical data and ML readiness check
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if warmup successful and ML ready
        """
        try:
            print(f"\n⏳ Warming up {symbol}...")
            
            # Initialize processor if not exists
            if symbol not in self.processors:
                self.processors[symbol] = EnhancedBarProcessor(self.config, symbol, "5min")
            
            # Fetch historical data
            hist_data = self.fetch_historical_data(symbol, days=30)
            if hist_data is None or hist_data.empty:
                print(f"❌ No historical data for {symbol}")
                return False
            
            processor = self.processors[symbol]
            bars_processed = 0
            
            # Process historical bars
            for idx, row in hist_data.iterrows():
                result = processor.process_bar(
                    open_price=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume']
                )
                bars_processed += 1
            
            # FIXED: Check ML readiness
            ml_ready = processor.bars_processed >= processor.settings.max_bars_back
            
            print(f"✅ {symbol}: Processed {bars_processed} bars")
            print(f"   Bars in processor: {processor.bars_processed}")
            print(f"   ML ready: {'Yes' if ml_ready else f'No (need {processor.settings.max_bars_back - processor.bars_processed} more)'}")
            
            # Initialize symbol stats
            self.symbol_stats[symbol] = {
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'total_pnl': 0.0,
                'ml_ready': ml_ready
            }
            
            return ml_ready
            
        except Exception as e:
            self.logger.error(f"Error warming up {symbol}: {e}")
            return False
    
    def evaluate_market_conditions(self) -> Tuple[bool, str, float]:
        """
        Evaluate current market conditions for trading
        
        Returns:
            (can_trade, condition_description, time_score)
        """
        current_time = datetime.now()
        current_hour = current_time.hour + current_time.minute / 60
        
        # Market closed
        if current_hour < self.market_open or current_hour > self.market_close:
            return False, "Market Closed", 0.0
        
        # Too early - wait for market to settle
        if current_hour < self.momentum_start:
            return False, "Market Opening Buffer", 0.0
        
        # Prime momentum window
        if self.prime_start <= current_hour <= 14.0:
            return True, "Prime Momentum Window", 1.0
        
        # Good momentum window
        if self.momentum_start <= current_hour <= self.prime_end:
            return True, "Good Momentum Window", 0.7
        
        # Late session - avoid
        return False, "Late Session - Avoid", 0.0
    
    def evaluate_pattern_quality(self, result, symbol: str) -> Tuple[float, str]:
        """
        Comprehensive pattern quality evaluation
        
        Returns:
            (score, explanation)
        """
        score = 5.0  # Base score
        factors = []
        
        # 1. ML Prediction Strength (0-3 points)
        pred_strength = abs(result.prediction)
        if pred_strength > 6:
            score += 3
            factors.append(f"Very strong ML signal ({result.prediction:.1f})")
        elif pred_strength > 4:
            score += 2
            factors.append(f"Strong ML signal ({result.prediction:.1f})")
        elif pred_strength > 2:
            score += 1
            factors.append(f"Moderate ML signal ({result.prediction:.1f})")
        else:
            score -= 1
            factors.append(f"Weak ML signal ({result.prediction:.1f})")
        
        # 2. Filter Alignment (0-2 points)
        filters_passed = sum([
            result.filter_states.get('volatility', False),
            result.filter_states.get('regime', False),
            result.filter_states.get('adx', False),
            result.filter_states.get('kernel', False)
        ])
        
        if filters_passed == 4:
            score += 2
            factors.append("All filters aligned")
        elif filters_passed >= 3:
            score += 1
            factors.append(f"{filters_passed}/4 filters passed")
        elif filters_passed < 2:
            score -= 1
            factors.append(f"Only {filters_passed}/4 filters passed")
        
        # 3. Time Window Bonus (0-1 point)
        _, _, time_score = self.evaluate_market_conditions()
        if time_score >= 1.0:
            score += 1
            factors.append("Prime time window")
        elif time_score >= 0.7:
            score += 0.5
            factors.append("Good time window")
        
        # 4. Symbol Performance (0-1 point)
        if symbol in self.symbol_stats:
            stats = self.symbol_stats[symbol]
            if stats['trades'] > 0:
                win_rate = stats['wins'] / stats['trades']
                if win_rate >= 0.6:
                    score += 1
                    factors.append(f"Good symbol performance ({win_rate*100:.0f}% win)")
                elif win_rate < 0.3:
                    score -= 0.5
                    factors.append(f"Poor symbol performance ({win_rate*100:.0f}% win)")
        
        # Cap score between 1 and 10
        final_score = min(10, max(1, score))
        explanation = ", ".join(factors)
        
        return final_score, explanation
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> int:
        """
        Calculate position size based on risk management rules
        """
        # Risk per share
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0:
            return 0
        
        # Maximum position value (capital allocation)
        max_position_value = self.capital / max(self.max_positions, len(self.active_signals) + 1)
        
        # Risk-based position size
        risk_amount = self.capital * self.max_risk_per_trade
        risk_based_shares = int(risk_amount / risk_per_share)
        
        # Capital-based position size
        capital_based_shares = int(max_position_value / entry_price)
        
        # Use the smaller of the two
        position_size = min(risk_based_shares, capital_based_shares)
        
        # Apply minimum position size
        return max(1, position_size)
    
    def check_risk_limits(self) -> Tuple[bool, str]:
        """
        Check if we're within risk limits
        
        Returns:
            (can_trade, reason)
        """
        # Check daily loss limit
        if self.daily_pnl <= -(self.capital * self.max_daily_risk):
            return False, f"Daily loss limit reached (₹{abs(self.daily_pnl):.2f})"
        
        # Check position limit
        if len(self.active_signals) >= self.max_positions:
            return False, f"Maximum positions reached ({self.max_positions})"
        
        # Check remaining risk capacity
        current_risk = sum(
            abs(sig['entry_price'] - sig['stop_loss']) * sig['position_size']
            for sig in self.active_signals.values()
        )
        
        if current_risk >= self.capital * self.max_daily_risk * 0.8:
            return False, "Near daily risk limit (80%)"
        
        return True, "Within risk limits"
    
    def calculate_trade_levels(self, entry_price: float, is_long: bool, 
                             processor: EnhancedBarProcessor) -> Tuple[float, float, float]:
        """
        Calculate stop loss and take profit levels
        
        Returns:
            (stop_loss, target_1, target_2)
        """
        # Get recent bars for ATR calculation
        if hasattr(processor, 'bars') and len(processor.bars) >= 20:
            high_values = []
            low_values = []
            close_values = []
            
            for i in range(min(20, len(processor.bars))):
                high_values.append(processor.bars.get_high(i))
                low_values.append(processor.bars.get_low(i))
                close_values.append(processor.bars.get_close(i))
            
            # Calculate using ATR method
            stop_loss, take_profit = calculate_trade_levels(
                entry_price=entry_price,
                high_values=high_values,
                low_values=low_values,
                close_values=close_values,
                is_long=is_long,
                method="atr",
                atr_length=14,
                atr_multiplier=1.5,  # Tighter stop
                risk_reward_ratio=self.profit_target_ratio
            )
            
            # Calculate intermediate target (50% exit)
            if is_long:
                target_1 = entry_price + (take_profit - entry_price) * 0.5
            else:
                target_1 = entry_price - (entry_price - take_profit) * 0.5
                
        else:
            # Fallback to percentage-based
            if is_long:
                stop_loss = entry_price * 0.98  # 2% stop
                target_1 = entry_price * 1.01   # 1% first target
                take_profit = entry_price * 1.04  # 4% final target
            else:
                stop_loss = entry_price * 1.02
                target_1 = entry_price * 0.99
                take_profit = entry_price * 0.96
        
        return stop_loss, target_1, take_profit
    
    def process_live_bar(self, symbol: str, bar_data: Dict) -> Dict:
        """
        Process a single live bar with all checks
        """
        try:
            processor = self.processors.get(symbol)
            if not processor:
                return {'symbol': symbol, 'error': 'No processor initialized'}
            
            # Check ML readiness
            if processor.bars_processed < processor.settings.max_bars_back:
                return {
                    'symbol': symbol,
                    'status': 'warming_up',
                    'bars_processed': processor.bars_processed,
                    'bars_needed': processor.settings.max_bars_back
                }
            
            # Process the bar
            result = processor.process_bar(
                open_price=bar_data['open'],
                high=bar_data['high'],
                low=bar_data['low'],
                close=bar_data['close'],
                volume=bar_data['volume']
            )
            
            # Evaluate conditions
            can_trade_time, time_condition, _ = self.evaluate_market_conditions()
            can_trade_risk, risk_reason = self.check_risk_limits()
            pattern_score, pattern_explanation = self.evaluate_pattern_quality(result, symbol)
            
            # Prepare result summary
            summary = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'close': bar_data['close'],
                'prediction': result.prediction,
                'signal': result.signal,
                'pattern_score': pattern_score,
                'pattern_explanation': pattern_explanation,
                'can_trade': can_trade_time and can_trade_risk and pattern_score >= self.min_pattern_score,
                'conditions': f"{time_condition}, {risk_reason}"
            }
            
            # Check for new signals
            if summary['can_trade']:
                if result.start_long_trade and symbol not in self.active_signals:
                    self._enter_long_position(symbol, bar_data, result, pattern_score, pattern_explanation)
                elif result.start_short_trade and symbol not in self.active_signals:
                    self._enter_short_position(symbol, bar_data, result, pattern_score, pattern_explanation)
            
            # Check for exits on active positions
            if symbol in self.active_signals:
                self._check_exit_conditions(symbol, bar_data, result)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error processing bar for {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def _enter_long_position(self, symbol: str, bar_data: Dict, result, score: float, explanation: str):
        """Enter a long position with risk management"""
        entry_price = bar_data['close']
        processor = self.processors[symbol]
        
        # Calculate levels
        stop_loss, target_1, target_2 = self.calculate_trade_levels(
            entry_price, is_long=True, processor=processor
        )
        
        # Calculate position size
        position_size = self.calculate_position_size(entry_price, stop_loss)
        if position_size <= 0:
            return
        
        # Create position
        signal_info = {
            'type': 'LONG',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'position_size': position_size,
            'entry_time': datetime.now(),
            'prediction': result.prediction,
            'pattern_score': score,
            'partial_exit': False,
            'original_size': position_size
        }
        
        self.active_signals[symbol] = signal_info
        self.daily_trades += 1
        
        # Update symbol stats
        self.symbol_stats[symbol]['trades'] += 1
        
        # Print entry details
        print(f"\n{'='*60}")
        print(f"🟢 LONG ENTRY - {symbol}")
        print(f"{'='*60}")
        print(f"📊 Entry Details:")
        print(f"   Price: ₹{entry_price:.2f} x {position_size} shares")
        print(f"   Stop Loss: ₹{stop_loss:.2f} (-{(entry_price-stop_loss)/entry_price*100:.1f}%)")
        print(f"   Target 1: ₹{target_1:.2f} (+{(target_1-entry_price)/entry_price*100:.1f}%) [50% exit]")
        print(f"   Target 2: ₹{target_2:.2f} (+{(target_2-entry_price)/entry_price*100:.1f}%) [full exit]")
        print(f"📈 Signal Quality:")
        print(f"   ML Prediction: {result.prediction:.2f}")
        print(f"   Pattern Score: {score:.1f}/10")
        print(f"   Factors: {explanation}")
        print(f"💰 Risk Management:")
        print(f"   Position Value: ₹{entry_price * position_size:.2f}")
        print(f"   Risk Amount: ₹{(entry_price - stop_loss) * position_size:.2f}")
        print(f"   Risk/Reward: 1:{self.profit_target_ratio:.1f}")
        
        # Store in results
        if symbol not in self.results:
            self.results[symbol] = []
        self.results[symbol].append({
            'action': 'LONG_ENTRY',
            'time': datetime.now(),
            'price': entry_price,
            'size': position_size,
            'score': score
        })
    
    def _enter_short_position(self, symbol: str, bar_data: Dict, result, score: float, explanation: str):
        """Enter a short position with risk management"""
        entry_price = bar_data['close']
        processor = self.processors[symbol]
        
        # Calculate levels
        stop_loss, target_1, target_2 = self.calculate_trade_levels(
            entry_price, is_long=False, processor=processor
        )
        
        # Calculate position size
        position_size = self.calculate_position_size(entry_price, stop_loss)
        if position_size <= 0:
            return
        
        # Create position
        signal_info = {
            'type': 'SHORT',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'position_size': position_size,
            'entry_time': datetime.now(),
            'prediction': result.prediction,
            'pattern_score': score,
            'partial_exit': False,
            'original_size': position_size
        }
        
        self.active_signals[symbol] = signal_info
        self.daily_trades += 1
        
        # Update symbol stats
        self.symbol_stats[symbol]['trades'] += 1
        
        # Print entry details
        print(f"\n{'='*60}")
        print(f"🔴 SHORT ENTRY - {symbol}")
        print(f"{'='*60}")
        print(f"📊 Entry Details:")
        print(f"   Price: ₹{entry_price:.2f} x {position_size} shares")
        print(f"   Stop Loss: ₹{stop_loss:.2f} (+{(stop_loss-entry_price)/entry_price*100:.1f}%)")
        print(f"   Target 1: ₹{target_1:.2f} (-{(entry_price-target_1)/entry_price*100:.1f}%) [50% exit]")
        print(f"   Target 2: ₹{target_2:.2f} (-{(entry_price-target_2)/entry_price*100:.1f}%) [full exit]")
        print(f"📈 Signal Quality:")
        print(f"   ML Prediction: {result.prediction:.2f}")
        print(f"   Pattern Score: {score:.1f}/10")
        print(f"   Factors: {explanation}")
        print(f"💰 Risk Management:")
        print(f"   Position Value: ₹{entry_price * position_size:.2f}")
        print(f"   Risk Amount: ₹{(stop_loss - entry_price) * position_size:.2f}")
        print(f"   Risk/Reward: 1:{self.profit_target_ratio:.1f}")
    
    def _check_exit_conditions(self, symbol: str, bar_data: Dict, result):
        """Check exit conditions with partial profit booking"""
        signal = self.active_signals[symbol]
        current_price = bar_data['close']
        time_in_trade = (datetime.now() - signal['entry_time']).seconds / 60
        
        if signal['type'] == 'LONG':
            # Stop loss hit
            if current_price <= signal['stop_loss']:
                self._close_position(symbol, current_price, 'STOP_LOSS')
            # First target hit (partial exit)
            elif not signal['partial_exit'] and current_price >= signal['target_1']:
                self._partial_exit(symbol, current_price)
            # Second target hit (full exit)
            elif current_price >= signal['target_2']:
                self._close_position(symbol, current_price, 'TARGET_2')
            # Time-based exit (30 minutes)
            elif time_in_trade > 30:
                pnl_percent = (current_price - signal['entry_price']) / signal['entry_price'] * 100
                if abs(pnl_percent) < 0.5:  # Less than 0.5% move
                    self._close_position(symbol, current_price, 'TIME_EXIT')
            # ML exit signal
            elif result.end_long_trade:
                self._close_position(symbol, current_price, 'ML_EXIT')
                
        else:  # SHORT
            # Stop loss hit
            if current_price >= signal['stop_loss']:
                self._close_position(symbol, current_price, 'STOP_LOSS')
            # First target hit (partial exit)
            elif not signal['partial_exit'] and current_price <= signal['target_1']:
                self._partial_exit(symbol, current_price)
            # Second target hit (full exit)
            elif current_price <= signal['target_2']:
                self._close_position(symbol, current_price, 'TARGET_2')
            # Time-based exit
            elif time_in_trade > 30:
                pnl_percent = (signal['entry_price'] - current_price) / signal['entry_price'] * 100
                if abs(pnl_percent) < 0.5:
                    self._close_position(symbol, current_price, 'TIME_EXIT')
            # ML exit signal
            elif result.end_short_trade:
                self._close_position(symbol, current_price, 'ML_EXIT')
    
    def _partial_exit(self, symbol: str, exit_price: float):
        """Execute partial exit at first target"""
        signal = self.active_signals[symbol]
        
        # Exit 50% of position
        exit_size = int(signal['original_size'] * 0.5)
        remaining_size = signal['position_size'] - exit_size
        
        # Calculate P&L
        if signal['type'] == 'LONG':
            pnl = (exit_price - signal['entry_price']) * exit_size
        else:
            pnl = (signal['entry_price'] - exit_price) * exit_size
        
        self.daily_pnl += pnl
        
        # Update position
        signal['position_size'] = remaining_size
        signal['partial_exit'] = True
        
        # Move stop to breakeven
        signal['stop_loss'] = signal['entry_price']
        
        print(f"\n💰 PARTIAL EXIT - {symbol}")
        print(f"   Exit: {exit_size} shares @ ₹{exit_price:.2f}")
        print(f"   P&L: ₹{pnl:+.2f}")
        print(f"   Remaining: {remaining_size} shares")
        print(f"   Stop moved to breakeven @ ₹{signal['stop_loss']:.2f}")
    
    def _close_position(self, symbol: str, exit_price: float, exit_reason: str):
        """Close an active position"""
        if symbol not in self.active_signals:
            return
            
        signal = self.active_signals[symbol]
        
        # Calculate P&L
        if signal['type'] == 'LONG':
            pnl = (exit_price - signal['entry_price']) * signal['position_size']
            # Add partial exit P&L if applicable
            if signal['partial_exit']:
                partial_pnl = (signal['target_1'] - signal['entry_price']) * (signal['original_size'] * 0.5)
                pnl += partial_pnl
        else:
            pnl = (signal['entry_price'] - exit_price) * signal['position_size']
            if signal['partial_exit']:
                partial_pnl = (signal['entry_price'] - signal['target_1']) * (signal['original_size'] * 0.5)
                pnl += partial_pnl
        
        pnl_percent = (pnl / (signal['entry_price'] * signal['original_size'])) * 100
        self.daily_pnl += pnl
        
        # Update symbol stats
        if pnl > 0:
            self.symbol_stats[symbol]['wins'] += 1
        else:
            self.symbol_stats[symbol]['losses'] += 1
        self.symbol_stats[symbol]['total_pnl'] += pnl
        
        # Record trade
        trade_record = {
            'symbol': symbol,
            'type': signal['type'],
            'entry_price': signal['entry_price'],
            'exit_price': exit_price,
            'position_size': signal['original_size'],
            'entry_time': signal['entry_time'],
            'exit_time': datetime.now(),
            'hold_minutes': (datetime.now() - signal['entry_time']).seconds / 60,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'exit_reason': exit_reason,
            'pattern_score': signal['pattern_score'],
            'partial_exit': signal['partial_exit']
        }
        
        self.trade_history.append(trade_record)
        del self.active_signals[symbol]
        
        emoji = "✅" if pnl > 0 else "❌"
        print(f"\n{emoji} CLOSED {signal['type']} - {symbol}")
        print(f"   Exit: ₹{exit_price:.2f} ({exit_reason})")
        print(f"   P&L: ₹{pnl:+.2f} ({pnl_percent:+.2f}%)")
        print(f"   Daily P&L: ₹{self.daily_pnl:+.2f}")
    
    def fetch_live_data(self) -> Dict[str, Dict]:
        """
        Fetch live data for all symbols
        """
        live_data = {}
        
        try:
            # Get LTP for all symbols
            instruments = [f"NSE:{symbol}" for symbol in self.test_symbols]
            quotes = self.kite_client.kite.quote(instruments)
            
            for symbol in self.test_symbols:
                instrument = f"NSE:{symbol}"
                if instrument in quotes:
                    quote = quotes[instrument]
                    live_data[symbol] = {
                        'open': quote['ohlc']['open'],
                        'high': quote['ohlc']['high'],
                        'low': quote['ohlc']['low'],
                        'close': quote['last_price'],
                        'volume': quote['volume']
                    }
                    
        except Exception as e:
            self.logger.error(f"Error fetching live data: {e}")
            
        return live_data
    
    def run_continuous_test(self, duration_minutes: int = 60):
        """
        Run continuous live market test with advanced features
        """
        print(f"\n🏃 Starting Enhanced Live Test for {duration_minutes} minutes...")
        
        # First warmup all processors
        print("\n📊 Warming up processors with historical data...")
        ml_ready_count = 0
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self.warmup_processor, symbol): symbol 
                      for symbol in self.test_symbols}
            
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    success = future.result()
                    if success:
                        ml_ready_count += 1
                except Exception as e:
                    print(f"⚠️  Failed to warmup {symbol}: {e}")
        
        print(f"\n✅ ML Ready: {ml_ready_count}/{len(self.test_symbols)} symbols")
        
        # Run live test
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        update_interval = 5  # seconds
        
        print(f"\n📈 Live testing started at {start_time.strftime('%H:%M:%S')}")
        print(f"   Will run until {end_time.strftime('%H:%M:%S')}")
        print("\n" + "="*80)
        
        try:
            while datetime.now() < end_time:
                # Check market conditions
                can_trade, condition, _ = self.evaluate_market_conditions()
                
                # Fetch and process live data
                if can_trade:
                    live_data = self.fetch_live_data()
                    
                    if live_data:
                        # Process each symbol
                        for symbol, bar_data in live_data.items():
                            # Only process if ML is ready
                            if symbol in self.symbol_stats and self.symbol_stats[symbol]['ml_ready']:
                                result = self.process_live_bar(symbol, bar_data)
                                
                                # Store result
                                if symbol not in self.results:
                                    self.results[symbol] = []
                                self.results[symbol].append(result)
                    
                    # Display status
                    active_count = len(self.active_signals)
                    total_trades = len(self.trade_history)
                    profitable_trades = sum(1 for t in self.trade_history if t['pnl'] > 0)
                    win_rate = (profitable_trades/total_trades*100) if total_trades > 0 else 0
                    
                    risk_ok, risk_status = self.check_risk_limits()
                    
                    print(f"\r📊 {condition} | Active: {active_count} | "
                          f"Trades: {total_trades} | Win: {win_rate:.0f}% | "
                          f"P&L: ₹{self.daily_pnl:+.2f} | Risk: {risk_status} | "
                          f"{datetime.now().strftime('%H:%M:%S')}", end='')
                else:
                    print(f"\r⏸️  {condition} | Time: {datetime.now().strftime('%H:%M:%S')}", end='')
                
                # Wait before next update
                time.sleep(update_interval)
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted by user")
        except Exception as e:
            print(f"\n\n❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
        
        # Print final summary
        self._print_summary()
    
    def _print_summary(self):
        """Print comprehensive test summary"""
        print("\n\n" + "="*80)
        print("📊 ENHANCED LIVE MARKET TEST SUMMARY")
        print("="*80)
        
        # Overall stats
        total_signals = sum(len(v) for v in self.results.values())
        total_trades = len(self.trade_history)
        
        print(f"\n📈 Overall Statistics:")
        print(f"   Total bars processed: {total_signals}")
        print(f"   Total trades: {total_trades}")
        print(f"   Daily P&L: ₹{self.daily_pnl:+.2f} ({self.daily_pnl/self.capital*100:+.2f}%)")
        
        if total_trades > 0:
            profitable = sum(1 for t in self.trade_history if t['pnl'] > 0)
            total_pnl = sum(t['pnl'] for t in self.trade_history)
            avg_pnl = total_pnl / total_trades
            
            print(f"\n💰 Trade Performance:")
            print(f"   Profitable trades: {profitable}/{total_trades} ({profitable/total_trades*100:.1f}%)")
            print(f"   Average P&L per trade: ₹{avg_pnl:.2f}")
            
            # Best and worst trades
            best_trade = max(self.trade_history, key=lambda x: x['pnl'])
            worst_trade = min(self.trade_history, key=lambda x: x['pnl'])
            
            print(f"\n🏆 Best Trade:")
            print(f"   {best_trade['symbol']} {best_trade['type']}: ₹{best_trade['pnl']:+.2f} "
                  f"({best_trade['pnl_percent']:+.2f}%)")
            print(f"\n💔 Worst Trade:")
            print(f"   {worst_trade['symbol']} {worst_trade['type']}: ₹{worst_trade['pnl']:+.2f} "
                  f"({worst_trade['pnl_percent']:+.2f}%)")
        
        # Symbol performance
        print(f"\n📊 Symbol Performance:")
        for symbol, stats in sorted(self.symbol_stats.items(), 
                                  key=lambda x: x[1]['total_pnl'], reverse=True)[:5]:
            if stats['trades'] > 0:
                win_rate = stats['wins'] / stats['trades'] * 100
                print(f"   {symbol}: {stats['trades']} trades, "
                      f"{win_rate:.0f}% win, P&L: ₹{stats['total_pnl']:+.2f}")
        
        # Active positions
        if self.active_signals:
            print(f"\n📍 Active Positions ({len(self.active_signals)}):")
            for symbol, signal in self.active_signals.items():
                print(f"   {symbol}: {signal['type']} @ ₹{signal['entry_price']:.2f} "
                      f"({signal['position_size']} shares)")
        
        # Export results
        self._export_results()
    
    def _export_results(self):
        """Export test results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export trade history
        if self.trade_history:
            trades_df = pd.DataFrame(self.trade_history)
            trades_file = f"enhanced_live_trades_{timestamp}.csv"
            trades_df.to_csv(trades_file, index=False)
            print(f"\n💾 Trade history exported to: {trades_file}")
        
        # Export symbol stats
        if self.symbol_stats:
            stats_df = pd.DataFrame.from_dict(self.symbol_stats, orient='index')
            stats_file = f"symbol_stats_{timestamp}.csv"
            stats_df.to_csv(stats_file)
            print(f"💾 Symbol statistics exported to: {stats_file}")
        
        # Export detailed results
        results_file = f"enhanced_live_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'config': {
                    'capital': self.capital,
                    'max_risk_per_trade': self.max_risk_per_trade,
                    'max_daily_risk': self.max_daily_risk,
                    'max_positions': self.max_positions,
                    'min_pattern_score': self.min_pattern_score
                },
                'test_duration': str(datetime.now() - self.trade_history[0]['entry_time']) if self.trade_history else "0",
                'symbols_tested': self.test_symbols,
                'total_trades': len(self.trade_history),
                'daily_pnl': self.daily_pnl,
                'active_signals': {k: {kk: str(vv) if isinstance(vv, datetime) else vv 
                                     for kk, vv in v.items()} 
                                 for k, v in self.active_signals.items()},
                'summary_stats': self._calculate_summary_stats()
            }, f, indent=2, default=str)
        print(f"💾 Detailed results exported to: {results_file}")
    
    def _calculate_summary_stats(self) -> Dict:
        """Calculate summary statistics"""
        if not self.trade_history:
            return {}
            
        trades_df = pd.DataFrame(self.trade_history)
        
        # Time-based analysis
        trades_df['entry_hour'] = pd.to_datetime(trades_df['entry_time']).dt.hour + \
                                  pd.to_datetime(trades_df['entry_time']).dt.minute / 60
        
        prime_trades = trades_df[(trades_df['entry_hour'] >= self.prime_start) & 
                                (trades_df['entry_hour'] <= 14.0)]
        
        return {
            'total_trades': len(trades_df),
            'win_rate': (trades_df['pnl'] > 0).mean() * 100,
            'avg_pnl': trades_df['pnl'].mean(),
            'total_pnl': trades_df['pnl'].sum(),
            'best_trade': trades_df['pnl'].max(),
            'worst_trade': trades_df['pnl'].min(),
            'avg_trade_duration': trades_df['hold_minutes'].mean(),
            'avg_pattern_score': trades_df['pattern_score'].mean(),
            'prime_window_trades': len(prime_trades),
            'prime_window_win_rate': (prime_trades['pnl'] > 0).mean() * 100 if len(prime_trades) > 0 else 0
        }


def main():
    """Main execution function"""
    print("="*80)
    print("🚀 ENHANCED LORENTZIAN CLASSIFIER - LIVE MARKET TEST")
    print("="*80)
    print("\nIncorporating advanced techniques from:")
    print("• Quantitative Trading: Systematic risk management")
    print("• Trading Warrior: Momentum patterns and quality scoring")
    print("• AI Knowledge Base: Time windows and position sizing")
    
    # Optional: Specify custom symbols to test
    # test_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICIBANK']
    test_symbols = None  # Use default list
    
    # Get capital
    capital_input = input("\nEnter trading capital (default ₹10,000): ").strip()
    capital = float(capital_input) if capital_input else 10000.0
    
    # Create tester
    tester = EnhancedLiveMarketTest(test_symbols, capital)
    
    # Initialize Zerodha
    if not tester.initialize_zerodha():
        print("\n❌ Failed to initialize Zerodha. Exiting.")
        return
    
    # Run test
    try:
        # Run for specified duration (in minutes)
        test_duration = input("Enter test duration in minutes (default 60): ").strip()
        duration = int(test_duration) if test_duration else 60
        
        tester.run_continuous_test(duration_minutes=duration)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()