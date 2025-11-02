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
        self.state = None
        self.weights = None
        self.portfolio_value = None
        
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
            # Return default config if file doesn't exist
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """
        Return default configuration.
        
        Returns:
            Default config dictionary
        """
        return {
            'physical': {
                'n_assets': 152,
                'volatility_threshold': 0.23,
                'correlation_breakdown': 0.85,
                'risk_free_rate': 0.042
            },
            'computational': {
                'tension_regularization': 0.0075,
                'workspace_constraint': 0.92,
                'cable_stiffness': 310.0,
                'force_balance_tolerance': 0.0018,
                'diversification_gain': 0.24
            },
            'integration': {
                'position_max': 0.08,
                'position_min': -0.05,
                'min_effective_assets': 20
            },
            'solver': {
                'algorithm': 'OSQP',
                'max_iterations': 200,
                'ftol': 1e-6
            },
            'targets': {
                'target_return': 0.08,
                'max_risk': 0.15,
                'min_effective_assets': 20
            }
        }
    
    def initialize_state(self, n_assets: int) -> CTPOState:
        """
        Initialize optimization state.
        
        Args:
            n_assets: Number of assets
            
        Returns:
            Initialized state
        """
        self.state = CTPOState(n_assets)
        return self.state
    
    def optimize(self, 
                 returns: np.ndarray,
                 covariance: Optional[np.ndarray] = None,
                 expected_returns: Optional[np.ndarray] = None,
                 market_returns: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Optimize portfolio weights using CDPR force balance.
        
        Args:
            returns: Historical returns matrix (T x N)
            covariance: Covariance matrix (N x N), computed if None
            expected_returns: Expected returns vector (N,), estimated if None
            market_returns: Market returns (T,), computed if None
            
        Returns:
            Optimal portfolio weights (N,)
        """
        n_assets = returns.shape[1]
        
        # Initialize or update state
        if self.state is None or self.state.n != n_assets:
            self.initialize_state(n_assets)
        
        self.state.update_from_data(returns, market_returns)
        
        # For CHUNK 2: Return equal weights (CDPR optimization in CHUNK 3)
        # This will be replaced with full CVXPY optimization
        weights = np.ones(n_assets) / n_assets
        self.weights = weights
        
        return weights
    
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
        
        return {
            'weights': self.weights,
            'expected_returns': self.state.mu,
            'market_volatility': self.state.sigma_market,
            'stress_level': self.state.alpha_stress,
            'avg_correlation': self.state.rho_realized,
            'condition_number': cond_number
        }
