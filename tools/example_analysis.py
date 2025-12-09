"""
Example: Complete Overfitting and Monte Carlo Analysis
=======================================================

This example script demonstrates how to use both the overfitting analyzer
and Monte Carlo tools to assess trading strategy robustness.

It shows:
1. Walk-Forward Analysis to detect overfitting
2. Parameter Sensitivity Analysis to test robustness
3. Monte Carlo Trade Shuffle to verify strategy edge
4. Monte Carlo Equity Bootstrap for confidence intervals
5. Visualization of all results

Usage:
------
1. Run your backtest first to get results
2. Analyze results using the tools in this script
3. Review plots and recommendations
4. Decide if strategy is tradeable based on analysis
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from backtest_engine import BacktestEngine
from example_strategy import SimpleMovingAverageStrategy
from data_fetcher import DataFetcher
from datetime import datetime, timedelta

# Import analysis tools
from tools.overfitting_analyzer import (
    WalkForwardAnalyzer,
    ParameterSensitivityAnalyzer,
    MetricsComparisonReport
)
from tools.monte_carlo_analyzer import (
    MonteCarloTradeShuffler,
    MonteCarloEquityCurveResampler,
    MonteCarloVisualizer,
    create_monte_carlo_summary_plot
)


def fetch_sample_data(symbol='BTC', days=365, interval='1d'):
    """
    Fetch sample data for analysis.
    
    Args:
        symbol: 'BTC' or 'EURUSD'
        days: Number of days to fetch
        interval: Data interval ('1m', '5m', '15m', '30m', '1h', '1d')
    
    Returns:
        DataFrame with OHLCV data
    """
    print(f"\nFetching {days} days of {interval} data for {symbol}...")
    
    if interval in ['1m', '5m', '15m', '30m', '1h']:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        data = DataFetcher.fetch_data_by_dates(
            symbol=symbol,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            interval=interval
        )
    else:
        data = DataFetcher.fetch_data(
            symbol=symbol,
            period=f'{days}d',
            interval=interval
        )
    
    return data


def run_complete_analysis():
    """
    Run complete overfitting and Monte Carlo analysis pipeline.
    """
    
    print("="*80)
    print("COMPLETE TRADING STRATEGY ANALYSIS")
    print("Overfitting Detection + Monte Carlo Robustness Testing")
    print("="*80)
    
    # ========================================================================
    # STEP 1: Fetch Data and Run Initial Backtest
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 1: DATA FETCHING & INITIAL BACKTEST")
    print("="*80)
    
    # Fetch data (using BTC daily data for speed, adjust as needed)
    data = fetch_sample_data(symbol='BTC', days=365, interval='1d')
    
    # Create strategy
    strategy = SimpleMovingAverageStrategy(fast_period=10, slow_period=30)
    
    # Run initial backtest
    engine = BacktestEngine(
        initial_capital=10000.0,
        commission=0.001,
        slippage=0.0005
    )
    
    engine.run_backtest(strategy, data)
    engine.print_performance()
    
    # Store results for analysis
    results = engine.get_results()
    
    # ========================================================================
    # STEP 2: Walk-Forward Analysis
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 2: WALK-FORWARD ANALYSIS (Overfitting Detection)")
    print("="*80)
    
    walk_forward = WalkForwardAnalyzer(
        engine=engine,
        strategy=strategy,
        data=data,
        num_periods=5  # Test 5 sequential periods
    )
    
    wf_results = walk_forward.analyze()
    
    # Generate metrics report
    metrics_report = MetricsComparisonReport(
        in_sample_metrics=wf_results['in_sample_results'],
        out_of_sample_metrics=wf_results['out_of_sample_results']
    )
    
    overfitting_metrics = metrics_report.generate_report()
    metrics_report.print_report(overfitting_metrics)
    
    # ========================================================================
    # STEP 3: Parameter Sensitivity Analysis
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 3: PARAMETER SENSITIVITY ANALYSIS (Robustness Testing)")
    print("="*80)
    
    # Test sensitivity to fast MA period
    param_analyzer = ParameterSensitivityAnalyzer(
        engine=engine,
        strategy=strategy,
        data=data,
        parameters={'fast_period': [8, 10, 12, 14, 16]}
    )
    
    param_results = param_analyzer.analyze()
    
    # ========================================================================
    # STEP 4: Monte Carlo Trade Shuffle Analysis
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 4: MONTE CARLO TRADE SHUFFLE (Verify Strategy Edge)")
    print("="*80)
    
    if results['trades']:
        shuffle_analyzer = MonteCarloTradeShuffler(
            backtest_results=results,
            num_simulations=1000
        )
        
        shuffle_results = shuffle_analyzer.run_simulations()
        
        # Visualize trade shuffle results
        MonteCarloVisualizer.plot_distribution(
            shuffle_results,
            save_path='tools/plots/monte_carlo_trade_shuffle.png'
        )
        
        MonteCarloVisualizer.plot_cumulative_distribution(
            shuffle_results,
            save_path='tools/plots/monte_carlo_shuffle_cdf.png'
        )
    
    # ========================================================================
    # STEP 5: Monte Carlo Equity Curve Bootstrap
    # ========================================================================
    print("\n" + "="*80)
    print("STEP 5: MONTE CARLO EQUITY BOOTSTRAP (Confidence Intervals)")
    print("="*80)
    
    if results['trades']:
        bootstrap_analyzer = MonteCarloEquityCurveResampler(
            backtest_results=results,
            initial_capital=engine.initial_capital,
            num_simulations=1000
        )
        
        bootstrap_results = bootstrap_analyzer.run_simulations()
        
        # Visualize bootstrap results
        MonteCarloVisualizer.plot_distribution(
            bootstrap_results,
            save_path='tools/plots/monte_carlo_equity_bootstrap.png'
        )
        
        MonteCarloVisualizer.plot_qq_plot(
            bootstrap_results,
            save_path='tools/plots/monte_carlo_qq_plot.png'
        )
    
    # ========================================================================
    # STEP 6: Comprehensive Summary
    # ========================================================================
    print("\n" + "="*80)
    print("FINAL ANALYSIS SUMMARY")
    print("="*80)
    
    summary_dict = {}
    if results['trades']:
        summary_dict['Trade Shuffle'] = shuffle_results
        summary_dict['Equity Bootstrap'] = bootstrap_results
    
    if summary_dict:
        create_monte_carlo_summary_plot(
            summary_dict,
            save_path='tools/plots/monte_carlo_summary.png'
        )
    
    # ========================================================================
    # Final Recommendations
    # ========================================================================
    print("\n" + "="*80)
    print("FINAL RECOMMENDATIONS")
    print("="*80)
    
    print("\n📊 OVERFITTING ASSESSMENT:")
    print(f"   Risk Level: {overfitting_metrics.overfitting_risk_level}")
    print(f"   Overfitting Score: {overfitting_metrics.overfitting_score:.1f}/100")
    print(f"   Walk-Forward Degradation: {overfitting_metrics.sharpe_ratio_degradation:.1f}%")
    
    print("\n📈 STRATEGY ROBUSTNESS:")
    if param_results and 'stability_metrics' in param_results:
        sm = param_results['stability_metrics']
        print(f"   Sharpe Ratio CV: {sm['sharpe_cv']:.4f} {'✓ ROBUST' if sm['sharpe_cv'] < 0.5 else '✗ SENSITIVE'}")
        print(f"   Return CV: {sm['return_cv']:.4f} {'✓ ROBUST' if sm['return_cv'] < 0.5 else '✗ SENSITIVE'}")
    
    print("\n🎲 MONTE CARLO ASSESSMENT:")
    if results['trades']:
        print(f"   Trade Shuffle P-Value: {shuffle_results.p_value:.4f}")
        if shuffle_results.p_value < 0.05:
            print(f"   → Strategy has statistically significant edge (p < 0.05) ✓")
        else:
            print(f"   → Strategy may be due to luck (p >= 0.05) ✗")
        
        print(f"\n   Equity Bootstrap 5-95% Range: {bootstrap_results.percentile_5:.1f}% to {bootstrap_results.percentile_95:.1f}%")
        actual_return = ((engine.initial_capital + sum([t.pnl for t in results['trades'] if t.pnl])) 
                        - engine.initial_capital) / engine.initial_capital * 100
        if bootstrap_results.percentile_5 < actual_return < bootstrap_results.percentile_95:
            print(f"   → Actual return ({actual_return:.1f}%) within expected range ✓")
        else:
            print(f"   → Actual return ({actual_return:.1f}%) is outlier ⚠️")
    
    print("\n📋 ACTIONABLE RECOMMENDATIONS:")
    for rec in overfitting_metrics.recommendations:
        print(f"   {rec}")
    
    print("\n" + "="*80)
    print("Analysis complete! Check tools/plots/ for visualizations.")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        run_complete_analysis()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
