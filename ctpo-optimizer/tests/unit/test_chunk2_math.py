"""
Unit tests for CHUNK 2 mathematical components
"""

import pytest
import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ctpo.risk.capm import CAPMModel
from ctpo.risk.correlation import StressCorrelation
from ctpo.risk.garch import GARCHModel, estimate_garch_volatilities
from ctpo.core.constraints import (
    construct_structure_matrix,
    construct_wrench_vector,
    force_balance_residual,
    compute_workspace_constraint,
    compute_effective_n_assets,
    CDPRValidator
)
from ctpo.core.optimizer import CTPOState


class TestCAPMModel:
    """Test CAPM with stress correction."""
    
    def test_beta_calculation(self):
        """Test beta calculation from returns."""
        np.random.seed(42)
        market_returns = np.random.randn(100) * 0.01
        
        # Create correlated asset returns
        returns = np.zeros((100, 5))
        for i in range(5):
            beta_true = 0.5 + i * 0.3  # Betas: 0.5, 0.8, 1.1, 1.4, 1.7
            returns[:, i] = beta_true * market_returns + np.random.randn(100) * 0.005
        
        capm = CAPMModel()
        betas = capm.calculate_betas(returns, market_returns)
        
        assert len(betas) == 5
        assert np.all(betas > 0)
        # Betas should be roughly increasing
        assert betas[4] > betas[0]
    
    def test_stress_correction(self):
        """Test stress penalty activation."""
        capm = CAPMModel(lambda_stress=0.15, vol_threshold=0.23, rho_threshold=0.85)
        
        betas = np.array([1.0, 1.0, 1.0])
        
        # Low volatility - no stress
        expected_low = capm.compute_expected_returns(
            betas, sigma_market=0.15, rho_stress=np.array([0.9, 0.9, 0.9])
        )
        
        # High volatility - stress activated
        expected_high = capm.compute_expected_returns(
            betas, sigma_market=0.35, rho_stress=np.array([0.9, 0.9, 0.9])
        )
        
        # High volatility should reduce expected returns
        assert np.all(expected_high < expected_low)
    
    def test_expected_returns_estimation(self):
        """Test full expected returns estimation."""
        np.random.seed(42)
        returns = np.random.randn(100, 5) * 0.01 + 0.001
        
        capm = CAPMModel()
        expected_returns, betas = capm.estimate_expected_returns(returns)
        
        assert len(expected_returns) == 5
        assert len(betas) == 5
        assert not np.any(np.isnan(expected_returns))
        assert not np.any(np.isnan(betas))


class TestStressCorrelation:
    """Test stress-adjusted correlation."""
    
    def test_stress_level_computation(self):
        """Test stress level calculation."""
        stress_corr = StressCorrelation(vol_threshold=0.23)
        
        # Low volatility
        alpha_low = stress_corr.compute_stress_level(0.15)
        assert alpha_low == 0.0
        
        # At threshold
        alpha_thresh = stress_corr.compute_stress_level(0.23)
        assert alpha_thresh == 0.0
        
        # High volatility
        alpha_high = stress_corr.compute_stress_level(0.40)
        assert alpha_high > 0.0
        assert alpha_high <= 1.0
    
    def test_correlation_estimation(self):
        """Test correlation matrix estimation."""
        np.random.seed(42)
        returns = np.random.randn(100, 5) * 0.01
        
        stress_corr = StressCorrelation()
        correlation = stress_corr.estimate_correlation(returns)
        
        assert correlation.shape == (5, 5)
        assert np.allclose(correlation, correlation.T)
        assert np.allclose(np.diag(correlation), 1.0)
        assert np.all(correlation >= -1.0)
        assert np.all(correlation <= 1.0)
    
    def test_stress_application(self):
        """Test stress application to correlation."""
        np.random.seed(42)
        returns = np.random.randn(100, 5) * 0.01
        
        stress_corr = StressCorrelation(max_corr=0.85)
        
        # Low stress
        P_low, alpha_low = stress_corr.apply_stress(
            returns=returns, sigma_market=0.15
        )
        
        # High stress
        P_high, alpha_high = stress_corr.apply_stress(
            returns=returns, sigma_market=0.40
        )
        
        assert P_low.shape == P_high.shape == (5, 5)
        assert alpha_high > alpha_low
        assert np.all(P_low <= 0.85)
        assert np.all(P_high <= 0.85)
    
    def test_covariance_conditioning(self):
        """Test covariance conditioning for stability."""
        # Create ill-conditioned matrix
        n = 5
        Sigma = np.eye(n)
        Sigma[0, 0] = 1e6  # Very large eigenvalue
        Sigma[-1, -1] = 1e-6  # Very small eigenvalue
        
        stress_corr = StressCorrelation()
        Sigma_conditioned = stress_corr.condition_covariance(Sigma, max_cond=1e4)
        
        # Check condition number improved
        cond_original = np.linalg.cond(Sigma)
        cond_new = np.linalg.cond(Sigma_conditioned)
        
        assert cond_new < cond_original
        assert cond_new <= 1e4 * 1.1  # Allow small tolerance


