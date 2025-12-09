"""
Quick Reference Guide: Overfitting & Monte Carlo Tools
=======================================================

This guide provides quick copy-paste examples for common analysis tasks.
"""

# ==============================================================================
# COMPLETE ANALYSIS IN 10 LINES
# ==============================================================================

"""
from tools import WalkForwardAnalyzer, MonteCarloTradeShuffler, MonteCarloVisualizer
from backtest_engine import BacktestEngine
from example_strategy import SimpleMovingAverageStrategy
from data_fetcher import DataFetcher

data = DataFetcher.fetch_data('BTC', period='1y')
engine = BacktestEngine()
strategy = SimpleMovingAverageStrategy()
engine.run_backtest(strategy, data)
results = engine.get_results()

# Walk-forward analysis
wf = WalkForwardAnalyzer(engine, strategy, data, num_periods=5)
wf_results = wf.analyze()

# Monte Carlo
mc = MonteCarloTradeShuffler(results, num_simulations=1000)
mc_results = mc.run_simulations()
MonteCarloVisualizer.plot_distribution(mc_results, 'plots/analysis.png')
"""


# ==============================================================================
# SCENARIO 1: Check if strategy is overfitted
# ==============================================================================

"""
# Problem: Your strategy has great backtest results, but you suspect overfitting

from tools import WalkForwardAnalyzer, MetricsComparisonReport

# Step 1: Run walk-forward analysis
wf = WalkForwardAnalyzer(engine, strategy, data, num_periods=5)
wf_results = wf.analyze()

# Step 2: Get comprehensive metrics
report = MetricsComparisonReport(
    wf_results['in_sample_results'],
    wf_results['out_of_sample_results']
)
metrics = report.generate_report()
report.print_report(metrics)

# Step 3: Check the score
if metrics.overfitting_score > 60:
    print("❌ Strategy is likely overfitted, needs redesign")
elif metrics.overfitting_score > 30:
    print("⚠️  Moderate overfitting detected, use walk-forward optimization")
else:
    print("✓ Strategy appears robust")
"""


# ==============================================================================
# SCENARIO 2: Test parameter robustness
# ==============================================================================

"""
# Problem: Strategy works with MA periods (10, 30) but you want to verify
# it's not just lucky with those specific values

from tools import ParameterSensitivityAnalyzer

# Test sensitivity to fast MA parameter
analyzer = ParameterSensitivityAnalyzer(
    engine, strategy, data,
    parameters={'fast_period': [8, 10, 12, 14, 16]}
)
results = analyzer.analyze()

# Check stability metrics
sm = results['stability_metrics']
print(f"Sharpe CV: {sm['sharpe_cv']:.4f}")

if sm['sharpe_cv'] < 0.3:
    print("✓ Robust - strategy works across parameter range")
else:
    print("✗ Sensitive - overfitted to specific parameters")
"""


# ==============================================================================
# SCENARIO 3: Verify strategy has real edge (not just luck)
# ==============================================================================

"""
# Problem: You have profitable backtest, but want to verify it's not due to
# lucky trade sequencing

from tools import MonteCarloTradeShuffler, MonteCarloVisualizer

# Run trade shuffle (randomly reorders trades)
mc = MonteCarloTradeShuffler(results, num_simulations=1000)
mc_results = mc.run_simulations()

# Interpret results
if mc_results.p_value < 0.05:
    print("✓ Strategy edge is statistically significant (p < 0.05)")
elif mc_results.p_value < 0.20:
    print("⚠️  Marginally significant, investigate further")
else:
    print("✗ Result likely due to chance, strategy has no real edge")

# Visualize for clarity
MonteCarloVisualizer.plot_distribution(mc_results)
"""


# ==============================================================================
# SCENARIO 4: Build confidence intervals around returns
# ==============================================================================

"""
# Problem: Want to know realistic range of expected returns

from tools import MonteCarloEquityCurveResampler, MonteCarloVisualizer

# Bootstrap the equity curve
mc = MonteCarloEquityCurveResampler(results, num_simulations=1000)
mc_results = mc.run_simulations()

# Get confidence intervals
print(f"5% worst case:   {mc_results.percentile_5:.1f}%")
print(f"Expected return: {mc_results.percentile_50:.1f}%")
print(f"5% best case:    {mc_results.percentile_95:.1f}%")

# Visualize
MonteCarloVisualizer.plot_distribution(mc_results)
"""


