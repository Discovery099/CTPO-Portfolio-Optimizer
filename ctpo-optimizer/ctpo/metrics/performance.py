"""
Portfolio performance metrics
"""

import numpy as np
import pandas as pd
from typing import Union, Optional


class PerformanceMetrics:
    """
    Calculate portfolio performance metrics.
    """
    
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
