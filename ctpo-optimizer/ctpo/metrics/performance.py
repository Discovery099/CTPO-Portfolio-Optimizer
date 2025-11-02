"""
Portfolio performance metrics
"""

import numpy as np
import pandas as pd
from typing import Union, Optional, Dict, List
from scipy import stats


class PerformanceMetrics:
    """
    Calculate comprehensive portfolio performance metrics.
    """
    
    def __init__(self, risk_free_rate: float = 0.042):
        """
        Initialize performance metrics calculator.
        
        Args:
            risk_free_rate: Annual risk-free rate
        """
        self.rf = risk_free_rate / 252  # Daily risk-free rate
        self.rf_annual = risk_free_rate
    
    @staticmethod
    def sharpe_ratio(returns: Union[np.ndarray, pd.Series],
                     risk_free_rate: float = 0.02,
                     periods_per_year: int = 252) -> float:
        """
        Calculate Sharpe ratio.
        
        Args:
            returns: Portfolio returns
            risk_free_rate: Annual risk-free rate
            periods_per_year: Trading periods per year
            
        Returns:
            Sharpe ratio
        """
        if isinstance(returns, pd.Series):
            returns = returns.values
        
        excess_returns = returns - (risk_free_rate / periods_per_year)
        
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        
        sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(periods_per_year)
        
        return sharpe
    
    @staticmethod
    def max_drawdown(returns: Union[np.ndarray, pd.Series]) -> float:
        """
        Calculate maximum drawdown.
        
        Args:
            returns: Portfolio returns
            
        Returns:
            Maximum drawdown (positive number)
        """
        if isinstance(returns, pd.Series):
            returns = returns.values
        
        # Calculate cumulative returns
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        
        return abs(np.min(drawdown))
    
    @staticmethod
    def sortino_ratio(returns: Union[np.ndarray, pd.Series],
                      risk_free_rate: float = 0.02,
                      periods_per_year: int = 252) -> float:
        """
        Calculate Sortino ratio (downside deviation).
        
        Args:
            returns: Portfolio returns
            risk_free_rate: Annual risk-free rate
            periods_per_year: Trading periods per year
            
        Returns:
            Sortino ratio
        """
        if isinstance(returns, pd.Series):
            returns = returns.values
        
        excess_returns = returns - (risk_free_rate / periods_per_year)
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0:
            return np.inf
        
        downside_std = np.std(downside_returns)
        if downside_std == 0:
            return 0.0
        
        sortino = np.mean(excess_returns) / downside_std * np.sqrt(periods_per_year)
        
        return sortino
    
    @staticmethod
    def calmar_ratio(returns: Union[np.ndarray, pd.Series],
                     periods_per_year: int = 252) -> float:
        """
        Calculate Calmar ratio (return / max drawdown).
        
        Args:
            returns: Portfolio returns
            periods_per_year: Trading periods per year
            
        Returns:
            Calmar ratio
        """
        annual_return = PerformanceMetrics.annualized_return(returns, periods_per_year)
        max_dd = PerformanceMetrics.max_drawdown(returns)
        
        if max_dd == 0:
            return np.inf
        
        return annual_return / max_dd
    
    @staticmethod
    def annualized_return(returns: Union[np.ndarray, pd.Series],
                         periods_per_year: int = 252) -> float:
        """
        Calculate annualized return.
        
        Args:
            returns: Portfolio returns
            periods_per_year: Trading periods per year
            
        Returns:
            Annualized return
        """
        if isinstance(returns, pd.Series):
            returns = returns.values
        
        if len(returns) == 0:
            return 0.0
        
        total_return = np.prod(1 + returns) - 1
        n_periods = len(returns)
        annualized = (1 + total_return) ** (periods_per_year / n_periods) - 1
        
        return annualized
    
    @staticmethod
    def turnover(weights_history: np.ndarray) -> float:
        """
        Calculate portfolio turnover.
        
        Args:
            weights_history: Array of weights over time (T x N)
            
        Returns:
            Average turnover per period
        """
        if len(weights_history) < 2:
            return 0.0
        
        # Calculate weight changes
        weight_changes = np.abs(np.diff(weights_history, axis=0))
        turnover = np.sum(weight_changes, axis=1) / 2  # Divide by 2 (buy + sell)
        
        return np.mean(turnover)
    
    def calculate_all(self, 
                     returns: Union[np.ndarray, pd.Series],
                     weights_history: Optional[List[Dict]] = None,
                     trades: Optional[pd.DataFrame] = None) -> Dict:
        """
        Calculate complete metric suite.
        
        Args:
            returns: Portfolio returns
            weights_history: List of weight dictionaries over time
            trades: Trade log DataFrame
            
        Returns:
            Complete metrics dictionary
        """
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
        
        metrics = {}
        
        # === Return Metrics ===
        metrics['total_return'] = float(np.prod(1 + returns) - 1)
        metrics['annualized_return'] = self.annualized_return(returns)
        
        # === Risk Metrics ===
        metrics['volatility'] = float(returns.std() * np.sqrt(252))
        downside = returns[returns < 0]
        metrics['downside_deviation'] = float(downside.std() * np.sqrt(252) if len(downside) > 0 else 0)
        metrics['max_drawdown'] = self.max_drawdown(returns)
        metrics['var_95'] = float(np.percentile(returns, 5))
        metrics['cvar_95'] = float(returns[returns <= metrics['var_95']].mean())
        
        # === Risk-Adjusted Returns ===
        metrics['sharpe_ratio'] = self.sharpe_ratio(returns, self.rf_annual)
        metrics['sortino_ratio'] = self.sortino_ratio(returns, self.rf_annual)
        metrics['calmar_ratio'] = self.calmar_ratio(returns)
        
        # Omega ratio
        returns_above = returns[returns > 0]
        returns_below = -returns[returns < 0]
        metrics['omega_ratio'] = float(returns_above.sum() / returns_below.sum() if returns_below.sum() > 0 else np.inf)
        
        # === Distribution Metrics ===
        metrics['skewness'] = float(stats.skew(returns))
        metrics['kurtosis'] = float(stats.kurtosis(returns))
        p95 = np.percentile(returns, 95)
        p5 = np.percentile(returns, 5)
        metrics['tail_ratio'] = float(abs(p95 / p5) if p5 != 0 else np.inf)
        
        # === Portfolio Characteristics ===
        if weights_history:
            enps = [1.0 / np.sum(w['weights']**2) for w in weights_history if 'weights' in w]
            metrics['avg_effective_assets'] = float(np.mean(enps)) if enps else 0
            
            herfindahls = [np.sum(w['weights']**2) for w in weights_history if 'weights' in w]
            metrics['avg_concentration'] = float(np.mean(herfindahls)) if herfindahls else 0
        
        # === Stress Period Performance ===
        if len(returns) > 20:
            monthly_returns = returns.resample('M').apply(lambda x: np.prod(1 + x) - 1)
            metrics['worst_month'] = float(monthly_returns.min())
            metrics['best_month'] = float(monthly_returns.max())
        
        return metrics
    
    def print_report(self, metrics: Dict):
        """
        Pretty print metrics report.
        
        Args:
            metrics: Metrics dictionary
        """
        print("\n" + "="*70)
        print("📊 COMPREHENSIVE PERFORMANCE REPORT")
        print("="*70 + "\n")
        
        print("Return Metrics:")
        print(f"  Total Return:           {metrics['total_return']:>12.2%}")
        print(f"  Annualized Return:      {metrics['annualized_return']:>12.2%}")
        
        print("\nRisk Metrics:")
        print(f"  Volatility (Ann.):      {metrics['volatility']:>12.2%}")
        print(f"  Downside Deviation:     {metrics['downside_deviation']:>12.2%}")
        print(f"  Maximum Drawdown:       {metrics['max_drawdown']:>12.2%}")
        print(f"  VaR (95%):              {metrics['var_95']:>12.2%}")
        print(f"  CVaR (95%):             {metrics['cvar_95']:>12.2%}")
        
        print("\nRisk-Adjusted Returns:")
        print(f"  Sharpe Ratio:           {metrics['sharpe_ratio']:>12.3f}")
        print(f"  Sortino Ratio:          {metrics['sortino_ratio']:>12.3f}")
        print(f"  Calmar Ratio:           {metrics['calmar_ratio']:>12.3f}")
        print(f"  Omega Ratio:            {metrics['omega_ratio']:>12.3f}")
        
        print("\nDistribution:")
        print(f"  Skewness:               {metrics['skewness']:>12.3f}")
        print(f"  Excess Kurtosis:        {metrics['kurtosis']:>12.3f}")
        print(f"  Tail Ratio:             {metrics['tail_ratio']:>12.3f}")
        
        if 'avg_effective_assets' in metrics:
            print("\nPortfolio Characteristics:")
            print(f"  Avg Effective Assets:   {metrics['avg_effective_assets']:>12.1f}")
            print(f"  Avg Concentration:      {metrics['avg_concentration']:>12.3f}")
        
        if 'worst_month' in metrics:
            print("\nStress Period Performance:")
            print(f"  Worst Month:            {metrics['worst_month']:>12.2%}")
            print(f"  Best Month:             {metrics['best_month']:>12.2%}")
        
        print("\n" + "="*70 + "\n")
