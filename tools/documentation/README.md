# Trading Strategy Analysis Tools

This directory contains professional-grade tools for detecting overfitting and testing strategy robustness using Monte Carlo methods.

## Tools Overview

### 1. **overfitting_analyzer.py**

Detects overfitting in trading strategies using multiple statistical methods.

#### Components:

- **WalkForwardAnalyzer**: Gold-standard overfitting detection
  - Divides data into rolling train/test windows
  - Compares in-sample vs out-of-sample performance
  - Measures performance degradation on unseen data
  - Key metric: Walk-forward degradation percentage

- **ParameterSensitivityAnalyzer**: Tests strategy robustness to parameter changes
  - Varies strategy parameters (e.g., MA periods)
  - Calculates stability score (coefficient of variation)
  - Identifies "parameter cliffs" (overfitting indicator)
  - Lower CV = more robust

- **MetricsComparisonReport**: Comprehensive overfitting assessment
  - Compares all metrics between in/out-of-sample
  - Generates composite Overfitting Score (0-100)
  - Risk levels: LOW (0-30), MODERATE (30-60), HIGH (60-80), SEVERE (80-100)
  - Actionable recommendations

#### Usage Example:

```python
from overfitting_analyzer import WalkForwardAnalyzer, MetricsComparisonReport

# Run walk-forward analysis
wf_analyzer = WalkForwardAnalyzer(engine, strategy, data, num_periods=5)
wf_results = wf_analyzer.analyze()

# Generate metrics report
report = MetricsComparisonReport(
    wf_results['in_sample_results'],
    wf_results['out_of_sample_results']
)
metrics = report.generate_report()
report.print_report(metrics)

# Check recommendations
print(f"Overfitting Score: {metrics.overfitting_score:.1f}/100")
print(f"Risk Level: {metrics.overfitting_risk_level}")
for rec in metrics.recommendations:
    print(f"  - {rec}")
```

---

### 2. **monte_carlo_analyzer.py**

Implements multiple Monte Carlo methods to test strategy robustness with professional visualizations.

#### Components:

- **MonteCarloTradeShuffler**: Shuffle Trade Analysis
  - Randomly reorders completed trades
  - Tests if strategy's success relies on specific trade sequence
  - Overfitted strategies collapse under shuffling
  - Returns p-value indicating statistical significance
  
  Key insight: If strategy performs well with shuffled trades,
  it's just lucky sequencing, not a real edge.

