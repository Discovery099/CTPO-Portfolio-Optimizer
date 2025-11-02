"""
CHUNK 2 - Mathematical Foundation Demo

Demonstrates all mathematical components implemented in CHUNK 2.
"""

import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ctpo.core.optimizer import CTPOOptimizer, CTPOState
from ctpo.risk.capm import CAPMModel
from ctpo.risk.correlation import StressCorrelation
from ctpo.risk.garch import estimate_garch_volatilities
from ctpo.core.constraints import (
    construct_structure_matrix,
    construct_wrench_vector,
    force_balance_residual,
    compute_effective_n_assets,
    CDPRValidator
)

print("="*70)
print("CTPO CHUNK 2 - Mathematical Foundation Demonstration")
print("="*70)
print()

# Generate synthetic market data
np.random.seed(42)
n_days = 252
n_assets = 25

print(f"Generating synthetic data: {n_days} days, {n_assets} assets")
print()

# Create correlated returns
market_returns = np.random.randn(n_days) * 0.015 + 0.0005
returns = np.zeros((n_days, n_assets))

for i in range(n_assets):
    beta = 0.5 + i * 0.1  # Varying betas
    idiosyncratic = np.random.randn(n_days) * 0.01
    returns[:, i] = beta * market_returns + idiosyncratic

returns_df = pd.DataFrame(returns, columns=[f'Asset_{i}' for i in range(n_assets)])

# 1. CAPM with Stress Correction
print("1. CAPM Model with Stress Correction")
print("-" * 70)

capm = CAPMModel(
    risk_free_rate=0.042,
    lambda_stress=0.15,
    vol_threshold=0.23,
    rho_threshold=0.85
)

expected_returns, betas = capm.estimate_expected_returns(returns, market_returns)

print(f"   Betas (first 5): {betas[:5]}")
print(f"   Expected Returns (first 5): {expected_returns[:5]}")
print(f"   Market Volatility: {np.std(market_returns) * np.sqrt(252):.4f}")
print()

# Demonstrate stress impact
low_vol = 0.15
high_vol = 0.35

expected_low = capm.compute_expected_returns(betas, low_vol, rho_stress=np.array([0.9]*n_assets))
expected_high = capm.compute_expected_returns(betas, high_vol, rho_stress=np.array([0.9]*n_assets))

print(f"   Expected return (Asset 0) at low vol ({low_vol}): {expected_low[0]:.4f}")
print(f"   Expected return (Asset 0) at high vol ({high_vol}): {expected_high[0]:.4f}")
print(f"   Stress penalty applied: {expected_low[0] - expected_high[0]:.4f}")
print()

# 2. Stress-Adjusted Correlation
print("2. Stress-Adjusted Correlation Matrix")
print("-" * 70)

stress_corr = StressCorrelation(
    vol_threshold=0.23,
    max_corr=0.85,
    shrinkage_target=0.25
)

# Estimate volatilities
volatilities = estimate_garch_volatilities(returns_df)
print(f"   GARCH Volatilities (first 5): {volatilities[:5]}")
print()

# Compute stress covariance
sigma_market_low = 0.15
Sigma_low, alpha_low = stress_corr.compute_stress_covariance(
    returns_df, volatilities, sigma_market_low
)

sigma_market_high = 0.35
Sigma_high, alpha_high = stress_corr.compute_stress_covariance(
    returns_df, volatilities, sigma_market_high
)

print(f"   Low volatility stress level (α): {alpha_low:.4f}")
print(f"   High volatility stress level (α): {alpha_high:.4f}")
print(f"   Covariance condition number (low stress): {np.linalg.cond(Sigma_low):.2f}")
print(f"   Covariance condition number (high stress): {np.linalg.cond(Sigma_high):.2f}")
print()

# 3. CDPR Force Balance
print("3. CDPR Force Balance Mapping")
print("-" * 70)

# Construct structure matrix
A = construct_structure_matrix(betas, volatilities, stiffness=310.0)
print(f"   Structure matrix A shape: {A.shape}")
print(f"   A matrix (first 3 columns):")
print(f"   {A[:, :3]}")
print()

# Construct wrench vector
W = construct_wrench_vector(
    target_return=0.08,
    max_risk=0.15,
    min_eff_assets=20
)
print(f"   Wrench vector W: {W}")
print()

# Test with equal weights
weights_equal = np.ones(n_assets) / n_assets
force_applied = A @ weights_equal

print(f"   Equal weights force: {force_applied}")
print(f"   Target wrench: {W}")
print(f"   Residual: {np.linalg.norm(force_applied - W):.6f}")

satisfied, residual = force_balance_residual(weights_equal, A, W, tolerance=0.1)
print(f"   Force balance satisfied (tol=0.1): {satisfied}")
print()

# 4. Diversification Metrics
print("4. Portfolio Diversification")
print("-" * 70)

enp_equal = compute_effective_n_assets(weights_equal)
print(f"   Equal weights ENP: {enp_equal:.2f}")

# Concentrated portfolio
weights_conc = np.zeros(n_assets)
weights_conc[0] = 0.5
weights_conc[1:] = 0.5 / (n_assets - 1)

enp_conc = compute_effective_n_assets(weights_conc)
print(f"   Concentrated portfolio ENP: {enp_conc:.2f}")
print()

# 5. CDPR Validator
print("5. CDPR Solution Validation")
print("-" * 70)

validator = CDPRValidator(
    force_balance_tol=0.1,
    workspace_constraint=0.92,
    min_effective_assets=20
)

valid, report = validator.validate_solution(weights_equal, A, W)

print(f"   Solution valid: {valid}")
print(f"   Force balance satisfied: {report['force_balance_satisfied']}")
print(f"   Diversification satisfied: {report['diversification_satisfied']}")
print(f"   Effective N assets: {report['effective_n_assets']:.2f}")
print(f"   Force residual: {report['force_residual']:.6f}")
print()

# 6. State Management
print("6. CTPO State Management")
print("-" * 70)

state = CTPOState(n_assets=n_assets)
state.update_from_data(returns, market_returns)

print(f"   State initialized for {state.n} assets")
print(f"   Expected returns (first 5): {state.mu[:5]}")
print(f"   Market volatility: {state.sigma_market:.4f}")
print(f"   Average correlation: {state.rho_realized:.4f}")
print(f"   Covariance condition number: {np.linalg.cond(state.Sigma):.2f}")
print()

# 7. Optimizer Integration
print("7. Optimizer with Mathematical Components")
print("-" * 70)

optimizer = CTPOOptimizer()
weights = optimizer.optimize(returns, market_returns=market_returns)

metrics = optimizer.get_metrics()

print(f"   Optimization complete")
print(f"   Weights sum: {weights.sum():.6f}")
print(f"   State market volatility: {metrics['market_volatility']:.4f}")
print(f"   State stress level: {metrics['stress_level']:.4f}")
print(f"   State avg correlation: {metrics['avg_correlation']:.4f}")
print()

print("="*70)
print("CHUNK 2 Implementation Complete!")
print("="*70)
print()
print("Next Steps (CHUNK 3):")
print("  - Implement full CVXPY-based CDPR optimization")
print("  - Add crisis period backtesting")
print("  - Parameter sensitivity analysis")
print("  - Live demo notebooks")
