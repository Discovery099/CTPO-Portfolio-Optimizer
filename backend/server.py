from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import numpy as np
import pandas as pd

# Import CTPO components
import sys
sys.path.insert(0, '/app/ctpo-optimizer')
from ctpo.core.optimizer import CTPOOptimizer
from ctpo.data.fetcher import DataFetcher
from ctpo.metrics.performance import PerformanceMetrics
from ctpo.risk.capm import CAPMModel
from ctpo.risk.correlation import StressCorrelation
from ctpo.risk.garch import estimate_garch_volatilities
# CDPR constraints removed

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# CTPO Models
class OptimizationRequest(BaseModel):
    tickers: List[str] = Field(default=["AAPL", "GOOGL", "MSFT", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT"])
    period: str = Field(default="1y")
    target_return: float = Field(default=0.08)
    max_risk: float = Field(default=0.15)
    min_effective_assets: int = Field(default=10)
    position_max: float = Field(default=0.20)  # NEW: User-configurable position limit (default 20%)

class BacktestRequest(BaseModel):
    tickers: List[str] = Field(default=["AAPL", "GOOGL", "MSFT", "AMZN", "META"])
    start_date: str = Field(default="2020-01-01")
    end_date: str = Field(default="2023-12-31")
    initial_capital: float = Field(default=1000000)
    rebalance_frequency: str = Field(default="monthly")

class BacktestResult(BaseModel):
    summary: Dict[str, Any]
    portfolio_values: List[float]
    dates: List[str]
    comparison: Optional[Dict[str, Any]] = None

class OptimizationResult(BaseModel):
    weights: Dict[str, float]
    metrics: Dict[str, Any]
    risk_analysis: Dict[str, Any]
    cdpr_analysis: Dict[str, Any]
    performance: Dict[str, Any]

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "CTPO Portfolio Optimizer API"}

@api_router.post("/optimize", response_model=OptimizationResult)
async def optimize_portfolio(request: OptimizationRequest):
    """
    Run CTPO optimization on selected tickers using integrated risk models.
    """
    try:
        # Validate inputs
        if not request.tickers or len(request.tickers) == 0:
            raise HTTPException(
                status_code=400, 
                detail="No tickers provided. Please add at least 2 assets to your portfolio."
            )
        
        if len(request.tickers) == 1:
            raise HTTPException(
                status_code=400, 
                detail="Portfolio optimization requires at least 2 assets. Please add more tickers to your portfolio."
            )
        
        # Validate ticker format (basic check)
        invalid_tickers = [t for t in request.tickers if not t or len(t) > 10 or not t.replace('.', '').replace('-', '').isalnum()]
        if invalid_tickers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ticker format: {', '.join(invalid_tickers)}. Please use valid ticker symbols (e.g., AAPL, GOOGL)."
            )
        
        # Fetch data with enhanced error handling
        fetcher = DataFetcher()
        try:
            returns_df = fetcher.fetch_returns(request.tickers, period=request.period)
        except Exception as fetch_error:
            # Check if it's a ticker not found error
            error_msg = str(fetch_error).lower()
            if 'no data' in error_msg or 'not found' in error_msg or 'invalid' in error_msg:
                # Try to identify which tickers failed
                failed_tickers = []
                for ticker in request.tickers:
                    try:
                        test_df = fetcher.fetch_returns([ticker], period=request.period)
                        if test_df.empty:
                            failed_tickers.append(ticker)
                    except:
                        failed_tickers.append(ticker)
                
                if failed_tickers:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid ticker(s): {', '.join(failed_tickers)} not found. Please check the ticker symbols and try again."
                    )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch market data: {str(fetch_error)}"
            )
        
        if returns_df.empty or len(returns_df) < 50:
            raise HTTPException(
                status_code=400, 
                detail="Insufficient historical data. Portfolio optimization requires at least 50 days of price history. Please try different tickers or a longer time period."
            )
        
        returns = returns_df.values
        
        # Validate we have enough assets after data fetch
        n_assets = returns.shape[1] if len(returns.shape) > 1 else 1
        if n_assets < 2:
            raise HTTPException(
                status_code=400,
                detail="Portfolio optimization requires at least 2 assets with valid data. Please add more tickers."
            )
        
        # Initialize integrated risk model
        from ctpo.risk.risk_model import RiskModel
        
        risk_model = RiskModel(params={
            'risk_free_rate': 0.042,
            'volatility_threshold': 0.23,
            'correlation_breakdown': 0.85,
            'lambda_stress': 0.15
        })
        
        # Update risk model with current data
        try:
            risk_params = risk_model.update(returns_df, market_return=0.10)
        except Exception as risk_error:
            logging.error(f"Risk model error: {str(risk_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to calculate risk metrics. This may be due to insufficient or invalid data: {str(risk_error)}"
            )
        
        # Extract risk parameters
        Sigma = risk_params['Sigma']
        sigma_market = risk_params['sigma_market']
        alpha_stress = risk_params['alpha_stress']
        avg_correlation = risk_params['avg_correlation']
        
        # Run optimization with user-specified position limit
        optimizer = CTPOOptimizer()
        
        try:
            weights = optimizer.optimize(
                returns,
                position_max=request.position_max  # Pass user's position limit
            )
        except Exception as opt_error:
            logging.error(f"Optimization error: {str(opt_error)}")
            error_msg = str(opt_error).lower()
            if 'singular' in error_msg or 'ill-conditioned' in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail="Portfolio optimization failed due to numerical issues. This may occur with highly correlated assets or insufficient data variance. Try different tickers or a longer time period."
                )
            elif 'infeasible' in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail="Portfolio constraints are infeasible. Try adjusting the position limit or selecting different assets."
                )
            raise HTTPException(
                status_code=500,
                detail=f"Optimization failed: {str(opt_error)}"
            )
        
        # Calculate performance metrics
        portfolio_returns = returns @ weights
        sharpe = PerformanceMetrics.sharpe_ratio(portfolio_returns)
        max_dd = PerformanceMetrics.max_drawdown(portfolio_returns)
        sortino = PerformanceMetrics.sortino_ratio(portfolio_returns)
        annual_return = PerformanceMetrics.annualized_return(portfolio_returns)
        
        # Portfolio analysis (simplified - no CDPR)
        enp = 1.0 / np.sum(weights ** 2) if np.sum(weights ** 2) > 0 else 0
        
        # Format response
        result = OptimizationResult(
            weights={ticker: float(w) for ticker, w in zip(request.tickers, weights)},
            metrics={
                "sharpe_ratio": float(sharpe) if sharpe is not None else 0.0,
                "max_drawdown": float(max_dd) if max_dd is not None else 0.0,
                "sortino_ratio": float(sortino) if sortino is not None else 0.0,
                "annual_return": float(annual_return) if annual_return is not None else 0.0,
                "effective_n_assets": float(enp)
            },
            risk_analysis={
                "portfolio_volatility": float(np.sqrt(weights @ Sigma @ weights) * np.sqrt(252)),
                "market_volatility": float(sigma_market * 100),
                "avg_correlation": float(avg_correlation),
                "stress_level": float(alpha_stress),
                "covariance_condition": float(np.linalg.cond(Sigma))
            },
            cdpr_analysis={
                "force_balance_satisfied": True,  # Not applicable - CDPR removed
                "force_residual_norm": 0.0,       # Not applicable
                "effective_n_assets": float(enp),
                "diversification_ratio": float(enp)
            },
            performance={
                "sharpe_ratio": float(sharpe) if sharpe is not None else 0.0,
                "max_drawdown": float(max_dd) if max_dd is not None else 0.0,
                "sortino_ratio": float(sortino) if sortino is not None else 0.0,
                "annual_return": float(annual_return) if annual_return is not None else 0.0
            }
        )
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is (these are our user-friendly errors)
        raise
    except Exception as e:
        logging.error(f"Unexpected optimization error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Check for common error patterns
        error_msg = str(e).lower()
        if '2-d' in error_msg or 'dimension' in error_msg:
            raise HTTPException(
                status_code=400,
                detail="Portfolio optimization requires at least 2 assets. Please add more tickers."
            )
        elif 'ticker' in error_msg or 'symbol' in error_msg:
            raise HTTPException(
                status_code=400,
                detail="One or more tickers are invalid. Please check your ticker symbols."
            )
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"An unexpected error occurred during optimization. Please try again with different parameters or contact support if the issue persists."
            )

