"""
Unit tests for risk models
"""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ctpo.risk.garch import GARCHModel
from ctpo.risk.correlation import StressCorrelation
from ctpo.risk.capm import CAPMModel


def test_garch_initialization():
    """Test GARCH model initialization."""
    model = GARCHModel(p=1, q=1)
    assert model.p == 1
    assert model.q == 1
    assert model.fitted_model is None


def test_garch_fit():
    """Test GARCH model fitting (skeleton)."""
    model = GARCHModel()
    returns = np.random.randn(100) * 0.01
    
    # Fit should return self
    result = model.fit(returns)
    assert result is model


def test_stress_correlation():
    """Test stress correlation estimation."""
    stress_corr = StressCorrelation(stress_multiplier=1.5)
    
    # Create dummy returns
    np.random.seed(42)
    returns = np.random.randn(100, 5) * 0.01
    
    # Estimate correlation
    correlation = stress_corr.estimate_correlation(returns)
    
    assert correlation.shape == (5, 5)
    assert np.allclose(correlation, correlation.T)  # Symmetric
    assert np.allclose(np.diag(correlation), 1.0)  # Diagonal = 1


def test_capm_model():
    """Test CAPM expected returns."""
    capm = CAPMModel(risk_free_rate=0.02)
    
    # Create dummy returns
    np.random.seed(42)
    returns = np.random.randn(100, 5) * 0.01
    
    # Estimate expected returns
    expected_returns = capm.estimate_expected_returns(returns)
    
    assert len(expected_returns) == 5
    assert not np.any(np.isnan(expected_returns))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
