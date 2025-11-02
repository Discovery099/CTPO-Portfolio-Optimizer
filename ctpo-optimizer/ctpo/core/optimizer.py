"""
CTPO Optimizer - Main optimization engine

Applies Cable-Driven Parallel Robot (CDPR) force distribution
algorithms to portfolio optimization.
"""

import numpy as np
import cvxpy as cp
from typing import Dict, List, Optional, Tuple
import yaml
import os
from time import perf_counter
from .objective import build_objective
from .constraints import (
    build_constraints, 
    construct_structure_matrix, 
    construct_wrench_vector
)


# Default system parameters
SYSTEM_PARAMS = {
    'n_assets': 152,
    'volatility_threshold': 0.23,
    'correlation_breakdown': 0.85,
    'risk_free_rate': 0.042,
    'tension_regularization': 0.0075,
    'workspace_constraint': 0.92,
    'cable_stiffness': 310.0,
    'force_balance_tolerance': 0.0018,
    'diversification_gain': 0.24,
    'transaction_cost_limit': 0.005,
    'leverage_max': 2.0,
    'position_max': 0.08,
    'position_min': -0.05,
    'min_effective_assets': 20,
    'condition_number_max': 10000,
    'max_iterations': 200,
    'ftol': 1e-6,
    'solver': 'OSQP',
    'warm_start': True
}


class CTPOState:
    """
    State vector for CTPO optimization.
    
    Maintains all necessary state variables for the optimization problem.
    """
    
    def __init__(self, n_assets: int = 152):
        """
        Initialize optimization state.
        
        Args:
            n_assets: Number of assets in universe
        """
        self.n = n_assets
        self.w = np.ones(n_assets) / n_assets  # Portfolio weights (decision variables)
        self.w_prev = self.w.copy()             # Previous weights (for transaction costs)
        self.mu = np.zeros(n_assets)            # Expected returns (updated each period)
        self.Sigma = np.eye(n_assets) * 0.01    # Covariance matrix (PSD, conditioned)
        self.sigma_market = 0.15                 # Market volatility (GARCH estimated)
        self.rho_realized = 0.50                 # Average correlation (rolling)
        self.alpha_stress = 0.0                  # Stress activation [0,1]
        self.beta = np.ones(n_assets)            # CAPM betas vs market proxy
        self.volatilities = np.ones(n_assets) * 0.15  # Individual asset volatilities
    
    def update_from_data(self, 
                        returns: np.ndarray,
                        market_returns: Optional[np.ndarray] = None):
        """
        Update state variables from new return data.
        
        Args:
            returns: Asset returns (T x N)
            market_returns: Market returns (T,), optional
        """
        # Update dimensions if needed
        n_assets = returns.shape[1]
        if n_assets != self.n:
            self.n = n_assets
            self.w = np.ones(n_assets) / n_assets
            self.w_prev = self.w.copy()
            self.beta = np.ones(n_assets)
        
        # Compute basic statistics
        self.mu = returns.mean(axis=0)
        self.Sigma = np.cov(returns.T)
        
        # Market volatility
        if market_returns is None:
            market_returns = returns.mean(axis=1)
        self.sigma_market = np.std(market_returns)
        
        # Average correlation
        correlation = np.corrcoef(returns.T)
        n = correlation.shape[0]
        self.rho_realized = (np.sum(correlation) - n) / (n * (n - 1))


