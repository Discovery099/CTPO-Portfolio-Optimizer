# Mathematical Derivation of CTPO

## Overview

This document outlines the mathematical foundation for mapping Cable-Driven Parallel Robot (CDPR) force distribution to portfolio optimization.

## 1. CDPR Fundamentals

### Force Balance Equation

In a CDPR system with N cables, the force balance equation is:

```
A * f = w
```

Where:
- `A` ∈ ℝ^(6×N): Structure matrix (cable geometry)
- `f` ∈ ℝ^N: Cable tension vector (f_i ≥ 0)
- `w` ∈ ℝ^6: External wrench (forces + moments)

### Tension Constraints

Each cable must satisfy:

```
f_min ≤ f_i ≤ f_max
```

All tensions must be positive (cables can only pull, not push).

## 2. Portfolio Mapping

### Analogy

| CDPR Concept | Portfolio Equivalent |
|--------------|---------------------|
| Cable tension f_i | Portfolio weight w_i |
| Force balance ∑(A_ij * f_i) = w_j | Weight constraint ∑w_i = 1 |
| Minimum tension | Minimum position size |
| Maximum tension | Maximum position size |
| Wrench feasibility | Portfolio feasibility |

### Force Balance → Portfolio Constraint

```
∑(w_i) = 1
w_min ≤ w_i ≤ w_max
w_i ≥ 0 (long-only)
```

## 3. Optimization Problem

### Objective Function

Minimize portfolio risk measured by Value at Risk (VaR):

```
minimize: VaR_α(w) + λ * R(w)
```

Where:
- `VaR_α(w)`: Value at Risk at confidence level α (typically 95% or 99%)
- `R(w)`: Regularization term (prevents extreme positions)
- `λ`: Regularization parameter

### Constraints

1. **Force Balance (Portfolio)**: ∑w_i = 1
2. **Tension Limits (Position Limits)**: w_min ≤ w_i ≤ w_max
3. **Non-negativity**: w_i ≥ 0
4. **Diversification**: At least N_min assets with w_i > threshold
5. **CDPR Stability**: Condition number of covariance matrix < κ_max

### VaR Calculation

Parametric VaR (assuming normal distribution):

```
VaR_α(w) = -z_α * σ_p(w)
```

Where:
- `z_α`: α-quantile of standard normal (e.g., z_0.95 = 1.645)
- `σ_p(w) = √(w^T * Σ * w)`: Portfolio volatility
- `Σ`: Covariance matrix

### Regularization Term

L2 regularization to prevent concentration:

```
R(w) = ||w||_2^2 = ∑(w_i^2)
```

## 4. Stress Testing Enhancement

### Correlation Stress

During market stress, correlations tend toward 1. Apply stress factor:

```
Σ_stress = Σ_base + β * (J - Σ_base)
```

Where:
- `J`: Matrix of ones (perfect correlation)
- `β ∈ [0,1]`: Stress intensity

### GARCH Volatility

Use GARCH(1,1) for time-varying volatility:

```
σ_t^2 = ω + α * ε_{t-1}^2 + β * σ_{t-1}^2
```

## 5. Numerical Stability

### Covariance Conditioning

To ensure numerical stability:

```
Σ_conditioned = (1-α) * Σ + α * trace(Σ)/N * I
```

Where:
- `α ∈ [0,1]`: Shrinkage parameter (Ledoit-Wolf)
- `I`: Identity matrix
- Target condition number: κ(Σ) < 10^4

## 6. Solution Method

Use convex optimization (CVXPY) with ECOS solver:

```python
import cvxpy as cp

# Decision variable
w = cp.Variable(n_assets)

# Objective: minimize VaR + regularization
objective = cp.Minimize(
    cp.sqrt(cp.quad_form(w, Sigma)) + lambda_reg * cp.sum_squares(w)
)

# Constraints
constraints = [
    cp.sum(w) == 1,           # Force balance
    w >= w_min,               # Minimum tension
    w <= w_max,               # Maximum tension
    cp.sum(w >= threshold) >= n_min  # Diversification
]

# Solve
problem = cp.Problem(objective, constraints)
problem.solve(solver='ECOS')
```

## References

1. Pott, A., & Bruckmann, T. (2019). *Cable-Driven Parallel Robots*
2. Markowitz, H. (1952). *Portfolio Selection*
3. Rockafellar, R.T., & Uryasev, S. (2000). *Optimization of CVaR*

---

**Status**: Mathematical framework defined (CHUNK 1)

**Next**: Implement full optimization algorithm (CHUNK 2)
