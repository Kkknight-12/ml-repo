"""
Test Relaxed Confirmation Filters
=================================

Test confirmation filters with more permissive parameters.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from data.smart_data_manager import SmartDataManager
from scanner.confirmation_processor import ConfirmationProcessor
from scanner.ml_quality_filter import MLQualityFilter
from config.adaptive_config import create_adaptive_config
from config.settings import TradingConfig


class RelaxedConfirmationProcessor(ConfirmationProcessor):
    """Confirmation processor with relaxed parameters"""
    
    def __init__(self, config, symbol: str, timeframe: str,
                 require_volume: bool = True,
                 require_momentum: bool = True,
                 require_sr: bool = False,
                 min_confirmations: int = 2):
        """Initialize with relaxed parameters"""
        super().__init__(config, symbol, timeframe,
                        require_volume, require_momentum, 
                        require_sr, min_confirmations)
        
        # Override with relaxed parameters
        self.volume_filter.min_volume_ratio = 1.2  # Down from 1.5
        self.volume_filter.spike_threshold = 1.8   # Down from 2.0
        
        self.momentum_filter.rsi_overbought = 75   # Up from 70
        self.momentum_filter.rsi_oversold = 25     # Down from 30
        
        # Relax confirmation score requirement
        self.min_confirmation_score = 0.4  # Down from 0.6
    
    def process_bar(self, open_price: float, high: float, low: float, 
                   close: float, volume: float):
        """Process with relaxed scoring"""
        result = super().process_bar(open_price, high, low, close, volume)
        
        if result and result.mode_filtered_signal != 0:
            # Re-evaluate with relaxed criteria
            if result.confirmation_score >= self.min_confirmation_score:
                # Use OR logic for required confirmations
                if self.require_volume and self.require_momentum:
                    # Either volume OR momentum is enough
                    if result.volume_confirmed or result.momentum_confirmed:
                        result.confirmed_signal = result.mode_filtered_signal
                elif result.confirmation_count >= 1:  # At least one confirmation
                    result.confirmed_signal = result.mode_filtered_signal
        
        return result


def test_relaxed_filters(symbol: str = 'RELIANCE'):
    """Test with relaxed confirmation parameters"""
    
    print(f"\n{'='*60}")
    print(f"TESTING RELAXED CONFIRMATION FILTERS - {symbol}")
    print(f"{'='*60}")
    
    # Get data
    data_manager = SmartDataManager()
    df = data_manager.get_data(symbol, interval='5minute', days=90)
    
    if df is None or len(df) < 2000:
        print(f"⚠️  Insufficient data: {len(df) if df is not None else 0} bars")
        return None
    
    print(f"\nData loaded: {len(df)} bars")
    
    # Get adaptive config
    stats = data_manager.analyze_price_movement(df)
    adaptive_config = create_adaptive_config(symbol, '5minute', stats)
    
    # Create trading config
    trading_config = TradingConfig(
        source=adaptive_config.source,
        neighbors_count=adaptive_config.neighbors_count,
        max_bars_back=adaptive_config.max_bars_back,
        feature_count=adaptive_config.feature_count,
        features=adaptive_config.features
    )
    
    # Test configurations
    configs = [
        {
            'name': 'Original Strict',
            'processor_class': ConfirmationProcessor,
            'require_volume': True,
            'require_momentum': True,
            'require_sr': False,
            'min_confirmations': 2
        },
        {
            'name': 'Relaxed Parameters',
            'processor_class': RelaxedConfirmationProcessor,
            'require_volume': True,
            'require_momentum': True,
            'require_sr': False,
            'min_confirmations': 2
        },
        {
            'name': 'Volume OR Momentum',
            'processor_class': RelaxedConfirmationProcessor,
            'require_volume': True,
            'require_momentum': True,
            'require_sr': False,
            'min_confirmations': 1
        },
        {
            'name': 'Single Filter',
            'processor_class': RelaxedConfirmationProcessor,
            'require_volume': True,
            'require_momentum': False,
            'require_sr': False,
            'min_confirmations': 1
        }
    ]
    
    # ML filter - try lower threshold too
    ml_thresholds = [3.0, 2.5]
    
    all_results = {}
    
    for ml_threshold in ml_thresholds:
        print(f"\n{'='*60}")
        print(f"ML THRESHOLD: {ml_threshold}")
        print(f"{'='*60}")
        
        ml_filter = MLQualityFilter(min_confidence=ml_threshold)
        results = {}
        
        for config in configs:
            print(f"\n{'='*50}")
            print(f"Testing: {config['name']}")
            print(f"{'='*50}")
            
            # Create processor
            ProcessorClass = config['processor_class']
            processor = ProcessorClass(
                config=trading_config,
                symbol=symbol,
                timeframe='5minute',
                require_volume=config['require_volume'],
                require_momentum=config['require_momentum'],
                require_sr=config['require_sr'],
                min_confirmations=config['min_confirmations']
            )
            
            # Track signals
            raw_signals = 0
            mode_filtered_signals = 0
            confirmed_signals = 0
            
            print(f"Processing {len(df)} bars...")
            
            for idx, row in df.iterrows():
                result = processor.process_bar(
                    open_price=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume']
                )
                
                if result:
                    if result.signal != 0:
                        raw_signals += 1
                    
                    if result.mode_filtered_signal != 0:
                        # Apply ML filter
                        signal_dict = {
                            'timestamp': idx,
                            'signal': result.mode_filtered_signal,
                            'prediction': result.prediction,
                            'filter_states': result.filter_states,
                            'features': {}
                        }
                        
                        ml_signal = ml_filter.filter_signal(signal_dict, symbol)
                        if ml_signal is not None:
                            mode_filtered_signals += 1
                            
                            if result.confirmed_signal != 0:
                                confirmed_signals += 1
            
            results[config['name']] = {
                'raw': raw_signals,
                'mode_filtered': mode_filtered_signals,
                'confirmed': confirmed_signals,
                'reduction': (1 - confirmed_signals/mode_filtered_signals) * 100 
                            if mode_filtered_signals > 0 else 100
            }
            
            print(f"\nResults:")
            print(f"  Raw signals: {raw_signals}")
            print(f"  Mode-filtered: {mode_filtered_signals}")
            print(f"  Confirmed: {confirmed_signals}")
            print(f"  Reduction: {results[config['name']]['reduction']:.1f}%")
        
        all_results[ml_threshold] = results
    
    # Summary comparison
    print(f"\n{'='*60}")
    print("SUMMARY COMPARISON")
    print(f"{'='*60}")
    
    print(f"\n{'Config':<25} {'ML 3.0':<15} {'ML 2.5':<15} {'Improvement':<15}")
    print("-" * 70)
    
    for config_name in ['Original Strict', 'Relaxed Parameters', 'Volume OR Momentum', 'Single Filter']:
        ml30 = all_results[3.0][config_name]['confirmed']
        ml25 = all_results[2.5][config_name]['confirmed']
        improvement = ml25 - ml30
        
        print(f"{config_name:<25} {ml30:<15} {ml25:<15} {improvement:<15}")
    
    # Recommendations
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print(f"{'='*60}")
    
    best_config = None
    best_signals = 0
    
    for threshold, results in all_results.items():
        for config_name, data in results.items():
            if data['confirmed'] > best_signals and data['confirmed'] >= 100:
                best_signals = data['confirmed']
                best_config = (threshold, config_name)
    
    if best_config:
        print(f"\n✅ Best configuration:")
        print(f"   ML Threshold: {best_config[0]}")
        print(f"   Filter Config: {best_config[1]}")
        print(f"   Signals: {best_signals}")
        print(f"\nThis provides a good balance between signal quality and quantity.")
    else:
        print("\n⚠️  All configurations still too restrictive")
        print("   Consider further relaxing parameters")


def main():
    """Run relaxed confirmation tests"""
    
    print("\n" + "="*60)
    print("RELAXED CONFIRMATION FILTER TEST")
    print("="*60)
    
    test_relaxed_filters('RELIANCE')


if __name__ == "__main__":
    main()