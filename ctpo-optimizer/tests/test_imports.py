"""
Basic import test
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_import_core():
    """Test core module imports."""
    from ctpo.core.optimizer import CTPOOptimizer
    from ctpo.core.constraints import CableConstraints, PortfolioConstraints
    from ctpo.core.objective import ObjectiveFunction
    
    assert CTPOOptimizer is not None
    assert CableConstraints is not None
    assert PortfolioConstraints is not None
    assert ObjectiveFunction is not None


def test_import_risk():
    """Test risk module imports."""
    from ctpo.risk.garch import GARCHModel
    from ctpo.risk.correlation import StressCorrelation
    from ctpo.risk.capm import CAPMModel
    
    assert GARCHModel is not None
    assert StressCorrelation is not None
    assert CAPMModel is not None


def test_import_data():
    """Test data module imports."""
    from ctpo.data.fetcher import DataFetcher
    from ctpo.data.preprocessor import DataPreprocessor
    
    assert DataFetcher is not None
    assert DataPreprocessor is not None


def test_import_execution():
    """Test execution module imports."""
    from ctpo.execution.backtester import Backtester
    from ctpo.execution.paper_trader import PaperTrader
    from ctpo.execution.alpaca_broker import MockAlpacaBroker
    
    assert Backtester is not None
    assert PaperTrader is not None
    assert MockAlpacaBroker is not None


def test_import_metrics():
    """Test metrics module imports."""
    from ctpo.metrics.performance import PerformanceMetrics
    
    assert PerformanceMetrics is not None


def test_import_utils():
    """Test utils module imports."""
    from ctpo.utils.matrix_ops import MatrixOps
    from ctpo.utils.validators import PortfolioValidator
    
    assert MatrixOps is not None
    assert PortfolioValidator is not None


def test_package_import():
    """Test main package import."""
    import ctpo
    from ctpo import CTPOOptimizer, DataFetcher
    
    assert ctpo.__version__ == "0.1.0"
    assert CTPOOptimizer is not None
    assert DataFetcher is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
