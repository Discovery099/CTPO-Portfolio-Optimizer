"""
Backtesting engine
"""

import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from datetime import datetime


class Backtester:
    """
    Historical backtesting engine.
    """
    
    def __init__(self,
                 initial_capital: float = 1000000.0,
                 transaction_cost: float = 0.001):
        """
        Initialize backtester.
        
        Args:
            initial_capital: Starting portfolio value
            transaction_cost: Transaction cost (fraction)
        """
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.results = None
    
    def run(self,
            returns: pd.DataFrame,
            weight_function: Callable,
            rebalance_frequency: str = 'monthly') -> pd.DataFrame:
        """
        Run backtest.
        
        Args:
            returns: Historical returns DataFrame
            weight_function: Function that generates portfolio weights
            rebalance_frequency: How often to rebalance ('daily', 'weekly', 'monthly')
            
        Returns:
            DataFrame with backtest results
        """
        # Frequency mapping
        freq_map = {'daily': 1, 'weekly': 5, 'monthly': 21}
        rebal_period = freq_map.get(rebalance_frequency, 21)
        
        n_periods = len(returns)
        n_assets = returns.shape[1]
        
        # Initialize tracking arrays
        portfolio_values = np.zeros(n_periods)
        weights_history = []
        portfolio_returns = np.zeros(n_periods)
        
        # Starting values
        portfolio_values[0] = self.initial_capital
        current_weights = np.ones(n_assets) / n_assets
        
        # Simulation loop
        for t in range(n_periods):
            # Rebalance if needed
            if t % rebal_period == 0 and t > 0:
                # Get historical returns up to this point
                hist_returns = returns.iloc[:t]
                
                if len(hist_returns) >= 50:  # Minimum data requirement
                    try:
                        new_weights = weight_function(hist_returns.values)
                        
                        # Apply transaction costs
                        turnover = np.sum(np.abs(new_weights - current_weights))
                        tc_cost = turnover * self.transaction_cost * portfolio_values[t-1]
                        portfolio_values[t-1] -= tc_cost
                        
                        current_weights = new_weights
                    except Exception as e:
                        print(f"Rebalancing failed at t={t}: {e}")
            
            # Calculate portfolio return
            period_return = returns.iloc[t].values @ current_weights
            portfolio_returns[t] = period_return
            
            # Update portfolio value
            if t > 0:
                portfolio_values[t] = portfolio_values[t-1] * (1 + period_return)
            
            weights_history.append(current_weights.copy())
        
        # Create results DataFrame
        results = pd.DataFrame({
            'portfolio_value': portfolio_values,
            'returns': portfolio_returns,
            'date': returns.index
        })
        results['weights'] = weights_history
        
        self.results = results
        return results
    
    def get_summary(self) -> Dict:
        """
        Get backtest summary statistics.
        
        Returns:
            Dictionary of summary statistics
        """
        if self.results is None:
            return {}
        
        returns = self.results['returns'].values
        portfolio_values = self.results['portfolio_value'].values
        
        # Calculate metrics
        total_return = (portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0]
        
        # Sharpe ratio
        excess_returns = returns - 0.02/252  # Daily risk-free rate
        sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        
        # Max drawdown
        cumulative = portfolio_values / portfolio_values[0]
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        # Volatility
        volatility = np.std(returns) * np.sqrt(252)
        
        # Num trades (count rebalances)
        weights_array = np.array([w for w in self.results['weights']])
        weight_changes = np.sum(np.abs(np.diff(weights_array, axis=0)), axis=1)
        num_trades = np.sum(weight_changes > 0.01)  # 1% threshold
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'num_trades': num_trades,
            'final_value': portfolio_values[-1],
            'calmar_ratio': total_return / abs(max_drawdown) if max_drawdown != 0 else 0
        }