# ==============================================================================
# SCENARIO 5: Compare multiple strategies
# ==============================================================================

"""
# Problem: Have multiple strategies, want to pick the most robust

from tools import (
    WalkForwardAnalyzer, 
    ParameterSensitivityAnalyzer,
    MonteCarloTradeShuffler,
    MetricsComparisonReport
)

strategies = [
    SimpleMovingAverageStrategy(10, 30),
    RSIStrategy(14, 30, 70),
    # ... more strategies
]

results_summary = {}

for strat in strategies:
    engine.run_backtest(strat, data)
    results = engine.get_results()
    
    # Walk-forward
    wf = WalkForwardAnalyzer(engine, strat, data, num_periods=5)
    wf_results = wf.analyze()
    
    # Get metrics
    report = MetricsComparisonReport(
        wf_results['in_sample_results'],
        wf_results['out_of_sample_results']
    )
    metrics = report.generate_report()
    
    # Monte Carlo
    mc = MonteCarloTradeShuffler(results, num_simulations=1000)
    mc_results = mc.run_simulations()
    
    results_summary[strat.get_name()] = {
        'overfitting_score': metrics.overfitting_score,
        'mc_p_value': mc_results.p_value,
        'final_return': results['metrics'].total_pnl_pct
    }

# Find best strategy
best = min(results_summary.items(), 
          key=lambda x: (x[1]['overfitting_score'], -x[1]['mc_p_value']))
print(f"Best strategy: {best[0]}")
"""


# ==============================================================================
# SCENARIO 6: Full professional analysis with visualizations
# ==============================================================================

"""
# Problem: Need production-grade analysis for client/stakeholder presentation

from tools import (
    WalkForwardAnalyzer,
    ParameterSensitivityAnalyzer,
    MonteCarloTradeShuffler,
    MonteCarloEquityCurveResampler,
    MonteCarloVisualizer,
    MetricsComparisonReport
)

# 1. Walk-Forward
wf = WalkForwardAnalyzer(engine, strategy, data, num_periods=5)
wf_results = wf.analyze()

# 2. Metrics Report
report = MetricsComparisonReport(
    wf_results['in_sample_results'],
    wf_results['out_of_sample_results']
)
metrics = report.generate_report()
report.print_report(metrics)

# 3. Parameter Sensitivity
param_analyzer = ParameterSensitivityAnalyzer(
    engine, strategy, data,
    parameters={'fast_period': [8, 10, 12, 14, 16]}
)
param_results = param_analyzer.analyze()

# 4. Monte Carlo Trade Shuffle
mc_shuffle = MonteCarloTradeShuffler(results, num_simulations=1000)
shuffle_results = mc_shuffle.run_simulations()

# 5. Monte Carlo Bootstrap
mc_bootstrap = MonteCarloEquityCurveResampler(results, num_simulations=1000)
bootstrap_results = mc_bootstrap.run_simulations()

# 6. Generate Visualizations
MonteCarloVisualizer.plot_distribution(
    shuffle_results,
    save_path='plots/monte_carlo_trade_shuffle.png'
)

MonteCarloVisualizer.plot_cumulative_distribution(
    shuffle_results,
    save_path='plots/monte_carlo_shuffle_cdf.png'
)

MonteCarloVisualizer.plot_distribution(
    bootstrap_results,
    save_path='plots/monte_carlo_bootstrap.png'
)

MonteCarloVisualizer.plot_qq_plot(
    bootstrap_results,
    save_path='plots/monte_carlo_qq_plot.png'
)

# 7. Summary
from tools.monte_carlo_analyzer import create_monte_carlo_summary_plot
create_monte_carlo_summary_plot({
    'Trade Shuffle': shuffle_results,
    'Equity Bootstrap': bootstrap_results
}, save_path='plots/monte_carlo_summary.png')

print(f"\n✓ Analysis complete! Check plots/ directory for visualizations")
"""


# ==============================================================================
# KEY DECISION MATRIX
# ==============================================================================

