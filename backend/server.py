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
    Run CTPO optimization on selected tickers.
    """
    try:
        # Fetch data
        fetcher = DataFetcher()
        returns_df = fetcher.fetch_returns(request.tickers, period=request.period)
        
        if returns_df.empty or len(returns_df) < 50:
            raise HTTPException(status_code=400, detail="Insufficient data for optimization")
        
        returns = returns_df.values
        market_returns = returns.mean(axis=1)
        
        # Run optimization
        optimizer = CTPOOptimizer()
        weights = optimizer.optimize(returns, market_returns=market_returns)
        
        # Get metrics
        metrics = optimizer.get_metrics()
        
        # Calculate performance
        portfolio_returns = returns @ weights
        sharpe = PerformanceMetrics.sharpe_ratio(portfolio_returns)
        max_dd = PerformanceMetrics.max_drawdown(portfolio_returns)
        sortino = PerformanceMetrics.sortino_ratio(portfolio_returns)
        annual_return = PerformanceMetrics.annualized_return(portfolio_returns)
        
        # Risk analysis
        capm = CAPMModel()
        expected_returns, betas = capm.estimate_expected_returns(returns, market_returns)
        
        # GARCH volatilities
        volatilities = estimate_garch_volatilities(returns_df)
        
        # Stress correlation
        stress_corr = StressCorrelation()
        sigma_market = np.std(market_returns) * np.sqrt(252)
        Sigma_stress, alpha_stress = stress_corr.compute_stress_covariance(
            returns_df, volatilities, sigma_market
        )
        
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
                "expected_returns": {ticker: float(er) for ticker, er in zip(request.tickers, expected_returns)},
                "betas": {ticker: float(b) for ticker, b in zip(request.tickers, betas)},
                "volatilities": {ticker: float(v) for ticker, v in zip(request.tickers, volatilities)},
                "market_volatility": float(sigma_market),
                "avg_correlation": float(metrics['avg_correlation']),
                "stress_level": float(alpha_stress)
            },
            risk_analysis={
                "covariance_condition_number": float(np.linalg.cond(Sigma_stress)),
                "portfolio_volatility": float(np.sqrt(weights.T @ Sigma_stress @ weights)),
                "diversification_ratio": float(enp)
            },
            cdpr_analysis={
                "force_balance_satisfied": bool(fb_satisfied),
                "force_residual": float(fb_residual),
                "effective_n_assets": float(enp),
                "validation_report": validation_report
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