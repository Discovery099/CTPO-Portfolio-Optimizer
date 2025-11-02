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
    Fetch market data from Yahoo Finance with caching and error handling.
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
        self.data_cache = {}
    
    def fetch_historical(self,
                        symbols: List[str],
                        lookback_days: int = 1260,
                        start_date: Optional[Union[str, datetime]] = None,
                        end_date: Optional[Union[str, datetime]] = None) -> pd.DataFrame:
        """
        Fetch historical OHLCV data.
        
        Args:
            symbols: List of ticker symbols
            lookback_days: Days of history (default ~5 years)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with MultiIndex (date, symbol) or simple index
        """
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=lookback_days)
        
        print(f"📡 Fetching data for {len(symbols)} symbols from {start_date.date() if isinstance(start_date, datetime) else start_date} to {end_date.date() if isinstance(end_date, datetime) else end_date}...")
        
        data = yf.download(
            symbols,
            start=start_date,
            end=end_date,
            interval='1d',
            progress=False,
            group_by='ticker' if len(symbols) > 1 else None
        )
        
        if len(symbols) > 1 and isinstance(data.columns, pd.MultiIndex):
            # Pivot to (date, symbol) MultiIndex
            prices = data.stack(level=0).swaplevel()
            prices = prices[['Adj Close']].rename(columns={'Adj Close': 'price'})
        else:
            # Single symbol
            if 'Adj Close' in data.columns:
                prices = data[['Adj Close']].rename(columns={'Adj Close': 'price'})
            else:
                prices = data[['Close']].rename(columns={'Close': 'price'})
            prices['symbol'] = symbols[0]
            prices = prices.set_index('symbol', append=True)
        
        self.data_cache['prices'] = prices
        return prices
    
    def compute_returns(self, price_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Compute log returns from prices.
        
        Args:
            price_df: Price DataFrame, uses cached if None
            
        Returns:
            Returns DataFrame (date × symbols)
        """
        if price_df is None:
            price_df = self.data_cache.get('prices')
        
        if price_df is None:
            raise ValueError("No price data available. Call fetch_historical() first.")
        
        # Unstack to wide format (date × symbols)
        if isinstance(price_df.index, pd.MultiIndex):
            prices_wide = price_df['price'].unstack(level='symbol')
        else:
            prices_wide = price_df
        
        # Log returns
        returns = np.log(prices_wide / prices_wide.shift(1)).dropna()
        
        self.data_cache['returns'] = returns
        return returns
    
    def get_latest_bar(self, symbols: List[str], interval: str = '1m') -> pd.DataFrame:
        """
        Fetch most recent bar (for live trading).
        
        Args:
            symbols: List of symbols
            interval: Time interval (1m, 5m, 1h, 1d, etc.)
            
        Returns:
            Latest bar data
        """
        data = yf.download(
            symbols,
            period='1d',
            interval=interval,
            progress=False
        )
        return data.iloc[-1] if len(data) > 0 else None
    
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
            period: Period string if dates not provided
            
        Returns:
            DataFrame with adjusted close prices
        """
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
