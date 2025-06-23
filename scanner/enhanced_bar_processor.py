"""
Enhanced Bar Processor - Uses stateful indicators
=================================================

This is the enhanced version of BarProcessor that uses stateful indicators
to maintain state across bars, just like Pine Script.
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from data.data_types import (
    Settings, Label, FeatureArrays, FeatureSeries,
    Filter, FilterSettings
)
from data.bar_data import BarData
from config.settings import TradingConfig

# Import enhanced stateful versions instead of old ones
from core.enhanced_indicators import (
    enhanced_series_from, enhanced_ema, enhanced_sma, enhanced_atr,
    enhanced_change, enhanced_crossover, enhanced_crossunder,
    enhanced_barssince, get_indicator_manager, reset_symbol_indicators
)
from core.enhanced_ml_extensions import enhanced_regime_filter, enhanced_filter_adx, enhanced_filter_volatility
from core.kernel_functions import is_kernel_bullish, is_kernel_bearish, get_kernel_crossovers
from ml.lorentzian_knn_fixed import LorentzianKNNFixed
from scanner.signal_generator import SignalGenerator
from core.na_handling import validate_ohlcv
from utils.risk_management import calculate_trade_levels

# Reuse the same BarResult dataclass
from scanner.bar_processor import BarResult


class EnhancedBarProcessor:
    """
    Enhanced Bar Processor that uses stateful indicators.
    
    Key differences from original:
    - Uses stateful indicators that maintain state across bars
    - No need to pass full history arrays to indicators
    - More efficient and accurate (matches Pine Script behavior)
    """

    def __init__(self, config: TradingConfig, symbol: str, timeframe: str = "5min"):
        """
        Initialize with configuration and symbol info

        Args:
            config: Complete trading configuration
            symbol: Trading symbol (e.g., 'RELIANCE')
            timeframe: Timeframe for indicators (e.g., '5min', 'daily')
        """
        self.config = config
        self.symbol = symbol
        self.timeframe = timeframe
        self.settings = config.get_settings()
        self.filter_settings = config.get_filter_settings()

        # Reset indicators for this symbol to ensure clean state
        reset_symbol_indicators(symbol)

        # Initialize components
        self.label = Label()
        self.ml_model = LorentzianKNNFixed(self.settings, self.label)
        self.signal_generator = SignalGenerator(self.label)

        # Feature arrays (historical storage)
        self.feature_arrays = FeatureArrays()

        # Historical data for calculations (still needed for some operations)
        self.bars = BarData(max_bars=config.max_bars_back + 100)

        # State tracking (for stateless signal generation)
        self.signal_history: List[int] = []
        self.entry_history: List[Tuple[bool, bool]] = []

        # For trend calculations
        self.current_ema_value: Optional[float] = None
        self.current_sma_value: Optional[float] = None
        
        # Track bars processed
        self.bars_processed = 0

    def process_bar(self, open_price: float, high: float, low: float,
                    close: float, volume: float = 0.0) -> Optional[BarResult]:
        """
        Process a single bar and generate all signals using stateful indicators

        Args:
            open_price, high, low, close, volume: OHLCV data

        Returns:
            BarResult with all calculated values, or None if invalid data
        """
        # Validate input data
        is_valid, error_msg = validate_ohlcv(open_price, high, low, close, volume)
        if not is_valid:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Skipping invalid bar: {error_msg}")
            return None
        
        # Ensure volume is not None
        if volume is None:
            volume = 0.0
            
        # Update bar data (still needed for historical access)
        self.bars.add_bar(open_price, high, low, close, volume)
        bar_index = self.bars.bar_index
        self.bars_processed += 1

        # Calculate features using stateful indicators
        feature_series = self._calculate_features_stateful(high, low, close)

        # Update feature arrays
        self._update_feature_arrays(feature_series)

        # Update training data (look back 4 bars)
        if bar_index >= 4:
            close_4_bars_ago = self.bars.get_close(4)
            self.ml_model.update_training_data(close, close_4_bars_ago)

        # Run ML prediction if we have enough training data
        min_training_bars = 20
        
        if len(self.ml_model.y_train_array) >= min_training_bars:
            self.ml_model.predict(
                feature_series, self.feature_arrays, bar_index
            )
        else:
            self.ml_model.prediction = 0.0
        
        # Apply filters using stateful calculations
        filter_states = self._apply_filters_stateful(high, low, close)
        filter_all = all(filter_states.values())
        
        # Keep ML prediction separate from signal
        ml_prediction = self.ml_model.prediction
        
        # Update signal based on prediction AND filters
        signal = self.ml_model.update_signal(filter_all)
        
        # Debug output
        if self.bars_processed % 100 == 0 or (self.bars_processed > 50 and abs(ml_prediction) < 0.1):
            print(f"\n📊 Enhanced DEBUG Bar {bar_index} [{self.symbol}]:")
            print(f"  ML Prediction (raw): {ml_prediction:.2f}")
            print(f"  Signal (after filters): {signal}")
            print(f"  Filters: {filter_states}")
            print(f"  Training data: {len(self.ml_model.y_train_array)} bars")

        # Calculate trend filters using stateful indicators
        is_ema_uptrend, is_ema_downtrend = self._calculate_ema_trend_stateful(close)
        is_sma_uptrend, is_sma_downtrend = self._calculate_sma_trend_stateful(close)

        # Calculate kernel filters (still using historical data)
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
        return BarResult(
            bar_index=bar_index,
            open=open_price,
            high=high,
            low=low,
            close=close,
            prediction=ml_prediction,
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

    def _calculate_features_stateful(self, high: float, low: float, close: float) -> FeatureSeries:
        """Calculate all features using stateful indicators"""
        features = self.config.features

        # Calculate each feature using stateful indicators
        f1 = enhanced_series_from(
            features["f1"][0], close, high, low,
            features["f1"][1], features["f1"][2],
            self.symbol, self.timeframe
        )

        f2 = enhanced_series_from(
            features["f2"][0], close, high, low,
            features["f2"][1], features["f2"][2],
            self.symbol, self.timeframe
        )

        f3 = enhanced_series_from(
            features["f3"][0], close, high, low,
            features["f3"][1], features["f3"][2],
            self.symbol, self.timeframe
        )

        f4 = enhanced_series_from(
            features["f4"][0], close, high, low,
            features["f4"][1], features["f4"][2],
            self.symbol, self.timeframe
        )

        f5 = enhanced_series_from(
            features["f5"][0], close, high, low,
            features["f5"][1], features["f5"][2],
            self.symbol, self.timeframe
        )

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
            self.feature_arrays.f1.pop(0)
            self.feature_arrays.f2.pop(0)
            self.feature_arrays.f3.pop(0)
            self.feature_arrays.f4.pop(0)
            self.feature_arrays.f5.pop(0)

    def _apply_filters_stateful(self, high: float, low: float, close: float) -> Dict[str, bool]:
        """Apply filters using stateful calculations"""
        # Calculate current ohlc4 for regime filter
        current_ohlc4 = self.bars.get_ohlc4(0) if len(self.bars) > 0 else close

        # Apply each filter using enhanced stateful versions with CORRECT parameter order
        volatility = enhanced_filter_volatility(
            high, low, close,
            1, 10,  # min_length, max_length
            self.filter_settings.use_volatility_filter,
            self.symbol, self.timeframe
        )

        regime = enhanced_regime_filter(
            current_ohlc4, high, low,
            self.filter_settings.regime_threshold,
            self.filter_settings.use_regime_filter,
            self.symbol, self.timeframe
        )

        adx = enhanced_filter_adx(
            high, low, close,
            14, self.filter_settings.adx_threshold,
            self.filter_settings.use_adx_filter,
            self.symbol, self.timeframe
        )

        return {
            "volatility": volatility,
            "regime": regime,
            "adx": adx
        }

    def _calculate_ema_trend_stateful(self, close: float) -> Tuple[bool, bool]:
        """Calculate EMA trend using stateful indicator"""
        if not self.config.use_ema_filter:
            return True, True

        # Update EMA with current close
        self.current_ema_value = enhanced_ema(
            close, self.config.ema_period, 
            self.symbol, f"{self.timeframe}_trend"
        )

        # Check if we have enough bars
        if self.bars_processed < self.config.ema_period:
            return True, True

        is_uptrend = close > self.current_ema_value
        is_downtrend = close < self.current_ema_value

        return is_uptrend, is_downtrend

    def _calculate_sma_trend_stateful(self, close: float) -> Tuple[bool, bool]:
        """Calculate SMA trend using stateful indicator"""
        if not self.config.use_sma_filter:
            return True, True

        # Update SMA with current close
        self.current_sma_value = enhanced_sma(
            close, self.config.sma_period,
            self.symbol, f"{self.timeframe}_trend"
        )

        # Check if we have enough bars
        if self.bars_processed < self.config.sma_period:
            return True, True

        is_uptrend = close > self.current_sma_value
        is_downtrend = close < self.current_sma_value

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

    def get_indicator_stats(self) -> dict:
        """Get statistics about stateful indicators being used"""
        return get_indicator_manager().get_stats()
