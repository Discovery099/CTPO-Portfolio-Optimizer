"""
Correlation estimation with stress adjustments
"""

import numpy as np
from typing import Optional, Tuple
import pandas as pd


class StressCorrelation:
    """
    Correlation matrix estimation with crisis stress adjustments.
    """
    
    def __init__(self, 
                 stress_multiplier: float = 1.5,
                 vol_threshold: float = 0.23,
                 shrinkage_target: float = 0.25,
                 max_corr: float = 0.85,
                 transition_smoothness: float = 5.0):
        """
        Initialize stress correlation estimator.
        
        Args:
            stress_multiplier: Factor to increase correlations during stress
            vol_threshold: Volatility threshold for stress activation
            shrinkage_target: Ledoit-Wolf shrinkage parameter
            max_corr: Maximum allowed correlation (breakdown threshold)
            transition_smoothness: Gaussian transition parameter
        """
        self.stress_multiplier = stress_multiplier
        self.vol_threshold = vol_threshold
        self.shrinkage_target = shrinkage_target
        self.max_corr = max_corr
        self.transition_smoothness = transition_smoothness
        self.base_correlation = None
    
    def compute_stress_level(self, sigma_market: float) -> float:
        """
        Compute stress activation parameter α(t).
        
        α(t) = min(1, max(0, (σ_M - threshold) / 0.27))
        
        Args:
            sigma_market: Market volatility
            
        Returns:
            Stress level in [0, 1]
        """
        if sigma_market <= self.vol_threshold:
            return 0.0
        
        # Linear ramp from threshold to threshold + 0.27
        alpha = (sigma_market - self.vol_threshold) / 0.27
        return np.clip(alpha, 0.0, 1.0)
    
    def estimate_correlation(self, returns: np.ndarray) -> np.ndarray:
        """
        Estimate base correlation matrix with robustness.
        
        Args:
            returns: Returns matrix (T x N) or DataFrame
            
        Returns:
            Correlation matrix (N x N)
        """
        if isinstance(returns, pd.DataFrame):
            correlation = returns.corr().values
        else:
            correlation = np.corrcoef(returns.T)
        
        # Ensure valid correlation matrix
        np.fill_diagonal(correlation, 1.0)
        correlation = np.clip(correlation, -1.0, 1.0)
        
        self.base_correlation = correlation
        return correlation
    
    def apply_stress(self, 
                     correlation: Optional[np.ndarray] = None,
                     sigma_market: float = 0.15,
                     returns: Optional[np.ndarray] = None) -> Tuple[np.ndarray, float]:
        """
        Apply stress scenario to correlation matrix.
        
        Blends normal and stressed correlation structures based on market volatility.
        
        Args:
            correlation: Base correlation matrix, computed if None
            sigma_market: Market volatility
            returns: Returns data for computing correlation if needed
            
        Returns:
            (stressed_correlation, alpha_stress)
        """
        # Compute or use provided correlation
        if correlation is None:
            if returns is not None:
                correlation = self.estimate_correlation(returns)
            elif self.base_correlation is not None:
                correlation = self.base_correlation
            else:
                raise ValueError("Must provide correlation matrix or returns data")
        
        n = correlation.shape[0]
        
        # Compute stress level
        alpha = self.compute_stress_level(sigma_market)
        
        # Create low-correlation target (shrinkage)
        P_low = np.eye(n) * (1 - self.shrinkage_target)
        P_low += self.shrinkage_target * np.ones((n, n)) / n
        
        # Smooth transition function (Gaussian)
        theta = np.exp(-self.transition_smoothness * (sigma_market - self.vol_threshold)**2)
        theta = np.clip(theta, 0.0, 1.0)
        
        # Blend correlations
        P_stress = theta * correlation + (1 - theta) * P_low
        
        # Cap correlations at breakdown threshold
        P_stress = np.clip(P_stress, -self.max_corr, self.max_corr)
        np.fill_diagonal(P_stress, 1.0)
        
        # Ensure symmetry
        P_stress = (P_stress + P_stress.T) / 2
        
        return P_stress, alpha
    
    def compute_stress_covariance(self,
                                 returns: pd.DataFrame,
                                 volatilities: np.ndarray,
                                 sigma_market: float,
                                 max_cond: float = 1e4) -> Tuple[np.ndarray, float]:
        """
        Compute full stress-adjusted covariance matrix.
        
        Σ_stress = D(σ) × P_stress(t) × D(σ)
        
        Args:
            returns: Returns DataFrame for correlation estimation
            volatilities: Asset volatilities (N,)
            sigma_market: Market volatility
            max_cond: Maximum condition number
            
        Returns:
            (Sigma_stress, alpha_stress)
        """
        # Get stressed correlation matrix
        P_stress, alpha = self.apply_stress(
            correlation=None,
            sigma_market=sigma_market,
            returns=returns.values if isinstance(returns, pd.DataFrame) else returns
        )
        
        # Construct covariance matrix
        D = np.diag(volatilities)
        Sigma_stress = D @ P_stress @ D
        
        # Ensure numerical stability
        Sigma_stable = self.condition_covariance(Sigma_stress, max_cond)
        
        return Sigma_stable, alpha
    
    def condition_covariance(self, 
                            Sigma: np.ndarray, 
                            max_cond: float = 1e4,
                            min_eigenvalue: float = 1e-6) -> np.ndarray:
        """
        Ensure Σ is positive definite with acceptable condition number.
        
        Args:
            Sigma: Covariance matrix
            max_cond: Maximum condition number
            min_eigenvalue: Minimum eigenvalue floor
            
        Returns:
            Conditioned covariance matrix
        """
        # Eigenvalue decomposition
        eigvals, eigvecs = np.linalg.eigh(Sigma)
        
        # Floor eigenvalues
        eigvals = np.maximum(eigvals, min_eigenvalue)
        
        # Condition number control
        if eigvals.max() / eigvals.min() > max_cond:
            eigvals = np.clip(eigvals, eigvals.max() / max_cond, eigvals.max())
        
        # Reconstruct
        Sigma_conditioned = eigvecs @ np.diag(eigvals) @ eigvecs.T
        
        # Ensure symmetry
        Sigma_conditioned = (Sigma_conditioned + Sigma_conditioned.T) / 2
        
        return Sigma_conditioned
