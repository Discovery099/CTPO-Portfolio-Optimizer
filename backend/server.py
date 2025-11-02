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
from ctpo.core.optimizer import CTPOOptimizer, CTPOState
from ctpo.data.fetcher import DataFetcher
from ctpo.metrics.performance import PerformanceMetrics
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
        # Fetch data
        fetcher = DataFetcher()
        returns_df = fetcher.fetch_returns(request.tickers, period=request.period)
        
        if returns_df.empty or len(returns_df) < 50:
            raise HTTPException(status_code=400, detail="Insufficient data for optimization")
        
        returns = returns_df.values
        
        # Initialize integrated risk model
        from ctpo.risk.risk_model import RiskModel
        
        risk_model = RiskModel(params={
            'risk_free_rate': 0.042,
            'volatility_threshold': 0.23,
            'correlation_breakdown': 0.85,
            'lambda_stress': 0.15
        })
        
        # Update risk model with current data
        risk_params = risk_model.update(returns_df, market_return=0.10)
        
        # Extract risk parameters
        mu = risk_params['mu']
        Sigma = risk_params['Sigma']
        betas = risk_params['betas']
        volatilities = risk_params['volatilities']
        sigma_market = risk_params['sigma_market']
        alpha_stress = risk_params['alpha_stress']
        avg_correlation = risk_params['avg_correlation']
        
        # Run optimization with integrated risk model
        optimizer = CTPOOptimizer()
        
        # Compute market returns for optimizer
        market_returns = returns_df.mean(axis=1).values
        
        weights = optimizer.optimize(
            returns,
            covariance=Sigma,
            expected_returns=mu,
            market_returns=market_returns
        )
        
        # Calculate performance
        portfolio_returns = returns @ weights
        sharpe = PerformanceMetrics.sharpe_ratio(portfolio_returns)
        max_dd = PerformanceMetrics.max_drawdown(portfolio_returns)
        sortino = PerformanceMetrics.sortino_ratio(portfolio_returns)
        annual_return = PerformanceMetrics.annualized_return(portfolio_returns)
        
        # CDPR analysis
        A = construct_structure_matrix(betas, volatilities)
        W = construct_wrench_vector(request.target_return, request.max_risk, request.min_effective_assets)
        fb_satisfied, fb_residual = force_balance_residual(weights, A, W, tolerance=0.1)
        enp = compute_effective_n_assets(weights)
        
        # Validate solution
        validator = CDPRValidator()
        valid, validation_report = validator.validate_solution(weights, A, W)
        
        # Format response
        result = OptimizationResult(
            weights={ticker: float(w) for ticker, w in zip(request.tickers, weights)},
            metrics={
                "expected_returns": {ticker: float(er) for ticker, er in zip(request.tickers, mu)},
                "betas": {ticker: float(b) for ticker, b in zip(request.tickers, betas)},
                "volatilities": {ticker: float(v) for ticker, v in zip(request.tickers, volatilities)},
                "market_volatility": float(sigma_market),
                "avg_correlation": float(avg_correlation),
                "stress_level": float(alpha_stress)
            },
            risk_analysis={
                "covariance_condition_number": float(np.linalg.cond(Sigma)),
                "portfolio_volatility": float(np.sqrt(weights.T @ Sigma @ weights)),
                "diversification_ratio": float(enp)
            },
            cdpr_analysis={
                "force_balance_satisfied": bool(int(fb_satisfied)),  # Convert numpy.bool_ to Python bool
                "force_residual": float(fb_residual),
                "effective_n_assets": float(enp),
                "validation_report": {
                    "force_balance_satisfied": bool(int(validation_report['force_balance_satisfied'])),
                    "workspace_satisfied": bool(int(validation_report['workspace_satisfied'])),
                    "diversification_satisfied": bool(int(validation_report['diversification_satisfied'])),
                    "force_residual": float(validation_report['force_residual']),
                    "workspace_deviation": float(validation_report['workspace_deviation']),
                    "effective_n_assets": float(validation_report['effective_n_assets']),
                    "violations": validation_report['violations']
                }
            },
            performance={
                "sharpe_ratio": float(sharpe),
                "sortino_ratio": float(sortino),
                "max_drawdown": float(max_dd),
                "annual_return": float(annual_return),
                "total_return": float(np.prod(1 + portfolio_returns) - 1)
            }
        )
        
        return result
        
    except Exception as e:
        logging.error(f"Optimization error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

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