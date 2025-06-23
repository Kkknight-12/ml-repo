"""
Bar Processor - Orchestrates bar-by-bar processing
This is the main engine that ties everything together
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from data.data_types import (
    Settings, Label, FeatureArrays, FeatureSeries,
    Filter, FilterSettings
)
from data.bar_data import BarData
from config.settings import TradingConfig
from core.enhanced_indicators import enhanced_series_from
from core.enhanced_ml_extensions import enhanced_regime_filter, enhanced_filter_adx, enhanced_filter_volatility
from core.kernel_functions import is_kernel_bullish, is_kernel_bearish, get_kernel_crossovers
from core.math_helpers import pine_ema, pine_sma
from ml.lorentzian_knn_fixed import LorentzianKNNFixed as LorentzianKNN
from scanner.signal_generator import SignalGenerator
from core.na_handling import validate_ohlcv  # Add NA handling
from utils.risk_management import calculate_trade_levels


@dataclass
class BarResult:
    """Result of processing a single bar"""
    bar_index: int

    # Prices
    open: float
    high: float
    low: float
    close: float

    # ML Output
    prediction: float
    signal: int

    # Entry/Exit Signals
    start_long_trade: bool
    start_short_trade: bool
    end_long_trade: bool
    end_short_trade: bool

    # Filters
    filter_states: Dict[str, bool]

    # Additional Info
    is_early_signal_flip: bool
    prediction_strength: float
    
    # Risk Management (optional)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class BarProcessor:
    """
    Processes bars one at a time, maintaining all necessary state
    Implements the complete Pine Script logic
    """

    def __init__(self, config: TradingConfig, total_bars: Optional[int] = None,
                 symbol: str = "DEFAULT", timeframe: str = "5minute", 
                 use_enhanced: bool = True):
        """
        Initialize with configuration

        Args:
            config: Complete trading configuration
            total_bars: Deprecated - kept for compatibility
            symbol: Trading symbol (e.g., 'RELIANCE')
            timeframe: Timeframe (e.g., '5minute')
            use_enhanced: Whether to use enhanced stateful indicators
        """
        self.config = config
        self.settings = config.get_settings()
        self.filter_settings = config.get_filter_settings()
        self.symbol = symbol
        self.timeframe = timeframe
        self.use_enhanced = use_enhanced

        # Initialize components
        self.label = Label()
        self.ml_model = LorentzianKNN(self.settings, self.label)
        self.signal_generator = SignalGenerator(self.label)

        # Feature arrays (historical storage)
        self.feature_arrays = FeatureArrays()

        # Historical data for calculations
        self.bars = BarData(max_bars=config.max_bars_back + 100)

        # State tracking (for stateless signal generation)
        self.signal_history: List[int] = []
        self.entry_history: List[Tuple[bool, bool]] = []

        # For EMA/SMA calculations
        self.close_values: List[float] = []
        self.ema_values: List[float] = []
        self.sma_values: List[float] = []
        
        # Track bars processed for sliding window
        self.bars_processed = 0

    def process_bar(self, open_price: float, high: float, low: float,
                    close: float, volume: float = 0.0) -> Optional[BarResult]:
        """
        Process a single bar and generate all signals

        This is the main entry point that orchestrates:
        1. Update bar data
        2. Calculate features
        3. Run ML prediction
        4. Apply filters
        5. Generate signals

        Args:
            open_price, high, low, close, volume: OHLCV data

        Returns:
            BarResult with all calculated values, or None if invalid data
        """
        # PHASE 3 FIX: Validate input data
        is_valid, error_msg = validate_ohlcv(open_price, high, low, close, volume)
        if not is_valid:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Skipping invalid bar: {error_msg}")
            return None
        
        # Ensure volume is not None
        if volume is None:
            volume = 0.0
        # Update bar data
        self.bars.add_bar(open_price, high, low, close, volume)
        bar_index = self.bars.bar_index
        self.bars_processed += 1

        # Update price history for calculations
        # Pine Script style - append to end for correct chronological order
        self.close_values.append(close)
        if len(self.close_values) > self.settings.max_bars_back:
            self.close_values.pop(0)  # Remove oldest

        # Calculate features for current bar
        feature_series = self._calculate_features()

        # Update feature arrays
        self._update_feature_arrays(feature_series)

        # Update training data (look back 4 bars)
        # Pine Script: src[4] < src[0] - where [4] is 4 bars ago, [0] is current
        if len(self.close_values) >= 5:  # Need at least 5 values (current + 4 historical)
            # Python negative indexing with newest at end:
            # close_values[-1] = current bar (0 bars ago)
            # close_values[-2] = 1 bar ago
            # close_values[-3] = 2 bars ago
            # close_values[-4] = 3 bars ago
            # close_values[-5] = 4 bars ago ✓
            close_4_bars_ago = self.close_values[-5]
            self.ml_model.update_training_data(close, close_4_bars_ago)

        # Pine Script logic: ML starts after we have enough historical data
        # In live trading, we need at least some bars for training
        # We'll start ML once we have at least 20 bars of training data
        min_training_bars = 20  # Minimum bars needed to start ML
        
        # Only run ML if we have enough training data
        if len(self.ml_model.y_train_array) >= min_training_bars:
            # Run ML prediction - this updates self.ml_model.prediction
            self.ml_model.predict(
                feature_series, self.feature_arrays, bar_index
            )
        else:
            # Before ML starts, set neutral prediction
            self.ml_model.prediction = 0.0
        
        # Apply filters
        filter_states = self._apply_filters()
        filter_all = all(filter_states.values())
        
        # IMPORTANT: Keep ML prediction separate from signal
        # Prediction is the raw ML output (-8 to +8)
        # Signal is the trading decision after filters (long/short/neutral)
        ml_prediction = self.ml_model.prediction  # Store the actual prediction
        
        # Update signal based on prediction AND filters
        signal = self.ml_model.update_signal(filter_all)
        
        # Enhanced DEBUG: Show both prediction and signal
        if self.bars_processed % 100 == 0 or (self.bars_processed > 50 and abs(ml_prediction) < 0.1):
            print(f"\n📊 DEBUG Bar {bar_index}:")
            print(f"  ML Prediction (raw): {ml_prediction:.2f} (range: -8 to +8)")
            print(f"  Signal (after filters): {signal} (1=long, -1=short, 0=neutral)")
            print(f"  Filters: Vol={filter_states['volatility']} Regime={filter_states['regime']} ADX={filter_states['adx']}")
            print(f"  All filters pass: {filter_all}")
            print(f"  Training data: {len(self.ml_model.y_train_array)} bars")
            print(f"  Neighbors used: {len(self.ml_model.predictions)}")
            if len(self.ml_model.predictions) > 0:
                print(f"  Neighbor predictions: {self.ml_model.predictions}")

        # Calculate trend filters
        is_ema_uptrend, is_ema_downtrend = self._calculate_ema_trend()
        is_sma_uptrend, is_sma_downtrend = self._calculate_sma_trend()

        # Calculate kernel filters
        is_bullish_kernel = self._calculate_kernel_bullish()
        is_bearish_kernel = self._calculate_kernel_bearish()
        
        # Get kernel crossovers for dynamic exits
        kernel_crosses = self._get_kernel_crossovers()

        # Generate entry signals
        start_long, start_short = self.signal_generator.check_entry_conditions(
            signal, self.signal_history, is_bullish_kernel, is_bearish_kernel,
            is_ema_uptrend, is_ema_downtrend, is_sma_uptrend, is_sma_downtrend
        )

        # Calculate bars held
        bars_held = self.signal_generator.calculate_bars_held(self.entry_history)

        # Generate exit signals
        end_long, end_short = self.signal_generator.check_exit_conditions(
            bars_held, self.signal_history, self.entry_history,
            self.settings.use_dynamic_exits, kernel_crosses
        )

        # Check for early signal flip
        is_early_flip = self.signal_generator.is_early_signal_flip(self.signal_history)

        # Update history
        # For signal history, keep newest at index 0 (Pine Script style for series)
        self.signal_history.insert(0, signal)
        self.entry_history.insert(0, (start_long, start_short))

        # Limit history size
        if len(self.signal_history) > 10:
            self.signal_history.pop()
        if len(self.entry_history) > 10:
            self.entry_history.pop()
        
        # Calculate SL/TP if we have a new entry signal
        stop_loss = None
        take_profit = None
        
        if start_long or start_short:
            # Get historical data for calculations
            high_values = [self.bars.get_high(i) for i in range(min(20, len(self.bars)))]
            low_values = [self.bars.get_low(i) for i in range(min(20, len(self.bars)))]
            close_values = [self.bars.get_close(i) for i in range(min(20, len(self.bars)))]
            
            # Calculate using ATR method by default
            if high_values and low_values and close_values:
                stop_loss, take_profit = calculate_trade_levels(
                    entry_price=close,
                    high_values=high_values,
                    low_values=low_values,
                    close_values=close_values,
                    is_long=start_long,
                    method="atr",
                    atr_length=14,
                    atr_multiplier=2.0,
                    risk_reward_ratio=2.0
                )

        # Create result
        # CRITICAL FIX: Return actual ML prediction, not the signal!
        return BarResult(
            bar_index=bar_index,
            open=open_price,
            high=high,
            low=low,
            close=close,
            prediction=ml_prediction,  # Use the raw ML prediction
            signal=signal,
            start_long_trade=start_long,
            start_short_trade=start_short,
            end_long_trade=end_long,
            end_short_trade=end_short,
            filter_states=filter_states,
            is_early_signal_flip=is_early_flip,
            prediction_strength=self.ml_model.get_prediction_strength(),
            stop_loss=stop_loss,
            take_profit=take_profit
        )

    def _calculate_features(self) -> FeatureSeries:
        """Calculate all features for current bar"""
        if self.use_enhanced:
            # Use enhanced stateful indicators
            return self._calculate_features_enhanced()
        else:
            # Original implementation
            return self._calculate_features_original()
    
    def _calculate_features_enhanced(self) -> FeatureSeries:
        """Calculate features using enhanced stateful indicators"""
        # Get current bar OHLC data
        current_ohlc = {
            'high': self.bars.get_high(0),
            'low': self.bars.get_low(0),
            'close': self.bars.get_close(0)
        }
        
        # Get previous close for RSI calculation
        previous_close = self.bars.get_close(1) if len(self.bars) > 1 else None
        
        # Calculate each feature using enhanced version
        features = self.config.features
        
        f1 = enhanced_series_from(features["f1"][0], current_ohlc, previous_close,
                                 self.symbol, self.timeframe,
                                 features["f1"][1], features["f1"][2])
        
        f2 = enhanced_series_from(features["f2"][0], current_ohlc, previous_close,
                                 self.symbol, self.timeframe,
                                 features["f2"][1], features["f2"][2])
        
        f3 = enhanced_series_from(features["f3"][0], current_ohlc, previous_close,
                                 self.symbol, self.timeframe,
                                 features["f3"][1], features["f3"][2])
        
        f4 = enhanced_series_from(features["f4"][0], current_ohlc, previous_close,
                                 self.symbol, self.timeframe,
                                 features["f4"][1], features["f4"][2])
        
        f5 = enhanced_series_from(features["f5"][0], current_ohlc, previous_close,
                                 self.symbol, self.timeframe,
                                 features["f5"][1], features["f5"][2])
        
        return FeatureSeries(f1=f1, f2=f2, f3=f3, f4=f4, f5=f5)
    
    def _calculate_features_original(self) -> FeatureSeries:
        """Original feature calculation for backward compatibility"""
        # Get data arrays
        close_values = [self.bars.get_close(i) for i in range(len(self.bars))]
        high_values = [self.bars.get_high(i) for i in range(len(self.bars))]
        low_values = [self.bars.get_low(i) for i in range(len(self.bars))]
        hlc3_values = [self.bars.get_hlc3(i) for i in range(len(self.bars))]

        # Calculate each feature based on configuration
        features = self.config.features

        f1 = series_from(features["f1"][0], close_values, high_values,
                         low_values, hlc3_values, features["f1"][1], features["f1"][2])

        f2 = series_from(features["f2"][0], close_values, high_values,
                         low_values, hlc3_values, features["f2"][1], features["f2"][2])

        f3 = series_from(features["f3"][0], close_values, high_values,
                         low_values, hlc3_values, features["f3"][1], features["f3"][2])

        f4 = series_from(features["f4"][0], close_values, high_values,
                         low_values, hlc3_values, features["f4"][1], features["f4"][2])

        f5 = series_from(features["f5"][0], close_values, high_values,
                         low_values, hlc3_values, features["f5"][1], features["f5"][2])

        return FeatureSeries(f1=f1, f2=f2, f3=f3, f4=f4, f5=f5)

    def _update_feature_arrays(self, feature_series: FeatureSeries) -> None:
        """Update historical feature arrays - Pine Script style (append to end)"""
        # Pine Script: array.push() adds to END
        self.feature_arrays.f1.append(feature_series.f1)
        self.feature_arrays.f2.append(feature_series.f2)
        self.feature_arrays.f3.append(feature_series.f3)
        self.feature_arrays.f4.append(feature_series.f4)
        self.feature_arrays.f5.append(feature_series.f5)

        # Limit size - remove from beginning if too large
        max_size = self.settings.max_bars_back
        if len(self.feature_arrays.f1) > max_size:
            self.feature_arrays.f1.pop(0)  # Remove oldest (first element)
            self.feature_arrays.f2.pop(0)
            self.feature_arrays.f3.pop(0)
            self.feature_arrays.f4.pop(0)
            self.feature_arrays.f5.pop(0)

    def _apply_filters(self) -> Dict[str, bool]:
        """Apply all filters and return their states"""
        if self.use_enhanced:
            # Use enhanced stateful filters
            return self._apply_filters_enhanced()
        else:
            # Original implementation
            return self._apply_filters_original()
    
    def _apply_filters_enhanced(self) -> Dict[str, bool]:
        """Apply filters using enhanced stateful versions"""
        # Get current bar data
        current_high = self.bars.get_high(0)
        current_low = self.bars.get_low(0)
        current_close = self.bars.get_close(0)
        current_ohlc4 = self.bars.get_ohlc4(0)
        
        # Get previous OHLC4 for regime filter
        previous_ohlc4 = self.bars.get_ohlc4(1) if len(self.bars) > 1 else current_ohlc4
        
        # Apply each filter using enhanced versions
        volatility = enhanced_filter_volatility(
            current_high, current_low, current_close,
            self.symbol, self.timeframe,
            1, 10, self.filter_settings.use_volatility_filter
        )
        
        regime = enhanced_regime_filter(
            current_ohlc4, current_high, current_low, previous_ohlc4,
            self.symbol, self.timeframe,
            self.filter_settings.regime_threshold,
            self.filter_settings.use_regime_filter
        )
        
        adx = enhanced_filter_adx(
            current_high, current_low, current_close,
            self.symbol, self.timeframe,
            14, self.filter_settings.adx_threshold,
            self.filter_settings.use_adx_filter
        )
        
        return {
            "volatility": volatility,
            "regime": regime,
            "adx": adx
        }
    
    def _apply_filters_original(self) -> Dict[str, bool]:
        """Original filter implementation for backward compatibility"""
        # Get data for filters
        high_values = [self.bars.get_high(i) for i in range(len(self.bars))]
        low_values = [self.bars.get_low(i) for i in range(len(self.bars))]
        close_values = [self.bars.get_close(i) for i in range(len(self.bars))]
        ohlc4_values = [self.bars.get_ohlc4(i) for i in range(len(self.bars))]

        # Apply each filter
        volatility = filter_volatility(
            high_values, low_values, close_values,
            1, 10, self.filter_settings.use_volatility_filter
        )

        regime = regime_filter(
            ohlc4_values, self.filter_settings.regime_threshold,
            self.filter_settings.use_regime_filter, high_values, low_values
        )

        adx = filter_adx(
            high_values, low_values, close_values,
            14, self.filter_settings.adx_threshold,
            self.filter_settings.use_adx_filter
        )

        return {
            "volatility": volatility,
            "regime": regime,
            "adx": adx
        }

    def _calculate_ema_trend(self) -> Tuple[bool, bool]:
        """Calculate EMA trend filters"""
        if not self.config.use_ema_filter:
            return True, True

        if len(self.close_values) < self.config.ema_period:
            return True, True

        ema = pine_ema(self.close_values, self.config.ema_period)
        current_close = self.close_values[-1]  # Newest at end

        is_uptrend = current_close > ema
        is_downtrend = current_close < ema

        return is_uptrend, is_downtrend

    def _calculate_sma_trend(self) -> Tuple[bool, bool]:
        """Calculate SMA trend filters"""
        if not self.config.use_sma_filter:
            return True, True

        if len(self.close_values) < self.config.sma_period:
            return True, True

        sma = pine_sma(self.close_values, self.config.sma_period)
        current_close = self.close_values[-1]  # Newest at end

        is_uptrend = current_close > sma
        is_downtrend = current_close < sma

        return is_uptrend, is_downtrend

    def _calculate_kernel_bullish(self) -> bool:
        """Check if kernel regression is bullish"""
        if not self.config.use_kernel_filter:
            return True

        source_values = []
        for i in range(len(self.bars)):
            if self.settings.source == 'close':
                source_values.append(self.bars.get_close(i))
            elif self.settings.source == 'hlc3':
                source_values.append(self.bars.get_hlc3(i))
            else:
                source_values.append(self.bars.get_ohlc4(i))

        return is_kernel_bullish(
            source_values,
            self.config.kernel_lookback,
            self.config.kernel_relative_weight,
            self.config.kernel_regression_level,
            self.config.use_kernel_smoothing,
            self.config.kernel_lag
        )

    def _calculate_kernel_bearish(self) -> bool:
        """Check if kernel regression is bearish"""
        if not self.config.use_kernel_filter:
            return True

        source_values = []
        for i in range(len(self.bars)):
            if self.settings.source == 'close':
                source_values.append(self.bars.get_close(i))
            elif self.settings.source == 'hlc3':
                source_values.append(self.bars.get_hlc3(i))
            else:
                source_values.append(self.bars.get_ohlc4(i))

        return is_kernel_bearish(
            source_values,
            self.config.kernel_lookback,
            self.config.kernel_relative_weight,
            self.config.kernel_regression_level,
            self.config.use_kernel_smoothing,
            self.config.kernel_lag
        )
    
    def _get_kernel_crossovers(self) -> Tuple[bool, bool]:
        """Get kernel crossover signals for dynamic exits"""
        if not self.config.use_kernel_filter:
            return False, False
        
        source_values = []
        for i in range(len(self.bars)):
            if self.settings.source == 'close':
                source_values.append(self.bars.get_close(i))
            elif self.settings.source == 'hlc3':
                source_values.append(self.bars.get_hlc3(i))
            else:
                source_values.append(self.bars.get_ohlc4(i))
        
        return get_kernel_crossovers(
            source_values,
            self.config.kernel_lookback,
            self.config.kernel_relative_weight,
            self.config.kernel_regression_level,
            self.config.kernel_lag
        )