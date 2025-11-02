"""
Constraints module for CDPR force balance and portfolio constraints
"""

import numpy as np
from typing import List, Tuple


class CableConstraints:
    """
    CDPR cable tension constraints mapped to portfolio weights.
    """
    
    def __init__(self, min_tension: float = 0.01, max_tension: float = 0.25):
        """
        Initialize cable constraints.
        
        Args:
            min_tension: Minimum cable tension (minimum weight)
            max_tension: Maximum cable tension (maximum weight)
        """
        self.min_tension = min_tension
        self.max_tension = max_tension
    
    def force_balance_constraint(self, weights: np.ndarray) -> float:
        """
        CDPR force balance equation.
        
        In CDPR: Sum of cable forces must balance external wrench.
        In Portfolio: Sum of weights must equal 1.
        
        Args:
            weights: Portfolio weights
            
        Returns:
            Constraint violation (0 = satisfied)
        """
        # TODO: Implement full force balance in later chunks
        return np.abs(np.sum(weights) - 1.0)
    
    def tension_limits(self, weights: np.ndarray) -> Tuple[bool, List[int]]:
        """
        Check cable tension limits.
        
        Args:
            weights: Portfolio weights
            
        Returns:
            (satisfied, violating_indices)
        """
        violations = []
        for i, w in enumerate(weights):
            if w < self.min_tension or w > self.max_tension:
                violations.append(i)
        
        return len(violations) == 0, violations


class PortfolioConstraints:
    """
    Standard portfolio constraints.
    """
    
    def __init__(self, min_assets: int = 20, max_leverage: float = 1.0):
        """
        Initialize portfolio constraints.
        
        Args:
            min_assets: Minimum number of assets to hold
            max_leverage: Maximum leverage allowed
        """
        self.min_assets = min_assets
        self.max_leverage = max_leverage
    
    def diversification_constraint(self, weights: np.ndarray) -> bool:
        """
        Check minimum diversification requirement.
        
        Args:
            weights: Portfolio weights
            
        Returns:
            True if constraint satisfied
        """
        # TODO: Implement effective N assets calculation
        n_nonzero = np.sum(weights > 1e-6)
        return n_nonzero >= self.min_assets
