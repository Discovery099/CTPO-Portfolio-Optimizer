"""
Integrated risk model combining GARCH, correlation stress, and CAPM
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional
from .garch import estimate_garch_volatilities
from .correlation import StressCorrelation
from .capm import CAPMModel


def estimate_market_volatility(returns_df: pd.DataFrame, 
                               market_proxy: str = 'SPY') -> float:
    """
    Compute market volatility from proxy (SPY, ^GSPC, etc.).
    
    Args:
        returns_df: Returns DataFrame
        market_proxy: Market proxy ticker
        
    Returns:
        Market volatility (annualized)
    """
    if market_proxy in returns_df.columns:
        market_returns = returns_df[market_proxy]
    else:
        # Use equal-weighted portfolio as proxy
        market_returns = returns_df.mean(axis=1)
    
    # GARCH on market returns
    vol = estimate_garch_volatilities(
        market_returns.to_frame(),
        p=1, q=1
    )[0]
    
    return vol


class RiskModel:
    """
    Integrates GARCH, correlation stress, and CAPM for complete risk estimation.
    """
    
    def __init__(self, params: Optional[Dict] = None):
        """
        Initialize risk model.
        
        Args:
            params: Parameter dictionary
        """
        self.params = params or {
            'risk_free_rate': 0.042,
            'volatility_threshold': 0.23,
            'correlation_breakdown': 0.85,
            'lambda_stress': 0.15
        }
        self.market_proxy = 'SPY'
        
        # Initialize sub-models
        self.capm = CAPMModel(
            risk_free_rate=self.params.get('risk_free_rate', 0.042),
            lambda_stress=self.params.get('lambda_stress', 0.15),
            vol_threshold=self.params.get('volatility_threshold', 0.23),
            rho_threshold=self.params.get('correlation_breakdown', 0.85)
        )
        
        self.stress_corr = StressCorrelation(
            vol_threshold=self.params.get('volatility_threshold', 0.23),
            max_corr=self.params.get('correlation_breakdown', 0.85)
        )
        
    def update(self, 
               returns_df: pd.DataFrame, 
               market_return: float = 0.10) -> Dict:
        """
        Update all risk model components.
        
        Args:
            returns_df: DataFrame (T × n) of recent returns
            market_return: Expected market return (annual)
            
        Returns:
            Dictionary with mu, Sigma, sigma_market, betas, alpha_stress, avg_correlation
        """
        # 1. Estimate volatilities via GARCH
        volatilities = estimate_garch_volatilities(returns_df, p=1, q=1)
        
        # 2. Estimate market volatility
        sigma_market = estimate_market_volatility(returns_df, self.market_proxy)
        
        # 3. Compute stress-adjusted covariance
        Sigma, alpha_stress = self.stress_corr.compute_stress_covariance(
            returns_df,
            volatilities,
            sigma_market
        )
        
        # 4. Estimate CAPM betas
        if self.market_proxy in returns_df.columns:
            market_returns = returns_df[self.market_proxy].values
        else:
            market_returns = returns_df.mean(axis=1).values
        
        betas = self.capm.calculate_betas(returns_df.values, market_returns)
        
        # 5. Compute expected returns with stress adjustment
        correlation_matrix = returns_df.corr().values
        n = correlation_matrix.shape[0]
        avg_corr = (np.sum(np.abs(correlation_matrix)) - n) / (n * (n - 1))
        
        # Correlations with market
        rho_stress = np.array([
            np.corrcoef(returns_df.iloc[:, i].values, market_returns)[0, 1]
            for i in range(returns_df.shape[1])
        ])
        
        mu = self.capm.compute_expected_returns(
            betas,
            sigma_market,
            rho_stress,
            r_market=market_return
        )
        
        return {
            'mu': mu,
            'Sigma': Sigma,
            'sigma_market': sigma_market,
            'betas': betas,
            'alpha_stress': alpha_stress,
            'avg_correlation': avg_corr,
            'volatilities': volatilities,
            'rho_stress': rho_stress
        }
