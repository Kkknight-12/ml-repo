#!/usr/bin/env python3
"""
Enhanced Bar Processor with Relaxed Signal Generator
====================================================

Uses relaxed entry conditions to increase trade frequency while maintaining quality
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime
from dataclasses import dataclass

from data.data_types import Filter, Label, Settings, FeatureSeries, FeatureArrays
from ml.lorentzian_knn_fixed_corrected import LorentzianKNNFixedCorrected as LorentzianKNN
from scanner.signal_generator_relaxed import RelaxedSignalGenerator
from config.settings import TradingConfig


@dataclass
class BarData:
    """Result of processing a single bar"""
    timestamp: datetime
    signal: int
    prediction: float
    kernel_value: float
    start_long_trade: bool
    start_short_trade: bool
    filter_states: Dict[str, bool]
    feature_values: Dict[str, float]


class EnhancedBarProcessorRelaxed:
    """
    Enhanced bar processor using relaxed signal generator
    
    Key improvements:
    1. No "different signal" requirement
    2. EMA OR SMA trend (not both)
    3. Cooldown period between entries
    4. Optional ML threshold
    """
    
    def __init__(self, config: TradingConfig, symbol: str, timeframe: str):
        """Initialize with configuration"""
        self.config = config
        self.symbol = symbol
        self.timeframe = timeframe
        
        # Core components
        self.label = Label()
        
        # Create settings for ML model
        ml_settings = Settings(
            neighbors_count=config.neighbors_count,
            max_bars_back=config.max_bars_back,
            feature_count=config.feature_count
        )
        
        self.ml_model = LorentzianKNN(ml_settings, self.label)
        
        # Use relaxed signal generator
        self.signal_generator = RelaxedSignalGenerator(
            label=self.label,
            ml_threshold=getattr(config, 'ml_prediction_threshold', 0)
        )
        
        # State tracking
        self.bar_index = 0
        self.feature_arrays = FeatureArrays()
        self.signal_history = []
        self.entry_history = []
        
        # Indicators
        self._init_indicators()
        
        # Performance tracking
        self.ml_predictions = []
        self.ml_signals = []
        self.entries_generated = 0
        
        # Initialize ML model signal
        self.ml_model.signal = 0
        
    def _init_indicators(self):
        """Initialize indicator states"""
        # Price series
        self.close_array = []
        self.high_array = []
        self.low_array = []
        self.hlc3_array = []
        self.volume_array = []
        
        # Technical indicators
        self.rsi_array = []
        self.wt_array = []
        self.cci_array = []
        self.adx_array = []
        
        # Moving averages
        self.ema_fast_array = []
        self.ema_slow_array = []
        self.sma_fast_array = []
        self.sma_slow_array = []
        
        # Kernel
        self.kernel_array = []
        self.kernel_mae = []
        
        # ADX components
        self.tr_array = []
        self.di_plus_array = []
        self.di_minus_array = []
        self.dx_array = []
        
    def process_bar(self, open_price: float, high: float, low: float, 
                   close: float, volume: float) -> BarData:
        """
        Process a single bar with relaxed entry conditions
        
        CRITICAL: ML predictions must be made BEFORE updating feature arrays
        """
        # Update price arrays
        self.close_array.append(close)
        self.high_array.append(high)
        self.low_array.append(low)
        self.hlc3_array.append((high + low + close) / 3)
        self.volume_array.append(volume)
        
        # Default values
        result = BarData(
            timestamp=datetime.now(),
            signal=0,
            prediction=0.0,
            kernel_value=0.0,
            start_long_trade=False,
            start_short_trade=False,
            filter_states={},
            feature_values={}
        )
        
        # Need minimum bars
        if self.bar_index < self.config.max_bars_back:
            self.bar_index += 1
            return result
        
        # Calculate features (stateful)
        features_list = self._calculate_features_stateful(high, low, close)
        
        # Convert to FeatureSeries object
        feature_series = FeatureSeries(
            f1=features_list[0] if len(features_list) > 0 else 0.0,
            f2=features_list[1] if len(features_list) > 1 else 0.0,
            f3=features_list[2] if len(features_list) > 2 else 0.0,
            f4=features_list[3] if len(features_list) > 3 else 0.0,
            f5=features_list[4] if len(features_list) > 4 else 0.0
        )
        
        # Update training data (look back 4 bars) BEFORE predictions
        if self.bar_index >= 4 and len(self.close_array) > 4:
            close_4_bars_ago = self.close_array[-5]  # -5 because we already appended current
            self.ml_model.update_training_data(close, close_4_bars_ago)
        
        # CRITICAL: Make ML prediction BEFORE updating feature arrays
        ml_prediction = self.ml_model.predict(
            feature_series, 
            self.feature_arrays, 
            self.bar_index
        )
        
        # NOW update feature arrays for next prediction
        self._update_feature_arrays(features_list)
        
        # Store prediction for analysis
        self.ml_predictions.append(ml_prediction)
        result.prediction = ml_prediction
        
        # Get filter states
        filter_states = self._check_filters(close)
        result.filter_states = filter_states
        
        # Check if all filters pass
        all_filters_pass = all(filter_states.values())
        
        # Generate signal based on prediction and filters
        signal = self.ml_model.update_signal(all_filters_pass)
        self.signal_history.append(signal)
        self.ml_signals.append(signal)
        result.signal = signal
        
        if all_filters_pass:
            # Get trend and kernel states
            is_ema_uptrend, is_ema_downtrend = self._calculate_ema_trend_stateful(close)
            is_sma_uptrend, is_sma_downtrend = self._calculate_sma_trend_stateful(close)
            is_bullish_kernel = self._calculate_kernel_bullish()
            is_bearish_kernel = self._calculate_kernel_bearish()
            
            # Use relaxed entry conditions
            start_long, start_short = self.signal_generator.check_entry_conditions(
                signal=signal,
                signal_history=self.signal_history[:-1],  # Exclude current
                ml_prediction=ml_prediction,
                is_bullish_kernel=is_bullish_kernel,
                is_bearish_kernel=is_bearish_kernel,
                is_ema_uptrend=is_ema_uptrend,
                is_ema_downtrend=is_ema_downtrend,
                is_sma_uptrend=is_sma_uptrend,
                is_sma_downtrend=is_sma_downtrend,
                current_bar=self.bar_index
            )
            
            result.start_long_trade = start_long
            result.start_short_trade = start_short
            
            if start_long or start_short:
                self.entries_generated += 1
        
        # Track entry history
        self.entry_history.append((result.start_long_trade, result.start_short_trade))
        
        # Update bar index
        self.bar_index += 1
        
        return result
    
    def _calculate_features_stateful(self, high: float, low: float, close: float) -> List[float]:
        """Calculate features maintaining state"""
        # RSI
        rsi = self._calculate_rsi_stateful(close)
        self.rsi_array.append(rsi)
        
        # Wave Trend
        wt = self._calculate_wt_stateful(self.hlc3_array[-1] if self.hlc3_array else close)
        self.wt_array.append(wt)
        
        # CCI
        cci = self._calculate_cci_stateful(high, low, close)
        self.cci_array.append(cci)
        
        # ADX
        adx = self._calculate_adx_stateful(high, low, close)
        self.adx_array.append(adx)
        
        # Normalize features
        features = [
            self._rescale(rsi, 0, 100, 0, 1),
            self._rescale(wt, -60, 60, 0, 1),
            self._rescale(cci, -100, 100, 0, 1),
            self._rescale(adx, 0, 50, 0, 1)
        ]
        
        return features[:self.config.feature_count]
    
    def _update_feature_arrays(self, features: List[float]):
        """Update feature arrays for k-NN"""
        # Update each feature array
        if len(features) > 0:
            self.feature_arrays.f1.append(features[0])
            if len(self.feature_arrays.f1) > self.config.max_bars_back:
                self.feature_arrays.f1.pop(0)
                
        if len(features) > 1:
            self.feature_arrays.f2.append(features[1])
            if len(self.feature_arrays.f2) > self.config.max_bars_back:
                self.feature_arrays.f2.pop(0)
                
        if len(features) > 2:
            self.feature_arrays.f3.append(features[2])
            if len(self.feature_arrays.f3) > self.config.max_bars_back:
                self.feature_arrays.f3.pop(0)
                
        if len(features) > 3:
            self.feature_arrays.f4.append(features[3])
            if len(self.feature_arrays.f4) > self.config.max_bars_back:
                self.feature_arrays.f4.pop(0)
                
        if len(features) > 4:
            self.feature_arrays.f5.append(features[4])
            if len(self.feature_arrays.f5) > self.config.max_bars_back:
                self.feature_arrays.f5.pop(0)
    
    def _check_filters(self, close: float) -> Dict[str, bool]:
        """Check all filter conditions"""
        filters = {}
        
        # Volatility filter
        if self.config.use_volatility_filter:
            filters['volatility'] = self._check_volatility_filter()
        else:
            filters['volatility'] = True
        
        # Regime filter
        if self.config.use_regime_filter:
            filters['regime'] = self._check_regime_filter(close)
        else:
            filters['regime'] = True
        
        # ADX filter
        if self.config.use_adx_filter and len(self.adx_array) > 0:
            filters['adx'] = self.adx_array[-1] > self.config.adx_threshold
        else:
            filters['adx'] = True
        
        return filters
    
    def _calculate_rsi_stateful(self, close: float) -> float:
        """Calculate RSI maintaining state"""
        if len(self.close_array) < 2:
            return 50.0
        
        # Simple RSI calculation
        period = 14
        if len(self.close_array) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(len(self.close_array) - period, len(self.close_array)):
            change = self.close_array[i] - self.close_array[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_wt_stateful(self, hlc3: float) -> float:
        """Calculate Wave Trend maintaining state"""
        if len(self.hlc3_array) < 10:
            return 0.0
        
        # Simplified WT calculation
        period = 10
        hlc3_slice = self.hlc3_array[-period:]
        ema1 = np.mean(hlc3_slice)
        
        # Calculate deviation
        dev = np.std(hlc3_slice)
        
        # Calculate CI
        ci = (hlc3 - ema1) / (0.015 * dev) if dev > 0 else 0
        
        return ci
    
    def _calculate_cci_stateful(self, high: float, low: float, close: float) -> float:
        """Calculate CCI maintaining state"""
        if len(self.high_array) < 20:
            return 0.0
        
        period = 20
        tp = (high + low + close) / 3
        
        # Get typical prices
        tp_array = []
        for i in range(len(self.high_array) - period, len(self.high_array)):
            tp_i = (self.high_array[i] + self.low_array[i] + self.close_array[i]) / 3
            tp_array.append(tp_i)
        
        sma = np.mean(tp_array)
        mad = np.mean([abs(tp_i - sma) for tp_i in tp_array])
        
        if mad == 0:
            return 0.0
        
        cci = (tp - sma) / (0.015 * mad)
        return cci
    
    def _calculate_adx_stateful(self, high: float, low: float, close: float) -> float:
        """Calculate ADX maintaining state"""
        if len(self.high_array) < 2:
            return 0.0
        
        # True Range
        prev_close = self.close_array[-2]
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        tr = max(tr1, tr2, tr3)
        self.tr_array.append(tr)
        
        # Directional movements
        prev_high = self.high_array[-2]
        prev_low = self.low_array[-2]
        
        plus_dm = max(0, high - prev_high) if high > prev_high else 0
        minus_dm = max(0, prev_low - low) if prev_low > low else 0
        
        if plus_dm > minus_dm:
            minus_dm = 0
        elif minus_dm > plus_dm:
            plus_dm = 0
        
        # Need enough data
        if len(self.tr_array) < 14:
            return 0.0
        
        # Calculate smoothed values
        period = 14
        tr_sum = sum(self.tr_array[-period:])
        
        if tr_sum == 0:
            return 0.0
        
        # Simple ADX calculation
        di_plus = 100 * plus_dm / tr
        di_minus = 100 * minus_dm / tr
        
        di_sum = di_plus + di_minus
        if di_sum == 0:
            return 0.0
        
        dx = 100 * abs(di_plus - di_minus) / di_sum
        
        # Simple average for ADX
        if len(self.dx_array) >= period:
            self.dx_array.append(dx)
            adx = np.mean(self.dx_array[-period:])
        else:
            self.dx_array.append(dx)
            adx = dx
        
        return adx
    
    def _calculate_ema_trend_stateful(self, close: float) -> Tuple[bool, bool]:
        """Calculate EMA trend"""
        # Update EMAs
        if not self.ema_fast_array:
            self.ema_fast_array.append(close)
            self.ema_slow_array.append(close)
        else:
            alpha_fast = 2 / (9 + 1)
            alpha_slow = 2 / (12 + 1)
            
            ema_fast = alpha_fast * close + (1 - alpha_fast) * self.ema_fast_array[-1]
            ema_slow = alpha_slow * close + (1 - alpha_slow) * self.ema_slow_array[-1]
            
            self.ema_fast_array.append(ema_fast)
            self.ema_slow_array.append(ema_slow)
        
        if len(self.ema_fast_array) < 2:
            return False, False
        
        is_uptrend = self.ema_fast_array[-1] > self.ema_slow_array[-1]
        is_downtrend = self.ema_fast_array[-1] < self.ema_slow_array[-1]
        
        return is_uptrend, is_downtrend
    
    def _calculate_sma_trend_stateful(self, close: float) -> Tuple[bool, bool]:
        """Calculate SMA trend"""
        # Update SMAs
        if len(self.close_array) >= 50:
            sma_fast = np.mean(self.close_array[-50:])
            sma_slow = np.mean(self.close_array[-200:]) if len(self.close_array) >= 200 else sma_fast
            
            self.sma_fast_array.append(sma_fast)
            self.sma_slow_array.append(sma_slow)
            
            is_uptrend = sma_fast > sma_slow
            is_downtrend = sma_fast < sma_slow
            
            return is_uptrend, is_downtrend
        
        return False, False
    
    def _calculate_kernel_bullish(self) -> bool:
        """Check if kernel is bullish"""
        # For now, return based on RSI momentum
        if len(self.rsi_array) < 2:
            return False
        return self.rsi_array[-1] > self.rsi_array[-2] and self.rsi_array[-1] > 50
    
    def _calculate_kernel_bearish(self) -> bool:
        """Check if kernel is bearish"""
        # For now, return based on RSI momentum
        if len(self.rsi_array) < 2:
            return False
        return self.rsi_array[-1] < self.rsi_array[-2] and self.rsi_array[-1] < 50
    
    def _check_volatility_filter(self) -> bool:
        """Simplified volatility filter"""
        if len(self.close_array) < 20:
            return True
        
        returns = []
        for i in range(1, min(20, len(self.close_array))):
            ret = (self.close_array[-i] - self.close_array[-i-1]) / self.close_array[-i-1]
            returns.append(ret)
        
        volatility = np.std(returns) * np.sqrt(252)
        return volatility <= 0.5  # Max 50% annualized volatility
    
    def _check_regime_filter(self, close: float) -> bool:
        """Simplified regime filter"""
        if len(self.close_array) < 50:
            return True
        
        sma = np.mean(self.close_array[-50:])
        return close > sma * 0.98  # Within 2% of SMA
    
    def _rescale(self, value: float, old_min: float, old_max: float, 
                 new_min: float, new_max: float) -> float:
        """Rescale value to new range"""
        if old_max == old_min:
            return new_min
        return new_min + (value - old_min) * (new_max - new_min) / (old_max - old_min)
    
    def get_statistics(self) -> Dict:
        """Get processing statistics"""
        ml_signals_count = sum(1 for s in self.ml_signals if s != 0)
        non_zero_predictions = sum(1 for p in self.ml_predictions if abs(p) > 0.1)
        
        return {
            'bars_processed': self.bar_index,
            'ml_predictions_made': len(self.ml_predictions),
            'non_zero_predictions': non_zero_predictions,
            'non_zero_prediction_rate': non_zero_predictions / len(self.ml_predictions) * 100 if self.ml_predictions else 0,
            'ml_signals_generated': ml_signals_count,
            'entries_generated': self.entries_generated,
            'signal_to_entry_rate': self.entries_generated / ml_signals_count * 100 if ml_signals_count > 0 else 0
        }