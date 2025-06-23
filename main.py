"""
Lorentzian Classification - Demo
Shows how to use the complete system
"""
import random
import math
from config.settings import TradingConfig
from scanner import BarProcessor


def generate_sample_data(num_bars: int) -> list:
    """Generate sample OHLCV data for testing"""
    bars = []
    base_price = 100.0

    for i in range(num_bars):
        # Create realistic price movement
        trend = math.sin(i * 0.1) * 10  # Long-term trend
        noise = random.uniform(-1, 1)    # Short-term noise

        close = base_price + trend + noise
        open_price = close - random.uniform(-0.5, 0.5)
        high = max(open_price, close) + random.uniform(0, 1)
        low = min(open_price, close) - random.uniform(0, 1)
        volume = random.uniform(900, 1100) * 1000

        bars.append((open_price, high, low, close, volume))

    return bars


def display_signal(bar_num: int, result):
    """Display trading signal in a user-friendly format"""
    if result.start_long_trade:
        print(f"\n{'=' * 50}")
        print(f"🟢 BUY SIGNAL - Bar #{bar_num}")
        print(f"{'=' * 50}")
        print(f"Price: {result.close:.2f}")
        print(f"Prediction: {result.prediction:.2f}")
        print(f"Strength: {result.prediction_strength:.2%}")
        print(f"Filters: {result.filter_states}")

    elif result.start_short_trade:
        print(f"\n{'=' * 50}")
        print(f"🔴 SELL SIGNAL - Bar #{bar_num}")
        print(f"{'=' * 50}")
        print(f"Price: {result.close:.2f}")
        print(f"Prediction: {result.prediction:.2f}")
        print(f"Strength: {result.prediction_strength:.2%}")
        print(f"Filters: {result.filter_states}")

    if result.end_long_trade:
        print(f"\n{'=' * 50}")
        print(f"⬜ EXIT LONG - Bar #{bar_num}")
        print(f"{'=' * 50}")
        print(f"Price: {result.close:.2f}")

    elif result.end_short_trade:
        print(f"\n{'=' * 50}")
        print(f"⬜ EXIT SHORT - Bar #{bar_num}")
        print(f"{'=' * 50}")
        print(f"Price: {result.close:.2f}")


def main():
    """Main demo function"""
    print("=== Lorentzian Classification Trading System ===")
    print("Pine Script → Python Conversion Complete!\n")

    # Initialize configuration
    config = TradingConfig(
        # ML Settings
        neighbors_count=8,
        max_bars_back=2000,
        feature_count=5,

        # Filters
        use_volatility_filter=True,
        use_regime_filter=True,
        use_adx_filter=False,

        # Kernel Settings
        use_kernel_filter=True,
        use_kernel_smoothing=False,

        # Trend Filters
        use_ema_filter=False,
        use_sma_filter=False,

        # Display
        show_exits=True
    )

    print("Configuration:")
    print(f"- Neighbors: {config.neighbors_count}")
    print(f"- Features: {config.feature_count}")
    print(f"- Max bars back: {config.max_bars_back}")
    print(f"- Filters: Volatility={config.use_volatility_filter}, "
          f"Regime={config.use_regime_filter}, "
          f"Kernel={config.use_kernel_filter}")
    print()

    # Generate sample data
    print("Generating sample data...")
    bars = generate_sample_data(500)
    
    # Create bar processor with total bars for Pine Script compatibility
    processor = BarProcessor(config, total_bars=len(bars))
    print(f"\nPine Script Compatibility:")
    print(f"- Total bars: {len(bars)}")
    print(f"- Max bars back index: {processor.max_bars_back_index}")
    print(f"- ML will start at bar: {processor.max_bars_back_index}")
    print()

    # Process bars
    print(f"Processing {len(bars)} bars...\n")

    signal_count = 0
    for i, (open_price, high, low, close, volume) in enumerate(bars):
        # Process bar
        result = processor.process_bar(open_price, high, low, close, volume)

        # Display progress every 100 bars
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1} bars...")

        # Display signals (after warmup period)
        if i >= 50:  # Skip initial warmup
            if (result.start_long_trade or result.start_short_trade or
                result.end_long_trade or result.end_short_trade):
                display_signal(i, result)
                signal_count += 1

    print(f"\n{'=' * 50}")
    print(f"Processing Complete!")
    print(f"Total bars processed: {len(bars)}")
    print(f"Total signals generated: {signal_count}")
    print(f"{'=' * 50}")

    # Display final statistics
    if processor.ml_model.predictions:
        avg_neighbors = len(processor.ml_model.predictions)
        print(f"\nML Statistics:")
        print(f"- Average neighbors used: {avg_neighbors}")
        print(f"- Last prediction: {processor.ml_model.prediction:.2f}")
        print(f"- Last signal: {processor.ml_model.signal}")


if __name__ == "__main__":
    main()