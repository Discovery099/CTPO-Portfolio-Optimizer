"""
Objective function module for CTPO optimization
"""

import numpy as np
import cvxpy as cp
from typing import Optional, Dict


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
        # L2 regularization
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


def build_objective(w: cp.Variable, 
                   w_prev: np.ndarray,
                   mu: np.ndarray, 
                   Sigma: np.ndarray,
                   alpha_stress: float,
                   params: Dict,
                   A: np.ndarray = None,
                   W: np.ndarray = None) -> cp.Minimize:
    """
    Build CVXPY objective function - PURE MEAN-VARIANCE OPTIMIZATION
    
    ALL CDPR CODE REMOVED. This is now standard portfolio optimization.
    
    Minimize:
    J(w) = risk_weight × ½ w^T Σ w - lambda_return × w^T μ + lambda_tc × ||Δw||_1
    
    Where:
    - First term: Portfolio variance (risk)
    - Second term: Negative expected return (maximize return)
    - Third term: Transaction cost penalty
    
    Args:
        w: Portfolio weight variable (CVXPY)
        w_prev: Previous weights (for transaction costs)
        mu: Expected returns vector (N,)
        Sigma: Covariance matrix (N x N)
        alpha_stress: Stress activation level [0, 1] - NOT USED
        params: Parameter dictionary
        A: Structure matrix - NOT USED (CDPR removed)
        W: Wrench vector - NOT USED (CDPR removed)
        
    Returns:
        CVXPY Minimize objective
    """
    lambda_tc = params.get('transaction_cost_limit', 0.005)
    lambda_return = 25.0  # Strong return focus
    risk_weight = 0.05  # Very low risk aversion
    
    # Risk term (very low weight)
    risk_term = risk_weight * cp.quad_form(w, Sigma)
    
    # Return term (maximize - negative in minimization)
    return_term = -lambda_return * (mu @ w)
    
    # Transaction cost penalty
    Delta_w = w - w_prev
    tc_penalty = lambda_tc * cp.norm(Delta_w, 1)
    
    # Combined objective (ALL CDPR REMOVED)
    objective = risk_term + return_term + tc_penalty
    
    return cp.Minimize(objective)
