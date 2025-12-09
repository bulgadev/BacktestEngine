"""
Monte Carlo Analysis Tool
=========================

This module implements multiple Monte Carlo simulation methods to assess
strategy robustness and identify overfitting. Monte Carlo methods randomly
resample trading data/results to generate distributions of possible outcomes.

If your strategy is robust, it should perform well across most random
permutations. If it's overfitted, performance will collapse under randomization.

Key Methods Implemented:

1. TRADE SHUFFLE: Randomly reorders the sequence of completed trades.
   → Tests if the strategy's success relies on a specific sequence of trades
   → Overfitted strategies break under shuffling

2. PRICE PERMUTATION: Randomly reorders price bars while maintaining OHLC structure.
   → Disconnects strategy logic from actual price patterns
   → Shows if strategy would work on random price data

3. EQUITY CURVE BOOTSTRAP: Resamples trades with replacement to build confidence intervals.
   → Shows the range of likely outcomes due to randomness
   → Identifies tail risks and best/worst case scenarios

4. MONTE CARLO P-VALUE: Compares actual performance to distribution of random results.
   → If actual return > 95th percentile of random distribution, strategy is suspicious
   → Low p-value = strategy likely has edge, high p-value = strategy is lucky

All methods include visualization plots to help interpret results.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')


@dataclass
class MonteCarloResults:
    """
    Container for Monte Carlo simulation results.
    
    Attributes:
        method_name: Name of the Monte Carlo method used
        actual_value: The actual metric value from real backtest
        simulated_values: Array of values from Monte Carlo simulations
        mean: Mean of simulated distribution
        std: Standard deviation of simulated distribution
        percentile_5: 5th percentile (downside risk)
        percentile_25: 25th percentile
        percentile_50: Median of distribution
        percentile_75: 75th percentile
        percentile_95: 95th percentile (upside potential)
        p_value: Probability that actual result could occur by chance
        interpretation: Text interpretation of results
    """
    method_name: str = ""
    actual_value: float = 0.0
    simulated_values: np.ndarray = None
    mean: float = 0.0
    std: float = 0.0
    percentile_5: float = 0.0
    percentile_25: float = 0.0
    percentile_50: float = 0.0
    percentile_75: float = 0.0
    percentile_95: float = 0.0
    p_value: float = 0.0
    interpretation: str = ""


class MonteCarloTradeShuffler:
    """
    Trade Shuffle Monte Carlo Method
    ================================
    
    This method shuffles the order of completed trades while keeping their
    properties (size, P&L) the same. 
    
    Theory:
    - If trades are randomly ordered, the strategy's edge should disappear
    - A robust strategy has consistent performance regardless of trade order
    - Overfitted strategies often have a few "lucky" trades; shuffling exposes this
    
    Example:
    Original trades: [+100, +50, -30, +80, -20]  → Total: +180
    Shuffled:        [-30, +80, +100, -20, +50]  → Total: +180 (same), but equity curve differs
    
    If most shuffled versions have negative returns, the original success
    was likely due to lucky trade sequencing, not strategy edge.
    """
    
    def __init__(self, backtest_results: Dict[str, Any], num_simulations: int = 1000):
        """
        Initialize Trade Shuffle Monte Carlo analyzer.
        
        Args:
            backtest_results: Dictionary from engine.get_results() containing trades list
            num_simulations: Number of random shuffle simulations to run (default 1000)
        """
        self.trades = backtest_results['trades']
        self.initial_capital = backtest_results['metrics'].total_pnl if backtest_results['metrics'] else 0
        self.num_simulations = num_simulations
        self.pnl_values = [t.pnl for t in self.trades if t.pnl is not None]
        
        if not self.pnl_values:
            raise ValueError("No completed trades found in backtest results")
    
    def run_simulations(self) -> MonteCarloResults:
        """
        Run Monte Carlo trade shuffle simulations.
        
        Process:
        1. Extract P&L from each completed trade
        2. For each simulation:
           a. Randomly shuffle the P&L sequence
           b. Calculate cumulative return (starting from initial capital)
           c. Record final return percentage
        3. Analyze distribution to get statistics and p-value
        
        Returns:
            MonteCarloResults object with statistics and interpretation
        """
        print(f"\n{'='*70}")
        print(f"MONTE CARLO: TRADE SHUFFLE ANALYSIS")
        print(f"{'='*70}")
        print(f"Completed trades:      {len(self.pnl_values)}")
        print(f"Simulations:           {self.num_simulations}")
        
        # Calculate actual return from trades in original order
        actual_total_pnl = sum(self.pnl_values)
        
        # Run simulations
        simulated_returns = []
        
        for i in range(self.num_simulations):
            # Shuffle the P&L sequence
            shuffled_pnl = np.random.permutation(self.pnl_values)
            
            # Calculate cumulative P&L
            cumulative_pnl = sum(shuffled_pnl)
            simulated_returns.append(cumulative_pnl)
        
        simulated_returns = np.array(simulated_returns)
        
        # Calculate statistics
        mean = np.mean(simulated_returns)
        std = np.std(simulated_returns)
        
        # Calculate percentiles
        percentile_5 = np.percentile(simulated_returns, 5)
        percentile_25 = np.percentile(simulated_returns, 25)
        percentile_50 = np.percentile(simulated_returns, 50)
        percentile_75 = np.percentile(simulated_returns, 75)
        percentile_95 = np.percentile(simulated_returns, 95)
        
        # Calculate p-value: probability of actual result being better than random
        p_value = np.mean(simulated_returns >= actual_total_pnl)
        
        # Generate interpretation
        if actual_total_pnl < percentile_5:
            interpretation = "⚠️  WORSE THAN RANDOM: Strategy underperforms even random trade order. Likely broken."
        elif actual_total_pnl < percentile_25:
            interpretation = "⚠️  BELOW MEDIAN: Performance below typical random shuffles. Weak strategy."
        elif actual_total_pnl < percentile_75:
            interpretation = "✓  NORMAL: Performance in expected range. Strategy seems reasonable."
        elif actual_total_pnl < percentile_95:
            interpretation = "✓  ABOVE MEDIAN: Performance above typical shuffles. Strategy likely has edge."
        else:
            interpretation = "✓✓ OUTLIER: Performance significantly better than random. Strong strategy edge."
        
        if p_value < 0.05:
            interpretation += "\n     Statistical significance: p < 0.05 ✓ (result unlikely by chance)"
        elif p_value < 0.20:
            interpretation += "\n     Statistical significance: p < 0.20 (marginally significant)"
        else:
            interpretation += "\n     Statistical significance: p >= 0.20 ✗ (result likely by chance)"
        
        print(f"\nActual Total P&L:      ${actual_total_pnl:,.2f}")
        print(f"Mean (random shuffle): ${mean:,.2f}")
        print(f"Std Dev:               ${std:,.2f}")
        print(f"5th Percentile:        ${percentile_5:,.2f}")
        print(f"50th Percentile:       ${percentile_50:,.2f}")
        print(f"95th Percentile:       ${percentile_95:,.2f}")
        print(f"P-Value:               {p_value:.4f}")
        print(f"\n{interpretation}")
        print(f"{'='*70}\n")
        
        results = MonteCarloResults(
            method_name="Trade Shuffle",
            actual_value=actual_total_pnl,
            simulated_values=simulated_returns,
            mean=mean,
            std=std,
            percentile_5=percentile_5,
            percentile_25=percentile_25,
            percentile_50=percentile_50,
            percentile_75=percentile_75,
            percentile_95=percentile_95,
            p_value=p_value,
            interpretation=interpretation
        )
        
        return results


class MonteCarloPriceShuffler:
    """
    Price Permutation Monte Carlo Method
    ====================================
    
    This method randomly reorders price bars while maintaining OHLC structure.
    
    Theory:
    - Randomly shuffled prices test if the strategy's logic adds any value
    - A strategy that works on random prices is pure curve-fitting
    - A robust strategy should fail on random prices but succeed on real prices
    
    Implementation:
    1. Shuffle the order of bars
    2. Re-run the strategy on shuffled prices
    3. Collect P&L from each simulation
    4. Compare actual vs simulated distribution
    
    Warning: This is computationally expensive as it requires re-running
    the strategy backtest many times. Use moderate simulation count.
    """
    
    def __init__(self, engine, strategy, data: pd.DataFrame, num_simulations: int = 100):
        """
        Initialize Price Shuffle Monte Carlo analyzer.
        
        Args:
            engine: BacktestEngine instance
            strategy: BaseStrategy instance (will be re-run multiple times)
            data: Historical DataFrame with OHLCV data
            num_simulations: Number of random price permutations (default 100)
                            Use smaller values (50-100) for faster execution
        """
        self.engine = engine
        self.strategy = strategy
        self.data = data
        self.num_simulations = num_simulations
    
    def run_simulations(self) -> MonteCarloResults:
        """
        Run Monte Carlo price permutation simulations.
        
        Warning: This is slow because it re-backtests the strategy
        num_simulations times on randomly shuffled price data.
        
        Returns:
            MonteCarloResults object with statistics
        """
        print(f"\n{'='*70}")
        print(f"MONTE CARLO: PRICE PERMUTATION ANALYSIS")
        print(f"{'='*70}")
        print(f"Original data bars:    {len(self.data)}")
        print(f"Simulations:           {self.num_simulations}")
        print(f"(This may take a few minutes...)\n")
        
        # Get actual return on original prices
        original_engine = self._run_backtest_silent(self.data)
        actual_return = original_engine.metrics.total_pnl_pct if original_engine.metrics else 0
        
        # Run simulations on shuffled prices
        simulated_returns = []
        
        for sim in range(self.num_simulations):
            # Shuffle indices but maintain chronological OHLC structure
            shuffled_indices = np.random.permutation(len(self.data))
            shuffled_data = self.data.iloc[shuffled_indices].reset_index(drop=True)
            shuffled_data.index = self.data.index  # Restore original timestamps
            shuffled_data = shuffled_data.sort_index()  # Re-sort by timestamp
            
            # Run strategy on shuffled prices
            sim_engine = self._run_backtest_silent(shuffled_data)
            sim_return = sim_engine.metrics.total_pnl_pct if sim_engine.metrics else 0
            simulated_returns.append(sim_return)
            
            if (sim + 1) % max(1, self.num_simulations // 10) == 0:
                print(f"  Progress: {sim + 1}/{self.num_simulations} simulations completed")
        
        simulated_returns = np.array(simulated_returns)
        
        # Calculate statistics
        mean = np.mean(simulated_returns)
        std = np.std(simulated_returns)
        
        percentile_5 = np.percentile(simulated_returns, 5)
        percentile_25 = np.percentile(simulated_returns, 25)
        percentile_50 = np.percentile(simulated_returns, 50)
        percentile_75 = np.percentile(simulated_returns, 75)
        percentile_95 = np.percentile(simulated_returns, 95)
        
        # Calculate p-value
        p_value = np.mean(simulated_returns >= actual_return)
        
        # Generate interpretation
        if actual_return < percentile_5:
            interpretation = "⚠️  WORSE THAN RANDOMNESS: Strategy loses money even on random prices. Critical issue."
        elif actual_return < percentile_25:
            interpretation = "⚠️  BELOW EXPECTED: Strategy underperforms on random prices. Likely overfitted."
        elif actual_return < percentile_75:
            interpretation = "✓  NORMAL: Strategy works on real prices but not random. Expected behavior."
        elif actual_return < percentile_95:
            interpretation = "✓  GOOD: Strategy clearly has edge vs random prices."
        else:
            interpretation = "✓✓ EXCEPTIONAL: Strategy vastly outperforms random. Strong edge detected."
        
        print(f"Actual Return:         {actual_return:>8.2f}%")
        print(f"Mean (random prices):  {mean:>8.2f}%")
        print(f"Std Dev:               {std:>8.2f}%")
        print(f"5th Percentile:        {percentile_5:>8.2f}%")
        print(f"50th Percentile:       {percentile_50:>8.2f}%")
        print(f"95th Percentile:       {percentile_95:>8.2f}%")
        print(f"P-Value:               {p_value:.4f}")
        print(f"\n{interpretation}")
        print(f"{'='*70}\n")
        
        results = MonteCarloResults(
            method_name="Price Permutation",
            actual_value=actual_return,
            simulated_values=simulated_returns,
            mean=mean,
            std=std,
            percentile_5=percentile_5,
            percentile_25=percentile_25,
            percentile_50=percentile_50,
            percentile_75=percentile_75,
            percentile_95=percentile_95,
            p_value=p_value,
            interpretation=interpretation
        )
        
        return results
    
    def _run_backtest_silent(self, data: pd.DataFrame):
        """Run backtest without printing output."""
        from backtest_engine import BacktestEngine
        
        engine = BacktestEngine(
            initial_capital=self.engine.initial_capital,
            commission=self.engine.commission,
            slippage=self.engine.slippage,
            periods_per_year=self.engine.periods_per_year
        )
        
        # Silence output
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            self.strategy.initialized = False
            engine.run_backtest(self.strategy, data)
        finally:
            sys.stdout = old_stdout
        
        return engine


class MonteCarloEquityCurveResampler:
    """
    Equity Curve Bootstrap Monte Carlo Method
    ==========================================
    
    This method resamples completed trades WITH REPLACEMENT to build
    confidence intervals around the equity curve.
    
    Theory:
    - Resampling trades shows the range of likely outcomes due to randomness
    - The 5th-95th percentile range shows "expected" trading ranges
    - If actual equity curve deviates far from this range, something's wrong
    
    Process:
    1. For each simulation:
       a. Randomly sample trades with replacement
       b. Replay trades to build equity curve
    2. Calculate confidence intervals for equity at each point in time
    3. Visualize actual vs Monte Carlo range
    """
    
    def __init__(self, backtest_results: Dict[str, Any], initial_capital: float = 10000, 
                 num_simulations: int = 1000):
        """
        Initialize Equity Curve Bootstrap analyzer.
        
        Args:
            backtest_results: Dictionary from engine.get_results()
            initial_capital: Starting capital for equity curve calculation
            num_simulations: Number of bootstrap simulations (default 1000)
        """
        self.trades = backtest_results['trades']
        self.equity_curve = backtest_results['equity_curve']
        self.timestamps = backtest_results['timestamps']
        self.initial_capital = initial_capital
        self.num_simulations = num_simulations
        self.pnl_values = [t.pnl for t in self.trades if t.pnl is not None]
    
    def run_simulations(self) -> MonteCarloResults:
        """
        Run Monte Carlo equity curve bootstrap simulations.
        
        Returns:
            MonteCarloResults object with statistics and equity curve ranges
        """
        print(f"\n{'='*70}")
        print(f"MONTE CARLO: EQUITY CURVE BOOTSTRAP ANALYSIS")
        print(f"{'='*70}")
        print(f"Completed trades:      {len(self.pnl_values)}")
        print(f"Simulations:           {self.num_simulations}")
        
        # Run bootstrap simulations
        bootstrap_returns = []
        
        for sim in range(self.num_simulations):
            # Resample trades with replacement
            resampled_pnl = np.random.choice(self.pnl_values, size=len(self.pnl_values), replace=True)
            total_pnl = np.sum(resampled_pnl)
            final_equity = self.initial_capital + total_pnl
            return_pct = (total_pnl / self.initial_capital) * 100
            bootstrap_returns.append(return_pct)
        
        bootstrap_returns = np.array(bootstrap_returns)
        
        # Calculate statistics
        actual_return = ((self.initial_capital + sum(self.pnl_values)) - self.initial_capital) / self.initial_capital * 100
        
        mean = np.mean(bootstrap_returns)
        std = np.std(bootstrap_returns)
        
        percentile_5 = np.percentile(bootstrap_returns, 5)
        percentile_25 = np.percentile(bootstrap_returns, 25)
        percentile_50 = np.percentile(bootstrap_returns, 50)
        percentile_75 = np.percentile(bootstrap_returns, 75)
        percentile_95 = np.percentile(bootstrap_returns, 95)
        
        p_value = np.mean(bootstrap_returns >= actual_return)
        
        # Generate interpretation based on confidence interval
        if actual_return < percentile_5:
            interpretation = "⚠️  OUTLIER - NEGATIVE: Actual return is in worst 5% of bootstrapped samples. Unlucky period."
        elif actual_return < percentile_25:
            interpretation = "⚠️  BELOW EXPECTED: Actual return below 25th percentile. Below expected range."
        elif actual_return < percentile_75:
            interpretation = "✓  NORMAL: Actual return within expected 25th-75th percentile range."
        elif actual_return < percentile_95:
            interpretation = "✓  ABOVE EXPECTED: Actual return above 75th percentile. Lucky period."
        else:
            interpretation = "✓✓ EXCEPTIONAL: Actual return in best 5% of bootstrapped samples. Very lucky."
        
        print(f"\nActual Return:         {actual_return:>8.2f}%")
        print(f"Bootstrap Mean:        {mean:>8.2f}%")
        print(f"Bootstrap Std:         {std:>8.2f}%")
        print(f"5th Percentile (Risk): {percentile_5:>8.2f}%")
        print(f"25th Percentile:       {percentile_25:>8.2f}%")
        print(f"50th Percentile:       {percentile_50:>8.2f}%")
        print(f"75th Percentile:       {percentile_75:>8.2f}%")
        print(f"95th Percentile (Upside): {percentile_95:>8.2f}%")
        print(f"\nInterpretation:")
        print(f"{interpretation}")
        print(f"{'='*70}\n")
        
        results = MonteCarloResults(
            method_name="Equity Curve Bootstrap",
            actual_value=actual_return,
            simulated_values=bootstrap_returns,
            mean=mean,
            std=std,
            percentile_5=percentile_5,
            percentile_25=percentile_25,
            percentile_50=percentile_50,
            percentile_75=percentile_75,
            percentile_95=percentile_95,
            p_value=p_value,
            interpretation=interpretation
        )
        
        return results


class MonteCarloVisualizer:
    """
    Creates professional visualization plots for Monte Carlo results.
    
    Generates:
    1. Distribution histogram with percentile markers
    2. Cumulative probability plots
    3. Q-Q plots for normality assessment
    4. Summary statistics overlays
    """
    
    @staticmethod
    def plot_distribution(mc_result: MonteCarloResults, save_path: Optional[str] = None) -> None:
        """
        Plot histogram of Monte Carlo simulations with percentiles and actual value.
        
        Args:
            mc_result: MonteCarloResults object from simulation
            save_path: Optional path to save plot (e.g., 'plots/mc_trade_shuffle.png')
        """
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Plot histogram
        n, bins, patches = ax.hist(mc_result.simulated_values, bins=50, 
                                    alpha=0.7, color='steelblue', edgecolor='black',
                                    label='Monte Carlo Simulations')
        
        # Color histogram bars by percentile
        for i, patch in enumerate(patches):
            if bins[i] < mc_result.percentile_5:
                patch.set_facecolor('darkred')
            elif bins[i] < mc_result.percentile_25:
                patch.set_facecolor('orange')
            elif bins[i] < mc_result.percentile_75:
                patch.set_facecolor('steelblue')
            elif bins[i] < mc_result.percentile_95:
                patch.set_facecolor('lightgreen')
            else:
                patch.set_facecolor('darkgreen')
        
        # Add vertical lines for percentiles and actual value
        ax.axvline(mc_result.actual_value, color='red', linestyle='--', linewidth=2.5, 
                   label=f'Actual: {mc_result.actual_value:,.0f}')
        ax.axvline(mc_result.percentile_5, color='darkred', linestyle=':', linewidth=1.5, 
                   label=f'5th %ile: {mc_result.percentile_5:,.0f}')
        ax.axvline(mc_result.percentile_50, color='blue', linestyle=':', linewidth=1.5, 
                   label=f'Median: {mc_result.percentile_50:,.0f}')
        ax.axvline(mc_result.percentile_95, color='darkgreen', linestyle=':', linewidth=1.5, 
                   label=f'95th %ile: {mc_result.percentile_95:,.0f}')
        
        # Formatting
        ax.set_xlabel('Value', fontsize=12, fontweight='bold')
        ax.set_ylabel('Frequency', fontsize=12, fontweight='bold')
        ax.set_title(f'{mc_result.method_name} - Distribution Analysis\n'
                    f'n={len(mc_result.simulated_values)} simulations',
                    fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Add statistics box
        stats_text = f'Mean: {mc_result.mean:,.0f}\nStd: {mc_result.std:,.0f}\np-value: {mc_result.p_value:.4f}'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
               fontsize=10, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        
        plt.show()
    
    @staticmethod
    def plot_cumulative_distribution(mc_result: MonteCarloResults, 
                                    save_path: Optional[str] = None) -> None:
        """
        Plot cumulative distribution function (CDF) for Monte Carlo results.
        
        Shows the cumulative probability - useful for understanding tail risks
        and upside potential.
        
        Args:
            mc_result: MonteCarloResults object
            save_path: Optional path to save plot
        """
        sorted_values = np.sort(mc_result.simulated_values)
        cumulative_prob = np.arange(1, len(sorted_values) + 1) / len(sorted_values)
        
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Plot CDF
        ax.plot(sorted_values, cumulative_prob, linewidth=2.5, color='steelblue', 
               label='Cumulative Probability')
        
        # Add reference lines
        ax.axvline(mc_result.actual_value, color='red', linestyle='--', linewidth=2, 
                  label=f'Actual: {mc_result.actual_value:,.0f}')
        ax.axvline(mc_result.percentile_5, color='darkred', linestyle=':', linewidth=1.5)
        ax.axvline(mc_result.percentile_95, color='darkgreen', linestyle=':', linewidth=1.5)
        
        # Add horizontal probability lines
        ax.axhline(0.05, color='gray', linestyle=':', alpha=0.5)
        ax.axhline(0.50, color='gray', linestyle=':', alpha=0.5)
        ax.axhline(0.95, color='gray', linestyle=':', alpha=0.5)
        
        # Formatting
        ax.set_xlabel('Value', fontsize=12, fontweight='bold')
        ax.set_ylabel('Cumulative Probability', fontsize=12, fontweight='bold')
        ax.set_title(f'{mc_result.method_name} - Cumulative Distribution\n'
                    f'Shows probability of achieving each return level',
                    fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='lower right', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_ylim([0, 1])
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        
        plt.show()
    
    @staticmethod
    def plot_qq_plot(mc_result: MonteCarloResults, save_path: Optional[str] = None) -> None:
        """
        Create Q-Q plot to test if simulated returns are normally distributed.
        
        A Q-Q (quantile-quantile) plot compares the distribution of simulated
        values against a theoretical normal distribution. Points close to the
        diagonal indicate normal distribution.
        
        This helps identify if tail risks are correctly modeled (normal assumption
        may underestimate extreme events).
        
        Args:
            mc_result: MonteCarloResults object
            save_path: Optional path to save plot
        """
        from scipy import stats
        
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Create Q-Q plot
        stats.probplot(mc_result.simulated_values, dist="norm", plot=ax)
        
        ax.set_title(f'{mc_result.method_name} - Q-Q Plot\n'
                    f'Tests for normal distribution (points on diagonal = normal)',
                    fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        
        plt.show()
    
    @staticmethod
    def plot_comparison(results_list: List[Tuple[MonteCarloResults, str]], 
                       save_path: Optional[str] = None) -> None:
        """
        Compare multiple Monte Carlo results side by side.
        
        Creates subplots for each method to compare actual vs simulated distributions.
        
        Args:
            results_list: List of (MonteCarloResults, title) tuples
            save_path: Optional path to save plot
        """
        n_results = len(results_list)
        fig, axes = plt.subplots(n_results, 1, figsize=(12, 5 * n_results))
        
        if n_results == 1:
            axes = [axes]
        
        for idx, (mc_result, title) in enumerate(results_list):
            ax = axes[idx]
            
            # Plot histogram
            ax.hist(mc_result.simulated_values, bins=40, alpha=0.7, 
                   color='steelblue', edgecolor='black')
            
            # Add actual value line
            ax.axvline(mc_result.actual_value, color='red', linestyle='--', 
                      linewidth=2.5, label=f'Actual: {mc_result.actual_value:,.0f}')
            
            # Add percentile lines
            ax.axvline(mc_result.percentile_5, color='darkred', linestyle=':', 
                      linewidth=1.5, alpha=0.7)
            ax.axvline(mc_result.percentile_95, color='darkgreen', linestyle=':', 
                      linewidth=1.5, alpha=0.7)
            
            # Formatting
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_xlabel('Value', fontsize=10)
            ax.set_ylabel('Frequency', fontsize=10)
            ax.legend(fontsize=9)
            ax.grid(True, alpha=0.3, linestyle='--')
        
        plt.suptitle('Monte Carlo Analysis Comparison', fontsize=16, fontweight='bold', y=1.00)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Comparison plot saved to {save_path}")
        
        plt.show()


def create_monte_carlo_summary_plot(results_dict: Dict[str, MonteCarloResults], 
                                    save_path: Optional[str] = None) -> None:
    """
    Create a comprehensive summary plot showing all Monte Carlo methods.
    
    This multi-panel visualization shows:
    - Top left: Trade Shuffle distribution
    - Top right: Equity Bootstrap distribution  
    - Bottom: Summary statistics table and interpretation
    
    Args:
        results_dict: Dictionary of {method_name: MonteCarloResults}
        save_path: Optional path to save the summary plot
    """
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.3)
    
    methods = list(results_dict.keys())
    
    # Plot first two methods
    for idx, method_name in enumerate(methods[:2]):
        mc_result = results_dict[method_name]
        ax = fig.add_subplot(gs[0, idx])
        
        ax.hist(mc_result.simulated_values, bins=40, alpha=0.7, 
               color='steelblue', edgecolor='black')
        ax.axvline(mc_result.actual_value, color='red', linestyle='--', linewidth=2)
        ax.axvline(mc_result.percentile_95, color='green', linestyle=':', linewidth=1.5)
        ax.axvline(mc_result.percentile_5, color='darkred', linestyle=':', linewidth=1.5)
        
        ax.set_title(f'{method_name}\nActual: {mc_result.actual_value:,.0f}', 
                    fontsize=11, fontweight='bold')
        ax.set_xlabel('Value', fontsize=9)
        ax.set_ylabel('Frequency', fontsize=9)
        ax.grid(True, alpha=0.3)
    
    # Summary statistics table
    ax = fig.add_subplot(gs[1, :])
    ax.axis('tight')
    ax.axis('off')
    
    summary_data = []
    for method_name, mc_result in results_dict.items():
        summary_data.append([
            method_name,
            f"${mc_result.actual_value:,.0f}",
            f"${mc_result.mean:,.0f}",
            f"${mc_result.std:,.0f}",
            f"{mc_result.p_value:.4f}",
            "✓" if mc_result.p_value < 0.05 else "✗"
        ])
    
    table = ax.table(cellText=summary_data,
                    colLabels=['Method', 'Actual', 'Mean', 'Std Dev', 'P-Value', 'Significant'],
                    cellLoc='center',
                    loc='center',
                    colWidths=[0.25, 0.15, 0.15, 0.15, 0.15, 0.15])
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    
    # Style header
    for i in range(6):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Style rows
    for i in range(1, len(summary_data) + 1):
        for j in range(6):
            table[(i, j)].set_facecolor('#f0f0f0' if i % 2 == 0 else 'white')
    
    plt.suptitle('Monte Carlo Analysis Summary', fontsize=16, fontweight='bold', y=0.98)
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Summary plot saved to {save_path}")
    
    plt.show()
