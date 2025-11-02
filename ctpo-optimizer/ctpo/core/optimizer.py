"""
Pure Mean-Variance Portfolio Optimizer

Simple, clean implementation using CVXPY for portfolio optimization.
All CDPR code removed - standard Markowitz mean-variance optimization.
"""

import numpy as np
import cvxpy as cp
from typing import Dict, Optional
import time


# Default parameters
DEFAULT_PARAMS = {
    'risk_free_rate': 0.042,
    'transaction_cost_limit': 0.005,
    'position_max': 0.20,  # Default 20% - user configurable via frontend
    'position_min': 0.0,   # Long-only
    'max_iterations': 200,
    'ftol': 1e-6,
    'solver': 'CLARABEL',
    'lambda_return': 25.0,  # Return focus weight
    'risk_weight': 0.05     # Risk aversion (lower = less risk-averse)
}


class PortfolioOptimizer:
    """
    Mean-Variance Portfolio Optimizer
    
    Optimizes portfolio weights to maximize risk-adjusted returns
    using convex optimization.
    """
    
    def __init__(self, params: Dict = None):
        """
        Initialize optimizer with optional parameter overrides.
        
        Args:
            params: Optional dictionary to override default parameters
                   Keys can include: position_max, lambda_return, risk_weight, etc.
        """
        self.params = {**DEFAULT_PARAMS, **(params or {})}
        self.w_current = None
        self.last_solve_time = None
        self.last_status = None
    
    def optimize(self, 
                 returns: np.ndarray,
                 position_max: Optional[float] = None) -> np.ndarray:
        """
        Optimize portfolio weights.
        
        Args:
            returns: Historical returns matrix (T x N) where T = time periods, N = assets
            position_max: Optional position limit override (e.g., from frontend slider)
        
        Returns:
            Optimal portfolio weights (N,) summing to 1.0
        """
        start_time = time.perf_counter()
        
        n_assets = returns.shape[1]
        
        # Initialize current weights if first run
        if self.w_current is None or len(self.w_current) != n_assets:
            self.w_current = np.ones(n_assets) / n_assets
        
        # Compute expected returns and covariance
        mu = returns.mean(axis=0)
        Sigma = np.cov(returns.T)
        
        # Ensure covariance is positive definite
        min_eig = np.min(np.real(np.linalg.eigvals(Sigma)))
        if min_eig < 1e-8:
            Sigma += np.eye(n_assets) * (1e-8 - min_eig)
        
        # Use position_max from parameter or override
        pos_max = position_max if position_max is not None else self.params['position_max']
        
        # Ensure position_max is feasible (at least enough to sum to 1)
        pos_max = max(pos_max, 1.0 / n_assets * 1.2)
        
        # Get other parameters
        lambda_return = self.params['lambda_return']
        risk_weight = self.params['risk_weight']
        lambda_tc = self.params['transaction_cost_limit']
        
        # Define optimization variable
        w = cp.Variable(n_assets)
        
        # Build objective: minimize risk, maximize return, penalize turnover
        risk_term = risk_weight * cp.quad_form(w, Sigma)
        return_term = -lambda_return * (mu @ w)
        transaction_cost = lambda_tc * cp.norm(w - self.w_current, 1)
        
        objective = cp.Minimize(risk_term + return_term + transaction_cost)
        
        # Build constraints
        constraints = [
            cp.sum(w) == 1,      # Fully invested
            w >= 0,              # Long-only (no shorting)
            w <= pos_max         # Position limits
        ]
        
        # Solve
        problem = cp.Problem(objective, constraints)
        
        try:
            print(f"\n🔧 Optimizing {n_assets} assets (position_max={pos_max:.1%})...")
            
            problem.solve(
                solver=cp.CLARABEL,
                verbose=True,
                max_iter=self.params['max_iterations'],
                tol_feas=self.params['ftol'],
                tol_gap_abs=self.params['ftol'],
                tol_gap_rel=self.params['ftol']
            )
            
            if problem.status not in ['optimal', 'optimal_inaccurate']:
                print(f"⚠️  Solver status: {problem.status}. Using equal weights.")
                weights = np.ones(n_assets) / n_assets
                self.last_status = 'fallback'
            else:
                weights = w.value
                if weights is None:
                    print(f"⚠️  Solver returned None. Using equal weights.")
                    weights = np.ones(n_assets) / n_assets
                    self.last_status = 'fallback'
                else:
                    # Normalize to ensure sum = 1
                    weights = weights / np.sum(weights)
                    self.last_status = 'optimal'
                    
                    print(f"✅ Optimization successful!")
                    print(f"   Weight range: [{np.min(weights):.2%}, {np.max(weights):.2%}]")
                    print(f"   Effective N assets: {1.0/np.sum(weights**2):.2f}")
            
        except Exception as e:
            print(f"❌ Optimization failed: {e}")
            weights = np.ones(n_assets) / n_assets
            self.last_status = 'error'
        
        # Update current weights for next optimization
        self.w_current = weights.copy()
        
        # Record solve time
        self.last_solve_time = (time.perf_counter() - start_time) * 1000  # ms
        print(f"   Solve time: {self.last_solve_time:.2f} ms\n")
        
        return weights
    
    def get_metrics(self) -> Dict:
        """
        Get metrics from last optimization.
        
        Returns:
            Dictionary with solve_time_ms and status
        """
        return {
            'solve_time_ms': self.last_solve_time,
            'status': self.last_status
        }


# Keep CTPOOptimizer as alias for backward compatibility
CTPOOptimizer = PortfolioOptimizer
