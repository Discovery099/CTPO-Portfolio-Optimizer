"""
Data preprocessing and cleaning
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


class DataPreprocessor:
    """
    Clean and preprocess market data.
    """
    
    def __init__(self, 
                 max_missing: float = 0.1,
                 outlier_threshold: float = 5.0):
        """
        Initialize preprocessor.
        
        Args:
            max_missing: Maximum fraction of missing data allowed
            outlier_threshold: Standard deviations for outlier detection
        """
        self.max_missing = max_missing
        self.outlier_threshold = outlier_threshold
    
    def clean_returns(self, returns: pd.DataFrame) -> pd.DataFrame:
        """
        Clean return data.
        
        Args:
            returns: Raw returns DataFrame
            
        Returns:
            Cleaned returns DataFrame
        """
        # TODO: Implement full cleaning pipeline in later chunks
        
        # Remove columns with too much missing data
        missing_fraction = returns.isna().sum() / len(returns)
        valid_columns = missing_fraction[missing_fraction < self.max_missing].index
        returns_clean = returns[valid_columns].copy()
        
        # Forward fill remaining NaN values
        returns_clean = returns_clean.fillna(method='ffill').fillna(0)
        
        return returns_clean
    
    def remove_outliers(self, returns: pd.DataFrame) -> pd.DataFrame:
        """
        Remove or cap outlier returns.
        
        Args:
            returns: Returns DataFrame
            
        Returns:
            Returns with outliers handled
        """
        # TODO: Implement robust outlier handling in later chunks
        
        # Placeholder: cap at threshold * std
        returns_clean = returns.copy()
        for col in returns_clean.columns:
            mean = returns_clean[col].mean()
            std = returns_clean[col].std()
            upper = mean + self.outlier_threshold * std
            lower = mean - self.outlier_threshold * std
            returns_clean[col] = returns_clean[col].clip(lower, upper)
        
        return returns_clean
    
    def align_data(self, *dataframes: pd.DataFrame) -> Tuple[pd.DataFrame, ...]:
        """
        Align multiple dataframes by date index.
        
        Args:
            dataframes: Variable number of DataFrames to align
            
        Returns:
            Tuple of aligned DataFrames
        """
        # Find common dates
        common_index = dataframes[0].index
        for df in dataframes[1:]:
            common_index = common_index.intersection(df.index)
        
        # Align all dataframes
        aligned = tuple(df.loc[common_index] for df in dataframes)
        
        return aligned