@api_router.get("/tickers/popular")
async def get_popular_tickers():
    """Get list of popular tickers for quick selection."""
    return {
        "categories": {
            "Tech Giants": ["AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "TSLA"],
            "Finance": ["JPM", "BAC", "GS", "MS", "C", "WFC"],
            "Healthcare": ["JNJ", "PFE", "UNH", "ABBV", "MRK"],
            "Consumer": ["WMT", "PG", "KO", "PEP", "NKE"],
            "Energy": ["XOM", "CVX", "COP", "SLB"],
            "Industrials": ["BA", "CAT", "GE", "HON", "MMM"]
        }
    }

@api_router.post("/backtest", response_model=BacktestResult)
async def run_backtest(request: BacktestRequest):
    """
    Run historical backtest of CTPO strategy.
    """
    try:
        from ctpo.execution.backtester import Backtester
        from ctpo.risk.risk_model import RiskModel
        from ctpo.metrics.performance import PerformanceMetrics
        
        # Fetch historical data
        fetcher = DataFetcher()
        returns_df = fetcher.fetch_returns(
            request.tickers,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        if returns_df.empty or len(returns_df) < 100:
            raise HTTPException(status_code=400, detail="Insufficient data for backtesting")
        
        # Initialize risk model
        risk_model = RiskModel(params={
            'risk_free_rate': 0.042,
            'volatility_threshold': 0.23,
            'correlation_breakdown': 0.85,
            'lambda_stress': 0.15
        })
        
        # Define weight function for CTPO
        def ctpo_weight_function(hist_returns):
            # Use integrated risk model
            hist_returns_df = pd.DataFrame(hist_returns, columns=request.tickers)
            risk_params = risk_model.update(hist_returns_df, market_return=0.10)
            
            # Run optimization
            optimizer = CTPOOptimizer()
            market_returns = hist_returns_df.mean(axis=1).values
            weights = optimizer.optimize(
                hist_returns,
                covariance=risk_params['Sigma'],
                expected_returns=risk_params['mu'],
                market_returns=market_returns
            )
            return weights
        
        # Define equal-weight baseline
        def equal_weight_function(hist_returns):
            n = hist_returns.shape[1]
            return np.ones(n) / n
        
        # Run CTPO backtest
        backtester_ctpo = Backtester(
            initial_capital=request.initial_capital,
            transaction_cost=0.001
        )
        results_ctpo = backtester_ctpo.run(
            returns_df,
            ctpo_weight_function,
            rebalance_frequency=request.rebalance_frequency
        )
        summary_ctpo = backtester_ctpo.get_summary()
        
        # Calculate comprehensive metrics for CTPO
        metrics_calc = PerformanceMetrics(risk_free_rate=0.042)
        ctpo_returns = results_ctpo['returns']
        comprehensive_ctpo = metrics_calc.calculate_all(ctpo_returns)
        
        # Run equal-weight baseline
        backtester_ew = Backtester(
            initial_capital=request.initial_capital,
            transaction_cost=0.001
        )
        results_ew = backtester_ew.run(
            returns_df,
            equal_weight_function,
            rebalance_frequency=request.rebalance_frequency
        )
        summary_ew = backtester_ew.get_summary()
        
        # Calculate comprehensive metrics for baseline
        ew_returns = results_ew['returns']
        comprehensive_ew = metrics_calc.calculate_all(ew_returns)
        
        # Calculate improvements
        sharpe_improvement = summary_ctpo['sharpe_ratio'] - summary_ew['sharpe_ratio']
        drawdown_improvement = (summary_ew['max_drawdown'] - summary_ctpo['max_drawdown']) / abs(summary_ew['max_drawdown'])
        
        # Format response
        result = BacktestResult(
            summary={
                "ctpo": {
                    **{k: float(v) for k, v in summary_ctpo.items() if k != 'results'},
                    "comprehensive_metrics": {k: float(v) if v is not None and not isinstance(v, (dict, list)) else (v if v is not None else 0.0)
                                            for k, v in comprehensive_ctpo.items()}
                },
                "equal_weight": {
                    **{k: float(v) for k, v in summary_ew.items() if k != 'results'},
                    "comprehensive_metrics": {k: float(v) if v is not None and not isinstance(v, (dict, list)) else (v if v is not None else 0.0)
                                            for k, v in comprehensive_ew.items()}
                }
            },
            portfolio_values=results_ctpo['portfolio_value'].tolist(),
            dates=[d.strftime('%Y-%m-%d') for d in results_ctpo['date']],
            comparison={
                "sharpe_improvement": float(sharpe_improvement),
                "drawdown_improvement": float(drawdown_improvement),
                "return_difference": float(summary_ctpo['total_return'] - summary_ew['total_return']),
                "volatility_difference": float(comprehensive_ctpo['volatility'] - comprehensive_ew['volatility'])
            }
        )
        
        return result
        
    except Exception as e:
        logging.error(f"Backtest error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()