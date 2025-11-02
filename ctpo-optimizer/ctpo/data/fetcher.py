"""
Data fetcher for market data (Yahoo Finance)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Optional, Union
from datetime import datetime, timedelta


class DataFetcher:
    """
    Fetch market data from Yahoo Finance.
    """
    
    def __init__(self, cache_enabled: bool = True, cache_dir: str = '.cache'):
        """
        Initialize data fetcher.
        
        Args:
            cache_enabled: Enable data caching
            cache_dir: Cache directory path
        """
        self.cache_enabled = cache_enabled
        self.cache_dir = cache_dir
    
    def fetch_stocks(self,
                     tickers: List[str],
                     start_date: Optional[Union[str, datetime]] = None,
                     end_date: Optional[Union[str, datetime]] = None,
                     period: str = '1y') -> pd.DataFrame:
        """
        Fetch stock price data.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            period: Period string if dates not provided (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            
        Returns:
            DataFrame with adjusted close prices
        """
        # TODO: Add caching logic in later chunks
        
        if start_date is None and end_date is None:
            data = yf.download(tickers, period=period, progress=False)
        else:
            data = yf.download(tickers, start=start_date, end=end_date, progress=False)
        
        # Handle different return structures from yfinance
        if len(tickers) == 1:
            # Single ticker returns simple DataFrame
            if 'Adj Close' in data.columns:
                prices = data[['Adj Close']].copy()
                prices.columns = [tickers[0]]
            else:
                prices = data[['Close']].copy()
                prices.columns = [tickers[0]]
        else:
            # Multiple tickers returns MultiIndex DataFrame
            if isinstance(data.columns, pd.MultiIndex):
                if 'Adj Close' in data.columns.get_level_values(0):
                    prices = data['Adj Close'].copy()
                else:
                    prices = data['Close'].copy()
            else:
                # Fallback: assume it's already the right format
                prices = data.copy()
        
        return prices
    
    def fetch_returns(self,
                      tickers: List[str],
                      start_date: Optional[Union[str, datetime]] = None,
                      end_date: Optional[Union[str, datetime]] = None,
                      period: str = '1y',
                      log_returns: bool = False) -> pd.DataFrame:
        """
        Fetch and compute returns.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date
            period: Period string
            log_returns: Use log returns if True, simple returns if False
            
        Returns:
            DataFrame with returns
        """
        prices = self.fetch_stocks(tickers, start_date, end_date, period)
        
        if log_returns:
            returns = np.log(prices / prices.shift(1))
        else:
            returns = prices.pct_change()
        
        # Drop NaN values
        returns = returns.dropna()
        
        return returns
