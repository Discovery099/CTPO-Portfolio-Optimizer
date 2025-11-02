"""
Constraints module for CDPR force balance and portfolio constraints
"""

import numpy as np
import cvxpy as cp
from typing import List, Tuple, Optional, Dict


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
        n_nonzero = np.sum(weights > 1e-6)
        return n_nonzero >= self.min_assets


def construct_structure_matrix(beta: np.ndarray, 
                               volatilities: np.ndarray, 
                               stiffness: float = 310.0) -> np.ndarray:
    """
    Construct CDPR structure matrix A ∈ ℝ^{3×n}.
    
    Columns represent cable directions in force space:
    - Row 0: Return direction (CAPM betas)
    - Row 1: Risk direction (volatilities)
    - Row 2: Diversification direction (uniform)
    
    Args:
        beta: Asset betas (N,)
        volatilities: Asset volatilities (N,)
        stiffness: Cable stiffness parameter (k_c)
        
    Returns:
        Structure matrix A (3 x N)
    """
    n = len(beta)
    A = np.zeros((3, n))
    
    A[0, :] = beta / stiffness
    A[1, :] = volatilities / stiffness
    A[2, :] = np.ones(n) / stiffness
    
    return A


def construct_wrench_vector(target_return: float = 0.08,
                            max_risk: float = 0.15,
                            min_eff_assets: int = 20) -> np.ndarray:
    """
    Construct external wrench vector W ∈ ℝ^3.
    
    Represents portfolio objectives in force space:
    - W[0]: Target return
    - W[1]: Maximum acceptable risk
    - W[2]: Diversification target (1/N_eff)
    
    Args:
        target_return: Target portfolio return (annual)
        max_risk: Maximum portfolio volatility
        min_eff_assets: Minimum effective number of assets
        
    Returns:
        Wrench vector W (3,)
    """
    W = np.array([
        target_return,
        max_risk,
        1.0 / min_eff_assets
    ])
    
    return W


def build_constraints(w, 
                     w_prev: np.ndarray,
                     w_baseline: np.ndarray,
                     A: np.ndarray,
                     W: np.ndarray,
                     params: Dict) -> List:
    """
    Build CVXPY constraints - PURE MEAN-VARIANCE (ALL CDPR REMOVED)
    
    Only essential portfolio constraints remain:
    1. Capital conservation: sum(w) = 1
    2. Long-only: w >= 0
    3. Position limits: w <= position_max
    
    ALL CDPR force balance and diversification constraints REMOVED.
    
    Args:
        w: Portfolio weight variable (CVXPY)
        w_prev: Previous weights - NOT USED
        w_baseline: Baseline weights - NOT USED
        A: Structure matrix - NOT USED (CDPR removed)
        W: Wrench vector - NOT USED (CDPR removed)
        params: Parameter dictionary
        
    Returns:
        List of CVXPY constraints
    """
    import cvxpy as cp
    
    constraints = []
    n_assets = len(w_baseline)
    
    # === Capital conservation: Σw_i = 1 ===
    constraints.append(cp.sum(w) == 1)
    
    # === Long-only: no shorting ===
    constraints.append(w >= 0)
    
    # === Position limits ===
    position_max = params.get('position_max', 0.50)  # Increased to 50% - allow high concentration
    
    # Only enforce if significantly above equal-weight
    # This allows the optimizer to concentrate on best assets
    if position_max < 0.40:
        position_max = 0.50  # Override low limits
    
    constraints.append(w <= position_max)
    
    # ALL OTHER CONSTRAINTS REMOVED (diversification, force balance, etc.)
    
    return constraints


def force_balance_residual(weights: np.ndarray,
                           A: np.ndarray,
                           W: np.ndarray,
                           tolerance: float = 0.0018) -> Tuple[bool, float]:
    """
    Check CDPR force balance constraint: ||A @ w - W|| ≤ ε
    
    This is the core CDPR constraint mapping cable tensions (weights)
    to external forces (portfolio objectives).
    
    Args:
        weights: Portfolio weights (N,)
        A: Structure matrix (3 x N)
        W: Wrench vector (3,)
        tolerance: Force balance tolerance (ε)
        
    Returns:
        (satisfied: bool, residual: float)
    """
    residual = np.linalg.norm(A @ weights - W)
    satisfied = residual <= tolerance
    
    return satisfied, residual


