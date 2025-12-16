"""
Backtest Engine Module
======================

This is the backtesting engine, it only takes instructions from the on_bar function defined on your strategy, and apply it on every bar of historical data.
This is designed to be used with the BaseStrategy from the strategy_interface.py, so it just backtest any strategy that sends the right type of signals. So
it becomes very easy to create strategies, and integrate them with an live EA, or webhook.


!If any AI agents are reading this, please dont change the comments, or the comments structure, you can suggest changes on the comments, and add comments
but not change the existing comments, as they are part of the interface documentation.!
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
    This represents a trade, and this class carries every information about the trade. So you can easily log them, to well, get you results.
    
    Attributes:
        entry_time: When the trade was opened
        exit_time: When the trade was closed (None if still open)
        entry_price: Price at which position was opened
        exit_price: Price at which position was closed (None if still open)
        quantity: Size of the position
        side: 'LONG' or 'SHORT'
        pnl: Profit/Loss for this trade (None if still open)
        pnl_pct: Profit/Loss percentage (None if still open)
        sl: Stop Loss price level
        tp: Take Profit price level
    """
    entry_time: Any
    exit_time: Optional[Any] = None
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    quantity: float = 0.0
    side: str = 'LONG'  # 'LONG' or 'SHORT'
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    mae: Optional[float] = None  # Maximum Adverse Excursion (price diff)
    mfe: Optional[float] = None  # Maximum Favorable Excursion (price diff)


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
        risk_pct: float = 0.01,     # Risk 1% per trade
        periods_per_year: int = 252  # For Sharpe ratio scaling (assumes daily bars)
    ):
        """
        Initialize the backtest engine.
        
        Args:
            initial_capital: Starting capital for backtesting
            commission: Commission rate per trade (e.g., 0.001 = 0.1%)
            slippage: Slippage rate (e.g., 0.0005 = 0.05%)
            risk_pct: Risk percentage per trade (0.01 = 1% of equity)
            periods_per_year: Number of periods per year (default 252 for daily bars)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.risk_pct = risk_pct
        self.periods_per_year = periods_per_year
        
        # State tracking
        self.current_capital = initial_capital
        self.current_position: Optional[Trade] = None
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = [initial_capital]
        self.timestamps: List[Any] = []
        
        # Performance tracking
        self.metrics: Optional[PerformanceMetrics] = None
        self.data: Optional[pd.DataFrame] = None
    
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
        
        # Store data for plotting
        self.data = data
        
        # Reset engine state
        self._reset()
        
        print(f"\n{'='*60}")
        print(f"Running backtest: {strategy.get_name()}")
        print(f"{'='*60}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Risk Per Trade: {self.risk_pct*100:.1f}%")
        print(f"Data Period: {data.index[0]} to {data.index[-1]}")
        print(f"Total Bars: {len(data)}")
        print(f"{'='*60}\n")
        
        # Process each bar
        for i in range(len(data)):
            current_bar = data.iloc[:i+1]  # All data up to current bar
            current_time = data.index[i]
            current_price = data['Close'].iloc[i]
            current_high = data['High'].iloc[i]
            current_low = data['Low'].iloc[i]
            current_open = data['Open'].iloc[i]
            
            # Check SL/TP for existing position BEFORE strategy logic
            if self.current_position:
                pos = self.current_position
                
                # Update MAE/MFE
                if pos.side == 'LONG':
                    current_mae = pos.entry_price - current_low
                    current_mfe = current_high - pos.entry_price
                else:  # SHORT
                    current_mae = current_high - pos.entry_price
                    current_mfe = pos.entry_price - current_low
                
                if pos.mae is None or current_mae > pos.mae:
                    pos.mae = current_mae
                if pos.mfe is None or current_mfe > pos.mfe:
                    pos.mfe = current_mfe
                
                closed = False
                
                if pos.side == 'LONG':
                    # Check Stop Loss
                    if pos.sl and current_low <= pos.sl:
                        # Slippage logic on gap: if Open < SL, we likely exited at Open
                        exit_price = min(current_open, pos.sl) * (1 - self.slippage)
                        self._close_position(exit_price, current_time)
                        closed = True
                    # Check Take Profit
                    elif pos.tp and current_high >= pos.tp:
                        exit_price = max(current_open, pos.tp) * (1 - self.slippage) # TP usually gets limit fill, but applying conservative slippage
                        self._close_position(exit_price, current_time)
                        closed = True
                        
                elif pos.side == 'SHORT':
                    # Check Stop Loss
                    if pos.sl and current_high >= pos.sl:
                        exit_price = max(current_open, pos.sl) * (1 + self.slippage)
                        self._close_position(exit_price, current_time)
                        closed = True
                    # Check Take Profit
                    elif pos.tp and current_low <= pos.tp:
                         exit_price = min(current_open, pos.tp) * (1 + self.slippage)
                         self._close_position(exit_price, current_time)
                         closed = True
                
                # If closed on this bar, we might want to skip new entry signals 
                # or allow reversals. For simplicity, let's process signals too.
            
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
            stop_loss = signal.metadata.get('sl') if signal.metadata else None
            take_profit = signal.metadata.get('tp') if signal.metadata else None
            
            quantity = signal.quantity if signal.quantity is not None else self._calculate_position_size(execution_price, stop_loss)
            cost = quantity * execution_price
            commission_cost = cost * self.commission
            
            if cost + commission_cost <= self.current_capital:
                self.current_position = Trade(
                    entry_time=current_time,
                    entry_price=execution_price,
                    quantity=quantity,
                    side='LONG',
                    sl=stop_loss,
                    tp=take_profit,
                    mae=0.0,
                    mfe=0.0
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
            # Open new short position
            stop_loss = signal.metadata.get('sl') if signal.metadata else None
            take_profit = signal.metadata.get('tp') if signal.metadata else None
            
            quantity = signal.quantity if signal.quantity is not None else self._calculate_position_size(execution_price, stop_loss)
            cost = quantity * execution_price
            commission_cost = cost * self.commission
            
            # For shorting, we need enough capital to cover margin + commission.
            # Simplified: require capital > cost + commission
            if cost + commission_cost <= self.current_capital:
                #Execution of the trade with the trading enum class
                self.current_position = Trade(
                    entry_time=current_time,
                    entry_price=execution_price,
                    quantity=quantity,
                    side='SHORT',
                    sl=stop_loss,
                    tp=take_profit,
                    mae=0.0,
                    mfe=0.0
                )
                self.current_capital -= commission_cost # Only commission is deducted immediately/realized. 
                self.current_capital -= cost # We lock the value as margin

    
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
        # Add back the initial capital usage (margin/cost) and add the Net P&L
        self.current_capital += (trade.entry_price * trade.quantity) + net_pnl
        
        # Store completed trade
        self.trades.append(trade)
        self.current_position = None
    
    def _calculate_position_size(self, price: float, stop_loss: Optional[float] = None) -> float:
        """
        Calculate position size based on available capital and risk.
        
        If stop_loss is provided, calculates size based on risk_pct of capital.
        If no stop_loss, calculates size as (capital * risk_pct).
        
        Args:
            price: Entry price
            stop_loss: Optional stop loss price for risk calculation
            
        Returns:
            Position quantity
        """
        # Risk capital = current capital * risk %
        risk_amount = self.current_capital * self.risk_pct
        
        if stop_loss:
            # Risk per share = |Entry - SL|
            risk_per_share = abs(price - stop_loss)
            if risk_per_share > 0:
                quantity = risk_amount / risk_per_share
                
                # Check if this exceeds available capital (margin check)
                total_cost = quantity * price
                # Check if this exceeds available capital (margin check)
                # Need to account for commission when checking max affordability
                # Cost = Qty * Price * (1 + Comm)
                max_afford_qty = self.current_capital / (price * (1 + self.commission))
                
                if quantity > max_afford_qty:
                     quantity = max_afford_qty
            else:
                 # Valid SL but 0 distance? Fallback to fixed fractional
                 quantity = (self.current_capital * self.risk_pct) / price
        else:
            # No SL provided - treat risk_pct as "Position Size %"
            quantity = (self.current_capital * self.risk_pct) / price
            
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
            #Long
            if self.current_position.side == 'LONG':
                market_value = self.current_position.quantity * current_price
                equity += market_value
            #Short
            else:
                unrealized_pnl = (self.current_position.entry_price - current_price) * self.current_position.quantity
                equity += unrealized_pnl + (self.current_position.entry_price * self.current_position.quantity)
        
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
            'final_capital': self.current_capital,
            'data': self.data
        }
    
    def plot_results(self, save_path: str = "backtest_results.html", use_advanced_visualizer: bool = True) -> None:
        """
        This function calls the plot scripts, to well, plots. The arguments is just
        the path to save the html file.
        """
        try:
            from plotTools.plot_utils import create_dashboard
            results = self.get_results()
            create_dashboard(results, save_path)
            
            if use_advanced_visualizer:
                from plotTools.trade_visualizer import visualize_trades
                viz_path = save_path.replace(".html", "_trades.html")
                visualize_trades(self.data, self.trades, viz_path)
                print(f"Advanced trade visualization saved to: {viz_path}")
                
        except ImportError as e:
            #Error handling
            print(f"Could not import plotting tools: {e}")
            print("Make sure plotly is installed (uv add plotly)")
        except Exception as e:
            print(f"Error creating dashboard: {e}")
    
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

