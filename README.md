# Trading Strategy Backtest Engine

A robust and well-documented backtesting engine for trading strategies on BTC and EURUSD historical data. The engine is designed with a clean architecture that allows strategies to work with both backtesting and future live trading implementations.

## Features

- **Strategy Interface**: Clean abstract base class for implementing trading strategies
- **Historical Data**: Fetch 1 year of BTC or EURUSD data automatically
- **Backtest Engine**: Complete simulation with position tracking, P&L calculation, and performance metrics
- **Performance Metrics**: Win rate, profit factor, Sharpe ratio, max drawdown, and more
- **Well Documented**: Extensive comments and documentation for easy understanding
- **Extensible**: Easy to add new strategies or extend functionality

## Architecture

The engine is organized into several modules:

### Core Modules

1. **`strategy_interface.py`**: Defines the `BaseStrategy` abstract class that all strategies must implement
2. **`data_fetcher.py`**: Handles fetching historical market data (BTC/EURUSD)
3. **`backtest_engine.py`**: The main backtesting engine that simulates trading
4. **`example_strategy.py`**: Example strategies demonstrating the interface

### Design Philosophy

The strategy interface is designed so that:
- Strategies generate signals in a consistent format
- The same strategy can work with both backtest and live engines
- Strategies are decoupled from execution logic
- Easy to test and iterate on strategies

## Installation

1. Install dependencies:
```bash
pip install -e .
```

Or manually:
```bash
pip install pandas numpy yfinance
```

## Quick Start

### Running a Backtest

```python
from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from example_strategy import SimpleMovingAverageStrategy

# Fetch data
data = DataFetcher.fetch_data('BTC', period='1y', interval='1d')

# Create strategy
strategy = SimpleMovingAverageStrategy(fast_period=10, slow_period=30)

# Run backtest
engine = BacktestEngine(initial_capital=10000.0)
engine.run_backtest(strategy, data)
engine.print_performance()
```

Or simply run:
```bash
python main.py
```

## Creating Your Own Strategy

To create a custom strategy, inherit from `BaseStrategy` and implement the required methods:

```python
from strategy_interface import BaseStrategy, Signal, SignalType
import pandas as pd

class MyStrategy(BaseStrategy):
    def initialize(self, **kwargs):
        # Set up your strategy parameters
        self.lookback = kwargs.get('lookback', 20)
    
    def on_bar(self, data):
        # Process each bar and generate signals
        # data is a DataFrame with OHLCV data up to current bar
        
        if len(data) < self.lookback:
            return None
        
        # Your strategy logic here
        current_price = data['Close'].iloc[-1]
        current_time = data.index[-1]
        
        # Example: Generate BUY signal
        if your_buy_condition:
            return Signal(
                signal_type=SignalType.BUY,
                timestamp=current_time,
                price=current_price
            )
        
        return None
    
    def get_name(self):
        return "My Custom Strategy"
```

### Signal Types

- `SignalType.BUY`: Open a long position
- `SignalType.SELL`: Close current long position
- `SignalType.CLOSE`: Close any open position
- `SignalType.HOLD`: No action (or return None)

## Example Strategies

### Simple Moving Average Strategy

Uses two moving averages (fast and slow) and generates signals on crossovers:
- Fast MA crosses above slow MA → BUY
- Fast MA crosses below slow MA → SELL

### RSI Strategy

Uses Relative Strength Index for mean-reversion:
- RSI < 30 (oversold) → BUY
- RSI > 70 (overbought) → SELL

## Performance Metrics

The engine calculates comprehensive performance metrics:

- **Total Trades**: Number of completed trades
- **Win Rate**: Percentage of profitable trades
- **Total Return**: Overall return percentage
- **Profit Factor**: Gross profit / Gross loss
- **Average Win/Loss**: Average profit/loss per trade
- **Max Drawdown**: Maximum peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted return metric

## Configuration

### Backtest Engine Parameters

```python
engine = BacktestEngine(
    initial_capital=10000.0,  # Starting capital
    commission=0.001,         # 0.1% commission per trade
    slippage=0.0005           # 0.05% slippage
)
```

### Data Fetching

```python
# Fetch 1 year of daily data
data = DataFetcher.fetch_data('BTC', period='1y', interval='1d')

# Fetch specific date range
data = DataFetcher.fetch_data_by_dates(
    'EURUSD',
    start_date='2023-01-01',
    end_date='2024-01-01',
    interval='1d'
)
```

## Project Structure

```
BackEngine/
├── main.py                 # Main entry point with example
├── strategy_interface.py   # BaseStrategy abstract class
├── data_fetcher.py         # Historical data fetching
├── backtest_engine.py      # Backtest simulation engine
├── example_strategy.py     # Example strategies
├── pyproject.toml          # Project dependencies
└── README.md              # This file
```

## Future: Live Trading Engine

The architecture is designed so that when you implement a live trading engine, strategies can work with both:

```python
# Same strategy works with both
strategy = MyStrategy()

# Backtest
backtest_engine.run_backtest(strategy, historical_data)

# Live (future implementation)
live_engine.run(strategy, real_time_data)
```

The strategy interface ensures signals are generated consistently regardless of the execution engine.

## Notes

- The engine uses 100% of available capital per trade (can be customized)
- Commission and slippage are applied to all trades
- Positions are closed automatically at the end of the backtest
- All prices use the Close price of each bar

## Troubleshooting

**No data retrieved**: Check your internet connection and verify the symbol is supported (BTC or EURUSD).

**Strategy not generating signals**: Ensure your strategy has enough historical data (check `len(data)` in `on_bar`).

**Performance issues**: For large datasets, consider using hourly or daily intervals instead of minute data.

## License

This project is for educational and personal use.

# BacktestEngine
# BacktestEngine
# BacktestEngine
# BacktestEngine
