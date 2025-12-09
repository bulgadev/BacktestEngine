"""
Trading Strategy Analysis Tools Package
========================================

This package provides professional tools for detecting overfitting and
testing strategy robustness using Monte Carlo methods.

Tools Included:
- overfitting_analyzer: Detects overfitting via walk-forward and parameter sensitivity analysis
- monte_carlo_analyzer: Monte Carlo simulation methods with visualizations

Quick Start:
-----------
from tools.overfitting_analyzer import WalkForwardAnalyzer, ParameterSensitivityAnalyzer
from tools.monte_carlo_analyzer import MonteCarloTradeShuffler, MonteCarloVisualizer

# Run analysis
wf = WalkForwardAnalyzer(engine, strategy, data, num_periods=5)
results = wf.analyze()

# Monte Carlo test
mc = MonteCarloTradeShuffler(backtest_results, num_simulations=1000)
mc_results = mc.run_simulations()

# Visualize
MonteCarloVisualizer.plot_distribution(mc_results, save_path='plots/analysis.png')
"""

from .overfitting_analyzer import (
    WalkForwardAnalyzer,
    ParameterSensitivityAnalyzer,
    MetricsComparisonReport,
    OverfittingMetrics
)

from .monte_carlo_analyzer import (
    MonteCarloTradeShuffler,
    MonteCarloPriceShuffler,
    MonteCarloEquityCurveResampler,
    MonteCarloVisualizer,
    MonteCarloResults,
    create_monte_carlo_summary_plot
)

__all__ = [
    # Overfitting Analysis
    'WalkForwardAnalyzer',
    'ParameterSensitivityAnalyzer',
    'MetricsComparisonReport',
    'OverfittingMetrics',
    
    # Monte Carlo Analysis
    'MonteCarloTradeShuffler',
    'MonteCarloPriceShuffler',
    'MonteCarloEquityCurveResampler',
    'MonteCarloVisualizer',
    'MonteCarloResults',
    'create_monte_carlo_summary_plot',
]

__version__ = '1.0.0'
__author__ = 'Trading Strategy Analysis Tools'
