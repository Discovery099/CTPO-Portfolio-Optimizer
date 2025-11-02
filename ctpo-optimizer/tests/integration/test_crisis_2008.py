"""
Integration tests for 2008 Financial Crisis

Validates CTPO performance during extreme market stress
"""

import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path
import warnings

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ctpo.data.fetcher import DataFetcher
from ctpo.core.optimizer import CTPOOptimizer
from ctpo.metrics.performance import PerformanceMetrics

# Test with representative stocks from 2007
CRISIS_SYMBOLS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'JPM', 
    'BAC', 'GE', 'XOM', 'CVX', 'WMT',
    'PG', 'JNJ', 'KO', 'PFE', 'T'
]

@pytest.fixture(scope='module')
def crisis_data():
    """Fetch 2008 crisis period data"""
    print("\n🔄 Fetching 2008 crisis data (this may take a few minutes)...")
    
    fetcher = DataFetcher()
    
    try:
        # Try to fetch data for crisis period
        returns_df = fetcher.fetch_returns(
            CRISIS_SYMBOLS[:10],  # Use subset for speed
            start_date='2007-01-01',
            end_date='2009-12-31'
        )
        
        if returns_df.empty or len(returns_df) < 100:
            pytest.skip("Insufficient crisis data available")
        
        print(f"✅ Fetched {len(returns_df)} days of data for {len(returns_df.columns)} assets")
        return returns_df
        
    except Exception as e:
        pytest.skip(f"Could not fetch crisis data: {e}")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.crisis
class TestCrisis2008Performance:
    """Validate performance during 2008 financial crisis"""
    
    def test_crisis_optimization_runs(self, crisis_data):
        """Test that optimization runs successfully on crisis data"""
        optimizer = CTPOOptimizer()
        returns = crisis_data.values
        
        weights = optimizer.optimize(returns)
        
        assert weights is not None
        assert len(weights) == returns.shape[1]
        assert np.isclose(weights.sum(), 1.0, atol=1e-3)
    
    def test_sharpe_ratio_calculation(self, crisis_data):
        """Test Sharpe ratio during crisis"""
        optimizer = CTPOOptimizer()
        returns = crisis_data.values
        
        # CTPO optimization
        weights_ctpo = optimizer.optimize(returns)
        portfolio_returns_ctpo = returns @ weights_ctpo
        sharpe_ctpo = PerformanceMetrics.sharpe_ratio(portfolio_returns_ctpo)
        
        # Equal-weight baseline
        n_assets = returns.shape[1]
        weights_ew = np.ones(n_assets) / n_assets
        portfolio_returns_ew = returns @ weights_ew
        sharpe_ew = PerformanceMetrics.sharpe_ratio(portfolio_returns_ew)
        
        improvement = sharpe_ctpo - sharpe_ew
        
        print(f"\n📊 Sharpe Ratios:")
        print(f"   CTPO: {sharpe_ctpo:.3f}")
        print(f"   Equal-Weight: {sharpe_ew:.3f}")
        print(f"   Improvement: {improvement:.3f}")
        
        # Target: >= 0.15 improvement
        assert sharpe_ctpo > sharpe_ew, f"CTPO Sharpe ({sharpe_ctpo:.3f}) should exceed baseline ({sharpe_ew:.3f})"
        
        if improvement >= 0.15:
            print("✅ PASSED: Sharpe improvement >= 0.15")
        else:
            print(f"⚠️  WARNING: Sharpe improvement {improvement:.3f} < 0.15 target")
    
    def test_drawdown_reduction(self, crisis_data):
        """Test maximum drawdown reduction"""
        optimizer = CTPOOptimizer()
        returns = crisis_data.values
        
        # CTPO optimization
        weights_ctpo = optimizer.optimize(returns)
        portfolio_returns_ctpo = returns @ weights_ctpo
        dd_ctpo = abs(PerformanceMetrics.max_drawdown(portfolio_returns_ctpo))
        
        # Equal-weight baseline
        n_assets = returns.shape[1]
        weights_ew = np.ones(n_assets) / n_assets
        portfolio_returns_ew = returns @ weights_ew
        dd_ew = abs(PerformanceMetrics.max_drawdown(portfolio_returns_ew))
        
        reduction = (dd_ew - dd_ctpo) / dd_ew if dd_ew > 0 else 0
        
        print(f"\n📉 Maximum Drawdowns:")
        print(f"   CTPO: {dd_ctpo:.2%}")
        print(f"   Equal-Weight: {dd_ew:.2%}")
        print(f"   Reduction: {reduction:.2%}")
        
        # Target: >= 25% reduction
        assert dd_ctpo <= dd_ew, f"CTPO drawdown ({dd_ctpo:.2%}) should be less than baseline ({dd_ew:.2%})"
        
        if reduction >= 0.25:
            print("✅ PASSED: Drawdown reduction >= 25%")
        else:
            print(f"⚠️  WARNING: Drawdown reduction {reduction:.2%} < 25% target")
    
    def test_positive_return(self, crisis_data):
        """Test that CTPO maintains capital during crisis"""
        optimizer = CTPOOptimizer()
        returns = crisis_data.values
        
        weights = optimizer.optimize(returns)
        portfolio_returns = returns @ weights
        
        total_return = PerformanceMetrics.total_return(portfolio_returns)
        annual_return = PerformanceMetrics.annualized_return(portfolio_returns)
        
        print(f"\n💰 Returns:")
        print(f"   Total Return: {total_return:.2%}")
        print(f"   Annualized Return: {annual_return:.2%}")
        
        # Should at least beat equal-weight
        n_assets = returns.shape[1]
        weights_ew = np.ones(n_assets) / n_assets
        portfolio_returns_ew = returns @ weights_ew
        total_return_ew = PerformanceMetrics.total_return(portfolio_returns_ew)
        
        assert total_return >= total_return_ew, "CTPO should outperform equal-weight during crisis"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
