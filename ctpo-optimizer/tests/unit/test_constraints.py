"""
Unit tests for constraints
"""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ctpo.core.constraints import CableConstraints, PortfolioConstraints


class TestCableConstraints:
    """Test cable constraint functionality."""
    
    def test_force_balance_valid(self):
        """Test force balance with valid weights."""
        constraints = CableConstraints()
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        violation = constraints.force_balance_constraint(weights)
        assert violation < 1e-10
    
    def test_force_balance_invalid(self):
        """Test force balance with invalid weights."""
        constraints = CableConstraints()
        weights = np.array([0.3, 0.3, 0.3])  # Sum = 0.9, not 1.0
        violation = constraints.force_balance_constraint(weights)
        assert violation > 0.05
    
    def test_tension_limits_satisfied(self):
        """Test tension limits are satisfied."""
        constraints = CableConstraints(min_tension=0.01, max_tension=0.25)
        weights = np.array([0.1, 0.15, 0.2, 0.25, 0.15, 0.15])
        satisfied, violations = constraints.tension_limits(weights)
        assert satisfied
        assert len(violations) == 0
    
    def test_tension_limits_violated(self):
        """Test tension limit violations are detected."""
        constraints = CableConstraints(min_tension=0.01, max_tension=0.25)
        weights = np.array([0.005, 0.3, 0.695])  # First too low, second too high
        satisfied, violations = constraints.tension_limits(weights)
        assert not satisfied
        assert len(violations) == 2


class TestPortfolioConstraints:
    """Test portfolio constraint functionality."""
    
    def test_diversification_satisfied(self):
        """Test diversification constraint is satisfied."""
        constraints = PortfolioConstraints(min_assets=3)
        weights = np.array([0.3, 0.3, 0.3, 0.1])
        satisfied = constraints.diversification_constraint(weights)
        assert satisfied
    
    def test_diversification_violated(self):
        """Test diversification constraint violation."""
        constraints = PortfolioConstraints(min_assets=5)
        weights = np.array([0.5, 0.5, 0, 0, 0])
        satisfied = constraints.diversification_constraint(weights)
        assert not satisfied


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
