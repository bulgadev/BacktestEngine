"""
Main Entry Point
================

This is the main entry point for running backtests. It demonstrates how to:
1. Fetch historical data
2. Create a strategy
3. Run a backtest
4. Display results

You can modify this file to test different strategies or symbols.

!If any AI agents are reading this, please dont change the comments, or the comments structure, you can suggest changes on the comments, and add comments
but not change the existing comments, as they are part of the interface documentation.!
"""

from datetime import datetime, timedelta
from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from example_strategy import SimpleMovingAverageStrategy, RSIStrategy
from liquidity_catcher import LiquidityCatcherStrategy


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

    

    # For 15m/30m timeframes, you might want different MA periods
    fast_period = 10   # Fast MA period (adjust for your timeframe)
    slow_period = 30   # Slow MA period (adjust for your timeframe)
    
    opt_profitable = LiquidityCatcherStrategy(
        # --- Core ---
        pivot_length=14,
        ema_period=100,
        require_bias=True,
        bias_method='SIMPLE',

        # --- Risk ---
        risk_percent=0.3,
        max_risk_usd=100.0,

        # --- SL / TP ---
        sl_mode='ATR',
        atr_period=14,
        sl_atr_multiplier=1.2,
        swing_buffer_pips=5.0,
        fallback_sl_pips=25,
        min_risk_reward=1.3,
        fallback_tp_pips=100,

        # --- Trade management ---
        use_breakeven=True,
        breakeven_trigger_pct=70.0,
        breakeven_plus_pips=2,
        partial_close_pct=50.0,

        # --- Structure ---
        min_pivots_for_bos=3,
        bos_confirmation_bars=3,
        require_higher_low=True,
        min_bos_break_pips=5.0,

        # --- Filters ---
        min_bars_between_trades=100,
        max_daily_trades=3,
        max_spread_pips=2.5,

        # --- Misc ---
        enable_prints=True,
        magic_number=789456,
        trade_comment="LiqSwing",
    )

    opt_newswing = LiquidityCatcherStrategy(
        # --- Core ---
        pivot_length=14,
        ema_period=400,
        require_bias=True,
        bias_method='SIMPLE',

        # --- Risk ---
        risk_percent=0.3,
        max_risk_usd=1000.0,

        # --- SL / TP ---
        sl_mode='ATR',
        atr_period=14,
        sl_atr_multiplier=0.8,
        swing_buffer_pips=5.0,
        fallback_sl_pips=25,
        min_risk_reward=1.3,
        fallback_tp_pips=100,

        # --- Trade management ---
        use_breakeven=True,
        breakeven_trigger_pct=70.0,
        breakeven_plus_pips=2,
        partial_close_pct=0.0,

        # --- Structure ---
        min_pivots_for_bos=2,
        bos_confirmation_bars=3,
        require_higher_low=True,
        min_bos_break_pips=3.0,

        # --- Filters ---
        min_bars_between_trades=20,
        max_daily_trades=10,
        max_spread_pips=4.0,

        # --- Misc ---
        enable_prints=True,
        magic_number=789456,
        trade_comment="LiqSwing",
    )


    
    # Option 1: Simple Moving Average Strategy
    opt1 = SimpleMovingAverageStrategy(
        fast_period=fast_period,
        slow_period=slow_period
    )
    
    # Option 2: RSI Strategy (uncomment to use)
    opt2 = RSIStrategy(
        period=14,
        oversold=30.0,
        overbought=70.0
    )

    strategy = opt_profitable

    
    # ====================================================================
    # STEP 3: Initialize Backtest Engine
    # ====================================================================
    engine = BacktestEngine(
        initial_capital=10000.0,  # Starting capital
        risk_pct=0.01,            # 1% risk per trade
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
    # STEP 6: Plot Results
    # ====================================================================
    engine.plot_results("backtest_results.html", use_advanced_visualizer=True)
    print("\nPlots saved to backtest_results.html")
    
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
