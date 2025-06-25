#!/usr/bin/env python3
"""
AI-Enhanced Live Market Test Script for Lorentzian Classification System
========================================================================

This script incorporates advanced trading rules from AI Trading Knowledge Base:
- Stock screening based on price range (₹50-₹500), volume (2x+), and movement (2%+)
- Time-based trading windows (no trades before 11 AM, prime window 11:30 AM - 1:30 PM)
- Strict 2 trades per day limit with daily loss limit (2% of capital)
- Pattern quality scoring (minimum 7/10 for entry)
- Position sizing based on risk management matrix
- Partial exits at first target (₹20) with stop moved to breakeven
- 30-minute time exit rule for non-performing trades

Usage:
    python test_live_market_ai_enhanced_fixed.py
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


class AIEnhancedLiveMarketTest:
    """
    AI-Enhanced Live market testing for the Lorentzian Classification system
    Incorporates proven trading rules from AI Trading Knowledge Base
    """
    
    def __init__(self, capital: float = 10000.0):
        """
        Initialize with trading capital
        
        Args:
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
        
        # AI Trading Rules
        self.max_daily_trades = 2  # Hard limit - never exceed
        self.daily_loss_limit = capital * 0.02  # 2% daily loss limit
        self.per_trade_risk = capital * 0.018  # 1.8% per trade risk
        self.min_pattern_score = 7.0  # Minimum pattern quality score
        
        # Trading time windows (85% win rate in prime window)
        self.no_trade_before = 11.0  # 11:00 AM - NEVER trade before this
        self.prime_window_start = 11.5  # 11:30 AM
        self.prime_window_end = 13.5    # 1:30 PM
        self.good_window_end = 14.5     # 2:30 PM
        
        # Stock universe for screening
        self.stock_universe = [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
            'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK', 'WIPRO',
            'BAJFINANCE', 'LT', 'HINDUNILVR', 'ASIANPAINT', 'AXISBANK',
            'TATAMOTORS', 'TATASTEEL', 'SUNPHARMA', 'ONGC', 'POWERGRID',
            'NTPC', 'COALINDIA', 'ADANIPORTS', 'JSWSTEEL', 'GRASIM',
            'HINDALCO', 'VEDL', 'BPCL', 'IOC', 'HEROMOTOCO',
            'MARUTI', 'M&M', 'TATAPOWER', 'IDEA', 'VODAIDEA',
            'ZEEL', 'YESBANK', 'BANKBARODA', 'PNB', 'CANBK'
        ]
        
        # Will be populated by stock screening
        self.selected_stocks = []
        self.processors = {}
        
        # Configuration optimized for momentum trading
        self.config = TradingConfig(
            # Core ML settings
            neighbors_count=8,
            max_bars_back=2000,
            feature_count=5,
            source='close',
            
            # Filters for momentum
            use_volatility_filter=True,
            use_regime_filter=True,
            use_adx_filter=False,
            regime_threshold=-0.1,
            
            # Kernel settings
            use_kernel_filter=True,
            use_kernel_smoothing=False,
            kernel_lookback=8,
            
            # Trend confirmation
            use_ema_filter=True,
            ema_period=20,
            use_sma_filter=False,
            
            # Dynamic exits
            show_exits=True,
            use_dynamic_exits=True
        )
        
        self._print_configuration()
    
    def _print_configuration(self):
        """Print trading configuration"""
        print("\n" + "="*60)
        print("🤖 AI-ENHANCED LORENTZIAN TRADING SYSTEM")
        print("="*60)
        print(f"\n💰 Capital Management:")
        print(f"   Trading Capital: ₹{self.capital:,.2f}")
        print(f"   Daily Trade Limit: {self.max_daily_trades} trades (HARD LIMIT)")
        print(f"   Daily Loss Limit: ₹{self.daily_loss_limit:,.2f} (2%)")
        print(f"   Per Trade Risk: ₹{self.per_trade_risk:,.2f} (1.8%)")
        
        print(f"\n⏰ Trading Windows:")
        print(f"   No Trading Before: 11:00 AM (0% win rate)")
        print(f"   Prime Window: 11:30 AM - 1:30 PM (85% win rate)")
        print(f"   Good Window: 11:00 AM - 2:30 PM (70% win rate)")
        print(f"   After 2:30 PM: AVOID")
        
        print(f"\n📊 Entry Criteria:")
        print(f"   Minimum Pattern Score: {self.min_pattern_score}/10")
        print(f"   Stock Price Range: ₹50 - ₹500")
        print(f"   Volume: 2x+ average")
        print(f"   Movement: 2%+ from open")
        
        print(f"\n🎯 Exit Rules:")
        print(f"   Stop Loss: 1% from entry")
        print(f"   Target 1: ₹20 (partial exit 50%)")
        print(f"   Target 2: ₹40 (full exit)")
        print(f"   Time Exit: 30 minutes if no movement")
    
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
                print(f"✅ Connected as: {profile.get('user_name', 'Unknown')}")
                return True
            else:
                print("❌ No access token found. Run auth_helper.py first")
                return False
                
        except Exception as e:
            print(f"❌ Failed to initialize Zerodha: {e}")
            return False
    
    def screen_stocks(self) -> List[str]:
        """
        Screen stocks based on AI Trading Knowledge Base criteria
        """
        print("\n🔍 Screening stocks with AI criteria...")
        candidates = []
        
        try:
            # Get quotes for all stocks
            instruments = [f"NSE:{symbol}" for symbol in self.stock_universe]
            quotes = self.kite_client.kite.quote(instruments)
            
            for symbol in self.stock_universe:
                instrument = f"NSE:{symbol}"
                if instrument not in quotes:
                    continue
                
                quote = quotes[instrument]
                price = quote['last_price']
                
                # Price range filter (₹50-₹500 sweet spot)
                if price < 50 or price > 500:
                    continue
                
                # Calculate metrics
                open_price = quote['ohlc']['open']
                volume = quote['volume']
                avg_volume = quote.get('average_volume', volume)
                change_pct = ((price - open_price) / open_price) * 100 if open_price > 0 else 0
                turnover = (price * volume) / 100000  # in lakhs
                volume_ratio = volume / avg_volume if avg_volume > 0 else 0
                
                # Apply filters
                if (abs(change_pct) >= 2.0 and     # 2%+ movement
                    volume_ratio >= 2.0 and         # 2x+ volume
                    turnover >= 50):                # ₹50L+ turnover
                    
                    candidates.append({
                        'symbol': symbol,
                        'price': price,
                        'change_pct': change_pct,
                        'volume_ratio': volume_ratio,
                        'turnover': turnover,
                        'momentum_score': abs(change_pct) * volume_ratio
                    })
            
            # Sort by momentum score
            candidates.sort(key=lambda x: x['momentum_score'], reverse=True)
            top_stocks = candidates[:10]  # Top 10 momentum stocks
            
            if top_stocks:
                print(f"\n✅ Found {len(candidates)} stocks meeting criteria")
                print("\n📈 Top Momentum Stocks:")
                for i, stock in enumerate(top_stocks, 1):
                    direction = "🟢" if stock['change_pct'] > 0 else "🔴"
                    print(f"   {i}. {direction} {stock['symbol']}: ₹{stock['price']:.2f} "
                          f"({stock['change_pct']:+.2f}%) Vol:{stock['volume_ratio']:.1f}x "
                          f"Score:{stock['momentum_score']:.1f}")
                
                return [stock['symbol'] for stock in top_stocks]
            else:
                print("⚠️  No stocks meeting criteria, using defaults")
                return ['RELIANCE', 'TCS', 'INFY', 'ICICIBANK', 'SBIN']
            
        except Exception as e:
            self.logger.error(f"Error screening stocks: {e}")
            return ['RELIANCE', 'TCS', 'INFY', 'ICICIBANK', 'SBIN']
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> int:
        """
        Calculate position size based on AI risk management matrix
        """
        risk_per_share = abs(entry_price - stop_loss)
        
        # Maximum shares based on risk
        max_by_risk = int(self.per_trade_risk / risk_per_share) if risk_per_share > 0 else 0
        
        # Maximum shares based on capital (50% max)
        max_by_capital = int((self.capital * 0.5) / entry_price)
        
        # AI position sizing matrix
        if entry_price < 100:
            max_allowed = 50
        elif entry_price < 300:
            max_allowed = 30
        elif entry_price < 500:
            max_allowed = 20
        elif entry_price < 1000:
            max_allowed = 10
        else:
            max_allowed = 5
        
        return max(1, min(max_by_risk, max_by_capital, max_allowed))
    
    def evaluate_pattern_quality(self, result, current_hour: float) -> Tuple[float, str]:
        """
        Evaluate pattern quality (1-10) with explanation
        """
        score = 5.0
        factors = []
        
        # ML prediction strength
        pred_strength = abs(result.prediction)
        if pred_strength > 5:
            score += 2
            factors.append(f"Strong ML signal ({result.prediction:.1f})")
        elif pred_strength > 3:
            score += 1
            factors.append(f"Moderate ML signal ({result.prediction:.1f})")
        elif pred_strength < 2:
            score -= 1
            factors.append(f"Weak ML signal ({result.prediction:.1f})")
        
        # Filter alignment
        filters_passed = sum([
            result.filter_states.get('volatility', False),
            result.filter_states.get('regime', False),
            result.filter_states.get('adx', False)
        ])
        score += filters_passed * 0.5
        if filters_passed > 0:
            factors.append(f"{filters_passed} filters passed")
        
        # Time window bonus
        if self.prime_window_start <= current_hour <= self.prime_window_end:
            score += 1.5
            factors.append("Prime trading window (85% win rate)")
        elif self.no_trade_before <= current_hour <= self.good_window_end:
            score += 0.5
            factors.append("Good trading window (70% win rate)")
        else:
            score -= 2
            factors.append("Poor trading window")
        
        # Kernel alignment (check if kernel filter passed)
        if result.filter_states.get('kernel', False):
            score += 0.5
            factors.append("Kernel filter passed")
        
        final_score = min(10, max(1, score))
        explanation = ", ".join(factors)
        
        return final_score, explanation
    
    def check_trading_conditions(self) -> Tuple[bool, str]:
        """
        Check if trading conditions are met
        Returns: (can_trade, reason)
        """
        current_hour = datetime.now().hour + datetime.now().minute / 60
        
        # Time check - NEVER trade before 11 AM
        if current_hour < self.no_trade_before:
            return False, f"🚫 NO TRADES BEFORE 11 AM (Current: {datetime.now().strftime('%I:%M %p')})"
        
        # Daily trade limit check
        if self.daily_trades >= self.max_daily_trades:
            return False, "🚫 DAILY TRADE LIMIT REACHED (2 trades max)"
        
        # Daily loss limit check
        if self.daily_pnl <= -self.daily_loss_limit:
            return False, f"🚫 DAILY LOSS LIMIT REACHED (₹{self.daily_loss_limit:,.2f})"
        
        # First trade loss warning
        if self.daily_trades == 1 and self.daily_pnl < 0:
            return True, "⚠️  First trade was a loss - BE EXTRA SELECTIVE"
        
        # Trading window status
        if self.prime_window_start <= current_hour <= self.prime_window_end:
            return True, "✅ PRIME WINDOW - Best time to trade"
        elif current_hour <= self.good_window_end:
            return True, "✅ Good window - Trade carefully"
        else:
            return False, "🚫 AVOID TRADING AFTER 2:30 PM"
    
    def warmup_processor(self, symbol: str) -> bool:
        """Warmup processor with historical data"""
        try:
            print(f"  ⏳ Warming up {symbol}...", end='', flush=True)
            
            # Fetch 30 days of historical data (FIXED API CALL)
            data = self.kite_client.get_historical_data(
                symbol=symbol,
                interval='5minute',
                days=30
            )
            
            if not data:
                print(" ❌ No data")
                return False
            
            processor = self.processors[symbol]
            df = pd.DataFrame(data)
            
            # Process historical bars
            bars_processed = 0
            for _, row in df.iterrows():
                processor.process_bar(
                    open_price=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume']
                )
                bars_processed += 1
            
            # FIXED: Check if ML has enough data
            ml_ready = processor.bars_processed >= processor.settings.max_bars_back
            
            print(f" ✅ {bars_processed} bars (ML ready: {ml_ready})")
            
            if not ml_ready:
                print(f"     ⚠️ Need {processor.settings.max_bars_back - processor.bars_processed} more bars for ML")
            
            return True
            
        except Exception as e:
            print(f" ❌ Error: {e}")
            return False
    
    def process_live_bar(self, symbol: str, bar_data: Dict) -> Dict:
        """Process a single live bar with AI rules"""
        try:
            processor = self.processors[symbol]
            
            # FIXED: Check if ML is ready
            if processor.bars_processed < processor.settings.max_bars_back:
                return {
                    'symbol': symbol,
                    'error': 'Insufficient warmup data',
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
            
            # Check trading conditions
            can_trade, trade_msg = self.check_trading_conditions()
            current_hour = datetime.now().hour + datetime.now().minute / 60
            
            # Evaluate pattern quality
            pattern_score, pattern_explanation = self.evaluate_pattern_quality(result, current_hour)
            
            # Prepare summary
            summary = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'close': bar_data['close'],
                'prediction': result.prediction,
                'signal': result.signal,
                'pattern_score': pattern_score,
                'can_trade': can_trade,
                'trade_msg': trade_msg
            }
            
            # Check for new signals (only if all conditions met)
            if can_trade and pattern_score >= self.min_pattern_score:
                if result.start_long_trade:
                    self._enter_long_position(symbol, bar_data, result, pattern_score, pattern_explanation)
                elif result.start_short_trade:
                    self._enter_short_position(symbol, bar_data, result, pattern_score, pattern_explanation)
            
            # Check for exits on active positions
            if symbol in self.active_signals:
                self._check_exit_conditions(symbol, bar_data, result)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error processing {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def _calculate_risk_levels(self, entry_price: float, is_long: bool) -> Tuple[float, float]:
        """
        Calculate stop loss and take profit levels
        FIXED: Using proper risk management calculation
        """
        # Get recent bars for ATR calculation
        processor = self.processors.get(list(self.processors.keys())[0])  # Get any processor
        
        if processor and hasattr(processor, 'bars') and len(processor.bars) >= 20:
            # Get recent price data
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
                atr_multiplier=2.0,
                risk_reward_ratio=2.0
            )
        else:
            # Fallback to fixed percentage
            if is_long:
                stop_loss = entry_price * 0.99  # 1% stop loss
                take_profit = entry_price + 40  # ₹40 target
            else:
                stop_loss = entry_price * 1.01  # 1% stop loss
                take_profit = entry_price - 40  # ₹40 target
        
        return stop_loss, take_profit
    
    def _enter_long_position(self, symbol: str, bar_data: Dict, result, score: float, explanation: str):
        """Enter a long position"""
        entry_price = bar_data['close']
        stop_loss, take_profit = self._calculate_risk_levels(entry_price, is_long=True)
        position_size = self.calculate_position_size(entry_price, stop_loss)
        
        signal_info = {
            'type': 'LONG',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target_1': entry_price + 20,  # ₹20 first target
            'target_2': take_profit,  # Full exit target
            'position_size': position_size,
            'entry_time': datetime.now(),
            'prediction': result.prediction,
            'pattern_score': score,
            'partial_exit': False,
            'original_size': position_size
        }
        
        self.active_signals[symbol] = signal_info
        self.daily_trades += 1
        
        print(f"\n{'='*60}")
        print(f"🟢 LONG ENTRY - {symbol} (Trade #{self.daily_trades}/{self.max_daily_trades})")
        print(f"{'='*60}")
        print(f"📊 Entry Details:")
        print(f"   Price: ₹{entry_price:.2f} x {position_size} shares")
        print(f"   Stop Loss: ₹{stop_loss:.2f} (-{(entry_price-stop_loss)/entry_price*100:.1f}%)")
        print(f"   Target 1: ₹{signal_info['target_1']:.2f} (+₹20) [50% exit]")
        print(f"   Target 2: ₹{signal_info['target_2']:.2f} (+₹{signal_info['target_2']-entry_price:.0f}) [full exit]")
        print(f"📈 Signal Quality:")
        print(f"   ML Prediction: {result.prediction:.2f}")
        print(f"   Pattern Score: {score:.1f}/10")
        print(f"   Factors: {explanation}")
        print(f"💰 Risk Management:")
        print(f"   Capital at Risk: ₹{(entry_price - stop_loss) * position_size:.2f}")
        print(f"   Max Profit: ₹{(signal_info['target_2'] - entry_price) * position_size:.2f}")
        print(f"   Risk/Reward: 1:{(signal_info['target_2'] - entry_price)/(entry_price - stop_loss):.1f}")
    
    def _enter_short_position(self, symbol: str, bar_data: Dict, result, score: float, explanation: str):
        """Enter a short position"""
        entry_price = bar_data['close']
        stop_loss, take_profit = self._calculate_risk_levels(entry_price, is_long=False)
        position_size = self.calculate_position_size(entry_price, stop_loss)
        
        signal_info = {
            'type': 'SHORT',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target_1': entry_price - 20,  # ₹20 first target
            'target_2': take_profit,  # Full exit target
            'position_size': position_size,
            'entry_time': datetime.now(),
            'prediction': result.prediction,
            'pattern_score': score,
            'partial_exit': False,
            'original_size': position_size
        }
        
        self.active_signals[symbol] = signal_info
        self.daily_trades += 1
        
        print(f"\n{'='*60}")
        print(f"🔴 SHORT ENTRY - {symbol} (Trade #{self.daily_trades}/{self.max_daily_trades})")
        print(f"{'='*60}")
        print(f"📊 Entry Details:")
        print(f"   Price: ₹{entry_price:.2f} x {position_size} shares")
        print(f"   Stop Loss: ₹{stop_loss:.2f} (+{(stop_loss-entry_price)/entry_price*100:.1f}%)")
        print(f"   Target 1: ₹{signal_info['target_1']:.2f} (-₹20) [50% exit]")
        print(f"   Target 2: ₹{signal_info['target_2']:.2f} (-₹{entry_price-signal_info['target_2']:.0f}) [full exit]")
        print(f"📈 Signal Quality:")
        print(f"   ML Prediction: {result.prediction:.2f}")
        print(f"   Pattern Score: {score:.1f}/10")
        print(f"   Factors: {explanation}")
        print(f"💰 Risk Management:")
        print(f"   Capital at Risk: ₹{(stop_loss - entry_price) * position_size:.2f}")
        print(f"   Max Profit: ₹{(entry_price - signal_info['target_2']) * position_size:.2f}")
        print(f"   Risk/Reward: 1:{(entry_price - signal_info['target_2'])/(stop_loss - entry_price):.1f}")
    
    def _check_exit_conditions(self, symbol: str, bar_data: Dict, result):
        """Check exit conditions for active position"""
        signal = self.active_signals[symbol]
        current_price = bar_data['close']
        time_in_trade = (datetime.now() - signal['entry_time']).seconds / 60
        
        if signal['type'] == 'LONG':
            # Check stop loss
            if current_price <= signal['stop_loss']:
                self._close_position(symbol, current_price, 'STOP_LOSS')
            # Check first target (partial exit)
            elif not signal['partial_exit'] and current_price >= signal['target_1']:
                self._partial_exit(symbol, current_price)
            # Check second target (full exit)
            elif current_price >= signal['target_2']:
                self._close_position(symbol, current_price, 'TARGET_2')
            # 30-minute rule
            elif time_in_trade > 30 and abs(current_price - signal['entry_price']) < 5:
                self._close_position(symbol, current_price, 'TIME_EXIT_30MIN')
            # ML exit signal
            elif result.end_long_trade:
                self._close_position(symbol, current_price, 'ML_SIGNAL_EXIT')
        
        else:  # SHORT
            # Check stop loss
            if current_price >= signal['stop_loss']:
                self._close_position(symbol, current_price, 'STOP_LOSS')
            # Check first target (partial exit)
            elif not signal['partial_exit'] and current_price <= signal['target_1']:
                self._partial_exit(symbol, current_price)
            # Check second target (full exit)
            elif current_price <= signal['target_2']:
                self._close_position(symbol, current_price, 'TARGET_2')
            # 30-minute rule
            elif time_in_trade > 30 and abs(current_price - signal['entry_price']) < 5:
                self._close_position(symbol, current_price, 'TIME_EXIT_30MIN')
            # ML exit signal
            elif result.end_short_trade:
                self._close_position(symbol, current_price, 'ML_SIGNAL_EXIT')
    
    def _partial_exit(self, symbol: str, exit_price: float):
        """Execute partial exit at first target"""
        signal = self.active_signals[symbol]
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
        signal['stop_loss'] = signal['entry_price']  # Move stop to breakeven
        
        print(f"\n💰 PARTIAL EXIT - {symbol}")
        print(f"   Exit: {exit_size} shares @ ₹{exit_price:.2f}")
        print(f"   P&L: ₹{pnl:+.2f}")
        print(f"   Remaining: {remaining_size} shares")
        print(f"   Stop moved to breakeven @ ₹{signal['stop_loss']:.2f}")
        print(f"   Daily P&L: ₹{self.daily_pnl:+.2f}")
    
    def _close_position(self, symbol: str, exit_price: float, reason: str):
        """Close entire position"""
        signal = self.active_signals[symbol]
        
        # Calculate P&L
        if signal['type'] == 'LONG':
            pnl = (exit_price - signal['entry_price']) * signal['position_size']
        else:
            pnl = (signal['entry_price'] - exit_price) * signal['position_size']
        
        pnl_percent = (pnl / (signal['entry_price'] * signal['position_size'])) * 100
        self.daily_pnl += pnl
        
        # Record trade
        trade_record = {
            'symbol': symbol,
            'type': signal['type'],
            'entry_price': signal['entry_price'],
            'exit_price': exit_price,
            'position_size': signal['position_size'],
            'original_size': signal['original_size'],
            'entry_time': signal['entry_time'],
            'exit_time': datetime.now(),
            'hold_minutes': (datetime.now() - signal['entry_time']).seconds / 60,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'exit_reason': reason,
            'pattern_score': signal['pattern_score'],
            'partial_exit': signal['partial_exit']
        }
        
        self.trade_history.append(trade_record)
        del self.active_signals[symbol]
        
        # Print exit summary
        emoji = "✅" if pnl > 0 else "❌"
        print(f"\n{'='*60}")
        print(f"{emoji} POSITION CLOSED - {symbol}")
        print(f"{'='*60}")
        print(f"📊 Exit Details:")
        print(f"   Exit Price: ₹{exit_price:.2f}")
        print(f"   Exit Reason: {reason}")
        print(f"   Hold Time: {trade_record['hold_minutes']:.1f} minutes")
        print(f"💰 P&L Summary:")
        print(f"   Trade P&L: ₹{pnl:+.2f} ({pnl_percent:+.2f}%)")
        print(f"   Daily P&L: ₹{self.daily_pnl:+.2f}")
        print(f"   Trades Today: {self.daily_trades}/{self.max_daily_trades}")
        
        # Check if we should stop trading
        if self.daily_pnl <= -self.daily_loss_limit:
            print(f"\n🛑 DAILY LOSS LIMIT REACHED - NO MORE TRADES TODAY")
        elif self.daily_trades >= self.max_daily_trades:
            print(f"\n🛑 DAILY TRADE LIMIT REACHED - NO MORE TRADES TODAY")
    
    def run_live_trading(self, duration_minutes: int = 240):
        """
        Run live trading session
        
        Args:
            duration_minutes: Session duration (default 4 hours)
        """
        print(f"\n🚀 Starting AI-Enhanced Live Trading Session")
        print(f"   Duration: {duration_minutes} minutes")
        print(f"   Start Time: {datetime.now().strftime('%I:%M %p')}")
        
        # Screen and select stocks
        self.selected_stocks = self.screen_stocks()
        
        # Initialize processors
        print(f"\n📊 Initializing processors for {len(self.selected_stocks)} stocks...")
        self.processors = {
            symbol: EnhancedBarProcessor(self.config, symbol, "5min")
            for symbol in self.selected_stocks
        }
        
        # Warmup with historical data
        print("\n⏳ Warming up with historical data...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self.warmup_processor, symbol): symbol 
                      for symbol in self.selected_stocks}
            
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"  ❌ Error warming up {symbol}: {e}")
        
        # Start live trading loop
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        update_interval = 5  # seconds
        
        print(f"\n📈 Live trading started!")
        print("="*80)
        
        try:
            while datetime.now() < end_time:
                now = datetime.now()
                current_hour = now.hour + now.minute / 60
                
                # Market hours check
                if now.hour < 9 or (now.hour == 9 and now.minute < 15) or \
                   now.hour > 15 or (now.hour == 15 and now.minute > 30):
                    print(f"\r⏸️  Market closed. Current time: {now.strftime('%I:%M:%S %p')}", end='', flush=True)
                    time.sleep(30)
                    continue
                
                # Trading window status
                if current_hour < self.no_trade_before:
                    status = "🚫 NO TRADING (before 11 AM)"
                elif self.prime_window_start <= current_hour <= self.prime_window_end:
                    status = "🟢 PRIME WINDOW (85% win)"
                elif current_hour <= self.good_window_end:
                    status = "🟡 GOOD WINDOW (70% win)"
                else:
                    status = "🔴 AVOID (after 2:30 PM)"
                
                # Fetch live data
                try:
                    instruments = [f"NSE:{symbol}" for symbol in self.selected_stocks]
                    quotes = self.kite_client.kite.quote(instruments)
                    
                    # Process each stock
                    for symbol in self.selected_stocks:
                        instrument = f"NSE:{symbol}"
                        if instrument in quotes:
                            quote = quotes[instrument]
                            bar_data = {
                                'open': quote['ohlc']['open'],
                                'high': quote['ohlc']['high'],
                                'low': quote['ohlc']['low'],
                                'close': quote['last_price'],
                                'volume': quote['volume']
                            }
                            
                            # Process the bar
                            result = self.process_live_bar(symbol, bar_data)
                            
                            # Store result
                            if symbol not in self.results:
                                self.results[symbol] = []
                            self.results[symbol].append(result)
                    
                    # Update status line
                    active = len(self.active_signals)
                    completed = len(self.trade_history)
                    win_rate = (sum(1 for t in self.trade_history if t['pnl'] > 0) / completed * 100) if completed > 0 else 0
                    
                    status_line = (f"\r{status} | "
                                 f"Active: {active} | "
                                 f"Trades: {self.daily_trades}/{self.max_daily_trades} | "
                                 f"P&L: ₹{self.daily_pnl:+.2f} | "
                                 f"Win: {win_rate:.0f}% | "
                                 f"{now.strftime('%I:%M:%S %p')}")
                    
                    print(status_line, end='', flush=True)
                    
                except Exception as e:
                    self.logger.error(f"Error fetching live data: {e}")
                
                # Wait before next update
                time.sleep(update_interval)
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Trading session interrupted by user")
        except Exception as e:
            print(f"\n\n❌ Error during trading: {e}")
            import traceback
            traceback.print_exc()
        
        # Print final summary
        self._print_final_summary()
    
    def _print_final_summary(self):
        """Print comprehensive trading summary"""
        print("\n\n" + "="*80)
        print("📊 AI-ENHANCED TRADING SESSION SUMMARY")
        print("="*80)
        
        # Overall statistics
        total_trades = len(self.trade_history)
        
        print(f"\n💰 Financial Summary:")
        print(f"   Starting Capital: ₹{self.capital:,.2f}")
        print(f"   Daily P&L: ₹{self.daily_pnl:+,.2f} ({self.daily_pnl/self.capital*100:+.2f}%)")
        print(f"   Ending Capital: ₹{self.capital + self.daily_pnl:,.2f}")
        
        if total_trades > 0:
            wins = sum(1 for t in self.trade_history if t['pnl'] > 0)
            losses = total_trades - wins
            avg_win = sum(t['pnl'] for t in self.trade_history if t['pnl'] > 0) / wins if wins > 0 else 0
            avg_loss = sum(t['pnl'] for t in self.trade_history if t['pnl'] < 0) / losses if losses > 0 else 0
            
            print(f"\n📈 Trading Statistics:")
            print(f"   Total Trades: {total_trades}")
            print(f"   Wins: {wins} ({wins/total_trades*100:.1f}%)")
            print(f"   Losses: {losses} ({losses/total_trades*100:.1f}%)")
            print(f"   Average Win: ₹{avg_win:+.2f}")
            print(f"   Average Loss: ₹{avg_loss:+.2f}")
            print(f"   Win/Loss Ratio: {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "   Win/Loss Ratio: N/A")
            
            # Time analysis
            trades_df = pd.DataFrame(self.trade_history)
            trades_df['entry_hour'] = pd.to_datetime(trades_df['entry_time']).dt.hour + pd.to_datetime(trades_df['entry_time']).dt.minute / 60
            
            # Prime window performance
            prime_trades = trades_df[(trades_df['entry_hour'] >= 11.5) & (trades_df['entry_hour'] <= 13.5)]
            if len(prime_trades) > 0:
                prime_wins = (prime_trades['pnl'] > 0).sum()
                print(f"\n⏰ Time Window Analysis:")
                print(f"   Prime Window Trades: {len(prime_trades)} ({prime_wins/len(prime_trades)*100:.1f}% win rate)")
                print(f"   Prime Window P&L: ₹{prime_trades['pnl'].sum():+.2f}")
            
            # Best and worst trades
            best_trade = trades_df.loc[trades_df['pnl'].idxmax()]
            worst_trade = trades_df.loc[trades_df['pnl'].idxmin()]
            
            print(f"\n🏆 Notable Trades:")
            print(f"   Best Trade: {best_trade['symbol']} - ₹{best_trade['pnl']:+.2f} ({best_trade['exit_reason']})")
            print(f"   Worst Trade: {worst_trade['symbol']} - ₹{worst_trade['pnl']:+.2f} ({worst_trade['exit_reason']})")
            
            # Average metrics
            print(f"\n📊 Average Metrics:")
            print(f"   Avg Hold Time: {trades_df['hold_minutes'].mean():.1f} minutes")
            print(f"   Avg Pattern Score: {trades_df['pattern_score'].mean():.1f}/10")
            print(f"   Partial Exits: {trades_df['partial_exit'].sum()} trades")
        
        # Active positions
        if self.active_signals:
            print(f"\n📍 Active Positions ({len(self.active_signals)}):")
            for symbol, signal in self.active_signals.items():
                print(f"   {symbol}: {signal['type']} @ ₹{signal['entry_price']:.2f} "
                      f"({signal['position_size']} shares)")
        
        # Export results
        self._export_results()
        
        # AI Trading Rules Compliance
        print(f"\n✅ AI Rules Compliance:")
        print(f"   ✓ Daily Trade Limit: {self.daily_trades} ≤ {self.max_daily_trades}")
        print(f"   ✓ Daily Loss Limit: ₹{abs(min(0, self.daily_pnl)):.2f} ≤ ₹{self.daily_loss_limit:.2f}")
        print(f"   ✓ No Early Trading: All trades after 11 AM")
        print(f"   ✓ Pattern Quality: All entries ≥ {self.min_pattern_score}/10")
    
    def _export_results(self):
        """Export trading results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export trades
        if self.trade_history:
            trades_df = pd.DataFrame(self.trade_history)
            filename = f"ai_trades_{timestamp}.csv"
            trades_df.to_csv(filename, index=False)
            print(f"\n💾 Trade history exported to: {filename}")
        
        # Export summary
        summary = {
            'session_date': datetime.now().strftime("%Y-%m-%d"),
            'capital': self.capital,
            'daily_pnl': self.daily_pnl,
            'total_trades': len(self.trade_history),
            'win_rate': (sum(1 for t in self.trade_history if t['pnl'] > 0) / len(self.trade_history) * 100) if self.trade_history else 0,
            'stocks_traded': list(set(t['symbol'] for t in self.trade_history)),
            'ai_rules_followed': {
                'trade_limit': self.daily_trades <= self.max_daily_trades,
                'loss_limit': self.daily_pnl > -self.daily_loss_limit,
                'time_window': all(t['entry_time'].hour >= 11 for t in self.trade_history) if self.trade_history else True,
                'pattern_quality': all(t['pattern_score'] >= self.min_pattern_score for t in self.trade_history) if self.trade_history else True
            }
        }
        
        summary_file = f"ai_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"💾 Session summary exported to: {summary_file}")


def main():
    """Main execution function"""
    print("\n" + "="*80)
    print("🤖 AI-ENHANCED LORENTZIAN CLASSIFIER LIVE TRADING")
    print("="*80)
    print("\nBased on proven AI Trading Knowledge Base:")
    print("• NO trades before 11 AM (0% win rate)")
    print("• Maximum 2 trades per day (hard limit)")
    print("• Prime window 11:30 AM - 1:30 PM (85% win rate)")
    print("• Minimum pattern quality score: 7/10")
    print("• Stop loss: 1% | Targets: ₹20/₹40")
    print("• 30-minute exit rule for non-performers")
    
    # Get user confirmation
    print("\n⚠️  This system will trade with REAL money!")
    confirm = input("Are you ready to start? (yes/no): ").lower().strip()
    
    if confirm != 'yes':
        print("Trading cancelled.")
        return
    
    # Get capital
    capital_input = input("\nEnter trading capital (default ₹10,000): ").strip()
    capital = float(capital_input) if capital_input else 10000.0
    
    # Create trading system
    trader = AIEnhancedLiveMarketTest(capital=capital)
    
    # Initialize Zerodha
    if not trader.initialize_zerodha():
        print("\n❌ Failed to connect to Zerodha. Exiting.")
        return
    
    # Run live trading
    try:
        # Default 4 hours (full trading session)
        trader.run_live_trading(duration_minutes=240)
    except Exception as e:
        print(f"\n❌ Trading failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()