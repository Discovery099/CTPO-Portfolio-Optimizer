"""
CAPM and expected returns estimation with stress correction
"""

import numpy as np
from typing import Optional, Tuple
import pandas as pd


class CAPMModel:
    """
    Capital Asset Pricing Model with stress correction.
    
    Returns adjusted for volatility spikes and correlation breakdown.
    """
    
    def __init__(self, 
                 risk_free_rate: float = 0.042,
                 market_premium: float = 0.08,
                 lambda_stress: float = 0.15,
                 vol_threshold: float = 0.23,
                 rho_threshold: float = 0.85,
                 beta_floor: float = 0.1,
                 beta_ceiling: float = 3.0):
        """
        Initialize CAPM model with stress adjustment.
        
        Args:
            risk_free_rate: Annual risk-free rate
            market_premium: Expected market risk premium
            lambda_stress: Stress penalty coefficient
            vol_threshold: Volatility activation threshold
            rho_threshold: Correlation threshold for penalty
            beta_floor: Minimum beta
            beta_ceiling: Maximum beta
        """
        self.risk_free_rate = risk_free_rate
        self.market_premium = market_premium
        self.lambda_stress = lambda_stress
        self.vol_threshold = vol_threshold
        self.rho_threshold = rho_threshold
        self.beta_floor = beta_floor
        self.beta_ceiling = beta_ceiling
        self.betas = None
        self.market_return = None
    
    def calculate_betas(self,
                       returns: np.ndarray,
                       market_returns: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Calculate asset betas via OLS regression.
        
        Args:
            returns: Asset returns (T x N)
            market_returns: Market returns (T,), uses equal-weight if None
            
        Returns:
            Beta coefficients (N,)
        """
        if market_returns is None:
            # Use equal-weight portfolio as market proxy
            market_returns = returns.mean(axis=1)
        
        n_assets = returns.shape[1]
        betas = np.zeros(n_assets)
        
        # Demean for regression
        market_demeaned = market_returns - market_returns.mean()
        market_var = np.var(market_demeaned)
        
        if market_var < 1e-10:
            # Degenerate case: no market variation
            self.betas = np.ones(n_assets)
            return self.betas
        
        for i in range(n_assets):
            asset_demeaned = returns[:, i] - returns[:, i].mean()
            covariance = np.mean(asset_demeaned * market_demeaned)
            betas[i] = covariance / market_var
        
        # Clip betas to reasonable range
        betas = np.clip(betas, self.beta_floor, self.beta_ceiling)
        self.betas = betas
        
        return betas
    
    def compute_expected_returns(self,
                                beta: np.ndarray,
                                sigma_market: float,
                                rho_stress: Optional[np.ndarray] = None,
                                r_market: Optional[float] = None) -> np.ndarray:
        """
        Compute expected returns with stress correction.
        
        Formula:
        E(R_i) = R_f + β_i(R_m - R_f) - λ_stress × max(0, σ_M - threshold) × max(0, ρ_i - threshold)
        
        Args:
            beta: Asset betas (N,)
            sigma_market: Market volatility
            rho_stress: Asset correlations with market (N,), uses beta/|beta| if None
            r_market: Market return, uses risk_free + premium if None
            
        Returns:
            Expected returns (N,)
        """
        if r_market is None:
            r_market = self.risk_free_rate + self.market_premium
        
        # Base CAPM return
        base_return = self.risk_free_rate + beta * (r_market - self.risk_free_rate)
        
        # Stress penalty activates only when volatility > threshold
        vol_excess = np.maximum(0, sigma_market - self.vol_threshold)
        
        # Use beta-derived correlation if not provided
        if rho_stress is None:
            # Approximate correlation from beta (assuming β = ρ * σ_i / σ_m)
            rho_stress = np.sign(beta) * np.minimum(1.0, np.abs(beta))
        
        corr_excess = np.maximum(0, rho_stress - self.rho_threshold)
        stress_penalty = self.lambda_stress * vol_excess * corr_excess
        
        expected_returns = base_return - stress_penalty
        
        return expected_returns
    
    def estimate_expected_returns(self,
                                  returns: np.ndarray,
                                  market_returns: Optional[np.ndarray] = None,
                                  sigma_market: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Estimate expected returns with automatic beta calculation.
        
        Args:
            returns: Asset returns (T x N)
            market_returns: Market returns (T,)
            sigma_market: Market volatility, computed if None
            
        Returns:
            (expected_returns, betas)
        """
        # Calculate betas
        if market_returns is None:
            market_returns = returns.mean(axis=1)
        
        betas = self.calculate_betas(returns, market_returns)
        
        # Estimate market volatility if not provided
        if sigma_market is None:
            sigma_market = np.std(market_returns) * np.sqrt(252)  # Annualized
        
        # Compute correlations with market
        correlations = np.array([np.corrcoef(returns[:, i], market_returns)[0, 1] 
                                for i in range(returns.shape[1])])
        
        # Calculate expected returns with stress adjustment
        expected_returns = self.compute_expected_returns(
            betas, sigma_market, correlations
        )
        
        return expected_returns, betas