"""
Use this decision matrix to determine if strategy is tradeable:

                    Overfitting Score    MC P-Value    Parameter CV    Decision
                    ─────────────────    ──────────    ─────────────    ────────
Great           |   < 30                 < 0.05        < 0.3            TRADE ✓✓
Good            |   30-50                < 0.10        0.3-0.5          TRADE ✓
Questionable    |   50-70                < 0.20        0.5-1.0          INVESTIGATE
Concerning      |   70-85                > 0.20        > 1.0            REDESIGN ✗
Severe          |   > 85                 > 0.50        > 2.0            ABANDON ✗✗

Decision Guidelines:
- Strategy needs ALL metrics to be reasonable (don't trade if any are red)
- Use conservative approach: require < 40 overfitting score + p < 0.05
- Better to be safe and miss some profits than to trade an overfitted strategy
"""


# ==============================================================================
# INTERPRETATION CHEAT SHEET
# ==============================================================================

"""
OVERFITTING SCORE (0-100):
- 0-30: Low risk, strategy appears robust
- 30-60: Moderate risk, investigate with parameter sensitivity
- 60-80: High risk, strategy likely overfitted
- 80-100: Severe risk, do not trade

WALK-FORWARD DEGRADATION:
- 0-10%: Excellent
- 10-30%: Good
- 30-50%: Moderate (acceptable with caution)
- > 50%: Poor, severe overfitting

PARAMETER SENSITIVITY (Coefficient of Variation):
- < 0.3: Very robust (parameters don't matter)
- 0.3-0.5: Reasonably robust
- 0.5-1.0: Somewhat sensitive
- > 1.0: Very sensitive (overfitted)

MONTE CARLO P-VALUE:
- < 0.05: Statistically significant ✓
- 0.05-0.20: Marginally significant
- > 0.20: Not significant (likely luck)

PERCENTILE RANKING:
- > 95th percentile: Exceptional (possibly lucky?)
- 75-95th percentile: Above average
- 25-75th percentile: Normal/expected
- < 5th percentile: Below average (concerning)
"""


# ==============================================================================
# COMMON ERROR MESSAGES & FIXES
# ==============================================================================

"""
ERROR: "ModuleNotFoundError: No module named 'tools'"
FIX: Make sure you're in the BackEngine directory, or add path:
     import sys; sys.path.insert(0, '/path/to/BackEngine')

ERROR: "No completed trades found"
FIX: Strategy didn't generate any trades. Check signal generation logic.
     Verify strategy's on_bar() is returning valid signals.

ERROR: "Cannot import matplotlib"
FIX: Install matplotlib: pip install matplotlib

ERROR: "Results show overfitting but I think strategy is good"
FIX: Trust the data. Overfitting analysis is objective statistical analysis.
     Most trading strategies ARE overfitted. It's common.

ERROR: "Monte Carlo simulations are slow"
FIX: Use fewer simulations (500 instead of 1000)
     Use daily data instead of intraday
     Use faster strategy (fewer indicators)
"""


# ==============================================================================
# TIPS & TRICKS
# ==============================================================================

"""
1. FASTEST ANALYSIS (< 1 minute):
   - 5 walk-forward periods
   - 1 parameter sensitivity
   - 500 Monte Carlo simulations
   - Daily data

2. MOST THOROUGH ANALYSIS (10-30 minutes):
   - 10 walk-forward periods
   - Multiple parameter sensitivity tests
   - 5000 Monte Carlo simulations
   - Hourly or 30-minute data

3. PRODUCTION ANALYSIS (3-5 hours):
   - 20 walk-forward periods
   - Exhaustive parameter sensitivity
   - 10000 Monte Carlo simulations
   - 1-minute data
   - Multiple market regimes

4. COMPARING STRATEGIES:
   - Use same number of periods, simulations for fair comparison
   - Don't cherry-pick best analysis per strategy
   - Average metrics across strategies for baseline

5. IMPROVING OVERFITTED STRATEGY:
   - Add more data (longer historical period)
   - Reduce parameters (simpler = more robust)
   - Widen optimization ranges
   - Use ensemble of strategies with different parameters
   - Switch to walk-forward optimization instead of static parameters
"""
