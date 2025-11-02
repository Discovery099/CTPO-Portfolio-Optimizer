"""
GARCH volatility modeling
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Union
from arch import arch_model
import warnings


class GARCHModel:
    """
    GARCH(1,1) volatility forecasting for individual assets.
    """
    
    def __init__(self, 
                 p: int = 1, 
                 q: int = 1, 
                 distribution: str = 'normal',
                 min_volatility: float = 0.01,
                 max_volatility: float = 1.0):
        """
        Initialize GARCH model.
        
        Args:
            p: GARCH lag order
            q: ARCH lag order
            distribution: Error distribution ('normal', 't', 'skewt')
            min_volatility: Minimum volatility floor
            max_volatility: Maximum volatility cap
        """
        self.p = p
        self.q = q
        self.distribution = distribution
        self.min_volatility = min_volatility
        self.max_volatility = max_volatility
        self.fitted_model = None
        self.conditional_volatility = None
    
    def fit(self, returns: Union[np.ndarray, pd.Series], scale: float = 100.0) -> 'GARCHModel':
        """
        Fit GARCH model to returns.
        
        Args:
            returns: Return series
            scale: Scale factor for numerical stability (returns * scale)
            
        Returns:
            Self for chaining
        """
        # Convert to pandas Series if numpy array
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
        
        # Scale returns for numerical stability
        returns_scaled = returns * scale
        
        try:
            # Fit GARCH(p,q) model
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = arch_model(
                    returns_scaled, 
                    vol='Garch', 
                    p=self.p, 
                    q=self.q,
                    dist=self.distribution,
                    rescale=False
                )
                self.fitted_model = model.fit(disp='off', show_warning=False)
                
                # Extract conditional volatility (unscale)
                self.conditional_volatility = self.fitted_model.conditional_volatility.values / scale
                
        except Exception as e:
            # Fallback to historical volatility if GARCH fails
            warnings.warn(f"GARCH fitting failed: {e}. Using historical volatility.")
            self.conditional_volatility = np.ones(len(returns)) * np.std(returns)
        
        return self
    
    def forecast_volatility(self, horizon: int = 1) -> float:
        """
        Forecast volatility for specified horizon.
        
        Args:
            horizon: Forecast horizon (days)\
            
        Returns:
            Forecasted volatility (annualized if horizon=252)
        """
        if self.fitted_model is None:
            # Return last conditional volatility or default
            if self.conditional_volatility is not None:
                return float(self.conditional_volatility[-1])
            return self.min_volatility
        
        try:
            # Forecast from fitted model
            forecast = self.fitted_model.forecast(horizon=horizon)
            variance_forecast = forecast.variance.values[-1, 0]
            volatility = np.sqrt(variance_forecast)
            
            # Clip to reasonable range
            volatility = np.clip(volatility, self.min_volatility, self.max_volatility)
            
            return float(volatility)
            
        except Exception as e:
            warnings.warn(f\"GARCH forecast failed: {e}\")\n            return float(self.conditional_volatility[-1]) if self.conditional_volatility is not None else self.min_volatility
    
    def get_last_volatility(self) -> float:
        """
        Get most recent conditional volatility estimate.
        
        Returns:
            Last volatility estimate
        """
        if self.conditional_volatility is not None and len(self.conditional_volatility) > 0:
            return float(self.conditional_volatility[-1])
        return self.min_volatility


def estimate_garch_volatilities(returns_df: pd.DataFrame,
                                p: int = 1,
                                q: int = 1,
                                min_vol: float = 0.01,
                                max_vol: float = 1.0) -> np.ndarray:
    """
    Estimate GARCH volatilities for all assets in a DataFrame.
    
    Args:
        returns_df: Returns DataFrame (T x N)
        p: GARCH lag order
        q: ARCH lag order
        min_vol: Minimum volatility
        max_vol: Maximum volatility
        
    Returns:
        Array of volatilities (N,)
    """
    n_assets = returns_df.shape[1]
    volatilities = np.zeros(n_assets)
    
    for i in range(n_assets):
        asset_returns = returns_df.iloc[:, i]
        
        # Skip if insufficient data
        if len(asset_returns.dropna()) < 50:
            volatilities[i] = np.std(asset_returns.dropna())
            continue
        
        try:
            model = GARCHModel(p=p, q=q, min_volatility=min_vol, max_volatility=max_vol)
            model.fit(asset_returns.dropna())
            volatilities[i] = model.get_last_volatility()
        except Exception:
            # Fallback to historical std
            volatilities[i] = np.std(asset_returns.dropna())
    
    # Clip to range
    volatilities = np.clip(volatilities, min_vol, max_vol)
    
    return volatilities