class TestGARCHModel:
    """Test GARCH volatility estimation."""
    
    def test_garch_fit(self):
        """Test GARCH model fitting."""
        np.random.seed(42)
        returns = np.random.randn(200) * 0.01
        
        model = GARCHModel(p=1, q=1)
        model.fit(returns)
        
        assert model.conditional_volatility is not None
        assert len(model.conditional_volatility) == len(returns)
    
    def test_volatility_forecast(self):
        """Test volatility forecasting."""
        np.random.seed(42)
        returns = np.random.randn(200) * 0.01
        
        model = GARCHModel()
        model.fit(returns)
        
        vol_forecast = model.forecast_volatility(horizon=1)
        
        assert vol_forecast > 0
        assert vol_forecast < 1.0
    
    def test_batch_volatility_estimation(self):
        """Test batch GARCH estimation."""
        np.random.seed(42)
        returns_df = pd.DataFrame(
            np.random.randn(200, 5) * 0.01,
            columns=['A', 'B', 'C', 'D', 'E']
        )
        
        volatilities = estimate_garch_volatilities(returns_df)
        
        assert len(volatilities) == 5
        assert np.all(volatilities > 0)
        assert np.all(volatilities < 1.0)


class TestCDPRConstraints:
    """Test CDPR force balance constraints."""
    
    def test_structure_matrix_construction(self):
        """Test structure matrix A construction."""
        betas = np.array([0.8, 1.0, 1.2, 0.9, 1.1])
        volatilities = np.array([0.15, 0.18, 0.12, 0.20, 0.16])
        
        A = construct_structure_matrix(betas, volatilities, stiffness=310.0)
        
        assert A.shape == (3, 5)
        assert np.all(np.isfinite(A))
        # Third row should be uniform
        assert np.allclose(A[2, :], A[2, 0])
    
    def test_wrench_vector_construction(self):
        """Test wrench vector W construction."""
        W = construct_wrench_vector(
            target_return=0.08,
            max_risk=0.15,
            min_eff_assets=20
        )
        
        assert len(W) == 3
        assert W[0] == 0.08
        assert W[1] == 0.15
        assert W[2] == 1.0 / 20
    
    def test_force_balance_residual(self):
        """Test force balance checking."""
        # Create feasible solution
        n = 10
        weights = np.ones(n) / n
        betas = np.ones(n)
        volatilities = np.ones(n) * 0.15
        
        A = construct_structure_matrix(betas, volatilities)
        
        # Compute wrench that matches equal weights
        W = A @ weights
        
        satisfied, residual = force_balance_residual(weights, A, W, tolerance=0.01)
        
        assert residual < 1e-10  # Should be very small
        assert satisfied
    
    def test_workspace_constraint(self):
        """Test workspace constraint."""
        weights = np.array([0.2, 0.3, 0.2, 0.3])
        weights_baseline = np.array([0.25, 0.25, 0.25, 0.25])
        
        satisfied, deviation = compute_workspace_constraint(
            weights, weights_baseline, max_deviation=0.5
        )
        
        assert deviation > 0
        assert satisfied  # Small change should satisfy
    
    def test_effective_n_assets(self):
        """Test ENP calculation."""
        # Equal weights
        weights_equal = np.ones(10) / 10
        enp_equal = compute_effective_n_assets(weights_equal)
        assert np.isclose(enp_equal, 10.0, rtol=0.01)
        
        # Concentrated portfolio
        weights_conc = np.array([0.8, 0.1, 0.05, 0.05])
        enp_conc = compute_effective_n_assets(weights_conc)
        assert enp_conc < 4.0


class TestCDPRValidator:
    """Test CDPR solution validator."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = CDPRValidator(
            force_balance_tol=0.0018,
            workspace_constraint=0.92,
            min_effective_assets=20
        )
        
        assert validator.force_balance_tol == 0.0018
        assert validator.workspace_constraint == 0.92
        assert validator.min_effective_assets == 20
    
    def test_solution_validation(self):
        """Test complete solution validation."""
        n = 25
        weights = np.ones(n) / n  # Equal weights
        betas = np.ones(n)
        volatilities = np.ones(n) * 0.15
        
        A = construct_structure_matrix(betas, volatilities)
        W = A @ weights
        
        validator = CDPRValidator(min_effective_assets=20)
        valid, report = validator.validate_solution(weights, A, W)
        
        assert 'force_balance_satisfied' in report
        assert 'effective_n_assets' in report
        assert report['effective_n_assets'] >= 20


class TestCTPOState:
    """Test state management."""
    
    def test_state_initialization(self):
        """Test state initialization."""
        state = CTPOState(n_assets=10)
        
        assert state.n == 10
        assert len(state.w) == 10
        assert len(state.mu) == 10
        assert state.Sigma.shape == (10, 10)
        assert np.isclose(np.sum(state.w), 1.0)
    
    def test_state_update(self):
        """Test state update from data."""
        np.random.seed(42)
        returns = np.random.randn(100, 10) * 0.01
        
        state = CTPOState(n_assets=10)
        state.update_from_data(returns)
        
        assert len(state.mu) == 10
        assert state.Sigma.shape == (10, 10)
        assert state.sigma_market > 0
        assert 0 <= state.rho_realized <= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
