
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Any
from backtest_engine import Trade

def visualize_trades(data: pd.DataFrame, trades: List[Trade], save_path: str = "trade_visualizer.html"):
    """
    Visualize trades on a candlestick chart with SL/TP lines.
    
    Args:
        data: OHLCV DataFrame
        trades: List of Trade objects
        save_path: Path to save the HTML file
    """
    # Create Figure
    fig = go.Figure()

    # 1. Candlestick Chart
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name="Price"
        )
    )

    # 2. Add Trades
    # Separate Longs and Shorts for cleaner legend/coloring
    long_entries_x = []
    long_entries_y = []
    short_entries_x = []
    short_entries_y = []
    
    exits_x = []
    exits_y = []
    
    # Iterate through trades to add SL/TP lines and collect markers
    for trade in trades:
        # Markers
        if trade.side == 'LONG':
            long_entries_x.append(trade.entry_time)
            long_entries_y.append(trade.entry_price)
        else:
            short_entries_x.append(trade.entry_time)
            short_entries_y.append(trade.entry_price)
            
        if trade.exit_time:
            exits_x.append(trade.exit_time)
            exits_y.append(trade.exit_price)
            
        # SL/TP Lines
        # We draw a shape or line from entry time to exit time (or end of data)
        end_time = trade.exit_time if trade.exit_time else data.index[-1]
        
        # Stop Loss Line
        if trade.sl:
            fig.add_trace(
                go.Scatter(
                    x=[trade.entry_time, end_time],
                    y=[trade.sl, trade.sl],
                    mode="lines",
                    line=dict(color="red", width=1, dash="dash"),
                    showlegend=False,
                    hoverinfo="skip"
                )
            )
            
        # Take Profit Line
        if trade.tp:
            fig.add_trace(
                go.Scatter(
                    x=[trade.entry_time, end_time],
                    y=[trade.tp, trade.tp],
                    mode="lines",
                    line=dict(color="green", width=1, dash="dash"),
                    showlegend=False,
                    hoverinfo="skip"
                )
            )

    # Add Markers Traces
    if long_entries_x:
        fig.add_trace(
            go.Scatter(
                x=long_entries_x,
                y=long_entries_y,
                mode='markers',
                name='Long Entry',
                marker=dict(symbol='triangle-up', size=12, color='green', line=dict(width=1, color='black'))
            )
        )
        
    if short_entries_x:
        fig.add_trace(
            go.Scatter(
                x=short_entries_x,
                y=short_entries_y,
                mode='markers',
                name='Short Entry',
                marker=dict(symbol='triangle-down', size=12, color='red', line=dict(width=1, color='black'))
            )
        )

    if exits_x:
        fig.add_trace(
            go.Scatter(
                x=exits_x,
                y=exits_y,
                mode='markers',
                name='Exit',
                marker=dict(symbol='x', size=8, color='black', line=dict(width=1, color='white'))
            )
        )

    # Layout Updates
    fig.update_layout(
        title="Trade Visualizer",
        yaxis_title="Price",
        xaxis_title="Time",
        template="plotly_dark",
        height=800,
        xaxis_rangeslider_visible=False
    )
    
    # Save
    fig.write_html(save_path)
    print(f"Trade visualization saved to: {save_path}")
