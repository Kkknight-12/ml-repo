#!/usr/bin/env python3
"""
Test Modular Trading System
===========================

Demonstrates how to use the modular architecture to test different
strategy combinations independently.

Philosophy: Test one thing at a time. Measure everything.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

# Import modular system
from config.modular_strategies import ModularTradingSystem, StrategyModule

# Core imports
from scanner.enhanced_bar_processor import EnhancedBarProcessor
from config.settings import TradingConfig
from data.zerodha_client import ZerodhaClient

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModularTradingEngine:
    """Trading engine that uses modular strategies"""
    
    def __init__(self, preset: str = "baseline"):
        """Initialize with a preset configuration"""
        self.system = ModularTradingSystem().create_preset(preset)
        self.processors = {}
        self.trades = []
        
        print(f"\n🚀 Initialized Modular Trading Engine")
        print(f"   Preset: {preset}")
        print(f"   Active modules: {len(self.system.get_enabled_modules())}")
    
    def process_bar(self, symbol: str, bar: Dict) -> Dict:
        """Process a bar through all enabled modules"""
        
        # Initialize processor if needed
        if symbol not in self.processors:
            config = TradingConfig()
            self.processors[symbol] = EnhancedBarProcessor(config, symbol, "5min")
        
        processor = self.processors[symbol]
        
        # Get base ML signal
        ml_result = processor.process_bar(
            bar['open'], bar['high'], bar['low'], 
            bar['close'], bar['volume']
        )
        
        # Initialize signal scoring
        signal_score = 0.0
        signal_reasons = []
        filters_passed = {}
        
        # ===== CORE ML SIGNAL =====
        if self.system.modules[StrategyModule.LORENTZIAN_ML].enabled:
            if abs(ml_result.prediction) > 0:
                signal_score += ml_result.prediction
                signal_reasons.append(f"ML: {ml_result.prediction:.2f}")
        
        # ===== AI TRADING MODULES =====
        
        # Pattern Quality Scoring
        if self.system.modules[StrategyModule.AI_PATTERN_QUALITY].enabled:
            pattern_score = self._calculate_pattern_quality(ml_result, bar)
            config = self.system.modules[StrategyModule.AI_PATTERN_QUALITY].parameters
            
            if pattern_score >= config['min_score']:
                signal_score += 2.0
                signal_reasons.append(f"Pattern: {pattern_score:.1f}/10")
                filters_passed['pattern_quality'] = True
            else:
                filters_passed['pattern_quality'] = False
        
        # Time Window Filter
        if self.system.modules[StrategyModule.AI_TIME_WINDOWS].enabled:
            current_hour = datetime.now().hour + datetime.now().minute / 60
            config = self.system.modules[StrategyModule.AI_TIME_WINDOWS].parameters
            
            in_prime = config['prime_start'] <= current_hour <= config['prime_end']
            can_trade = config['no_trade_before'] <= current_hour <= config['no_trade_after']
            
            if not can_trade:
                signal_score = 0  # Override - no trades outside window
                signal_reasons.append("Outside trading hours")
            elif in_prime:
                signal_score *= config['prime_window_multiplier']
                signal_reasons.append("Prime window ✨")
            
            filters_passed['time_window'] = can_trade
        
        # Stock Filtering
        if self.system.modules[StrategyModule.AI_STOCK_FILTERING].enabled:
            config = self.system.modules[StrategyModule.AI_STOCK_FILTERING].parameters
            
            price_ok = config['min_price'] <= bar['close'] <= config['max_price']
            
            # Calculate volume ratio (would need historical average)
            volume_ratio = 1.5  # Placeholder
            volume_ok = volume_ratio >= config['min_volume_ratio']
            
            # Calculate change percent
            change_pct = abs((bar['close'] - bar['open']) / bar['open'] * 100)
            change_ok = change_pct >= config['min_change_percent']
            
            if not (price_ok and volume_ok and change_ok):
                signal_score = 0  # Don't trade this stock
                signal_reasons.append("Failed stock filter")
            
            filters_passed['stock_filter'] = price_ok and volume_ok and change_ok
        
        # ===== EHLERS DSP MODULES =====
        
        # Market Mode Detection
        market_mode = "UNKNOWN"
        if self.system.modules[StrategyModule.EHLERS_MARKET_MODE].enabled:
            config = self.system.modules[StrategyModule.EHLERS_MARKET_MODE].parameters
            
            # Simple ADX-based mode detection (placeholder)
            adx_value = 22  # Would calculate from bars
            
            if adx_value > config['trend_adx_threshold']:
                market_mode = "TREND"
                # In trend mode, reduce cycle-based signals
                if abs(signal_score) < 4:
                    signal_score *= 0.5
                    signal_reasons.append("Trend mode penalty")
            else:
                market_mode = "CYCLE"
                signal_reasons.append("Cycle mode ✓")
            
            filters_passed['market_mode'] = market_mode
        
        # ===== RISK MANAGEMENT MODULES =====
        
        # Position Sizing
        position_size = 1.0
        if self.system.modules[StrategyModule.AI_POSITION_SIZING].enabled:
            config = self.system.modules[StrategyModule.AI_POSITION_SIZING].parameters
            
            # Find appropriate bracket
            for (min_price, max_price), max_shares in config['price_brackets'].items():
                if min_price <= bar['close'] < max_price:
                    position_size = max_shares
                    break
            
            signal_reasons.append(f"Max size: {position_size}")
        
        # Daily Limits Check
        if self.system.modules[StrategyModule.AI_DAILY_LIMITS].enabled:
            config = self.system.modules[StrategyModule.AI_DAILY_LIMITS].parameters
            
            # Count today's trades
            today_trades = sum(1 for t in self.trades 
                             if t['date'].date() == datetime.now().date())
            
            if today_trades >= config['max_trades_per_day']:
                signal_score = 0
                signal_reasons.append("Daily trade limit reached")
                filters_passed['daily_limit'] = False
            else:
                filters_passed['daily_limit'] = True
        
        # ===== FINAL SIGNAL DECISION =====
        
        entry_signal = False
        signal_direction = 0
        
        if signal_score >= 3.0:
            entry_signal = True
            signal_direction = 1  # Long
        elif signal_score <= -3.0:
            entry_signal = True
            signal_direction = -1  # Short
        
        return {
            'symbol': symbol,
            'ml_prediction': ml_result.prediction,
            'signal_score': signal_score,
            'entry_signal': entry_signal,
            'signal_direction': signal_direction,
            'position_size': position_size,
            'market_mode': market_mode,
            'filters_passed': filters_passed,
            'signal_reasons': signal_reasons
        }
    
    def _calculate_pattern_quality(self, ml_result, bar) -> float:
        """Calculate pattern quality score (0-10)"""
        score = 5.0
        
        # ML prediction strength
        pred_strength = abs(ml_result.prediction)
        if pred_strength >= 6:
            score += 3
        elif pred_strength >= 4:
            score += 2
        elif pred_strength >= 2:
            score += 1
        
        # Filter alignment (simplified)
        filters_passed = sum([
            ml_result.filter_states.get('volatility', False),
            ml_result.filter_states.get('regime', False),
            ml_result.filter_states.get('adx', False)
        ])
        score += filters_passed * 0.5
        
        return min(10, score)
    
    def compare_modules(self, symbol: str, bars: pd.DataFrame):
        """Run same data through different module combinations"""
        
        results = {}
        
        # Test configurations
        test_configs = [
            ("baseline", "Lorentzian ML Only"),
            ("ai_enhanced", "ML + AI Trading Rules"),
            ("quantitative", "ML + Quant Methods"),
            ("ehlers_cycle", "ML + Ehlers DSP"),
            ("production", "Production Mix")
        ]
        
        print(f"\n📊 Module Comparison for {symbol}")
        print("="*60)
        
        for preset, description in test_configs:
            # Create system with preset
            self.system = ModularTradingSystem().create_preset(preset)
            
            # Reset state
            self.processors = {}
            self.trades = []
            
            # Process all bars
            signals = []
            for _, bar in bars.iterrows():
                result = self.process_bar(symbol, bar.to_dict())
                if result['entry_signal']:
                    signals.append(result)
            
            # Store results
            results[preset] = {
                'description': description,
                'total_signals': len(signals),
                'long_signals': sum(1 for s in signals if s['signal_direction'] > 0),
                'short_signals': sum(1 for s in signals if s['signal_direction'] < 0),
                'avg_score': np.mean([s['signal_score'] for s in signals]) if signals else 0,
                'modules_enabled': len(self.system.get_enabled_modules())
            }
            
            print(f"\n{description}:")
            print(f"  Modules enabled: {results[preset]['modules_enabled']}")
            print(f"  Total signals: {results[preset]['total_signals']}")
            print(f"  Long/Short: {results[preset]['long_signals']}/{results[preset]['short_signals']}")
            print(f"  Avg score: {results[preset]['avg_score']:.2f}")
        
        return results


def main():
    """Demo the modular system"""
    
    print("="*60)
    print("🧪 MODULAR TRADING SYSTEM TEST")
    print("="*60)
    
    # 1. Show available modules
    print("\n1️⃣ Available Modules:")
    system = ModularTradingSystem()
    
    for module in StrategyModule:
        config = system.modules[module]
        print(f"   • {module.value}: {config.description}")
    
    # 2. Test different presets
    print("\n2️⃣ Testing Presets:")
    
    presets = ["baseline", "ai_enhanced", "production"]
    for preset in presets:
        print(f"\n   {preset.upper()}:")
        test_system = ModularTradingSystem().create_preset(preset)
        enabled = test_system.get_enabled_modules()
        print(f"   Enabled: {[m.value for m in enabled]}")
    
    # 3. Custom module combination
    print("\n3️⃣ Custom Module Mix:")
    custom = ModularTradingSystem()
    
    # Enable specific combination for testing
    custom.enable_module(StrategyModule.AI_PATTERN_QUALITY)
    custom.enable_module(StrategyModule.EHLERS_MARKET_MODE)
    custom.enable_module(StrategyModule.RISK_MULTI_TARGET)
    
    print("\n   Custom configuration created!")
    
    # 4. A/B Testing example
    print("\n4️⃣ A/B Testing Example:")
    print("   Group A: Baseline (ML only)")
    print("   Group B: Baseline + AI Time Windows")
    print("   Group C: Baseline + Ehlers Market Mode")
    print("\n   Run same historical data through each group")
    print("   Compare: signals generated, win rate, profit factor")
    
    # 5. Module interaction example
    print("\n5️⃣ Module Interactions:")
    print("   • AI Time Windows can override all signals outside hours")
    print("   • Ehlers Market Mode can reduce signals in trends")
    print("   • Pattern Quality can boost high-conviction trades")
    print("   • Daily Limits provide hard stop on overtrading")
    
    print("\n✅ Modular system ready for A/B testing!")
    print("   Each technique can be tested in isolation")
    print("   Or combined for synergistic effects")
    print("   Always measure impact vs baseline")


if __name__ == "__main__":
    main()