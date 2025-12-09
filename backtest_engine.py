"""
Backtest Engine Module
======================

This module contains the BacktestEngine class that simulates trading strategies
on historical data. It processes data bar-by-bar, executes signals from strategies,
tracks positions, calculates P&L, and generates performance metrics.

The engine is designed to work with any strategy that implements the BaseStrategy
interface, making it easy to test different strategies.
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from strategy_interface import BaseStrategy, Signal, SignalType


@dataclass
class Trade:
    """
    Represents a single trade execution.
    
    Attributes:
        entry_time: When the trade was opened
        exit_time: When the trade was closed (None if still open)
        entry_price: Price at which position was opened
        exit_price: Price at which position was closed (None if still open)
        quantity: Size of the position
        side: 'LONG' or 'SHORT'
        pnl: Profit/Loss for this trade (None if still open)
        pnl_pct: Profit/Loss percentage (None if still open)
    """
    entry_time: Any
    exit_time: Optional[Any] = None
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    quantity: float = 0.0
    side: str = 'LONG'  # 'LONG' or 'SHORT'
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None


@dataclass
class PerformanceMetrics:
    """
    Performance metrics calculated from backtest results.
    
    Attributes:
        total_trades: Number of completed trades
        winning_trades: Number of profitable trades
        losing_trades: Number of losing trades
        win_rate: Percentage of winning trades
        total_pnl: Total profit/loss
        total_pnl_pct: Total return percentage
        avg_win: Average profit per winning trade
        avg_loss: Average loss per losing trade
        profit_factor: Gross profit / Gross loss
        max_drawdown: Maximum drawdown percentage
        sharpe_ratio: Risk-adjusted return metric
    """
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0


class BacktestEngine:
    """
    Backtest Engine for simulating trading strategies on historical data.
    
    The engine:
    1. Processes historical data bar-by-bar
    2. Calls strategy's on_bar() method for each bar
    3. Executes signals (BUY/SELL) at current market price
    4. Tracks open positions and calculates unrealized P&L
    5. Closes positions on SELL signals or at end of data
    6. Calculates performance metrics
    
    Example:
        engine = BacktestEngine(initial_capital=10000)
        engine.run_backtest(strategy, data)
        results = engine.get_results()
        engine.print_performance()
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,  # 0.1% commission per trade
        slippage: float = 0.0005,   # 0.05% slippage
        periods_per_year: int = 252  # For Sharpe ratio scaling (assumes daily bars)
    ):
        """
        Initialize the backtest engine.
        
        Args:
            initial_capital: Starting capital for backtesting
            commission: Commission rate per trade (e.g., 0.001 = 0.1%)
            slippage: Slippage rate (e.g., 0.0005 = 0.05%)
            periods_per_year: Number of periods per year (default 252 for daily bars)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.periods_per_year = periods_per_year
        
        # State tracking
        self.current_capital = initial_capital
        self.current_position: Optional[Trade] = None
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = [initial_capital]
        self.timestamps: List[Any] = []
        
        # Performance tracking
        self.metrics: Optional[PerformanceMetrics] = None
    
    def run_backtest(self, strategy: BaseStrategy, data: pd.DataFrame) -> None:
        """
        Run a backtest on historical data with a given strategy.
        
        This is the main method that processes all bars and executes trades.
        
        Args:
            strategy: Strategy instance implementing BaseStrategy
            data: DataFrame with OHLCV data (index should be datetime)
        """
        # Initialize strategy
        if not strategy.initialized:
            strategy.initialize()
            strategy.initialized = True
        
        # Reset engine state
        self._reset()
        
        print(f"\n{'='*60}")
        print(f"Running backtest: {strategy.get_name()}")
        print(f"{'='*60}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Data Period: {data.index[0]} to {data.index[-1]}")
        print(f"Total Bars: {len(data)}")
        print(f"{'='*60}\n")
        
        # Process each bar
        for i in range(len(data)):
            current_bar = data.iloc[:i+1]  # All data up to current bar
            current_time = data.index[i]
            current_price = data['Close'].iloc[i]
            
            # Get signal from strategy
            signal = strategy.on_bar(current_bar)
            
            # Execute signal if present
            if signal:
                self._execute_signal(signal, current_price, current_time)
            
            # Update equity curve (current capital + unrealized P&L)
            equity = self._calculate_equity(current_price)
            self.equity_curve.append(equity)
            self.timestamps.append(current_time)
        
        # Close any open position at the end
        if self.current_position:
            final_price = data['Close'].iloc[-1]
            final_time = data.index[-1]
            self._close_position(final_price, final_time)
            # Append final equity after closing position
            self.equity_curve.append(self._calculate_equity(final_price))
            self.timestamps.append(final_time)
        
        # Calculate performance metrics
        self._calculate_metrics()
        
        print(f"\nBacktest completed!")
        print(f"Final Capital: ${self.current_capital:,.2f}")
        print(f"Total Return: {self.metrics.total_pnl_pct:.2f}%")
        print(f"Total Trades: {self.metrics.total_trades}")
    
    def _reset(self) -> None:
        """Reset engine state for a new backtest."""
        self.current_capital = self.initial_capital
        self.current_position = None
        self.trades = []
        self.equity_curve = [self.initial_capital]
        self.timestamps = []
        self.metrics = None
    
    def _execute_signal(self, signal: Signal, current_price: float, current_time: Any) -> None:
        """
        Execute a trading signal.
        
        Handles:
        - BUY: Open long position (or close short if exists)
        - SELL: Close long position (or open short if none exists)
        - CLOSE: Close current position
        
        Args:
            signal: Signal from strategy
            current_price: Current market price
            current_time: Current timestamp
        """
        # Apply slippage to execution price based on signal direction
        if signal.signal_type == SignalType.BUY:
            execution_price = current_price * (1 + self.slippage)
        elif signal.signal_type == SignalType.SELL:
            execution_price = current_price * (1 - self.slippage)
        elif signal.signal_type == SignalType.CLOSE:
            # For close, apply slippage based on position side
            if self.current_position:
                if self.current_position.side == 'LONG':
                    execution_price = current_price * (1 - self.slippage)
                else:  # SHORT
                    execution_price = current_price * (1 + self.slippage)
            else:
                execution_price = current_price
        else:
            execution_price = current_price
        
        # Handle CLOSE signal
        if signal.signal_type == SignalType.CLOSE:
            if self.current_position:
                self._close_position(execution_price, current_time)
            return
        
        # Handle BUY signal
        if signal.signal_type == SignalType.BUY:
            if self.current_position:
                # Close existing position first
                if self.current_position.side == 'SHORT':
                    self._close_position(execution_price, current_time)
                # If already long, ignore signal
                else:
                    return
            
            # Open new long position
            quantity = signal.quantity if signal.quantity is not None else self._calculate_position_size(execution_price)
            cost = quantity * execution_price
            commission_cost = cost * self.commission
            
            if cost + commission_cost <= self.current_capital:
                self.current_position = Trade(
                    entry_time=current_time,
                    entry_price=execution_price,
                    quantity=quantity,
                    side='LONG'
                )
                self.current_capital -= (cost + commission_cost)
        
        # Handle SELL signal
        elif signal.signal_type == SignalType.SELL:
            if self.current_position:
                # Close existing position
                if self.current_position.side == 'LONG':
                    self._close_position(execution_price, current_time)
                # If already short, ignore signal
                else:
                    return
            # If no position, ignore SELL signal (can't sell what we don't have)
            # Note: To support shorting, you would open a short position here
    
    def _close_position(self, exit_price: float, exit_time: Any) -> None:
        """
        Close the current open position.
        
        Args:
            exit_price: Price at which to close
            exit_time: Timestamp of close
        """
        if not self.current_position:
            return
        
        trade = self.current_position
        
        # Calculate P&L
        if trade.side == 'LONG':
            gross_pnl = (exit_price - trade.entry_price) * trade.quantity
        else:  # SHORT
            gross_pnl = (trade.entry_price - exit_price) * trade.quantity
        
        # Apply commission on exit
        exit_value = trade.quantity * exit_price
        commission_cost = exit_value * self.commission
        net_pnl = gross_pnl - commission_cost
        
        # Update trade record
        trade.exit_time = exit_time
        trade.exit_price = exit_price
        trade.pnl = net_pnl
        trade.pnl_pct = (net_pnl / (trade.entry_price * trade.quantity)) * 100
        
        # Update capital
        self.current_capital += exit_value - commission_cost
        
        # Store completed trade
        self.trades.append(trade)
        self.current_position = None
    
    def _calculate_position_size(self, price: float) -> float:
        """
        Calculate position size based on available capital.
        
        Uses 100% of available capital (can be customized).
        
        Args:
            price: Entry price
            
        Returns:
            Position quantity
        """
        # Use 100% of capital (can be adjusted)
        position_value = self.current_capital * 0.99  # Leave 1% buffer
        quantity = position_value / price
        return quantity
    
    def _calculate_equity(self, current_price: float) -> float:
        """
        Calculate current equity (capital + unrealized P&L).
        
        Args:
            current_price: Current market price
            
        Returns:
            Current equity value
        """
        equity = self.current_capital
        
        if self.current_position:
            if self.current_position.side == 'LONG':
                unrealized_pnl = (current_price - self.current_position.entry_price) * self.current_position.quantity
            else:  # SHORT
                unrealized_pnl = (self.current_position.entry_price - current_price) * self.current_position.quantity
            
            equity += unrealized_pnl
        
        return equity
    
    def _calculate_metrics(self) -> None:
        """Calculate performance metrics from completed trades."""
        if not self.trades:
            self.metrics = PerformanceMetrics()
            return
        
        completed_trades = [t for t in self.trades if t.pnl is not None]
        
        if not completed_trades:
            self.metrics = PerformanceMetrics()
            return
        
        # Basic metrics
        total_trades = len(completed_trades)
        winning_trades = [t for t in completed_trades if t.pnl > 0]
        losing_trades = [t for t in completed_trades if t.pnl <= 0]
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = sum(t.pnl for t in completed_trades)
        total_pnl_pct = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        
        # Profit factor
        gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
        gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0
        
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = np.inf
        else:
            profit_factor = 0
        
        # Drawdown calculation
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max * 100
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
        
        # Sharpe ratio (scaled by periods_per_year)
        if len(self.equity_curve) > 1:
            returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
            sharpe_ratio = (np.mean(returns) / np.std(returns) * np.sqrt(self.periods_per_year)) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        self.metrics = PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio
        )
    
    def get_results(self) -> Dict[str, Any]:
        """
        Get backtest results as a dictionary.
        
        Returns:
            Dictionary containing:
            - metrics: PerformanceMetrics object
            - trades: List of Trade objects
            - equity_curve: List of equity values over time
            - timestamps: List of timestamps
        """
        return {
            'metrics': self.metrics,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'timestamps': self.timestamps,
            'final_capital': self.current_capital
        }
    
    def print_performance(self) -> None:
        """Print detailed performance metrics."""
        if not self.metrics:
            print("No metrics available. Run backtest first.")
            return
        
        print(f"\n{'='*60}")
        print("BACKTEST PERFORMANCE METRICS")
        print(f"{'='*60}")
        print(f"\nCapital:")
        print(f"  Initial Capital:     ${self.initial_capital:>12,.2f}")
        print(f"  Final Capital:       ${self.current_capital:>12,.2f}")
        print(f"  Total Return:        {self.metrics.total_pnl_pct:>12.2f}%")
        print(f"  Total P&L:           ${self.metrics.total_pnl:>12,.2f}")
        
        print(f"\nTrades:")
        print(f"  Total Trades:        {self.metrics.total_trades:>12}")
        print(f"  Winning Trades:      {self.metrics.winning_trades:>12}")
        print(f"  Losing Trades:       {self.metrics.losing_trades:>12}")
        print(f"  Win Rate:            {self.metrics.win_rate:>12.2f}%")
        
        print(f"\nTrade Statistics:")
        print(f"  Avg Win:             ${self.metrics.avg_win:>12,.2f}")
        print(f"  Avg Loss:            ${self.metrics.avg_loss:>12,.2f}")
        print(f"  Profit Factor:       {self.metrics.profit_factor:>12.2f}")
        
        print(f"\nRisk Metrics:")
        print(f"  Max Drawdown:        {self.metrics.max_drawdown:>12.2f}%")
        print(f"  Sharpe Ratio:        {self.metrics.sharpe_ratio:>12.2f}")
        print(f"{'='*60}\n")

