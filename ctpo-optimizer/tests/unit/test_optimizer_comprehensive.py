"""
Comprehensive unit tests for CTPOOptimizer
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ctpo.core.optimizer import CTPOOptimizer, CTPOState

@pytest.fixture
def optimizer():
    """Create optimizer instance for testing"""
    return CTPOOptimizer()

@pytest.fixture
def mock_returns():
    """Generate synthetic return data"""
    np.random.seed(42)
    n_assets = 10
    n_periods = 252
    
    # Generate returns with reasonable statistics
    returns = np.random.normal(0.0005, 0.02, (n_periods, n_assets))
    return returns

@pytest.mark.unit
class TestOptimizerCore:
    """Core optimization tests"""
    
    def test_convergence_time(self, optimizer, mock_returns):
        """Test that optimization completes within 50ms"""
        import time
        
        start = time.perf_counter()
        weights = optimizer.optimize(mock_returns)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 50, f"Solve time {elapsed_ms:.1f}ms exceeds 50ms limit"
    
    def test_weights_sum_to_one(self, optimizer, mock_returns):
        """Test capital conservation constraint"""
        weights = optimizer.optimize(mock_returns)
        
        assert np.isclose(weights.sum(), 1.0, atol=1e-3), f"Weights sum to {weights.sum():.6f}, not 1.0"
    
    def test_position_limits(self, optimizer, mock_returns):
        """Test individual position constraints"""
        weights = optimizer.optimize(mock_returns)
        
        # Long-only
        assert np.all(weights >= -1e-6), f"Min weight {weights.min():.6f} violates non-negativity"
        
        # Reasonable max
        n_assets = len(weights)
        max_allowed = max(0.5, 1.5 / n_assets)
        assert np.all(weights <= max_allowed + 1e-2), f"Max weight {weights.max():.4f} exceeds limit"
    
    def test_effective_assets(self, optimizer, mock_returns):
        """Test minimum diversification"""
        weights = optimizer.optimize(mock_returns)
        
        enp = 1.0 / np.sum(weights ** 2) if np.sum(weights ** 2) > 0 else 0
        
        # Should maintain reasonable diversification
        assert enp >= 2.0, f"Effective assets {enp:.1f} too low"
    
    def test_leverage_limit(self, optimizer, mock_returns):
        """Test leverage constraint"""
        weights = optimizer.optimize(mock_returns)
        
        leverage = np.sum(np.abs(weights))
        assert leverage <= 2.0, f"Leverage {leverage:.2f} exceeds maximum"
    
    def test_not_equal_weight_fallback(self, optimizer, mock_returns):
        """Test that optimizer produces optimized weights"""
        weights = optimizer.optimize(mock_returns)
        
        # Check variance - should not be all equal
        weight_std = np.std(weights)
        assert weight_std > 0.01, f"Weights too uniform (std={weight_std:.4f}), possible fallback"


@pytest.mark.unit
class TestNumericalStability:
    """Numerical stability tests"""
    
    def test_small_portfolio(self, optimizer):
        """Test with 3 assets"""
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.02, (100, 3))
        
        weights = optimizer.optimize(returns)
        
        assert len(weights) == 3
        assert np.isclose(weights.sum(), 1.0, atol=1e-3)
        assert np.all(weights >= 0)
    
    def test_large_portfolio(self, optimizer):
        """Test with 50 assets"""
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.02, (252, 50))
        
        weights = optimizer.optimize(returns)
        
        assert len(weights) == 50
        assert np.isclose(weights.sum(), 1.0, atol=1e-3)
    
    def test_high_correlation_scenario(self, optimizer):
        """Test with highly correlated assets"""
        np.random.seed(42)
        n_assets = 10
        n_periods = 252
        
        # Create correlated returns
        base = np.random.normal(0.0005, 0.02, n_periods)
        returns = np.column_stack([
            base + np.random.normal(0, 0.005, n_periods)
            for _ in range(n_assets)
        ])
        
        weights = optimizer.optimize(returns)
        
        assert np.isclose(weights.sum(), 1.0, atol=1e-3)
        assert np.all(weights >= 0)


@pytest.mark.unit
class TestStressActivation:
    """Test stress mode functionality"""
    
    def test_stress_level_computation(self, optimizer):
        """Test stress activation computation"""
        alpha_low = optimizer._compute_stress_level(0.10)
        alpha_high = optimizer._compute_stress_level(0.40)
        
        assert 0 <= alpha_low <= 1
        assert 0 <= alpha_high <= 1
        assert alpha_high > alpha_low


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
