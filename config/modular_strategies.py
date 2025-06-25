"""
Modular Trading Strategies Configuration
========================================

This module implements a clean, modular architecture for trading strategies.
Each technique can be independently enabled/disabled for A/B testing.

Philosophy: Keep it simple but effective. Test everything independently.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum

class StrategyModule(Enum):
    """All available strategy modules"""
    # Core Lorentzian ML
    LORENTZIAN_ML = "lorentzian_ml"
    
    # AI Trading Knowledge Base
    AI_PATTERN_QUALITY = "ai_pattern_quality"
    AI_TIME_WINDOWS = "ai_time_windows"
    AI_POSITION_SIZING = "ai_position_sizing"
    AI_DAILY_LIMITS = "ai_daily_limits"
    AI_STOCK_FILTERING = "ai_stock_filtering"
    
    # Quantitative Trading
    QUANT_KELLY_CRITERION = "quant_kelly_criterion"
    QUANT_RISK_PARITY = "quant_risk_parity"
    QUANT_MEAN_REVERSION = "quant_mean_reversion"
    QUANT_MOMENTUM = "quant_momentum"
    QUANT_STATISTICAL_ARB = "quant_statistical_arb"
    
    # Trading Warrior
    WARRIOR_MOMENTUM_CONFLUENCE = "warrior_momentum_confluence"
    WARRIOR_MULTI_TIMEFRAME = "warrior_multi_timeframe"
    WARRIOR_SUPPLY_DEMAND = "warrior_supply_demand"
    WARRIOR_VOLUME_PROFILE = "warrior_volume_profile"
    
    # Ehlers DSP Techniques
    EHLERS_MARKET_MODE = "ehlers_market_mode"
    EHLERS_SUPER_SMOOTHER = "ehlers_super_smoother"
    EHLERS_ROOFING_FILTER = "ehlers_roofing_filter"
    EHLERS_SINEWAVE = "ehlers_sinewave"
    EHLERS_ADAPTIVE_INDICATORS = "ehlers_adaptive_indicators"
    EHLERS_CYCLE_MEASUREMENT = "ehlers_cycle_measurement"
    
    # Risk Management
    RISK_ATR_STOPS = "risk_atr_stops"
    RISK_MULTI_TARGET = "risk_multi_target"
    RISK_TRAILING_STOPS = "risk_trailing_stops"
    RISK_POSITION_SIZING = "risk_position_sizing"


@dataclass
class ModuleConfig:
    """Configuration for a single module"""
    enabled: bool = False
    weight: float = 1.0  # Importance weight for combining signals
    parameters: Dict = field(default_factory=dict)
    description: str = ""
    source: str = ""  # Where this technique comes from


@dataclass
class ModularTradingSystem:
    """Main class for modular trading system"""
    
    # Module states - easily enable/disable
    modules: Dict[StrategyModule, ModuleConfig] = field(default_factory=dict)
    
    def __init__(self):
        """Initialize with all modules disabled by default"""
        self._initialize_modules()
    
    def _initialize_modules(self):
        """Define all available modules with descriptions"""
        
        # Core ML
        self.modules[StrategyModule.LORENTZIAN_ML] = ModuleConfig(
            enabled=True,  # Core is always on
            description="Core Lorentzian k-NN ML algorithm",
            source="Pine Script original"
        )
        
        # ===== AI TRADING KNOWLEDGE BASE MODULES =====
        
        self.modules[StrategyModule.AI_PATTERN_QUALITY] = ModuleConfig(
            enabled=False,
            description="Pattern quality scoring (1-10 scale)",
            source="AI-Trading-Knowledge-Base.md",
            parameters={
                "min_score": 7.0,
                "high_conviction_score": 8.5,
                "scoring_factors": ["ml_strength", "filter_alignment", "time_window", "momentum"]
            }
        )
        
        self.modules[StrategyModule.AI_TIME_WINDOWS] = ModuleConfig(
            enabled=False,
            description="Prime trading window 11:30-1:30 PM (85% win rate)",
            source="AI-Trading-Knowledge-Base.md",
            parameters={
                "no_trade_before": 11.0,  # 11:00 AM
                "prime_start": 11.5,      # 11:30 AM
                "prime_end": 13.5,        # 1:30 PM
                "no_trade_after": 14.75,  # 2:45 PM
                "prime_window_multiplier": 1.5  # Score boost in prime window
            }
        )
        
        self.modules[StrategyModule.AI_POSITION_SIZING] = ModuleConfig(
            enabled=False,
            description="Position sizing matrix based on stock price",
            source="AI-Trading-Knowledge-Base.md",
            parameters={
                "price_brackets": {
                    (0, 100): 50,      # Max 50 shares
                    (100, 300): 30,    # Max 30 shares
                    (300, 500): 20,    # Max 20 shares
                    (500, 1000): 10,   # Max 10 shares
                    (1000, float('inf')): 5  # Max 5 shares
                }
            }
        )
        
        self.modules[StrategyModule.AI_DAILY_LIMITS] = ModuleConfig(
            enabled=False,
            description="Strict 2 trades/day, 2% daily loss limit",
            source="AI-Trading-Knowledge-Base.md",
            parameters={
                "max_trades_per_day": 2,
                "max_daily_loss_percent": 2.0,
                "stop_on_limit": True
            }
        )
        
        self.modules[StrategyModule.AI_STOCK_FILTERING] = ModuleConfig(
            enabled=False,
            description="Stock screening: ₹50-500, 2x volume, 2%+ move",
            source="AI-Trading-Knowledge-Base.md",
            parameters={
                "min_price": 50,
                "max_price": 500,
                "min_volume_ratio": 2.0,
                "min_change_percent": 2.0,
                "min_turnover_lakhs": 50
            }
        )
        
        # ===== QUANTITATIVE TRADING MODULES =====
        
        self.modules[StrategyModule.QUANT_KELLY_CRITERION] = ModuleConfig(
            enabled=False,
            description="Optimal position sizing using Kelly formula",
            source="Quantitative-Trading-Introduction",
            parameters={
                "kelly_fraction": 0.25,  # Use 25% of Kelly
                "max_position_percent": 20,
                "use_historical_win_rate": True
            }
        )
        
        self.modules[StrategyModule.QUANT_RISK_PARITY] = ModuleConfig(
            enabled=False,
            description="Equal risk contribution across positions",
            source="Quantitative-Trading-Introduction",
            parameters={
                "target_volatility": 0.15,  # 15% annual
                "rebalance_threshold": 0.1,
                "use_correlation_matrix": True
            }
        )
        
        self.modules[StrategyModule.QUANT_MEAN_REVERSION] = ModuleConfig(
            enabled=False,
            description="Trade reversions to statistical mean",
            source="Quantitative-Trading-Introduction",
            parameters={
                "zscore_entry": 2.0,
                "zscore_exit": 0.5,
                "lookback_period": 20,
                "use_bollinger_bands": True
            }
        )
        
        self.modules[StrategyModule.QUANT_MOMENTUM] = ModuleConfig(
            enabled=False,
            description="Momentum factor with risk controls",
            source="Quantitative-Trading-Introduction",
            parameters={
                "momentum_period": 20,
                "holding_period": 5,
                "rank_threshold": 0.8,  # Top 20%
                "use_risk_adjusted": True
            }
        )
        
        # ===== TRADING WARRIOR MODULES =====
        
        self.modules[StrategyModule.WARRIOR_MOMENTUM_CONFLUENCE] = ModuleConfig(
            enabled=False,
            description="Multiple momentum indicators alignment",
            source="Trading-Warrior-Guide",
            parameters={
                "required_confluence": 3,  # Need 3 indicators aligned
                "indicators": ["RSI", "MACD", "Stochastic", "ADX"],
                "alignment_threshold": 0.7
            }
        )
        
        self.modules[StrategyModule.WARRIOR_MULTI_TIMEFRAME] = ModuleConfig(
            enabled=False,
            description="Multi-timeframe analysis for confirmation",
            source="Trading-Warrior-Guide",
            parameters={
                "timeframes": ["5min", "15min", "1hour"],
                "alignment_required": 2,  # 2 of 3 timeframes
                "higher_tf_weight": 1.5
            }
        )
        
        self.modules[StrategyModule.WARRIOR_SUPPLY_DEMAND] = ModuleConfig(
            enabled=False,
            description="Supply/Demand zone identification",
            source="Trading-Warrior-Guide",
            parameters={
                "zone_touches": 2,  # Min touches to confirm
                "zone_strength_threshold": 0.7,
                "use_volume_confirmation": True
            }
        )
        
        # ===== EHLERS DSP MODULES =====
        
        self.modules[StrategyModule.EHLERS_MARKET_MODE] = ModuleConfig(
            enabled=False,
            description="Detect Trend vs Cycle mode",
            source="Rocket Science for Traders",
            parameters={
                "trend_adx_threshold": 25,
                "use_sinewave_detection": True,
                "mode_persistence_bars": 3  # Avoid whipsaws
            }
        )
        
        self.modules[StrategyModule.EHLERS_SUPER_SMOOTHER] = ModuleConfig(
            enabled=False,
            description="Low-lag 2-pole Butterworth filter",
            source="Rocket Science for Traders",
            parameters={
                "cutoff_period": 10,
                "poles": 2,
                "use_for_all_smoothing": True
            }
        )
        
        self.modules[StrategyModule.EHLERS_SINEWAVE] = ModuleConfig(
            enabled=False,
            description="Leading cycle indicator with 45° advance",
            source="Rocket Science for Traders",
            parameters={
                "lead_degrees": 45,
                "min_amplitude": 0.5,
                "use_for_exits": True
            }
        )
        
        self.modules[StrategyModule.EHLERS_ADAPTIVE_INDICATORS] = ModuleConfig(
            enabled=False,
            description="Indicators that adapt to market cycle",
            source="Rocket Science for Traders",
            parameters={
                "adapt_rsi": True,
                "adapt_cci": True,
                "adapt_stochastic": True,
                "cycle_limits": (10, 48)
            }
        )
        
        # ===== RISK MANAGEMENT MODULES =====
        
        self.modules[StrategyModule.RISK_ATR_STOPS] = ModuleConfig(
            enabled=False,
            description="Dynamic stops based on ATR",
            source="Multiple sources",
            parameters={
                "atr_multiplier": 2.0,
                "atr_period": 14,
                "use_chandelier_exit": False
            }
        )
        
        self.modules[StrategyModule.RISK_MULTI_TARGET] = ModuleConfig(
            enabled=False,
            description="Multiple profit targets with partial exits",
            source="AI + Quant trading",
            parameters={
                "targets": [
                    (0.5, 1.5),  # 50% at 1.5R
                    (0.3, 3.0),  # 30% at 3R
                    (0.2, 5.0),  # 20% at 5R
                ],
                "move_to_breakeven_after": 1  # After target 1
            }
        )
    
    def enable_module(self, module: StrategyModule, parameters: Dict = None):
        """Enable a specific module with optional parameter override"""
        if module in self.modules:
            self.modules[module].enabled = True
            if parameters:
                self.modules[module].parameters.update(parameters)
            print(f"✅ Enabled: {module.value} - {self.modules[module].description}")
    
    def disable_module(self, module: StrategyModule):
        """Disable a specific module"""
        if module in self.modules:
            self.modules[module].enabled = False
            print(f"❌ Disabled: {module.value}")
    
    def get_enabled_modules(self) -> List[StrategyModule]:
        """Get list of currently enabled modules"""
        return [m for m, config in self.modules.items() if config.enabled]
    
    def create_preset(self, name: str) -> 'ModularTradingSystem':
        """Create preset configurations for common use cases"""
        
        system = ModularTradingSystem()
        
        if name == "baseline":
            # Only core ML
            pass  # Already enabled by default
            
        elif name == "ai_enhanced":
            # Core + AI Trading rules
            system.enable_module(StrategyModule.AI_PATTERN_QUALITY)
            system.enable_module(StrategyModule.AI_TIME_WINDOWS)
            system.enable_module(StrategyModule.AI_POSITION_SIZING)
            system.enable_module(StrategyModule.AI_DAILY_LIMITS)
            system.enable_module(StrategyModule.AI_STOCK_FILTERING)
            
        elif name == "quantitative":
            # Core + Quant methods
            system.enable_module(StrategyModule.QUANT_KELLY_CRITERION)
            system.enable_module(StrategyModule.QUANT_MOMENTUM)
            system.enable_module(StrategyModule.RISK_ATR_STOPS)
            system.enable_module(StrategyModule.RISK_MULTI_TARGET)
            
        elif name == "warrior":
            # Core + Trading Warrior
            system.enable_module(StrategyModule.WARRIOR_MOMENTUM_CONFLUENCE)
            system.enable_module(StrategyModule.WARRIOR_MULTI_TIMEFRAME)
            system.enable_module(StrategyModule.RISK_MULTI_TARGET)
            
        elif name == "ehlers_cycle":
            # Core + Ehlers DSP
            system.enable_module(StrategyModule.EHLERS_MARKET_MODE)
            system.enable_module(StrategyModule.EHLERS_SUPER_SMOOTHER)
            system.enable_module(StrategyModule.EHLERS_SINEWAVE)
            system.enable_module(StrategyModule.EHLERS_ADAPTIVE_INDICATORS)
            
        elif name == "kitchen_sink":
            # Everything enabled (for research only!)
            for module in StrategyModule:
                system.enable_module(module)
                
        elif name == "production":
            # Proven combination for live trading
            system.enable_module(StrategyModule.AI_PATTERN_QUALITY)
            system.enable_module(StrategyModule.AI_TIME_WINDOWS)
            system.enable_module(StrategyModule.RISK_ATR_STOPS)
            system.enable_module(StrategyModule.RISK_MULTI_TARGET)
            system.enable_module(StrategyModule.EHLERS_MARKET_MODE)
            
        return system
    
    def print_configuration(self):
        """Print current configuration in readable format"""
        print("\n" + "="*60)
        print("🔧 MODULAR TRADING SYSTEM CONFIGURATION")
        print("="*60)
        
        enabled_count = len(self.get_enabled_modules())
        total_count = len(self.modules)
        
        print(f"\n📊 Modules: {enabled_count}/{total_count} enabled\n")
        
        # Group by source
        by_source = {}
        for module, config in self.modules.items():
            source = config.source or "Unknown"
            if source not in by_source:
                by_source[source] = []
            by_source[source].append((module, config))
        
        for source, modules in by_source.items():
            print(f"\n📚 {source}:")
            for module, config in modules:
                status = "✅" if config.enabled else "⭕"
                print(f"   {status} {module.value}: {config.description}")
                
                if config.enabled and config.parameters:
                    # Show key parameters when enabled
                    for key, value in list(config.parameters.items())[:3]:
                        print(f"      • {key}: {value}")
    
    def export_config(self) -> Dict:
        """Export configuration as dictionary for saving/loading"""
        return {
            module.value: {
                "enabled": config.enabled,
                "weight": config.weight,
                "parameters": config.parameters
            }
            for module, config in self.modules.items()
        }
    
    def import_config(self, config_dict: Dict):
        """Import configuration from dictionary"""
        for module_str, settings in config_dict.items():
            try:
                module = StrategyModule(module_str)
                if module in self.modules:
                    self.modules[module].enabled = settings.get("enabled", False)
                    self.modules[module].weight = settings.get("weight", 1.0)
                    self.modules[module].parameters = settings.get("parameters", {})
            except ValueError:
                print(f"Warning: Unknown module {module_str}")


# ===== USAGE EXAMPLES =====

def demo_modular_system():
    """Demonstrate the modular system"""
    
    print("🚀 Modular Trading System Demo\n")
    
    # 1. Create baseline system
    print("1️⃣ Creating baseline system (ML only)...")
    baseline = ModularTradingSystem()
    baseline.print_configuration()
    
    # 2. Enable specific modules for testing
    print("\n2️⃣ Enabling specific modules for A/B testing...")
    baseline.enable_module(StrategyModule.AI_TIME_WINDOWS)
    baseline.enable_module(StrategyModule.EHLERS_MARKET_MODE)
    print(f"\nEnabled modules: {[m.value for m in baseline.get_enabled_modules()]}")
    
    # 3. Create preset configurations
    print("\n3️⃣ Creating AI-enhanced preset...")
    ai_system = ModularTradingSystem().create_preset("ai_enhanced")
    ai_system.print_configuration()
    
    # 4. Custom configuration
    print("\n4️⃣ Creating custom configuration...")
    custom = ModularTradingSystem()
    
    # Mix and match from different sources
    custom.enable_module(StrategyModule.AI_PATTERN_QUALITY)  # From AI
    custom.enable_module(StrategyModule.QUANT_KELLY_CRITERION)  # From Quant
    custom.enable_module(StrategyModule.EHLERS_SUPER_SMOOTHER)  # From Ehlers
    custom.enable_module(StrategyModule.RISK_MULTI_TARGET)  # Risk management
    
    print(f"\nCustom mix: {[m.value for m in custom.get_enabled_modules()]}")
    
    # 5. Export/Import configuration
    print("\n5️⃣ Exporting configuration...")
    config_export = custom.export_config()
    print(f"Exported {len([c for c in config_export.values() if c['enabled']])} enabled modules")


if __name__ == "__main__":
    demo_modular_system()