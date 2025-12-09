"""
Main Entry Point
================

This is the main entry point for running backtests. It demonstrates how to:
1. Fetch historical data
2. Create a strategy
3. Run a backtest
4. Display results

You can modify this file to test different strategies or symbols.
"""

from datetime import datetime, timedelta
from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from example_strategy import SimpleMovingAverageStrategy, RSIStrategy


def main():
    """
    Main function to run a backtest example.
    
    This demonstrates the complete workflow:
    1. Fetch historical data (adjustable timeframe: 15m, 30m, 1h, 1d, etc.)
    2. Create a moving average strategy
    3. Run backtest with $10,000 initial capital
    4. Print performance metrics
    
    Note: Adjust the timeframe and lookback_days variables at the top of this function
    to change the data granularity and period.
    """
    print("=" * 60)
    print("TRADING STRATEGY BACKTEST ENGINE")
    print("=" * 60)
    
    # ====================================================================
    # STEP 1: Fetch Historical Data
    # ====================================================================
    # Configuration: Adjust these parameters as needed
    symbol = 'BTC'           # Choose symbol: 'BTC' or 'EURUSD'
    timeframe = '15m'        # Timeframe: '1m', '5m', '15m', '30m', '1h', '1d', etc.
    lookback_days = 365      # Number of days to fetch (1 year = 365 days)
    
    # Fetch historical data
    # For intraday data (15m, 30m, etc.), we use date range with automatic chunking
    # For daily/weekly data, we can use period method
    if timeframe in ['1m', '5m', '15m', '30m', '1h']:
        # Use date range for intraday data (automatically chunks to handle yfinance limits)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        data = DataFetcher.fetch_data_by_dates(
            symbol=symbol,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            interval=timeframe
        )
    else:
        # Use period for daily/weekly data
        data = DataFetcher.fetch_data(
            symbol=symbol,
            period='1y',      # 1 year of data
            interval=timeframe
        )
    
    # ====================================================================
    # STEP 2: Create Strategy
    # ====================================================================
    # Strategy parameters - adjust based on your timeframe
    #the final strategy is chosen on the first strategy var, just put the choosen option from the ones you made
    #Structure a new strat using coments and a function, and then call it on strategy

    strategy = opt1

    # For 15m/30m timeframes, you might want different MA periods
    fast_period = 10   # Fast MA period (adjust for your timeframe)
    slow_period = 30   # Slow MA period (adjust for your timeframe)
    
    # Option 1: Simple Moving Average Strategy
    opt1 = SimpleMovingAverageStrategy(
        fast_period=fast_period,
        slow_period=slow_period
    )
    
    # Option 2: RSI Strategy (uncomment to use)
    # strategy = RSIStrategy(
    #     period=14,
    #     oversold=30.0,
    #     overbought=70.0
    # )
    
    # ====================================================================
    # STEP 3: Initialize Backtest Engine
    # ====================================================================
    engine = BacktestEngine(
        initial_capital=10000.0,  # Starting capital
        commission=0.001,         # 0.1% commission per trade
        slippage=0.0005           # 0.05% slippage
    )
    
    # ====================================================================
    # STEP 4: Run Backtest
    # ====================================================================
    engine.run_backtest(strategy, data)
    
    # ====================================================================
    # STEP 5: Display Results
    # ====================================================================
    engine.print_performance()
    
    # ====================================================================
    # Optional: Access detailed results
    # ====================================================================
    results = engine.get_results()
    
    # Example: Print first few trades
    if results['trades']:
        print("\nFirst 5 Trades:")
        print("-" * 80)
        for i, trade in enumerate(results['trades'][:5]):
            print(f"Trade {i+1}:")
            print(f"  Entry: {trade.entry_time} @ ${trade.entry_price:.2f}")
            print(f"  Exit:  {trade.exit_time} @ ${trade.exit_price:.2f}")
            print(f"  P&L:   ${trade.pnl:.2f} ({trade.pnl_pct:.2f}%)")
            print()


if __name__ == "__main__":
    main()