- **MonteCarloPriceShuffler**: Price Permutation Analysis (Computationally expensive)
  - Randomly reorders price bars
  - Tests if strategy works on random prices (it shouldn't!)
  - Slow but thorough overfitting detection
  - Use 50-100 simulations for speed

- **MonteCarloEquityCurveResampler**: Bootstrap Confidence Intervals
  - Resamples trades with replacement
  - Builds distribution of possible outcomes
  - Generates 5th-95th percentile confidence intervals
  - Shows range of likely returns due to randomness

- **MonteCarloVisualizer**: Professional Plotting
  - Histogram with percentile markers
  - Cumulative distribution functions (CDF)
  - Q-Q plots for normality assessment
  - Comparison plots across methods
  - Summary statistics visualizations

#### Monte Carlo Interpretation Guide:

**Trade Shuffle P-Value:**
- p < 0.05: Strategy has statistical significance ✓
- p >= 0.20: Result likely due to chance ✗
- 0.05 < p < 0.20: Marginally significant, investigate further

**Percentile Ranking:**
- Actual > 95th percentile: Exceptional performance (suspicious?)
- Actual in 75-95th percentile: Above average
- Actual in 25-75th percentile: Normal/expected
- Actual < 5th percentile: Below average (concerning)

#### Usage Example:

```python
from monte_carlo_analyzer import (
    MonteCarloTradeShuffler,
    MonteCarloEquityCurveResampler,
    MonteCarloVisualizer
)

# Get backtest results first
results = engine.get_results()

# Run Trade Shuffle analysis
shuffle_mc = MonteCarloTradeShuffler(results, num_simulations=1000)
shuffle_results = shuffle_mc.run_simulations()

# Run Equity Bootstrap analysis
bootstrap_mc = MonteCarloEquityCurveResampler(results, num_simulations=1000)
bootstrap_results = bootstrap_mc.run_simulations()

# Visualize results
MonteCarloVisualizer.plot_distribution(shuffle_results, 
    save_path='plots/trade_shuffle.png')

MonteCarloVisualizer.plot_cumulative_distribution(bootstrap_results,
    save_path='plots/equity_bootstrap_cdf.png')

# Compare multiple methods
MonteCarloVisualizer.plot_comparison([
    (shuffle_results, 'Trade Shuffle'),
    (bootstrap_results, 'Equity Bootstrap')
], save_path='plots/comparison.png')
```

---

### 3. **example_analysis.py**

Complete end-to-end example script showing how to use all analysis tools.

#### What it does:

1. Fetches historical market data
2. Runs initial backtest
3. Performs Walk-Forward Analysis
4. Tests Parameter Sensitivity
5. Runs Monte Carlo Trade Shuffle
6. Runs Monte Carlo Equity Bootstrap
7. Generates all visualizations
8. Produces final recommendations

#### Running the Example:

```bash
python tools/example_analysis.py
```

This will:
- Create plots in `tools/plots/` directory
- Print comprehensive analysis report
- Generate final recommendations
- Tell you if strategy is tradeable

---

## Overfitting Score Interpretation

The Overfitting Score combines all detection methods into a 0-100 scale:

### 0-30: LOW RISK (Robust Strategy) ✓
- Strategy appears genuinely robust
- Low performance degradation on new data
- Parameter sensitivity is reasonable
- **Recommendation**: Ready to trade (with appropriate risk management)

### 30-60: MODERATE RISK (Some Concerns) ⚠️
- Some overfitting detected
- Performance degrades moderately on new data
- Sensitive to certain parameters
- **Recommendation**: Use walk-forward optimization, validate on more data

### 60-80: HIGH RISK (Significant Overfitting) ⚠️⚠️
- Clear overfitting indicators
- Performance significantly worse on new data
- Strategy breaks with parameter changes
- **Recommendation**: Redesign strategy, simplify logic, use different approach

### 80-100: SEVERE RISK (Severely Curve-Fitted) ✗
- Strategy is not viable
- Complete performance collapse on new data
- Only works for specific parameter/time period combination
- **Recommendation**: Do not trade, redesign from scratch

---

## Practical Workflow

### Complete Analysis Workflow:

```python
from overfitting_analyzer import WalkForwardAnalyzer, ParameterSensitivityAnalyzer, MetricsComparisonReport
from monte_carlo_analyzer import MonteCarloTradeShuffler, MonteCarloEquityCurveResampler, MonteCarloVisualizer
from backtest_engine import BacktestEngine
from example_strategy import SimpleMovingAverageStrategy
from data_fetcher import DataFetcher

# 1. Get data
data = DataFetcher.fetch_data('BTC', period='1y', interval='1d')

# 2. Run backtest
engine = BacktestEngine(initial_capital=10000)
strategy = SimpleMovingAverageStrategy(fast_period=10, slow_period=30)
engine.run_backtest(strategy, data)
results = engine.get_results()

# 3. Walk-Forward Analysis
wf = WalkForwardAnalyzer(engine, strategy, data, num_periods=5)
wf_results = wf.analyze()

# 4. Metrics Comparison
report = MetricsComparisonReport(
    wf_results['in_sample_results'],
    wf_results['out_of_sample_results']
)
metrics = report.generate_report()
report.print_report(metrics)

# 5. Parameter Sensitivity
param_analyzer = ParameterSensitivityAnalyzer(
    engine, strategy, data,
    parameters={'fast_period': [8, 10, 12, 14, 16]}
)
param_results = param_analyzer.analyze()

# 6. Monte Carlo Analysis
shuffle_mc = MonteCarloTradeShuffler(results, num_simulations=1000)
shuffle_results = shuffle_mc.run_simulations()

bootstrap_mc = MonteCarloEquityCurveResampler(results, num_simulations=1000)
bootstrap_results = bootstrap_mc.run_simulations()

# 7. Visualizations
MonteCarloVisualizer.plot_distribution(shuffle_results, 'plots/shuffle.png')
MonteCarloVisualizer.plot_distribution(bootstrap_results, 'plots/bootstrap.png')

# 8. Decision
if metrics.overfitting_score < 40 and shuffle_results.p_value < 0.05:
    print("✓ Strategy appears tradeable")
else:
    print("✗ Strategy has overfitting issues")
```

---

## Output Files

All analysis tools generate visualizations in the `plots/` subdirectory:

- `monte_carlo_trade_shuffle.png` - Distribution of shuffled trade results
- `monte_carlo_shuffle_cdf.png` - Cumulative distribution (CDF) of trade shuffles
- `monte_carlo_equity_bootstrap.png` - Distribution of bootstrapped equity returns
- `monte_carlo_qq_plot.png` - Q-Q plot testing for normal distribution
- `monte_carlo_summary.png` - Summary of all Monte Carlo methods

---

## Key Concepts & Metrics

### Walk-Forward Degradation
- **What**: Performance drop when testing on new data (out-of-sample)
- **Interpretation**: 
  - 0-10%: Excellent, very robust
  - 10-30%: Good, reasonably robust
  - 30-50%: Moderate, some overfitting
  - >50%: Poor, likely severely overfitted

### Coefficient of Variation (CV)
- **Formula**: Standard Deviation / Mean
- **Interpretation for parameter sensitivity**:
  - < 0.3: Very robust (parameters don't matter much)
  - 0.3-0.5: Reasonably robust
  - 0.5-1.0: Somewhat sensitive
  - > 1.0: Very sensitive (likely overfitted)

### P-Value
- **Definition**: Probability that observed result could occur by chance
- **Interpretation**:
  - p < 0.05: Result is statistically significant (unlikely by chance)
  - p < 0.10: Marginally significant
  - p >= 0.20: Not significant (likely due to chance)

### Percentiles in Monte Carlo
- **5th percentile**: Downside risk (worst 5% of outcomes)
- **25th percentile**: Lower bound of expected range
- **50th percentile**: Median (most likely outcome)
- **75th percentile**: Upper bound of expected range
- **95th percentile**: Upside potential (best 5% of outcomes)

---

## Common Pitfalls & Solutions

### Pitfall 1: Strategy works perfectly in-sample but fails out-of-sample
**Diagnosis**: High walk-forward degradation (>50%)
**Solutions**:
- Use larger dataset for optimization
- Reduce number of parameters
- Simplify indicator logic
- Use robust statistics (median instead of mean)
- Increase minimum sample requirements

### Pitfall 2: Strategy extremely sensitive to parameter values
**Diagnosis**: High coefficient of variation (>0.5) in parameter sensitivity
**Solutions**:
- Use wider optimization ranges
- Test on different market regimes
- Use ensemble of strategies with different parameters
- Focus on robust parameters, not optimal ones

### Pitfall 3: Monte Carlo shows strategy works on random prices
**Diagnosis**: High p-value in price shuffle test
**Solutions**:
- Strategy has no real edge
- Review signal generation logic
- Ensure indicators are calculated correctly
- Test on out-of-sample data

### Pitfall 4: Actual return is outlier in bootstrap distribution
**Diagnosis**: Actual return > 95th percentile in bootstrap
**Solutions**:
- May be lucky period, not skill
- Use more bootstrap simulations for robust confidence intervals
- Test on longer historical period
- Use conservative position sizing

---

## Performance Considerations

### Computational Cost:

| Method | Speed | Accuracy | Recommendation |
|--------|-------|----------|-----------------|
| Walk-Forward (5 periods) | Fast | High | Always use |
| Parameter Sensitivity | Fast | Medium | Always use |
| Trade Shuffle (1000 sims) | Very Fast | High | Always use |
| Price Shuffle (100 sims) | Slow | Very High | Use if time allows |
| Equity Bootstrap (1000 sims) | Very Fast | High | Always use |

### Tips for Speed:
- Use fewer walk-forward periods (3-5 instead of 10)
- Use fewer parameter sensitivity tests
- Use fewer Monte Carlo simulations (500-1000 instead of 5000)
- Use daily or weekly data instead of intraday for faster backtests

---

## References & Further Reading

1. **Walk-Forward Analysis**: De Prado, M. L. (2018). Advances in Financial Machine Learning
2. **Overfitting in Trading**: Poundstone, W. (2005). Fortune's Formula
3. **Monte Carlo Methods**: Glasserman, P. (2004). Monte Carlo Methods in Financial Engineering
4. **Parameter Optimization**: Bailey, D. H., et al. (2017). The Probability of Backtest Overfitting

---

## Support & Questions

For issues or questions:
1. Check the example_analysis.py script for usage patterns
2. Review the docstrings in each class/function
3. Consult the interpretation guides above
4. Test on known strategies first to understand the metrics

---

**Last Updated**: December 2024
**Version**: 1.0