def compute_workspace_constraint(weights: np.ndarray,
                                 weights_baseline: np.ndarray,
                                 max_deviation: float = 0.92) -> Tuple[bool, float]:
    """
    Ensure portfolio stays within workspace (reachable region).
    
    Constraint: ||w - w_baseline||_1 ≤ δ
    
    Args:
        weights: Current portfolio weights (N,)
        weights_baseline: Baseline weights (N,)
        max_deviation: Maximum L1 deviation allowed (δ)
        
    Returns:
        (satisfied: bool, deviation: float)
    """
    deviation = np.sum(np.abs(weights - weights_baseline))
    satisfied = deviation <= max_deviation
    
    return satisfied, deviation


def compute_effective_n_assets(weights: np.ndarray, threshold: float = 1e-6) -> float:
    """
    Compute effective number of portfolio assets (ENP).
    
    ENP = 1 / sum(w_i^2) for non-zero weights
    
    Higher ENP indicates better diversification.
    
    Args:
        weights: Portfolio weights (N,)
        threshold: Minimum weight to consider non-zero
        
    Returns:
        Effective number of assets
    """
    active_weights = weights[weights > threshold]
    
    if len(active_weights) == 0:
        return 0.0
    
    # Normalize active weights
    active_weights = active_weights / np.sum(active_weights)
    
    # Compute ENP
    enp = 1.0 / np.sum(active_weights ** 2)
    
    return enp


class CDPRValidator:
    """
    Validator for CDPR-based portfolio constraints.
    """
    
    def __init__(self,
                 force_balance_tol: float = 0.0018,
                 workspace_constraint: float = 0.92,
                 min_effective_assets: int = 20):
        """
        Initialize CDPR validator.
        
        Args:
            force_balance_tol: Force balance tolerance
            workspace_constraint: Max workspace deviation
            min_effective_assets: Minimum ENP
        """
        self.force_balance_tol = force_balance_tol
        self.workspace_constraint = workspace_constraint
        self.min_effective_assets = min_effective_assets
    
    def validate_solution(self,
                         weights: np.ndarray,
                         A: np.ndarray,
                         W: np.ndarray,
                         weights_baseline: Optional[np.ndarray] = None) -> Tuple[bool, dict]:
        """
        Validate complete CDPR solution.
        
        Args:
            weights: Portfolio weights
            A: Structure matrix
            W: Wrench vector
            weights_baseline: Baseline weights for workspace check
            
        Returns:
            (valid: bool, report: dict)
        """
        report = {
            'force_balance_satisfied': False,
            'workspace_satisfied': True,
            'diversification_satisfied': False,
            'force_residual': 0.0,
            'workspace_deviation': 0.0,
            'effective_n_assets': 0.0,
            'violations': []
        }
        
        # Check force balance
        fb_satisfied, fb_residual = force_balance_residual(
            weights, A, W, self.force_balance_tol
        )
        report['force_balance_satisfied'] = fb_satisfied
        report['force_residual'] = fb_residual
        
        if not fb_satisfied:
            report['violations'].append(f"Force balance violated: residual={fb_residual:.6f}")
        
        # Check workspace constraint
        if weights_baseline is not None:
            ws_satisfied, ws_deviation = compute_workspace_constraint(
                weights, weights_baseline, self.workspace_constraint
            )
            report['workspace_satisfied'] = ws_satisfied
            report['workspace_deviation'] = ws_deviation
            
            if not ws_satisfied:
                report['violations'].append(f"Workspace constraint violated: deviation={ws_deviation:.6f}")
        
        # Check diversification
        enp = compute_effective_n_assets(weights)
        report['effective_n_assets'] = enp
        report['diversification_satisfied'] = enp >= self.min_effective_assets
        
        if not report['diversification_satisfied']:
            report['violations'].append(f"Diversification insufficient: ENP={enp:.2f} < {self.min_effective_assets}")
        
        # Overall validity
        valid = (report['force_balance_satisfied'] and 
                report['workspace_satisfied'] and 
                report['diversification_satisfied'])
        
        return valid, report
