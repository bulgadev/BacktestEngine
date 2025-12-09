"""
Overfitting Analyzer Tool
=========================

This module provides comprehensive tools to detect overfitting in trading strategies.
It uses multiple statistical and empirical methods including:
- Walk-Forward Analysis: Tests strategy on unseen data periods
- Parameter Sensitivity Analysis: Checks if strategy is robust to parameter changes
- Out-of-Sample Testing: Compares in-sample vs out-of-sample performance
- Metrics Degradation Analysis: Quantifies performance drop on unseen data

The analyzer generates a composite "Overfitting Score" (0-100) that combines
all detection methods to give a single assessment of overfitting risk.

Interpretation Guide:
- 0-30: Strategy appears robust (low overfitting risk)
- 30-60: Moderate overfitting risk, investigate parameter sensitivity
- 60-80: High overfitting risk, strategy likely curve-fitted
- 80-100: Severe overfitting, strategy not tradeable
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Any, Optional
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')


@dataclass
class OverfittingMetrics:
    """
    Container for all overfitting-related metrics.
    
    Attributes:
        walk_forward_degradation: % performance drop in out-of-sample data
        parameter_sensitivity_score: 0-100 score, lower = more robust
        in_sample_sharpe: Sharpe ratio on training data
        out_of_sample_sharpe: Sharpe ratio on test data
        sharpe_ratio_degradation: % drop in Sharpe ratio
        in_sample_win_rate: Win rate on training data
        out_of_sample_win_rate: Win rate on test data
        in_sample_profit_factor: Profit factor on training data
        out_of_sample_profit_factor: Profit factor on test data
        overfitting_score: 0-100 composite score (higher = more overfitted)
        overfitting_risk_level: 'LOW', 'MODERATE', 'HIGH', or 'SEVERE'
        recommendations: List of actionable improvement suggestions
    """
    walk_forward_degradation: float = 0.0
    parameter_sensitivity_score: float = 0.0
    in_sample_sharpe: float = 0.0
    out_of_sample_sharpe: float = 0.0
    sharpe_ratio_degradation: float = 0.0
    in_sample_win_rate: float = 0.0
    out_of_sample_win_rate: float = 0.0
    in_sample_profit_factor: float = 0.0
    out_of_sample_profit_factor: float = 0.0
    overfitting_score: float = 0.0
    overfitting_risk_level: str = 'UNKNOWN'
    recommendations: List[str] = None


class WalkForwardAnalyzer:
    """
    Implements Walk-Forward Analysis to detect overfitting.
    
    This method divides the data into multiple sequential windows:
    1. Training period: Strategy is backtested on this data
    2. Testing period: Strategy is backtested on completely new data
    3. Repeat with rolling windows
    
    If strategy is overfitted, performance will degrade significantly on
    out-of-sample (test) data. A robust strategy shows similar performance
    on both training and testing periods.
    
    This is the gold standard for overfitting detection in professional trading.
    """
    
    def __init__(self, engine, strategy, data: pd.DataFrame, num_periods: int = 5):
        """
        Initialize Walk-Forward Analyzer.
        
        Args:
            engine: BacktestEngine instance
            strategy: BaseStrategy instance (will be reused for each period)
            data: Full historical DataFrame with OHLCV data
            num_periods: Number of walk-forward periods to test (default 5)
        """
        self.engine = engine
        self.strategy = strategy
        self.data = data
        self.num_periods = num_periods
        
        self.in_sample_metrics = []
        self.out_of_sample_metrics = []
        self.degradation_ratios = []
    
    def analyze(self) -> Dict[str, Any]:
        """
        Run walk-forward analysis across all periods.
        
        Returns:
            Dictionary containing:
            - in_sample_results: List of metrics from training periods
            - out_of_sample_results: List of metrics from test periods
            - degradation_ratios: List of performance degradation % for each period
            - average_degradation: Average degradation across all periods
            - worst_degradation: Worst case degradation
        """
        total_bars = len(self.data)
        # Split data: 70% training, 30% testing per window
        split_point = int(total_bars / (self.num_periods + 1))
        
        print(f"\n{'='*70}")
        print(f"WALK-FORWARD ANALYSIS ({self.num_periods} periods)")
        print(f"{'='*70}")
        
        for period in range(self.num_periods):
            print(f"\nPeriod {period + 1}/{self.num_periods}:")
            print("-" * 70)
            
            # Define training window: expand from beginning
            train_end_idx = split_point * (period + 1)
            train_data = self.data.iloc[:train_end_idx]
            
            # Define testing window: next period
            test_start_idx = train_end_idx
            test_end_idx = min(train_end_idx + split_point, total_bars)
            test_data = self.data.iloc[test_start_idx:test_end_idx]
            
            print(f"  Training:   {train_data.index[0].date()} to {train_data.index[-1].date()} ({len(train_data)} bars)")
            print(f"  Testing:    {test_data.index[0].date()} to {test_data.index[-1].date()} ({len(test_data)} bars)")
            
            if len(train_data) < 50 or len(test_data) < 20:
                print(f"  ⚠️  Insufficient data for period {period + 1}, skipping...")
                continue
            
            # Run backtest on training data
            from backtest_engine import BacktestEngine
            train_engine = BacktestEngine(
                initial_capital=self.engine.initial_capital,
                commission=self.engine.commission,
                slippage=self.engine.slippage,
                periods_per_year=self.engine.periods_per_year
            )
            
            # Reset strategy state
            self.strategy.initialized = False
            train_engine.run_backtest(self.strategy, train_data)
            in_sample_result = train_engine.get_results()
            
            # Run backtest on test data (on same strategy state)
            test_engine = BacktestEngine(
                initial_capital=self.engine.initial_capital,
                commission=self.engine.commission,
                slippage=self.engine.slippage,
                periods_per_year=self.engine.periods_per_year
            )
            
            # Reinitialize strategy for test period
            self.strategy.initialized = False
            test_engine.run_backtest(self.strategy, test_data)
            out_of_sample_result = test_engine.get_results()
            
            # Extract metrics
            in_sample_metrics = in_sample_result['metrics']
            out_of_sample_metrics = out_of_sample_result['metrics']
            
            self.in_sample_metrics.append(in_sample_metrics)
            self.out_of_sample_metrics.append(out_of_sample_metrics)
            
            # Calculate degradation ratio
            # Use Sharpe ratio as primary metric (risk-adjusted return)
            if in_sample_metrics.sharpe_ratio > 0.1:
                degradation = ((in_sample_metrics.sharpe_ratio - out_of_sample_metrics.sharpe_ratio) 
                              / in_sample_metrics.sharpe_ratio * 100)
            else:
                degradation = 0
            
            self.degradation_ratios.append(degradation)
            
            print(f"  In-Sample Sharpe:     {in_sample_metrics.sharpe_ratio:.4f}")
            print(f"  Out-of-Sample Sharpe: {out_of_sample_metrics.sharpe_ratio:.4f}")
            print(f"  Degradation:          {degradation:.2f}%")
        
        # Calculate summary statistics
        avg_degradation = np.mean(self.degradation_ratios) if self.degradation_ratios else 0
        worst_degradation = np.max(self.degradation_ratios) if self.degradation_ratios else 0
        best_degradation = np.min(self.degradation_ratios) if self.degradation_ratios else 0
        
        print(f"\n{'='*70}")
        print(f"WALK-FORWARD SUMMARY")
        print(f"{'='*70}")
        print(f"Average Degradation:  {avg_degradation:.2f}%")
        print(f"Best Degradation:     {best_degradation:.2f}%")
        print(f"Worst Degradation:    {worst_degradation:.2f}%")
        print(f"{'='*70}\n")
        
        return {
            'in_sample_results': self.in_sample_metrics,
            'out_of_sample_results': self.out_of_sample_metrics,
            'degradation_ratios': self.degradation_ratios,
            'average_degradation': avg_degradation,
            'worst_degradation': worst_degradation,
            'best_degradation': best_degradation
        }


class ParameterSensitivityAnalyzer:
    """
    Analyzes strategy robustness to parameter changes.
    
    A robust strategy should maintain consistent performance across small
    parameter variations. If performance "cliffs" (drops sharply) with small
    parameter changes, this is a strong indicator of overfitting.
    
    Example: If MA period 20 gives +50% return but MA period 21 gives -10%,
    the strategy is likely curve-fitted to the specific parameter value.
    """
    
    def __init__(self, engine, strategy, data: pd.DataFrame, parameters: Dict[str, List[float]]):
        """
        Initialize Parameter Sensitivity Analyzer.
        
        Args:
            engine: BacktestEngine instance
            strategy: BaseStrategy instance (must have parameter-based constructor)
            data: Full historical DataFrame with OHLCV data
            parameters: Dict of {param_name: [list of values to test]}
                       Example: {'fast_period': [8, 10, 12, 14, 16],
                                'slow_period': [25, 30, 35, 40, 45]}
        """
        self.engine = engine
        self.strategy = strategy
        self.data = data
        self.parameters = parameters
        self.results = {}
    
    def analyze(self) -> Dict[str, Any]:
        """
        Run sensitivity analysis by testing different parameter values.
        
        Returns:
            Dictionary with performance metrics for each parameter combination
        """
        print(f"\n{'='*70}")
        print(f"PARAMETER SENSITIVITY ANALYSIS")
        print(f"{'='*70}")
        
        # For single parameter sensitivity
        if len(self.parameters) == 1:
            param_name = list(self.parameters.keys())[0]
            param_values = self.parameters[param_name]
            
            results = {}
            
            print(f"\nAnalyzing sensitivity to: {param_name}")
            print(f"Values to test: {param_values}\n")
            
            for value in param_values:
                # Create new strategy instance with specific parameter
                strategy_class = self.strategy.__class__
                # Get the strategy's init signature to pass parameter
                test_strategy = self._create_strategy_with_params({param_name: value})
                
                if test_strategy is None:
                    print(f"  {param_name}={value}: ⚠️  Could not create strategy")
                    continue
                
                from backtest_engine import BacktestEngine
                test_engine = BacktestEngine(
                    initial_capital=self.engine.initial_capital,
                    commission=self.engine.commission,
                    slippage=self.engine.slippage,
                    periods_per_year=self.engine.periods_per_year
                )
                
                test_engine.run_backtest(test_strategy, self.data)
                result = test_engine.get_results()
                metrics = result['metrics']
                
                results[value] = {
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'total_return': metrics.total_pnl_pct,
                    'win_rate': metrics.win_rate,
                    'profit_factor': metrics.profit_factor,
                    'max_drawdown': metrics.max_drawdown
                }
                
                print(f"  {param_name}={value:>8}: Sharpe={metrics.sharpe_ratio:>8.4f}, Return={metrics.total_pnl_pct:>8.2f}%, WinRate={metrics.win_rate:>6.1f}%")
            
            self.results[param_name] = results
            
            # Calculate stability metrics
            stability_metrics = self._calculate_stability(results)
            
            print(f"\n{'-'*70}")
            print(f"STABILITY ANALYSIS FOR {param_name}:")
            print(f"{'-'*70}")
            print(f"Sharpe Ratio - Mean:  {stability_metrics['sharpe_mean']:.4f}")
            print(f"Sharpe Ratio - Std:   {stability_metrics['sharpe_std']:.4f}")
            print(f"Sharpe Ratio - Coeff: {stability_metrics['sharpe_cv']:.4f}  {'✓ ROBUST' if stability_metrics['sharpe_cv'] < 0.5 else '✗ SENSITIVE'}")
            print(f"\nReturn % - Mean:      {stability_metrics['return_mean']:.2f}%")
            print(f"Return % - Std:       {stability_metrics['return_std']:.2f}%")
            print(f"Return % - Coeff:     {stability_metrics['return_cv']:.4f}  {'✓ ROBUST' if stability_metrics['return_cv'] < 0.5 else '✗ SENSITIVE'}")
            
            return {
                'parameter': param_name,
                'results': results,
                'stability_metrics': stability_metrics
            }
        
        return {'error': 'Multi-parameter analysis not yet implemented'}
    
    def _create_strategy_with_params(self, params: Dict[str, Any]):
        """
        Helper method to create strategy instance with specific parameters.
        
        This is a generic implementation that works with the example strategies.
        May need customization for other strategy types.
        """
        try:
            strategy_class = self.strategy.__class__
            # Try to create with all parameters
            return strategy_class(**params)
        except Exception as e:
            print(f"    Error creating strategy: {e}")
            return None
    
    def _calculate_stability(self, results: Dict[float, Dict[str, float]]) -> Dict[str, float]:
        """
        Calculate coefficient of variation (CV) for robustness assessment.
        
        CV = Standard Deviation / Mean
        Lower CV = more robust (performance doesn't vary much with parameter changes)
        Higher CV = less robust (overfitted to specific parameter value)
        
        Interpretation:
        - CV < 0.3: Very robust
        - CV 0.3-0.5: Reasonably robust
        - CV 0.5-1.0: Somewhat sensitive
        - CV > 1.0: Very sensitive (likely overfitted)
        """
        sharpe_ratios = [r['sharpe_ratio'] for r in results.values()]
        returns = [r['total_return'] for r in results.values()]
        
        sharpe_mean = np.mean(sharpe_ratios)
        sharpe_std = np.std(sharpe_ratios)
        sharpe_cv = sharpe_std / abs(sharpe_mean) if sharpe_mean != 0 else 0
        
        return_mean = np.mean(returns)
        return_std = np.std(returns)
        return_cv = return_std / abs(return_mean) if return_mean != 0 else 0
        
        return {
            'sharpe_mean': sharpe_mean,
            'sharpe_std': sharpe_std,
            'sharpe_cv': sharpe_cv,
            'return_mean': return_mean,
            'return_std': return_std,
            'return_cv': return_cv
        }


class MetricsComparisonReport:
    """
    Generates comprehensive report comparing in-sample vs out-of-sample metrics.
    
    This helps identify specific areas where strategy degrades on new data.
    """
    
    def __init__(self, in_sample_metrics, out_of_sample_metrics):
        """
        Initialize with metrics from walk-forward analysis.
        
        Args:
            in_sample_metrics: List of PerformanceMetrics objects from training
            out_of_sample_metrics: List of PerformanceMetrics objects from testing
        """
        self.in_sample = in_sample_metrics
        self.out_of_sample = out_of_sample_metrics
    
    def generate_report(self) -> OverfittingMetrics:
        """
        Generate comprehensive overfitting metrics report.
        
        Returns:
            OverfittingMetrics object with all relevant metrics and recommendations
        """
        if not self.in_sample or not self.out_of_sample:
            return OverfittingMetrics()
        
        # Average metrics across all periods
        avg_in_sample_sharpe = np.mean([m.sharpe_ratio for m in self.in_sample])
        avg_out_of_sample_sharpe = np.mean([m.sharpe_ratio for m in self.out_of_sample])
        
        avg_in_sample_win_rate = np.mean([m.win_rate for m in self.in_sample])
        avg_out_of_sample_win_rate = np.mean([m.win_rate for m in self.out_of_sample])
        
        avg_in_sample_pf = np.mean([m.profit_factor for m in self.in_sample if m.profit_factor > 0])
        avg_out_of_sample_pf = np.mean([m.profit_factor for m in self.out_of_sample if m.profit_factor > 0])
        
        # Calculate degradation
        sharpe_degradation = ((avg_in_sample_sharpe - avg_out_of_sample_sharpe) / 
                             (abs(avg_in_sample_sharpe) + 1e-6) * 100)
        
        win_rate_degradation = avg_in_sample_win_rate - avg_out_of_sample_win_rate
        
        pf_degradation = ((avg_in_sample_pf - avg_out_of_sample_pf) / 
                         (abs(avg_in_sample_pf) + 1e-6) * 100)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            sharpe_degradation, win_rate_degradation, avg_out_of_sample_sharpe
        )
        
        # Calculate composite overfitting score
        overfitting_score = self._calculate_overfitting_score(
            sharpe_degradation, win_rate_degradation, pf_degradation
        )
        
        risk_level = self._get_risk_level(overfitting_score)
        
        metrics = OverfittingMetrics(
            walk_forward_degradation=sharpe_degradation,
            in_sample_sharpe=avg_in_sample_sharpe,
            out_of_sample_sharpe=avg_out_of_sample_sharpe,
            sharpe_ratio_degradation=sharpe_degradation,
            in_sample_win_rate=avg_in_sample_win_rate,
            out_of_sample_win_rate=avg_out_of_sample_win_rate,
            in_sample_profit_factor=avg_in_sample_pf,
            out_of_sample_profit_factor=avg_out_of_sample_pf,
            overfitting_score=overfitting_score,
            overfitting_risk_level=risk_level,
            recommendations=recommendations
        )
        
        return metrics
    
    def _calculate_overfitting_score(self, sharpe_deg: float, win_rate_deg: float, 
                                     pf_deg: float) -> float:
        """
        Calculate composite overfitting score (0-100).
        
        Combines multiple degradation metrics with weights:
        - Sharpe ratio degradation: 50% weight (most important - risk-adjusted return)
        - Win rate degradation: 30% weight (trade success rate)
        - Profit factor degradation: 20% weight (gross profit/loss ratio)
        
        Thresholds:
        - Each metric clipped to max 100% degradation
        - Weighted average gives final score
        """
        # Clip degradation values to 0-100 range
        sharpe_score = min(abs(sharpe_deg), 100)
        win_rate_score = min(abs(win_rate_deg), 100)
        pf_score = min(abs(pf_deg), 100)
        
        # Weighted combination
        composite_score = (sharpe_score * 0.5 + win_rate_score * 0.3 + pf_score * 0.2)
        
        return min(composite_score, 100)
    
    def _generate_recommendations(self, sharpe_deg: float, win_rate_deg: float, 
                                  out_of_sample_sharpe: float) -> List[str]:
        """
        Generate actionable recommendations based on degradation analysis.
        """
        recommendations = []
        
        if sharpe_deg > 50:
            recommendations.append(
                "⚠️  SEVERE: Sharpe ratio drops >50% on out-of-sample data. Strategy is likely overfitted."
            )
            recommendations.append(
                "   → Simplify strategy logic, reduce indicator count, increase data amount"
            )
        elif sharpe_deg > 30:
            recommendations.append(
                "⚠️  HIGH: Sharpe ratio drops 30-50% on out-of-sample data. Significant overfitting detected."
            )
            recommendations.append(
                "   → Review parameter optimization range, consider wider parameter ranges"
            )
        elif sharpe_deg > 10:
            recommendations.append(
                "⚠️  MODERATE: Sharpe ratio drops 10-30% on out-of-sample data. Some overfitting likely."
            )
            recommendations.append(
                "   → Use walk-forward optimization instead of static parameters"
            )
        else:
            recommendations.append(
                "✓  LOW: Sharpe ratio stable across samples. Strategy appears robust."
            )
        
        if win_rate_deg > 20:
            recommendations.append(
                "   → Win rate drops significantly on new data. Review entry signal quality."
            )
        
        if out_of_sample_sharpe < 0.5:
            recommendations.append(
                "   → Out-of-sample Sharpe < 0.5. Consider if strategy is tradeable."
            )
        
        return recommendations
    
    def _get_risk_level(self, score: float) -> str:
        """
        Map overfitting score to risk level.
        
        Thresholds:
        - 0-30: LOW (robust strategy)
        - 30-60: MODERATE (some concern)
        - 60-80: HIGH (significant overfitting)
        - 80-100: SEVERE (not tradeable)
        """
        if score < 30:
            return 'LOW'
        elif score < 60:
            return 'MODERATE'
        elif score < 80:
            return 'HIGH'
        else:
            return 'SEVERE'
    
    def print_report(self, metrics: OverfittingMetrics) -> None:
        """Print comprehensive overfitting analysis report."""
        print(f"\n{'='*70}")
        print(f"OVERFITTING ANALYSIS REPORT")
        print(f"{'='*70}")
        
        print(f"\nRISK ASSESSMENT: {metrics.overfitting_risk_level}")
        print(f"Overfitting Score: {metrics.overfitting_score:.1f}/100")
        
        print(f"\n{'-'*70}")
        print(f"PERFORMANCE COMPARISON")
        print(f"{'-'*70}")
        print(f"                          In-Sample    Out-of-Sample    Degradation")
        print(f"Sharpe Ratio:             {metrics.in_sample_sharpe:>8.4f}         {metrics.out_of_sample_sharpe:>8.4f}         {metrics.sharpe_ratio_degradation:>7.1f}%")
        print(f"Win Rate:                 {metrics.in_sample_win_rate:>8.1f}%        {metrics.out_of_sample_win_rate:>8.1f}%        {metrics.in_sample_win_rate - metrics.out_of_sample_win_rate:>7.1f}%")
        print(f"Profit Factor:            {metrics.in_sample_profit_factor:>8.2f}         {metrics.out_of_sample_profit_factor:>8.2f}         {(metrics.in_sample_profit_factor - metrics.out_of_sample_profit_factor):>7.2f}")
        
        print(f"\n{'-'*70}")
        print(f"RECOMMENDATIONS")
        print(f"{'-'*70}")
        for rec in metrics.recommendations:
            print(rec)
        
        print(f"\n{'='*70}\n")
