"""
Enhanced Bar Processor with Pine Script Style Debug Logging
===========================================================

This version adds comprehensive debug logging to match Pine Script output
for troubleshooting filter and ML prediction issues.
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
import numpy as np

from data.data_types import (
    Settings, Label, FeatureArrays, FeatureSeries,
    Filter, FilterSettings
)
from data.bar_data import BarData
from config.settings import TradingConfig

# Import enhanced stateful versions
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

# Setup logging with Pine Script style
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s]: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S.%f'
)
logger = logging.getLogger(__name__)


class EnhancedBarProcessorDebug:
    """
    Enhanced Bar Processor with Pine Script style debug logging
    """

    def __init__(self, config: TradingConfig, symbol: str, timeframe: str = "5min"):
        """Initialize with configuration and symbol info"""
        self.config = config
        self.symbol = symbol
        self.timeframe = timeframe
        self.settings = config.get_settings()
        self.filter_settings = config.get_filter_settings()
        
        # Initialize tracking variables BEFORE logging
        self.bars_processed = 0
        self.volatility_pass_count = 0
        self.regime_pass_count = 0
        self.adx_pass_count = 0
        self.total_bars_for_filters = 0
        
        # Log configuration at startup
        self._log_configuration()
        
        # Reset indicators for this symbol
        reset_symbol_indicators(symbol)
        
        # Initialize components
        self.label = Label()
        self.ml_model = LorentzianKNNFixed(self.settings, self.label)
        self.signal_generator = SignalGenerator(self.label)
        
        # Feature arrays
        self.feature_arrays = FeatureArrays()
        
        # Historical data
        self.bars = BarData(max_bars=config.max_bars_back + 100)
        
        # State tracking
        self.signal_history: List[int] = []
        self.entry_history: List[Tuple[bool, bool]] = []
        
        # Trend values
        self.current_ema_value: Optional[float] = None
        self.current_sma_value: Optional[float] = None

    def _log_configuration(self):
        """Log configuration at startup like Pine Script"""
        if self.bars_processed == 0:
            logger.warning("========== PYTHON CONFIGURATION ==========")
            
            logger.info("🔧 CORE ML SETTINGS:")
            logger.info(f"  - Source: {self.settings.source}")
            logger.info(f"  - Neighbors Count: {self.settings.neighbors_count}")
            logger.info(f"  - Max Bars Back: {self.settings.max_bars_back}")
            logger.info(f"  - Feature Count: {self.settings.feature_count}")
            
            logger.info("📊 FILTER SETTINGS:")
            logger.info(f"  - Use Volatility Filter: {'ON ✅' if self.filter_settings.use_volatility_filter else 'OFF ❌'}")
            logger.info(f"  - Use Regime Filter: {'ON ✅' if self.filter_settings.use_regime_filter else 'OFF ❌'}")
            logger.info(f"  - Use ADX Filter: {'ON ✅' if self.filter_settings.use_adx_filter else 'OFF ❌'}")
            logger.info(f"  - Regime Threshold: {self.filter_settings.regime_threshold}")
            logger.info(f"  - ADX Threshold: {self.filter_settings.adx_threshold}")
            
            logger.info("🧮 KERNEL SETTINGS:")
            logger.info(f"  - Use Kernel Filter: {'ON ✅' if self.config.use_kernel_filter else 'OFF ❌'}")
            logger.info(f"  - Use Kernel Smoothing: {'ON ✅' if self.config.use_kernel_smoothing else 'OFF ❌'}")
            
            logger.warning("========== END CONFIGURATION ==========")

    def _calculate_pre_filter_values(self, high: float, low: float, close: float) -> Dict[str, float]:
        """Calculate raw values before filter application"""
        values = {}
        
        # ADX calculation (simplified)
        if len(self.bars) >= 14:
            # Get recent prices for calculations
            highs = [self.bars.get_high(i) for i in range(min(14, len(self.bars)))]
            lows = [self.bars.get_low(i) for i in range(min(14, len(self.bars)))]
            closes = [self.bars.get_close(i) for i in range(min(14, len(self.bars)))]
            
            # Simple ADX approximation
            tr_sum = sum(max(h - l, abs(h - c), abs(l - c)) 
                        for h, l, c in zip(highs, lows, closes))
            values['adx'] = tr_sum / len(highs) * 2  # Rough approximation
        else:
            values['adx'] = 0.0
        
        # ATR percentage
        if len(self.bars) >= 10:
            atr_values = []
            for i in range(min(10, len(self.bars))):
                h = self.bars.get_high(i)
                l = self.bars.get_low(i)
                c_prev = self.bars.get_close(i+1) if i+1 < len(self.bars) else close
                tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
                atr_values.append(tr)
            atr = sum(atr_values) / len(atr_values)
            values['atr_percent'] = (atr / close) * 100 if close > 0 else 0
        else:
            values['atr_percent'] = 0.0
        
        # StdDev percentage
        if len(self.bars) >= 10:
            closes = [self.bars.get_close(i) for i in range(min(10, len(self.bars)))]
            std_dev = np.std(closes) if len(closes) > 1 else 0
            values['stddev_percent'] = (std_dev / close) * 100 if close > 0 else 0
        else:
            values['stddev_percent'] = 0.0
        
        # Trend strength (SMA based)
        if len(self.bars) >= 30:
            sma_fast = sum(self.bars.get_close(i) for i in range(10)) / 10
            sma_slow = sum(self.bars.get_close(i) for i in range(30)) / 30
            values['trend_strength'] = (sma_fast - sma_slow) / sma_slow if sma_slow > 0 else 0
        else:
            values['trend_strength'] = 0.0
        
        return values

    def process_bar(self, open_price: float, high: float, low: float,
                    close: float, volume: float = 0.0) -> Optional[BarResult]:
        """Process a single bar with debug logging"""
        
        # Validate input
        is_valid, error_msg = validate_ohlcv(open_price, high, low, close, volume)
        if not is_valid:
            logger.warning(f"Skipping invalid bar: {error_msg}")
            return None
        
        if volume is None:
            volume = 0.0
        
        # Update bar data
        self.bars.add_bar(open_price, high, low, close, volume)
        bar_index = self.bars.bar_index
        self.bars_processed += 1
        
        # Calculate pre-filter values
        pre_filter_values = self._calculate_pre_filter_values(high, low, close)
        
        # Log pre-filter values
        logger.info(f"Bar {bar_index} | PRE-FILTER VALUES:")
        logger.info(f"  - ADX Calculated: {pre_filter_values['adx']:.2f} (Threshold: {self.filter_settings.adx_threshold})")
        logger.info(f"  - ATR%: {pre_filter_values['atr_percent']:.2f}, StdDev%: {pre_filter_values['stddev_percent']:.2f}")
        logger.info(f"  - Trend Strength: {pre_filter_values['trend_strength']:.3f} (Regime Threshold: {self.filter_settings.regime_threshold})")
        
        # Calculate features
        feature_series = self._calculate_features_stateful(high, low, close)
        
        # Update feature arrays
        self._update_feature_arrays(feature_series)
        
        # Update training data
        if bar_index >= 4:
            close_4_bars_ago = self.bars.get_close(4)
            self.ml_model.update_training_data(close, close_4_bars_ago)
        
        # Run ML prediction with debug
        min_training_bars = 20
        
        if len(self.ml_model.y_train_array) >= min_training_bars:
            # Log ML debug start
            logger.info(f"=== ML PREDICTION DEBUG START at Bar {bar_index} ===")
            
            # Run prediction (this will generate its own debug logs)
            self.ml_model.predict_with_debug(
                feature_series, self.feature_arrays, bar_index
            )
            
            logger.info(f"Bar {bar_index} | ML Prediction Value: {self.ml_model.prediction}")
        else:
            self.ml_model.prediction = 0.0
        
        # Apply filters with debug
        filter_states = self._apply_filters_stateful_debug(high, low, close)
        
        # Log individual filter results
        logger.info(f"Bar {bar_index} | FILTER RESULTS:")
        logger.info(f"  - Volatility Filter: {filter_states['volatility']} (Enabled: {self.filter_settings.use_volatility_filter})")
        logger.info(f"  - Regime Filter: {filter_states['regime']} (Enabled: {self.filter_settings.use_regime_filter})")
        logger.info(f"  - ADX Filter: {filter_states['adx']} (Enabled: {self.filter_settings.use_adx_filter})")
        
        # Update filter pass counts
        if filter_states['volatility']:
            self.volatility_pass_count += 1
        if filter_states['regime']:
            self.regime_pass_count += 1
        if filter_states['adx']:
            self.adx_pass_count += 1
        self.total_bars_for_filters += 1
        
        # Calculate and log pass rates
        if self.total_bars_for_filters > 0:
            volatility_rate = (self.volatility_pass_count / self.total_bars_for_filters) * 100
            regime_rate = (self.regime_pass_count / self.total_bars_for_filters) * 100
            adx_rate = (self.adx_pass_count / self.total_bars_for_filters) * 100
            
            logger.info(f"Bar {bar_index} | PASS RATES (Historical):")
            logger.info(f"  - Volatility: {volatility_rate:.1f}% ({self.volatility_pass_count}/{self.total_bars_for_filters} bars)")
            logger.info(f"  - Regime: {regime_rate:.1f}% ({self.regime_pass_count}/{self.total_bars_for_filters} bars)")
            logger.info(f"  - ADX: {adx_rate:.1f}% ({self.adx_pass_count}/{self.total_bars_for_filters} bars)")
        
        # Calculate filter_all
        filter_all = all(filter_states.values())
        
        # Log filter_all breakdown
        logger.info(f"Bar {bar_index} | FILTER_ALL BREAKDOWN:")
        logger.info(f"  - Result: {filter_all}")
        logger.info(f"  - Volatility: {filter_states['volatility']} (must be true)")
        logger.info(f"  - Regime: {filter_states['regime']} (must be true)")
        logger.info(f"  - ADX: {filter_states['adx']} (must be true)")
        logger.info(f"  - ALL filters must be TRUE for filter_all to be TRUE")
        
        # Store previous signal
        prev_signal = self.signal_history[0] if self.signal_history else 0
        logger.info(f"Bar {bar_index} | Previous Signal: {prev_signal}")
        
        # Keep ML prediction separate
        ml_prediction = self.ml_model.prediction
        
        # Update signal with debug
        signal = self.ml_model.update_signal(filter_all)
        
        # Log signal decision
        if ml_prediction > 0 and filter_all:
            logger.warning(f"Bar {bar_index} | *** SIGNAL SET TO LONG *** (prediction={ml_prediction} > 0 AND filter_all=true)")
        elif ml_prediction < 0 and filter_all:
            logger.warning(f"Bar {bar_index} | *** SIGNAL SET TO SHORT *** (prediction={ml_prediction} < 0 AND filter_all=true)")
        else:
            logger.info(f"Bar {bar_index} | SIGNAL UNCHANGED - Using previous: {prev_signal} (prediction={ml_prediction}, filter_all={filter_all})")
        
        logger.info(f"Bar {bar_index} | New Signal Value: {signal}")
        
        # Check if signal changed
        if signal != prev_signal:
            logger.error(f"Bar {bar_index} | ★★★ SIGNAL CHANGED ★★★ from {prev_signal} to {signal}")
        else:
            logger.info(f"Bar {bar_index} | Signal STUCK at {signal}")
        
        # Log why signal is stuck
        if not filter_all:
            logger.error(f"Bar {bar_index} | ⚠️ SIGNAL STUCK because filter_all=FALSE! Individual filter status above.")
            if not filter_states['volatility']:
                logger.error("  - Volatility filter FAILED")
            if not filter_states['regime']:
                logger.error("  - Regime filter FAILED")
            if not filter_states['adx']:
                logger.error("  - ADX filter FAILED")
        
        # Calculate trends
        is_ema_uptrend, is_ema_downtrend = self._calculate_ema_trend_stateful(close)
        is_sma_uptrend, is_sma_downtrend = self._calculate_sma_trend_stateful(close)
        
        # Calculate kernel filters
        is_bullish_kernel = self._calculate_kernel_bullish()
        is_bearish_kernel = self._calculate_kernel_bearish()
        
        # Log kernel filter status
        logger.info(f"Bar {bar_index} | Kernel Filter - isBullish: {is_bullish_kernel}, isBearish: {is_bearish_kernel}, useKernelFilter: {self.config.use_kernel_filter}")
        
        # Get kernel crossovers
        kernel_crosses = self._get_kernel_crossovers()
        
        # Generate entry signals
        start_long, start_short = self.signal_generator.check_entry_conditions(
            signal, self.signal_history, is_bullish_kernel, is_bearish_kernel,
            is_ema_uptrend, is_ema_downtrend, is_sma_uptrend, is_sma_downtrend
        )
        
        # Log entry signals
        if start_long:
            logger.error(f"Bar {bar_index} | 🚀🚀🚀 LONG ENTRY TRIGGERED 🚀🚀🚀")
        if start_short:
            logger.error(f"Bar {bar_index} | 📉📉📉 SHORT ENTRY TRIGGERED 📉📉📉")
        
        # Calculate bars held
        bars_held = self.signal_generator.calculate_bars_held(self.entry_history)
        logger.info(f"Bar {bar_index} | Bars Held: {bars_held}")
        
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
        
        # Summary log every 10 bars
        if bar_index % 10 == 0:
            logger.warning(f"====== SUMMARY at Bar {bar_index} ======")
            logger.warning(f"Signal: {signal} | Prediction: {ml_prediction} | filter_all: {filter_all}")
            logger.warning(f"Pass Rates - Vol: {volatility_rate:.1f}%, Regime: {regime_rate:.1f}%, ADX: {adx_rate:.1f}%")
            logger.warning("===============================")
        
        # Calculate SL/TP
        stop_loss = None
        take_profit = None
        
        if start_long or start_short:
            high_values = [self.bars.get_high(i) for i in range(min(20, len(self.bars)))]
            low_values = [self.bars.get_low(i) for i in range(min(20, len(self.bars)))]
            close_values = [self.bars.get_close(i) for i in range(min(20, len(self.bars)))]
            
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

    def _apply_filters_stateful_debug(self, high: float, low: float, close: float) -> Dict[str, bool]:
        """Apply filters with debug logging"""
        current_ohlc4 = self.bars.get_ohlc4(0) if len(self.bars) > 0 else close
        
        # Apply each filter
        volatility = enhanced_filter_volatility(
            high, low, close,
            1, 10,
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

    def _calculate_features_stateful(self, high: float, low: float, close: float) -> FeatureSeries:
        """Calculate all features using stateful indicators"""
        features = self.config.features
        
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
        """Update historical feature arrays"""
        self.feature_arrays.f1.append(feature_series.f1)
        self.feature_arrays.f2.append(feature_series.f2)
        self.feature_arrays.f3.append(feature_series.f3)
        self.feature_arrays.f4.append(feature_series.f4)
        self.feature_arrays.f5.append(feature_series.f5)
        
        max_size = self.settings.max_bars_back
        if len(self.feature_arrays.f1) > max_size:
            self.feature_arrays.f1.pop(0)
            self.feature_arrays.f2.pop(0)
            self.feature_arrays.f3.pop(0)
            self.feature_arrays.f4.pop(0)
            self.feature_arrays.f5.pop(0)

    def _calculate_ema_trend_stateful(self, close: float) -> Tuple[bool, bool]:
        """Calculate EMA trend"""
        if not self.config.use_ema_filter:
            return True, True
        
        self.current_ema_value = enhanced_ema(
            close, self.config.ema_period,
            self.symbol, f"{self.timeframe}_trend"
        )
        
        if self.bars_processed < self.config.ema_period:
            return True, True
        
        is_uptrend = close > self.current_ema_value
        is_downtrend = close < self.current_ema_value
        
        return is_uptrend, is_downtrend

    def _calculate_sma_trend_stateful(self, close: float) -> Tuple[bool, bool]:
        """Calculate SMA trend"""
        if not self.config.use_sma_filter:
            return True, True
        
        self.current_sma_value = enhanced_sma(
            close, self.config.sma_period,
            self.symbol, f"{self.timeframe}_trend"
        )
        
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
        """Get kernel crossover signals"""
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
