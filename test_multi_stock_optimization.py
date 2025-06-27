u"""
Multi-Stock Optimization Framework
=
=================================

Tests the comprehensive Lorentzian system across multiple stocks
with intelligent configuration and exit management.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
# from tabulate import tabulate  # Optional, will use simple formatting if not available
try:
    from tabulate import tabulate
except ImportError:
    tabulate = None
import warnings
warnings.filterwarnings('ignore')

# Import our components
from data.smart_data_manager import SmartDataManager
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from scanner.ml_quality_filter import MLQualityFilter
from scanner.smart_exit_manager import SmartExitManager
from config.adaptive_config import create_adaptive_config
from data.data_types import Settings, FilterSettings
from utils.kelly_criterion import KellyCriterion


class MultiStockOptimizer:
    """
    Framework for testing and optimizing across multiple stocks
    """
    
    def __init__(self, symbols: List[str], timeframe: str = "5minute",
                 lookback_days: int = 90):
        """
        Initialize multi-stock optimizer
        
        Args:
            symbols: List of stock symbols to test
            timeframe: Timeframe for analysis
            lookback_days: Days of historical data
        """
        self.symbols = symbols
        self.timeframe = timeframe
        self.lookback_days = lookback_days
        
        # Check for saved session
        if os.path.exists('.kite_session.json'):
            with open('.kite_session.json', 'r') as f:
                session_data = json.load(f)
                access_token = session_data.get('access_token')
                if access_token:
                    os.environ['KITE_ACCESS_TOKEN'] = access_token
        
        # Initialize components
        self.data_manager = SmartDataManager()
        self.ml_filter = MLQualityFilter(min_confidence=3.0, high_confidence=5.0)
        
        # Results storage
        self.results = {}
        self.detailed_trades = {}
        
        # Ensure we have sufficient data for all stocks
        self._ensure_sufficient_data()
    
    def _ensure_sufficient_data(self):
        """Ensure all stocks have sufficient data for testing"""
        min_required_bars = 2500
        
        print(f"\n{'='*60}")
        print("CHECKING DATA AVAILABILITY")
        print(f"{'='*60}")
        
        # Market is open ~6.5 hours per day, with 5-minute intervals
        # That's 78 bars per day (6.5 * 60 / 5)
        # But accounting for gaps, holidays etc, we get ~75 bars per day
        bars_per_day = 75 if self.timeframe == "5minute" else 1
        
        for symbol in self.symbols:
            # First check what we have with current lookback_days
            df = self.data_manager.get_data(
                symbol=symbol,
                interval=self.timeframe,
                days=self.lookback_days
            )
            
            current_bars = len(df) if df is not None else 0
            print(f"\n{symbol}: {current_bars} bars available with {self.lookback_days} days lookback")
            
            if current_bars < min_required_bars:
                print(f"  ⚠️  Insufficient data (need {min_required_bars}+)")
                
                # Progressively try more days until we get enough bars
                # Start with double the current days and increase if needed
                days_to_try = [self.lookback_days * 2, 250, 365, 500, 730]
                
                for days in days_to_try:
                    print(f"  📊 Trying {days} days of {self.timeframe} data...")
                    
                    # Try to fetch more data
                    df_extended = self.data_manager.get_data(
                        symbol=symbol,
                        interval=self.timeframe,
                        days=days
                    )
                    
                    new_bars = len(df_extended) if df_extended is not None else 0
                    print(f"     Got {new_bars} bars")
                    
                    if new_bars >= min_required_bars:
                        print(f"  ✅ Successfully obtained {new_bars} bars with {days} days lookback")
                        # Update lookback for this run to ensure consistency
                        self.actual_days_fetched = max(getattr(self, 'actual_days_fetched', self.lookback_days), days)
                        break
                else:
                    # If we exhausted all options
                    print(f"  ❌ Could not get sufficient data. Maximum found: {new_bars} bars")
                    print(f"     This stock may have limited history or be recently listed")
            else:
                print(f"  ✅ Sufficient data available")
    
    def run_baseline_test(self, use_ml_filter: bool = True,
                         use_smart_exits: bool = True) -> Dict:
        """
        Run baseline test across all stocks
        
        Args:
            use_ml_filter: Whether to use ML quality filtering
            use_smart_exits: Whether to use smart exit management
            
        Returns:
            Aggregated results
        """
        print(f"\n{'='*60}")
        print(f"Running Baseline Test - {len(self.symbols)} stocks")
        print(f"ML Filter: {use_ml_filter}, Smart Exits: {use_smart_exits}")
        print(f"{'='*60}\n")
        
        # Test each stock
        for symbol in self.symbols:
            print(f"\nProcessing {symbol}...")
            try:
                result = self._test_single_stock(
                    symbol, 
                    use_ml_filter=use_ml_filter,
                    use_smart_exits=use_smart_exits
                )
                self.results[symbol] = result
            except Exception as e:
                import traceback
                print(f"Error processing {symbol}: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                self.results[symbol] = {'error': str(e)}
        
        # Generate summary
        summary = self._generate_summary()
        self._print_results(summary)
        
        return summary
    
    def _test_single_stock(self, symbol: str, use_ml_filter: bool,
                          use_smart_exits: bool, use_kelly_sizing: bool = True) -> Dict:
        """
        Test a single stock with current configuration
        
        Args:
            symbol: Stock symbol
            use_ml_filter: Whether to filter by ML quality
            use_smart_exits: Whether to use smart exit management
            use_kelly_sizing: Whether to use Kelly Criterion for position sizing
        """
        # Initialize Kelly Criterion calculator
        kelly_calc = KellyCriterion(kelly_fraction=0.25) if use_kelly_sizing else None
        
        # Get data - use actual_days_fetched if we had to fetch more
        days_to_use = getattr(self, 'actual_days_fetched', self.lookback_days)
        df = self.data_manager.get_data(
            symbol=symbol,
            interval=self.timeframe,
            days=days_to_use
        )
        
        # Need at least 2000 bars for warmup + some for trading
        min_required_bars = 2500
        
        if df is None or len(df) < min_required_bars:
            actual_bars = len(df) if df is not None else 0
            return {'error': f'Insufficient data: {actual_bars} bars (need {min_required_bars}+)'}
        
        # Get stock statistics for adaptive config
        stats = self.data_manager.analyze_price_movement(df)
        
        # Create adaptive configuration
        config = create_adaptive_config(symbol, self.timeframe, stats)
        
        # Initialize processor with TradingConfig
        from config.settings import TradingConfig
        
        # Create TradingConfig from adaptive config
        trading_config = TradingConfig(
            # Core settings
            source=config.source,
            neighbors_count=config.neighbors_count,
            max_bars_back=config.max_bars_back,
            feature_count=config.feature_count,
            color_compression=config.color_compression,
            
            # Filters
            use_volatility_filter=config.use_volatility_filter,
            use_regime_filter=config.use_regime_filter,
            use_adx_filter=config.use_adx_filter,
            use_kernel_filter=config.use_kernel_filter,
            use_ema_filter=config.use_ema_filter,
            use_sma_filter=config.use_sma_filter,
            
            # Filter parameters
            regime_threshold=config.regime_threshold,
            adx_threshold=config.adx_threshold,
            kernel_lookback=config.kernel_lookback,
            kernel_relative_weight=config.kernel_relative_weight,
            kernel_regression_level=config.kernel_regression_level,
            kernel_lag=config.kernel_lag,
            use_kernel_smoothing=config.use_kernel_smoothing,
            
            # Features
            features=config.features
        )
        
        processor = EnhancedBarProcessor(
            config=trading_config,
            symbol=symbol,
            timeframe=self.timeframe
        )
        
        # Initialize exit manager if using smart exits
        if use_smart_exits:
            # Exit configuration based on multiple sources:
            
            # 1. From Quantitative Trading Introduction (Howard B. Bandy):
            #    - "Risk no more than 1-2% of portfolio on any single trade" (Section 6.2)
            #    - "Only take setups where potential profit is at least 2x risk (2:1 P/L ratio)"
            #    - "Use hard stop-loss orders - discipline to honor stops is key"
            
            # 2. From Warrior Trading methodology:
            #    - High-velocity momentum scalping with quick exits
            #    - Focus on small, consistent profits ("base hits not home runs")
            #    - Time stops are critical for day trading
            
            # 3. From Rocket Science (John Ehlers):
            #    - Preference for wider "disaster stops" vs tight stops (Section 10)
            #    - ATR-based dynamic targets recommended by practitioners
            #    - Adaptive approach based on market conditions
            
            # Conservative configuration for 5-minute intraday trading:
            exit_config_conservative = {
                'stop_loss_percent': 1.0,      # 1% stop per Quantitative Trading risk management
                'take_profit_targets': [2.0],   # Single target at 2:1 risk/reward ratio
                'target_sizes': [100],          # Exit full position (no partials)
                'use_trailing_stop': False,     # Keep it simple initially
                'max_holding_bars': 78          # Full trading day (6.5 hours * 12 bars/hour)
            }
            
            # Warrior-style scalping configuration:
            exit_config_scalping = {
                'stop_loss_percent': 0.5,                    # Tighter stop for scalping
                'take_profit_targets': [0.25, 0.5, 0.75],    # Quick profit targets
                'target_sizes': [100],                       # Full position exit
                'use_trailing_stop': True,
                'trailing_activation': 0.25,                 # Activate after first target
                'trailing_distance': 0.15,                   # Tight trailing
                'max_holding_bars': 12                       # 1 hour max (scalping timeframe)
            }
            
            # Ehlers-inspired adaptive configuration:
            exit_config_adaptive = {
                'stop_loss_percent': 2.0,       # Wider "disaster stop" per Ehlers
                'take_profit_targets': [1.0, 2.0, 3.0],  # ATR-based would be better
                'target_sizes': [40, 40, 20],   # Gradual exits
                'use_trailing_stop': True,
                'trailing_activation': 1.0,     # After first significant move
                'trailing_distance': 0.5,       # Wider trail for trends
                'max_holding_bars': 40          # ~3.3 hours
            }
            
            # ATR-based configuration (from Quantitative Trading principles):
            exit_config_atr = {
                'use_atr_stops': True,           # Enable ATR-based stops
                'atr_stop_multiplier': 2.0,      # 2x ATR for initial stop
                'atr_profit_multipliers': [1.5, 3.0, 5.0],  # Risk/reward ratios
                'target_sizes': [50, 30, 20],    # Gradual exits
                'use_trailing_stop': True,
                'atr_trailing_multiplier': 1.5,  # Tighter trail than initial stop
                'max_holding_bars': 78           # Full trading day
            }
            
            # Select exit strategy based on method argument or default
            # This allows testing different approaches systematically
            exit_strategy = getattr(self, 'exit_strategy', 'conservative')
            
            if exit_strategy == 'conservative':
                exit_config = exit_config_conservative.copy()
            elif exit_strategy == 'scalping':
                exit_config = exit_config_scalping.copy()
            elif exit_strategy == 'adaptive':
                exit_config = exit_config_adaptive.copy()
            elif exit_strategy == 'atr':
                exit_config = exit_config_atr.copy()
            else:
                # Default to conservative if unknown strategy
                exit_config = exit_config_conservative.copy()
            
            # IMPORTANT NOTE from Quantitative Trading Introduction (Directive 3.4):
            # "Good exits are noted as being able to salvage almost any system"
            # This emphasizes that exit strategy is CRITICAL to profitability
            
            # Note: Future enhancement would be to adapt exit strategy based on:
            # - Market volatility (ATR)
            # - Stock characteristics (from adaptive_config)
            # - Market mode (trending vs cycling per Ehlers)
            # Merge with adaptive config
            exit_config.update(config.__dict__)
            
            # Create exit manager with ATR support if needed
            use_atr = exit_config.get('use_atr_stops', False)
            exit_manager = SmartExitManager(exit_config, use_atr_stops=use_atr)
        else:
            exit_manager = None
        
        # Process bars and collect signals
        signals = []
        trades = []
        position = None
        current_date = None
        
        for idx, row in df.iterrows():
            # Get date and time info for intraday management
            bar_date = idx.date() if hasattr(idx, 'date') else idx
            bar_time = idx.time() if hasattr(idx, 'time') else None
            
            # Check if new trading day - must close any overnight positions
            if current_date and bar_date != current_date and position:
                # Force exit at last bar of previous day
                exit_price = row['open']  # Use open price of new day as proxy for previous close
                
                # Position is always a dict in our implementation
                entry_price = position['entry_price']
                direction = position['direction']
                
                # Calculate PnL correctly based on position direction
                if direction == 1:  # LONG position
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                else:  # SHORT position (direction == -1)
                    pnl_pct = (entry_price - exit_price) / entry_price * 100
                
                # Calculate bars held (we don't have result yet since this is before processing)
                bars_held = 1  # Conservative estimate for day-end exits
                
                trades.append({
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'bars_held': max(1, bars_held),
                    'direction': direction,
                    'exit_reason': 'day_end',  # Mark as forced day-end exit
                    'quantity': position.get('quantity', 100),
                    'is_partial': False  # Day-end exits are always full exits
                })
                
                # Clear position from exit manager if needed
                if exit_manager and symbol in exit_manager.positions:
                    del exit_manager.positions[symbol]
                    
                position = None
            
            current_date = bar_date
            
            # Update ATR if using ATR-based exits
            if exit_manager and hasattr(exit_manager, 'update_atr'):
                exit_manager.update_atr(row['high'], row['low'], row['close'])
            
            # Process bar
            result = processor.process_bar(
                open_price=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume']
            )
            
            # Skip if no result
            if result is None:
                continue
                
            # Get current state from result
            current_signal = result.signal
            ml_prediction = result.prediction
            
            # Create signal dict
            signal_dict = {
                'timestamp': idx,
                'signal': current_signal,
                'prediction': ml_prediction,
                'filter_states': result.filter_states,
                'features': {}  # Features not directly accessible from result
            }
            
            # Apply ML filter if enabled
            if use_ml_filter and current_signal != 0:
                ml_signal = self.ml_filter.filter_signal(signal_dict, symbol)
                if ml_signal is None:
                    current_signal = 0  # Filter out low confidence signals
            
            # Check exits if in position
            if position and exit_manager and symbol in exit_manager.positions:
                # The position in exit_manager is a Position object, not our dict
                exit_pos = exit_manager.positions[symbol]
                
                # Update current price for the Position object
                exit_pos.current_price = row['close']
                
                # Update max profit for trailing stop
                if exit_pos.direction == 1:
                    current_profit = (row['close'] - exit_pos.entry_price) / exit_pos.entry_price * 100
                else:
                    current_profit = (exit_pos.entry_price - row['close']) / exit_pos.entry_price * 100
                exit_pos.max_profit = max(exit_pos.max_profit, current_profit)
                
                exit_signal = exit_manager.check_exit(
                    symbol=symbol,
                    current_price=row['close'],
                    current_ml_signal=ml_prediction,
                    timestamp=idx,
                    high=row['high'],
                    low=row['low']
                )
                
                if exit_signal and exit_signal.should_exit:
                    # Execute exit
                    exit_record = exit_manager.execute_exit(symbol, exit_signal)
                    
                    # Convert to our trade format
                    # IMPORTANT: For partial exits, we need to scale the PnL by the exit quantity
                    exit_quantity = exit_record.get('quantity', 100)
                    # Get the original position quantity (not remaining)
                    original_quantity = 100  # Default position size
                    
                    # Scale PnL percentage by the portion of position being exited
                    partial_factor = exit_quantity / original_quantity if original_quantity > 0 else 1.0
                    scaled_pnl_pct = exit_record.get('pnl_pct', 0) * partial_factor
                    
                    trade_record = {
                        'symbol': symbol,
                        'entry_price': exit_record.get('entry_price', row['close']),
                        'exit_price': exit_record.get('exit_price', row['close']),
                        'pnl_pct': scaled_pnl_pct,  # Use scaled PnL for partial exits
                        'bars_held': exit_record.get('bars_held', 1),
                        'direction': exit_record.get('direction', 1),
                        'exit_reason': exit_record.get('exit_type', 'smart_exit'),
                        'quantity': exit_quantity,  # Track quantity for debugging
                        'is_partial': partial_factor < 1.0  # Flag partial exits
                    }
                    trades.append(trade_record)
                    
                    # Add trade to Kelly calculator
                    if kelly_calc:
                        kelly_calc.add_trade(scaled_pnl_pct)
                    
                    # Clear position if fully exited
                    if symbol not in exit_manager.positions:
                        position = None
            
            # Check for new entry if not in position
            # Also check time constraints for intraday trading
            can_enter = True
            if bar_time:
                # Avoid first 15 minutes (9:15-9:30) and last 15 minutes (3:15-3:30)
                if (bar_time.hour == 9 and bar_time.minute < 30) or \
                   (bar_time.hour == 15 and bar_time.minute >= 15):
                    can_enter = False
            
            if not position and current_signal != 0 and result.bar_index >= 2000 and can_enter:
                # Enter position
                direction = 1 if current_signal > 0 else -1
                entry_price = row['close']
                
                # Calculate position size using Kelly Criterion if available
                if kelly_calc and exit_manager:
                    # Get stop loss from exit manager
                    if hasattr(exit_manager, 'positions') and symbol in exit_manager.positions:
                        stop_loss = exit_manager.positions[symbol].stop_loss
                    else:
                        # Calculate stop based on exit config
                        if direction == 1:  # Long
                            stop_loss = entry_price * (1 - exit_manager.stop_loss_pct / 100)
                        else:  # Short
                            stop_loss = entry_price * (1 + exit_manager.stop_loss_pct / 100)
                    
                    # Use a hypothetical account balance for testing
                    # In production, this would come from broker API
                    account_balance = 1000000  # 10 lakh rupees
                    
                    # Calculate Kelly position size
                    kelly_position = kelly_calc.calculate_position_size(
                        account_balance=account_balance,
                        entry_price=entry_price,
                        stop_loss=stop_loss
                    )
                    
                    quantity = kelly_position['shares']
                    
                    # Log Kelly stats periodically
                    if len(trades) % 20 == 0 and len(trades) > 0:
                        print(f"\n  Kelly Stats for {symbol} after {len(trades)} trades:")
                        print(f"    Win Rate: {kelly_position['win_rate']:.1%}")
                        print(f"    Avg Win/Loss: {kelly_position['avg_win']:.2f}% / {kelly_position['avg_loss']:.2f}%")
                        print(f"    Kelly %: {kelly_position['kelly_pct']:.2f}%")
                        print(f"    Risk/Trade: {kelly_position['risk_pct']:.2f}%")
                        print(f"    Position: {quantity} shares")
                else:
                    # Default position size
                    quantity = 100
                
                if exit_manager:
                    # Enter position in exit manager (returns Position object)
                    exit_manager.enter_position(
                        symbol=symbol,
                        entry_price=entry_price,
                        quantity=quantity,
                        direction=direction,
                        ml_signal=ml_prediction,
                        timestamp=idx
                    )
                    # Keep our own simple position dict for compatibility
                    position = {
                        'entry_price': entry_price,
                        'entry_time': idx,
                        'entry_bar': result.bar_index,
                        'direction': direction,
                        'quantity': quantity
                    }
                else:
                    # Simple exit at next signal change
                    position = {
                        'entry_price': entry_price,
                        'entry_time': idx,
                        'entry_bar': result.bar_index,  # Track bar index for proper calculation
                        'direction': direction,
                        'quantity': quantity
                    }
                
                signals.append({
                    'timestamp': idx,
                    'type': 'entry',
                    'price': entry_price,
                    'signal': current_signal,
                    'ml': ml_prediction
                })
            
            # Simple exit if not using smart exits
            if position and not exit_manager:
                # Check if we need to exit before market close
                force_exit = False
                if bar_time and bar_time.hour == 15 and bar_time.minute >= 20:
                    # Force exit in last 10 minutes of trading day
                    force_exit = True
                
                # Exit on signal change or forced exit
                if isinstance(position, dict) and (current_signal * position['direction'] <= 0 or force_exit):
                    exit_price = row['close']
                    
                    # Calculate PnL correctly based on position direction
                    if position['direction'] == 1:  # LONG position
                        pnl_pct = (exit_price - position['entry_price']) / position['entry_price'] * 100
                    else:  # SHORT position (direction == -1)
                        pnl_pct = (position['entry_price'] - exit_price) / position['entry_price'] * 100
                    
                    # Calculate bars held properly
                    bars_held = result.bar_index - position.get('entry_bar', result.bar_index - 1)
                    
                    trades.append({
                        'symbol': symbol,
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'pnl_pct': pnl_pct,
                        'bars_held': max(1, bars_held),
                        'direction': position['direction'],
                        'exit_reason': 'time_exit' if force_exit else 'signal_change',
                        'quantity': position.get('quantity', 100),
                        'is_partial': False  # Signal exits are always full exits
                    })
                    
                    # Add trade to Kelly calculator
                    if kelly_calc:
                        kelly_calc.add_trade(pnl_pct)
                    
                    position = None
        
        # Force exit any remaining position
        if position:
            exit_price = df.iloc[-1]['close']
            if exit_manager and symbol in exit_manager.positions:
                exit_signal = exit_manager.check_exit(
                    symbol=symbol,
                    current_price=exit_price,
                    current_ml_signal=ml_prediction,
                    timestamp=df.index[-1]
                )
                if exit_signal and exit_signal.should_exit:
                    exit_record = exit_manager.execute_exit(symbol, exit_signal)
                    # Convert to our trade format
                    # Handle partial exits properly for end of data
                    exit_quantity = exit_record.get('quantity', 100)
                    original_quantity = 100  # Default position size
                    
                    # Scale PnL percentage by the portion of position being exited
                    partial_factor = exit_quantity / original_quantity if original_quantity > 0 else 1.0
                    scaled_pnl_pct = exit_record.get('pnl_pct', 0) * partial_factor
                    
                    trade_record = {
                        'symbol': symbol,
                        'entry_price': exit_record.get('entry_price', df.iloc[-1]['close']),
                        'exit_price': exit_record.get('exit_price', df.iloc[-1]['close']),
                        'pnl_pct': scaled_pnl_pct,  # Use scaled PnL for partial exits
                        'bars_held': exit_record.get('bars_held', 1),
                        'direction': exit_record.get('direction', 1),
                        'exit_reason': 'end_of_data',
                        'quantity': exit_quantity,
                        'is_partial': partial_factor < 1.0
                    }
                    trades.append(trade_record)
            elif isinstance(position, dict):
                # Calculate PnL correctly based on position direction
                if position['direction'] == 1:  # LONG position
                    pnl_pct = (exit_price - position['entry_price']) / position['entry_price'] * 100
                else:  # SHORT position (direction == -1)
                    pnl_pct = (position['entry_price'] - exit_price) / position['entry_price'] * 100
                trades.append({
                    'symbol': symbol,
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'bars_held': 1,  # Approximate
                    'direction': position['direction'],
                    'exit_reason': 'end_of_data',
                    'quantity': position.get('quantity', 100),
                    'is_partial': False
                })
        
        # Calculate statistics
        if trades:
            trades_df = pd.DataFrame(trades)
            winning_trades = trades_df[trades_df['pnl_pct'] > 0]
            losing_trades = trades_df[trades_df['pnl_pct'] <= 0]
            
            # Debug: Print sample trades
            if len(trades) > 0:
                print(f"\n  Sample trades for {symbol}:")
                print(f"  First 5 trades PnL: {[round(t['pnl_pct'], 2) for t in trades[:5]]}")
                print(f"  Avg bars held: {np.mean([t.get('bars_held', 1) for t in trades]):.1f}")
                # Show if we have partial exits
                partial_exits = [t for t in trades if t.get('is_partial', False)]
                if partial_exits:
                    print(f"  Partial exits: {len(partial_exits)} of {len(trades)} trades")
            
            # CRITICAL FIX: Compound returns correctly
            # Cannot sum percentages! Must compound them
            # Convert each trade to multiplier (1 + return)
            trade_multipliers = 1 + trades_df['pnl_pct'] / 100
            # Compound all trades
            compound_multiplier = trade_multipliers.prod()
            # Convert back to percentage
            total_return = (compound_multiplier - 1) * 100
            
            win_rate = len(winning_trades) / len(trades_df) * 100
            avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
            avg_loss = abs(losing_trades['pnl_pct'].mean()) if len(losing_trades) > 0 else 0
            
            # Calculate EXPECTANCY (Quantitative Trading formula)
            # This is THE critical metric - must be positive
            expectancy = (win_rate/100 * avg_win) - ((100-win_rate)/100 * avg_loss)
            
            # PROFIT FACTOR (Quantitative Trading)
            # Measures dollars won for every dollar lost
            total_wins = winning_trades['pnl_pct'].sum() if len(winning_trades) > 0 else 0
            total_losses = abs(losing_trades['pnl_pct'].sum()) if len(losing_trades) > 0 else 1
            profit_factor = total_wins / total_losses if total_losses > 0 else 0
            
            # Calculate maximum drawdown for CAR/MaxDD
            cumulative_returns = trades_df['pnl_pct'].cumsum()
            running_max = cumulative_returns.expanding().max()
            drawdown = cumulative_returns - running_max
            max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0
            
            # CAR/MaxDD (Quantitative Trading's crucial metric)
            # Annualized return / Max drawdown - return per unit of risk
            trading_days = len(df) / (78 * 252)  # Convert bars to years
            annualized_return = total_return / trading_days if trading_days > 0 else 0
            car_maxdd = annualized_return / max_drawdown if max_drawdown > 0 else 0
            
            result = {
                'total_trades': len(trades_df),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'total_return': total_return,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'expectancy': expectancy,  # Quantitative Trading: Must be positive
                'profit_factor': profit_factor,  # Quantitative Trading: Key robustness measure
                'max_drawdown': max_drawdown,
                'car_maxdd': car_maxdd,  # Quantitative Trading: Primary objective function
                'config': config.get_description()
            }
            
            # Store detailed trades
            self.detailed_trades[symbol] = trades_df
            
            # Get exit statistics if using smart exits
            if exit_manager:
                exit_stats = exit_manager.get_exit_statistics()
                result['exit_stats'] = exit_stats
            
        else:
            result = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'expectancy': 0,
                'profit_factor': 0,
                'config': config.get_description()
            }
        
        # Add ML accuracy stats
        ml_stats = self.ml_filter.get_accuracy_stats(symbol)
        if ml_stats and ml_stats['total_signals'] > 0:
            result['ml_accuracy'] = ml_stats['overall_accuracy']
        
        return result
    
    def _generate_summary(self) -> Dict:
        """Generate summary statistics across all stocks"""
        valid_results = {k: v for k, v in self.results.items() if 'error' not in v}
        
        if not valid_results:
            return {'error': 'No valid results'}
        
        # Aggregate metrics
        total_trades = sum(r['total_trades'] for r in valid_results.values())
        total_wins = sum(r['winning_trades'] for r in valid_results.values())
        total_losses = sum(r['losing_trades'] for r in valid_results.values())
        
        overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        avg_return = np.mean([r['total_return'] for r in valid_results.values()])
        # For summary, average return is more meaningful than sum
        total_return = avg_return
        
        # Calculate overall expectancy (weighted average by trades)
        total_expectancy = sum(r['expectancy'] * r['total_trades'] for r in valid_results.values())
        overall_expectancy = total_expectancy / total_trades if total_trades > 0 else 0
        
        # Best and worst performers
        returns_by_stock = {k: v['total_return'] for k, v in valid_results.items()}
        best_stock = max(returns_by_stock, key=returns_by_stock.get)
        worst_stock = min(returns_by_stock, key=returns_by_stock.get)
        
        summary = {
            'stocks_tested': len(valid_results),
            'total_trades': total_trades,
            'overall_win_rate': overall_win_rate,
            'avg_return_per_stock': avg_return,
            'total_return': total_return,
            'best_performer': {
                'symbol': best_stock,
                'return': returns_by_stock[best_stock],
                'trades': valid_results[best_stock]['total_trades']
            },
            'worst_performer': {
                'symbol': worst_stock,
                'return': returns_by_stock[worst_stock],
                'trades': valid_results[worst_stock]['total_trades']
            },
            'individual_results': valid_results,
            'overall_expectancy': overall_expectancy
        }
        
        return summary
    
    def _print_results(self, summary: Dict):
        """Print formatted results"""
        print(f"\n{'='*60}")
        print("MULTI-STOCK OPTIMIZATION RESULTS")
        print("(Intraday Trading - All positions closed by day end)")
        print(f"{'='*60}\n")
        
        if 'error' in summary:
            print(f"Error: {summary['error']}")
            return
            
        print(f"Stocks Tested: {summary['stocks_tested']}")
        print(f"Total Trades: {summary['total_trades']}")
        print(f"Overall Win Rate: {summary['overall_win_rate']:.1f}%")
        print(f"Average Return per Stock: {summary['avg_return_per_stock']:.2f}%")
        print(f"Total Return (All Stocks): {summary['total_return']:.2f}%")
        
        print(f"\nBest Performer: {summary['best_performer']['symbol']} "
              f"({summary['best_performer']['return']:.2f}% on "
              f"{summary['best_performer']['trades']} trades)")
        
        print(f"Worst Performer: {summary['worst_performer']['symbol']} "
              f"({summary['worst_performer']['return']:.2f}% on "
              f"{summary['worst_performer']['trades']} trades)")
        
        # Print Quantitative Trading criteria assessment
        print(f"\n{'='*60}")
        print("QUANTITATIVE TRADING CRITERIA ASSESSMENT")
        print(f"{'='*60}")
        
        if summary.get('overall_expectancy', 0) > 0:
            print(f"✅ Overall Expectancy: {summary.get('overall_expectancy', 0):.3f} (POSITIVE - System is viable)")
        else:
            print(f"❌ Overall Expectancy: {summary.get('overall_expectancy', 0):.3f} (NEGATIVE - System will lose money)")
        
        # Note about CAR/MaxDD
        print("\nNote: CAR/MaxDD > 1.0 indicates good return per unit of risk")
        print("      Higher values are better (2.0+ is excellent)")
        
        # Individual stock results table
        print(f"\n{'='*60}")
        print("INDIVIDUAL STOCK RESULTS")
        print(f"{'='*60}\n")
        
        table_data = []
        for symbol, result in summary['individual_results'].items():
            # Check if passes Quantitative Trading criteria
            passes_expectancy = '✅' if result.get('expectancy', 0) > 0 else '❌'
            passes_car = '✅' if result.get('car_maxdd', 0) > 1.0 else '❌'
            
            table_data.append([
                symbol,
                result['total_trades'],
                f"{result['win_rate']:.1f}%",
                f"{result['total_return']:.2f}%",
                f"{result['expectancy']:.3f} {passes_expectancy}",
                f"{result['profit_factor']:.2f}",
                f"{result.get('car_maxdd', 0):.2f} {passes_car}"
            ])
        
        headers = ['Symbol', 'Trades', 'Win Rate', 'Return', 'Expectancy', 'Profit Factor', 'CAR/MaxDD']
        if tabulate:
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
        else:
            # Simple formatting without tabulate
            print(f"{'Symbol':<10} {'Trades':<8} {'Win Rate':<10} {'Return':<10} {'Expectancy':<15} {'PF':<8} {'CAR/MaxDD':<12}")
            print("-" * 85)
            for row in table_data:
                print(f"{row[0]:<10} {row[1]:<8} {row[2]:<10} {row[3]:<10} {row[4]:<15} {row[5]:<8} {row[6]:<12}")
    
    def test_enhancement(self, enhancement_name: str, 
                        enhancement_config: Dict) -> Dict:
        """
        Test a specific enhancement against baseline
        
        Args:
            enhancement_name: Name of the enhancement
            enhancement_config: Configuration changes to apply
            
        Returns:
            Comparison results
        """
        print(f"\n{'='*60}")
        print(f"Testing Enhancement: {enhancement_name}")
        print(f"{'='*60}\n")
        
        # Run test with enhancement
        # This would modify the config with enhancement_config
        # and run the test again
        
        # For now, placeholder
        return {
            'enhancement': enhancement_name,
            'config': enhancement_config,
            'improvement': 'TBD'
        }
    
    def save_results(self, filename: str):
        """Save results to file"""
        # Convert detailed trades to JSON-serializable format
        detailed_trades_dict = {}
        for symbol, trades_df in self.detailed_trades.items():
            trades_list = trades_df.to_dict('records')
            # Convert any Timestamp objects to strings
            for trade in trades_list:
                for key, value in trade.items():
                    if hasattr(value, 'isoformat'):
                        trade[key] = value.isoformat()
            detailed_trades_dict[symbol] = trades_list
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'symbols': self.symbols,
            'timeframe': self.timeframe,
            'lookback_days': self.lookback_days,
            'results': self.results,
            'detailed_trades': detailed_trades_dict
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"\nResults saved to {filename}")


def main():
    """Main function to run multi-stock optimization"""
    
    # Define test stocks - mix of different volatilities
    test_stocks = [
        'RELIANCE',  # High volatility
        'INFY',      # Medium volatility
        'AXISBANK',  # Medium volatility
        'ITC',       # Low volatility
        'TCS'        # Medium volatility
    ]
    
    # Initialize optimizer - will fetch more data if needed
    optimizer = MultiStockOptimizer(
        symbols=test_stocks,
        timeframe='5minute',
        lookback_days=180  # NO COMPROMISE - start with 180 days, will auto-expand if needed
    )
    
    # Run baseline test
    print("\n" + "="*60)
    print("BASELINE TEST - Core System Performance")
    print("="*60)
    
    baseline_results = optimizer.run_baseline_test(
        use_ml_filter=True,
        use_smart_exits=False  # Disable smart exits to match Pine Script
    )
    
    # Save baseline results
    optimizer.save_results('baseline_results.json')
    
    # Test without ML filter for comparison
    print("\n" + "="*60)
    print("COMPARISON TEST - Without ML Filter")
    print("="*60)
    
    # Reset results for new test but keep same data
    optimizer.results = {}
    optimizer.detailed_trades = {}
    
    no_ml_results = optimizer.run_baseline_test(
        use_ml_filter=False,
        use_smart_exits=False  # Keep consistent with baseline
    )
    
    # Save no-ML results
    optimizer.save_results('no_ml_filter_results.json')
    
    # Compare results
    print("\n" + "="*60)
    print("COMPARISON: ML Filter Impact")
    print("="*60)
    
    if 'error' not in baseline_results and 'error' not in no_ml_results:
        print(f"With ML Filter - Total Return: {baseline_results['total_return']:.2f}%")
        print(f"Without ML Filter - Total Return: {no_ml_results['total_return']:.2f}%")
        print(f"Improvement: {baseline_results['total_return'] - no_ml_results['total_return']:.2f}%")
    else:
        print("Could not compare - errors in one or both tests")


def test_exit_strategies():
    """Test different exit strategies to improve returns"""
    
    print("\n" + "="*60)
    print("TESTING EXIT STRATEGIES")
    print("="*60)
    
    # Define test stocks
    test_stocks = [
        'RELIANCE',  # High volatility
        'INFY',      # Medium volatility
        'AXISBANK',  # Medium volatility
        'ITC',       # Low volatility
        'TCS'        # Medium volatility
    ]
    
    # Initialize optimizer
    optimizer = MultiStockOptimizer(
        symbols=test_stocks,
        timeframe='5minute',
        lookback_days=180
    )
    
    # Test different exit strategies
    strategies = ['conservative', 'scalping', 'adaptive', 'atr']
    results = {}
    
    for strategy in strategies:
        print("\n" + "="*60)
        print(f"TESTING: {strategy.upper()} EXIT STRATEGY")
        print("="*60)
        
        # Reset results
        optimizer.results = {}
        optimizer.detailed_trades = {}
        
        # Set the exit strategy
        optimizer.exit_strategy = strategy
        
        # Run test with smart exits
        strategy_results = optimizer.run_baseline_test(
            use_ml_filter=True,
            use_smart_exits=True
        )
        
        if 'error' not in strategy_results:
            results[strategy] = strategy_results
            print(f"\n{strategy.upper()} Results:")
            print(f"  Total Return: {strategy_results['total_return']:.2f}%")
            print(f"  Win Rate: {strategy_results['overall_win_rate']:.1f}%")
            print(f"  Total Trades: {strategy_results['total_trades']}")
            print(f"  Expectancy: {strategy_results.get('overall_expectancy', 0):.3f}")
        else:
            print(f"  Test failed: {strategy_results['error']}")
    
    # Compare all results
    print("\n" + "="*60)
    print("EXIT STRATEGY COMPARISON")
    print("="*60)
    
    if results:
        # Find best strategy
        best_strategy = max(results.items(), key=lambda x: x[1]['total_return'])
        print(f"\nBest Strategy: {best_strategy[0].upper()}")
        print(f"Best Return: {best_strategy[1]['total_return']:.2f}%")
        
        # Show comparison table
        print("\nStrategy Performance Summary:")
        print("-" * 60)
        print(f"{'Strategy':<15} {'Return':<10} {'Win Rate':<10} {'Trades':<10} {'Expectancy':<10}")
        print("-" * 60)
        
        for strategy, result in sorted(results.items(), key=lambda x: x[1]['total_return'], reverse=True):
            print(f"{strategy:<15} {result['total_return']:>8.2f}% {result['overall_win_rate']:>8.1f}% "
                  f"{result['total_trades']:>8} {result.get('overall_expectancy', 0):>10.3f}")
    
    # Save results
    with open('exit_strategy_comparison.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to exit_strategy_comparison.json")


if __name__ == "__main__":
    # Run the exit strategy test
    test_exit_strategies()