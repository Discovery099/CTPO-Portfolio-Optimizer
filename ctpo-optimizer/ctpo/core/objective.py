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
                   params: Dict) -> cp.Minimize:
    """
    Build CVXPY objective function for CTPO.
    
    Minimize:
    J(w) = ½ w^T Σ w + γ × α(t) × D(w) + λ_tc × ||Δw||_1 - λ × w^T μ
    
    Where:
    - First term: Portfolio variance (risk)
    - Second term: Stress-activated diversification penalty
    - Third term: Transaction cost penalty
    - Fourth term: Negative expected return (maximize)
    
    Args:
        w: Portfolio weight variable (CVXPY)
        w_prev: Previous weights (for transaction costs)
        mu: Expected returns vector (N,)
        Sigma: Covariance matrix (N x N)
        alpha_stress: Stress activation level [0, 1]
        params: Parameter dictionary
        
    Returns:
        CVXPY Minimize objective
    """
    gamma = params.get('tension_regularization', 0.0075)
    lambda_tc = params.get('transaction_cost_limit', 0.005)
    lambda_return = 1.0  # Weight for return term
    mu_d = params.get('diversification_gain', 0.24)
    
    n = len(mu)
    w0 = np.ones(n) / n  # Equal-weight baseline
    
    # Risk term (always active)
    risk_term = 0.5 * cp.quad_form(w, Sigma)
    
    # Return term (maximize, so negative in minimization)
    return_term = -lambda_return * (mu @ w)
    
    # Diversification penalty (activates during stress)
    # D(w) = ||w - w_0||² - μ_d (penalize deviation from equal-weight)
    if alpha_stress > 0.01:  # Only add if in stress regime
        div_penalty = gamma * alpha_stress * (cp.sum_squares(w - w0) - mu_d)
    else:
        div_penalty = 0
    
    # Transaction cost penalty
    Delta_w = w - w_prev
    tc_penalty = lambda_tc * cp.norm(Delta_w, 1)
    
    # Combined objective
    objective = risk_term + return_term + div_penalty + tc_penalty
    
    return cp.Minimize(objective)
