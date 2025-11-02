"""
Objective function module for CTPO optimization
"""

import numpy as np
from typing import Optional


class ObjectiveFunction:
    """
    CTPO objective function: VaR minimization + regularization.
    """
    
    def __init__(self, var_confidence: float = 0.95, lambda_reg: float = 0.01):
        """
        Initialize objective function.
        
        Args:
            var_confidence: VaR confidence level
            lambda_reg: Regularization parameter
        """
        self.var_confidence = var_confidence
        self.lambda_reg = lambda_reg
    
    def compute_var(self, 
                    weights: np.ndarray, 
                    returns: np.ndarray,
                    covariance: Optional[np.ndarray] = None) -> float:
        """
        Compute portfolio Value at Risk.
        
        Args:
            weights: Portfolio weights
            returns: Historical returns
            covariance: Covariance matrix (computed if None)
            
        Returns:
            Portfolio VaR
        """
        # TODO: Implement parametric VaR in later chunks
        if covariance is None:
            covariance = np.cov(returns.T)
        
        portfolio_std = np.sqrt(weights.T @ covariance @ weights)
        # Simplified VaR for skeleton
        var = 1.645 * portfolio_std  # 95% confidence
        
        return var
    
    def regularization_term(self, weights: np.ndarray) -> float:
        """
        Regularization term to prevent extreme positions.
        
        Args:
            weights: Portfolio weights
            
        Returns:
            Regularization penalty
        """
        # TODO: Add proper regularization in later chunks
        # L2 regularization for now
        return self.lambda_reg * np.sum(weights ** 2)
    
    def evaluate(self, 
                 weights: np.ndarray,
                 returns: np.ndarray,
                 covariance: Optional[np.ndarray] = None) -> float:
        """
        Evaluate total objective function.
        
        Args:
            weights: Portfolio weights
            returns: Historical returns
            covariance: Covariance matrix
            
        Returns:
            Objective value (to minimize)
        """
        var = self.compute_var(weights, returns, covariance)
        reg = self.regularization_term(weights)
        
        return var + reg
