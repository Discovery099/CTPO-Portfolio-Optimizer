"""
Constraint and solution validators
"""

import numpy as np
from typing import Dict, List, Tuple


class PortfolioValidator:
    """
    Validate portfolio constraints and solutions.
    """
    
    def __init__(self, tolerance: float = 1e-6):
        """
        Initialize validator.
        
        Args:
            tolerance: Numerical tolerance for constraint checking
        """
        self.tolerance = tolerance
    
    def validate_weights(self,
                        weights: np.ndarray,
                        min_weight: float = 0.0,
                        max_weight: float = 1.0) -> Tuple[bool, List[str]]:
        """
        Validate portfolio weights.
        
        Args:
            weights: Portfolio weights
            min_weight: Minimum allowed weight
            max_weight: Maximum allowed weight
            
        Returns:
            (valid, list of violations)
        """
        violations = []
        
        # Check sum to 1
        weight_sum = np.sum(weights)
        if abs(weight_sum - 1.0) > self.tolerance:
            violations.append(f"Weights sum to {weight_sum:.6f}, not 1.0")
        
        # Check bounds
        if np.any(weights < min_weight - self.tolerance):
            violations.append(f"Weights below minimum {min_weight}")
        
        if np.any(weights > max_weight + self.tolerance):
            violations.append(f"Weights above maximum {max_weight}")
        
        # Check for NaN or inf
        if np.any(np.isnan(weights)) or np.any(np.isinf(weights)):
            violations.append("Weights contain NaN or Inf")
        
        return len(violations) == 0, violations
    
    def validate_solution(self,
                         weights: np.ndarray,
                         returns: np.ndarray,
                         constraints: Dict) -> Tuple[bool, Dict]:
        """
        Validate complete optimization solution.
        
        Args:
            weights: Portfolio weights
            returns: Historical returns
            constraints: Constraint dictionary
            
        Returns:
            (valid, validation report)
        """
        report = {
            'weights_valid': False,
            'constraints_satisfied': False,
            'violations': []
        }
        
        # Validate weights
        min_weight = constraints.get('min_weight', 0.0)
        max_weight = constraints.get('max_weight', 1.0)
        weights_valid, weight_violations = self.validate_weights(
            weights, min_weight, max_weight
        )
        
        report['weights_valid'] = weights_valid
        report['violations'].extend(weight_violations)
        
        # TODO: Add more constraint checks in later chunks
        
        report['constraints_satisfied'] = len(report['violations']) == 0
        
        return report['constraints_satisfied'], report
