
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import os

def create_dashboard(results: Dict[str, Any], save_path: str = "backtest_dashboard.html"):
    """
    Create a comprehensive backtest dashboard with multiple scrollable plots.
    
    Args:
        results: Dictionary containing backtest results (trades, equity_curve, metrics, etc.)
        save_path: Path to save the interactive HTML dashboard
    """
    trades = results.get('trades', [])
    equity_curve = results.get('equity_curve', [])
    timestamps = results.get('timestamps', [])
    
    # Filter completed trades
    completed_trades = [t for t in trades if t.pnl is not None]
    
    if not completed_trades:
        print("No completed trades to plot.")
        return

    # Prepare Data
    
    # 1. Equity & Drawdown
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max * 100
    
    # 2. Trade PnL
    pnls = [t.pnl for t in completed_trades]
    pnl_colors = ['#2ecc71' if p > 0 else '#e74c3c' for p in pnls]
    trade_indices = list(range(1, len(completed_trades) + 1))
    
    # 3. Cumulative PnL (Simple Sum)
    cum_pnl = np.cumsum(pnls)
    
    # 4. R-Multiple
    r_multiples = []
    for t in completed_trades:
        # Calculate Risk Amount
        risk_amount = 0.0
        if t.sl is not None:
             risk_amount = abs(t.entry_price - t.sl) * t.quantity
        
        # Avoid division by zero
        if risk_amount > 0:
            r = t.pnl / risk_amount
        else:
            # Fallback: if no SL, we can't calculate R accurately.
            # Using 0 or maybe PnL/Capital? No, R is PnL/Risk.
            r = 0.0 
        
        r_multiples.append(r)

    # 5. Win/Loss Distribution
    # (pnls list is already prepared)
    
    # 6. MAE vs MFE
    # Engine tracks MAE/MFE as price distance (positive values)
    maes = []
    mfes = []
    mae_mfe_colors = []
    mae_mfe_text = [] # Hover text
    
    for i, t in enumerate(completed_trades):
        # Default to 0 if None
        mae = t.mae if t.mae is not None else 0.0
        mfe = t.mfe if t.mfe is not None else 0.0
        
        # Convert to percentage? User asked for "scatter".
        # Price distance is fine, but % might be more comparable across different price levels.
        # Let's stick to price distance or maybe % of Entry.
        # Given "MAE vs MFE scatter", raw values or % are both valid. 
        # But if asset price changes significantly, % is better.
        # However, to be safe and simple, let's use % Entry.
        
        mae_pct = (mae / t.entry_price) * 100 if t.entry_price else 0
        mfe_pct = (mfe / t.entry_price) * 100 if t.entry_price else 0
        
        maes.append(mae_pct)
        mfes.append(mfe_pct)
        
        color = '#2ecc71' if t.pnl > 0 else '#e74c3c'
        mae_mfe_colors.append(color)
        mae_mfe_text.append(f"Trade #{i+1}<br>PnL: ${t.pnl:.2f}<br>MAE: {mae_pct:.2f}%<br>MFE: {mfe_pct:.2f}%")

    # Create Subplots
    # Vertical layout to make it "scrollable"
    fig = make_subplots(
        rows=7, cols=1,
        subplot_titles=(
            "Equity Curve (Balance over time)", 
            "Drawdown Curve (%)", 
            "Trade PnL per Trade", 
            "Cumulative PnL (No compounding)",
            "R-Multiple Distribution",
            "Win / Loss Distribution",
            "MAE vs MFE Scatter (One dot per trade)"
        ),
        vertical_spacing=0.06,
        specs=[[{"type": "scatter"}],
               [{"type": "scatter"}],
               [{"type": "bar"}],
               [{"type": "scatter"}],
               [{"type": "histogram"}],
               [{"type": "histogram"}],
               [{"type": "scatter"}]]
    )
    
    # 1. Equity Curve
    fig.add_trace(
        go.Scatter(x=timestamps, y=equity_curve, name="Equity", line=dict(color='#3498db', width=2)),
        row=1, col=1
    )
    
    # 2. Drawdown
    fig.add_trace(
        go.Scatter(x=timestamps, y=drawdown, name="Drawdown", fill='tozeroy', line=dict(color='#e74c3c', width=1)),
        row=2, col=1
    )
    
    # 3. Trade PnL
    fig.add_trace(
        go.Bar(x=trade_indices, y=pnls, name="Trade PnL", marker_color=pnl_colors),
        row=3, col=1
    )
    
    # 4. Cumulative PnL
    fig.add_trace(
        go.Scatter(x=trade_indices, y=cum_pnl, name="Cumulative PnL", line=dict(color='#f1c40f', width=2)),
        row=4, col=1
    )
    
    # 5. R-Multiple Dist
    fig.add_trace(
        go.Histogram(x=r_multiples, name="R-Multiple", nbinsx=30, marker_color='#9b59b6'),
        row=5, col=1
    )
    
    # 6. Win/Loss Dist
    fig.add_trace(
        go.Histogram(x=pnls, name="Win/Loss", nbinsx=30, marker_color='#34495e'),
        row=6, col=1
    )
    
    # 7. MAE vs MFE
    fig.add_trace(
        go.Scatter(
            x=mfes, 
            y=maes, 
            mode='markers', 
            name="MAE/MFE",
            marker=dict(color=mae_mfe_colors, size=8, opacity=0.7),
            text=mae_mfe_text,
            hovertemplate="%{text}"
        ),
        row=7, col=1
    )
    
    # Update Axes for Scatter
    fig.update_xaxes(title_text="MFE (%)", row=7, col=1)
    fig.update_yaxes(title_text="MAE (%)", row=7, col=1)
    
    # Global Layout
    fig.update_layout(
        height=2500,  # Tall height for scrolling
        title_text="Backtest Analysis Dashboard",
        showlegend=False,
        template="plotly_white",
        hovermode="x unified"
    )
    
    # Save
    fig.write_html(save_path)
    print(f"Interactive dashboard saved to: {os.path.abspath(save_path)}")
