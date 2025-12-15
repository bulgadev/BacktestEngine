import pandas as pd
import numpy as np
import warnings
from backtest_engine import BacktestEngine
from liquidity_catcher import LiquidityCatcherStrategy

warnings.filterwarnings('ignore')

def generate_synthetic_data(length=1000):
    """Generate synthetic trending data with swings."""
    np.random.seed(42)
    
    # Create a trend + sine wave + noise
    t = np.linspace(0, 100, length)
    trend = t * 0.5  # Upward trend
    cycle = np.sin(t) * 5 # Swings
    noise = np.random.normal(0, 0.5, length)
    
    close = 100 + trend + cycle + noise
    
    # Create OHLC
    data = pd.DataFrame(index=pd.date_range(start='2024-01-01', periods=length, freq='1H'))
    data['Close'] = close
    data['Open'] = close + np.random.normal(0, 0.2, length)
    data['High'] = data[['Open', 'Close']].max(axis=1) + abs(np.random.normal(0, 0.3, length))
    data['Low'] = data[['Open', 'Close']].min(axis=1) - abs(np.random.normal(0, 0.3, length))
    
    return data

def run_verification():
    print("Generating synthetic data...")
    data = generate_synthetic_data(1000)
    
    print("\n--- Testing 'SIMPLE' Bias Mode (Default) ---")
    engine = BacktestEngine(initial_capital=10000)
    strategy = LiquidityCatcherStrategy(
        ema_period=20, 
        pivot_length=3,
        bias_method='SIMPLE',
        risk_reward=1.5
    )
    
    engine.run_backtest(strategy, data)
    engine.print_performance()
    
    results = engine.get_results()
    if results['metrics'].total_trades > 0:
        print("PASS: Trades were generated in SIMPLE mode.")
    else:
        print("FAIL: No trades in SIMPLE mode.")
        
    print("\n--- Testing 'ORIGINAL' Bias Mode ---")
    engine_orig = BacktestEngine(initial_capital=10000)
    strategy_orig = LiquidityCatcherStrategy(
        ema_period=20, 
        pivot_length=3,
        bias_method='ORIGINAL', # Stricter
        risk_reward=1.5
    )
    
    engine_orig.run_backtest(strategy_orig, data)
    engine_orig.print_performance()
    
    results = engine_orig.get_results()
    print(f"Original Mode Trades: {results['metrics'].total_trades}")

if __name__ == "__main__":
    run_verification()
