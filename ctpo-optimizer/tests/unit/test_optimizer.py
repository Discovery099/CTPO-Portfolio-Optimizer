"""
Unit tests for CTPO optimizer
"""

import pytest
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ctpo.core.optimizer import CTPOOptimizer
from ctpo.core.constraints import CableConstraints, PortfolioConstraints
from ctpo.core.objective import ObjectiveFunction


def test_optimizer_initialization():
    """Test optimizer can be initialized."""
    optimizer = CTPOOptimizer()
    assert optimizer is not None
    assert optimizer.config is not None


def test_optimizer_basic_optimization():
    """Test basic optimization returns valid weights."""
    optimizer = CTPOOptimizer()
    
    # Create dummy returns data
    np.random.seed(42)
    n_days = 100
    n_assets = 10
    returns = np.random.randn(n_days, n_assets) * 0.01
    
    # Run optimization
    weights = optimizer.optimize(returns)
    
    # Check weights are valid
    assert weights is not None
    assert len(weights) == n_assets
    assert np.abs(np.sum(weights) - 1.0) < 1e-6
    assert np.all(weights >= 0)


def test_cable_constraints():
    """Test cable constraint checking."""
    constraints = CableConstraints(min_tension=0.01, max_tension=0.25)
    
    # Valid weights
    valid_weights = np.array([0.1, 0.2, 0.15, 0.15, 0.1, 0.1, 0.1, 0.1])
    violation = constraints.force_balance_constraint(valid_weights)
    assert violation < 1e-6
    
    # Test tension limits
    satisfied, violations = constraints.tension_limits(valid_weights)
    assert satisfied


def test_portfolio_constraints():
    """Test portfolio constraint checking."""
    constraints = PortfolioConstraints(min_assets=5, max_leverage=1.0)
    
    # Diversified portfolio
    weights = np.array([0.2, 0.2, 0.2, 0.2, 0.2])
    satisfied = constraints.diversification_constraint(weights)
    assert satisfied


def test_objective_function():
    """Test objective function evaluation."""
    objective = ObjectiveFunction(var_confidence=0.95)
    
    # Create dummy data
    np.random.seed(42)
    returns = np.random.randn(100, 5) * 0.01
    weights = np.ones(5) / 5
    
    # Evaluate objective
    obj_value = objective.evaluate(weights, returns)
    assert obj_value > 0
    assert not np.isnan(obj_value)
    assert not np.isinf(obj_value)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