class CTPOOptimizer:
    """
    Main CTPO optimization engine.
    
    Maps portfolio weights to cable tensions in a CDPR system,
    enforcing force balance constraints for robust diversification.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the CTPO optimizer.
        
        Args:
            config_path: Path to configuration YAML file
        """
        self.config = self._load_config(config_path)
        self.params = {**SYSTEM_PARAMS, **self.config.get('computational', {}), 
                       **self.config.get('integration', {}), **self.config.get('solver', {})}
        
        self.state = None
        self.weights = None
        self.w_current = None
        self.w_baseline = None
        self.portfolio_value = None
        
        # Solver settings
        self.solver_name = self.params.get('solver', 'OSQP')
        self.max_iter = self.params.get('max_iterations', 200)
        self.ftol = self.params.get('ftol', 1e-6)
        self.warm_start_enabled = self.params.get('warm_start', True)
        
    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to config file
            
        Returns:
            Configuration dictionary
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), 
                '../../config/default_params.yaml'
            )
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """
        Return default configuration.
        
        Returns:
            Default config dictionary
        """
        return {
            'computational': {
                'tension_regularization': 0.0075,
                'cable_stiffness': 310.0,
                'force_balance_tolerance': 0.0018
            },
            'integration': {
                'position_max': 0.08,
                'position_min': -0.05,
                'min_effective_assets': 20,
                'leverage_max': 2.0
            },
            'solver': {
                'algorithm': 'OSQP',
                'max_iterations': 200,
                'ftol': 1e-6,
                'warm_start': True
            }
        }
    
    def _compute_stress_level(self, sigma_market: float) -> float:
        """
        Compute stress activation parameter.
        
        α(t) = min(1, max(0, (σ_M - threshold) / 0.27))
        
        Args:
            sigma_market: Market volatility
            
        Returns:
            Stress level in [0, 1]
        """
        vol_threshold = self.params.get('volatility_threshold', 0.23)
        alpha = (sigma_market - vol_threshold) / 0.27
        return np.clip(alpha, 0.0, 1.0)
    
    def initialize_state(self, n_assets: int) -> CTPOState:
        """
        Initialize optimization state.
        
        Args:
            n_assets: Number of assets
            
        Returns:
            Initialized state
        """
        self.state = CTPOState(n_assets)
        self.w_current = np.ones(n_assets) / n_assets
        self.w_baseline = self.w_current.copy()
        return self.state
    
    def optimize(self, 
                 returns: np.ndarray,
                 covariance: Optional[np.ndarray] = None,
                 expected_returns: Optional[np.ndarray] = None,
                 market_returns: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Optimize portfolio weights using CDPR force balance with CVXPY.
        
        Args:
            returns: Historical returns matrix (T x N)
            covariance: Covariance matrix (N x N), computed if None
            expected_returns: Expected returns vector (N,), estimated if None
            market_returns: Market returns (T,), computed if None
            
        Returns:
            Optimal portfolio weights (N,)
        """
        tic = perf_counter()
        
        n_assets = returns.shape[1]
        
        # Initialize or update state
        if self.state is None or self.state.n != n_assets:
            self.initialize_state(n_assets)
        
        if self.w_current is None:
            self.w_current = np.ones(n_assets) / n_assets
        if self.w_baseline is None:
            self.w_baseline = self.w_current.copy()
        
        self.state.update_from_data(returns, market_returns)
        
        # Use provided or computed values
        if covariance is None:
            covariance = self.state.Sigma
        if expected_returns is None:
            expected_returns = self.state.mu
        if market_returns is None:
            market_returns = returns.mean(axis=1)
        
        # Compute stress level
        sigma_market = np.std(market_returns) * np.sqrt(252)  # Annualized
        alpha_stress = self._compute_stress_level(sigma_market)
        
        # Get betas and volatilities for CDPR structure
        from ..risk.capm import CAPMModel
        from ..risk.garch import estimate_garch_volatilities
        import pandas as pd
        
        capm = CAPMModel()
        betas = capm.calculate_betas(returns, market_returns)
        
        # Use simpler volatility estimation for speed
        volatilities = np.std(returns, axis=0)
        
        # Construct CDPR structure
        A = construct_structure_matrix(betas, volatilities, self.params['cable_stiffness'])
        W = construct_wrench_vector(
            target_return=0.08,
            max_risk=0.15,
            min_eff_assets=min(self.params['min_effective_assets'], n_assets)
        )
        
        # Define optimization variable
        w = cp.Variable(n_assets)
        
        # Build objective
        objective = build_objective(w, self.w_current, expected_returns, covariance, alpha_stress, self.params)
        
        # Build constraints
        constraints = build_constraints(w, self.w_current, self.w_baseline, A, W, self.params)
        
        # Solve
        problem = cp.Problem(objective, constraints)
        
        try:
            # Map solver name
            solver_map = {'OSQP': cp.OSQP, 'SCS': cp.SCS, 'ECOS': cp.ECOS}
            solver = solver_map.get(self.solver_name, cp.OSQP)
            
            print(f"🔧 Starting optimization with {n_assets} assets...")
            print(f"   Solver: {self.solver_name}, Max iterations: {self.max_iter}")
            print(f"   Constraints: {len(constraints)} total")
            
            problem.solve(
                solver=solver,
                warm_start=self.warm_start_enabled,
                max_iter=self.max_iter,
                eps_abs=self.ftol,
                eps_rel=self.ftol,
                verbose=True  # Enable verbose for debugging
            )
            
            print(f"📊 Solver status: {problem.status}")
            print(f"   Objective value: {problem.value}")
            
            if problem.status not in ['optimal', 'optimal_inaccurate']:
                print(f"⚠️  Solver status: {problem.status}. Using fallback to equal weights.")
                print(f"   This indicates constraint conflicts or numerical issues.")
                w_optimal = self.w_baseline.copy()
                status = 'fallback'
            else:
                w_optimal = w.value
                if w_optimal is None:
                    print(f"⚠️  Solver returned None. Using equal-weight fallback.")
                    w_optimal = self.w_baseline.copy()
                    status = 'fallback'
                else:
                    status = problem.status
                    # Normalize to ensure sum = 1
                    w_sum = np.sum(w_optimal)
                    print(f"✅ Optimization successful! Weight sum: {w_sum:.6f}")
                    w_optimal = w_optimal / w_sum
                    print(f"   Max weight: {np.max(w_optimal):.4f}, Min weight: {np.min(w_optimal):.4f}")
                    print(f"   Effective N: {1.0/np.sum(w_optimal**2):.2f}")
                
        except Exception as e:
            print(f"❌ Solver failed with exception: {e}")
            import traceback
            traceback.print_exc()
            print(f"   Using equal-weight fallback.")
            w_optimal = self.w_baseline.copy()
            status = 'error'
        
        toc = perf_counter()
        solve_time_ms = (toc - tic) * 1000
        
        # Update state
        self.weights = w_optimal
        self.w_current = w_optimal
        
        # Store metrics
        self.last_metrics = {
            'solve_time_ms': solve_time_ms,
            'objective_value': problem.value if status == 'optimal' else None,
            'status': status,
            'alpha_stress': alpha_stress,
            'effective_assets': 1.0 / np.sum(w_optimal**2) if np.sum(w_optimal**2) > 0 else n_assets,
            'turnover': np.sum(np.abs(w_optimal - self.w_baseline)),
            'max_position': np.max(np.abs(w_optimal)),
            'leverage': np.sum(np.abs(w_optimal))
        }
        
        # Validate timing constraint
        if solve_time_ms > 50:
            print(f"⚠️  Solve time {solve_time_ms:.1f} ms exceeds 50 ms target")
        
        return w_optimal
    
    def get_metrics(self) -> Dict:
        """
        Get current optimization metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        if self.state is None:
            return {
                'weights': self.weights,
                'state': None,
                'convergence': None,
                'condition_number': None
            }
        
        # Compute condition number
        cond_number = np.linalg.cond(self.state.Sigma) if self.state.Sigma is not None else None
        
        metrics = {
            'weights': self.weights,
            'expected_returns': self.state.mu,
            'market_volatility': self.state.sigma_market,
            'stress_level': self.state.alpha_stress,
            'avg_correlation': self.state.rho_realized,
            'condition_number': cond_number
        }
        
        # Add last solve metrics if available
        if hasattr(self, 'last_metrics'):
            metrics.update(self.last_metrics)
        
        return metrics
