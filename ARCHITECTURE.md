# Architecture Documentation

**Technical deep-dive into the Portfolio Optimizer system.**

---

## System Overview

```
┌─────────────┐      HTTP/REST      ┌──────────────┐
│   React     │ ◄─────────────────► │   FastAPI    │
│  Frontend   │                     │   Backend    │
└─────────────┘                     └──────────────┘
       │                                    │
       │                                    │
       v                                    v
  ┌─────────┐                        ┌──────────────┐
  │ Recharts│                        │  Optimizer   │
  │ Shadcn  │                        │   (CVXPY)    │
  └─────────┘                        └──────────────┘
                                            │
                                            v
                                     ┌──────────────┐
                                     │ Yahoo Finance│
                                     │  (yfinance)  │
                                     └──────────────┘
```

---

## Backend Architecture

### Core Components

#### 1. Portfolio Optimizer (`ctpo/core/optimizer.py`)

**Purpose:** Solve mean-variance portfolio optimization

**Algorithm:**
```python
Minimize: risk_weight × ½w'Σw - lambda_return × w'μ + tc_cost

Subject to:
  sum(w) = 1      # Fully invested
  w >= 0          # Long-only
  w <= pos_max    # Position limit
```

**Key Method:**
```python
def optimize(returns: np.ndarray, 
             position_max: float = 0.20) -> np.ndarray:
    # 1. Compute expected returns (mu) and covariance (Sigma)
    mu = returns.mean(axis=0)
    Sigma = np.cov(returns.T)
    
    # 2. Define optimization variable
    w = cp.Variable(n_assets)
    
    # 3. Build objective
    objective = cp.Minimize(
        risk_weight * cp.quad_form(w, Sigma) - 
        lambda_return * (mu @ w) +
        tc_penalty
    )
    
    # 4. Add constraints
    constraints = [
        cp.sum(w) == 1,
        w >= 0,
        w <= position_max
    ]
    
    # 5. Solve
    problem = cp.Problem(objective, constraints)
    problem.solve(solver=cp.CLARABEL)
    
    return w.value
```

**Parameters:**
- `risk_weight = 0.05`: Low risk aversion (focuses on returns)
- `lambda_return = 25.0`: Strong return focus
- `position_max = 0.20`: Default 20% limit (user-adjustable)

#### 2. Data Fetcher (`ctpo/data/fetcher.py`)

**Purpose:** Retrieve historical market data

**Data Source:** Yahoo Finance via `yfinance` library

**Key Method:**
```python
def fetch_returns(tickers: List[str], 
                 period: str = "1y") -> pd.DataFrame:
    # Download adjusted close prices
    data = yf.download(tickers, period=period)
    
    # Compute returns
    returns = data['Adj Close'].pct_change().dropna()
    
    return returns
```

**Supported Periods:**
- `3mo`: 3 months (~60 trading days)
- `6mo`: 6 months (~120 trading days)
- `1y`: 1 year (~252 trading days)
- `2y`: 2 years
- `5y`: 5 years

#### 3. Performance Metrics (`ctpo/metrics/performance.py`)

**Purpose:** Calculate portfolio performance metrics

**Key Metrics:**

```python
class PerformanceMetrics:
    @staticmethod
    def sharpe_ratio(returns: np.ndarray, 
                    risk_free_rate: float = 0.042) -> float:
        excess_returns = returns - risk_free_rate/252
        return np.sqrt(252) * excess_returns.mean() / returns.std()
    
    @staticmethod
    def max_drawdown(returns: np.ndarray) -> float:
        cum_returns = (1 + returns).cumprod()
        running_max = np.maximum.accumulate(cum_returns)
        drawdown = (cum_returns - running_max) / running_max
        return drawdown.min()
    
    @staticmethod
    def sortino_ratio(returns: np.ndarray,
                     risk_free_rate: float = 0.042) -> float:
        excess_returns = returns - risk_free_rate/252
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std()
        return np.sqrt(252) * excess_returns.mean() / downside_std
```

#### 4. Risk Model (`ctpo/risk/risk_model.py`)

**Purpose:** Compute risk parameters for optimization

**Components:**
- **GARCH**: Volatility forecasting
- **CAPM**: Expected returns via beta
- **Correlation Stress**: Dynamic correlation adjustment

**Flow:**
```python
class RiskModel:
    def update(self, returns_df, market_return):
        # 1. GARCH volatility estimates
        volatilities = estimate_garch_volatilities(returns_df)
        
        # 2. CAPM betas
        betas = calculate_betas(returns_df, market_return)
        
        # 3. Expected returns
        mu = capm_expected_returns(betas, market_return)
        
        # 4. Stress-adjusted covariance
        Sigma = compute_stress_covariance(returns_df, stress_level)
        
        return {mu, Sigma, betas, volatilities, stress_level}
```

---

## Frontend Architecture

### Component Structure

```
App.js
  └── Dashboard.jsx (main page)
       ├── Portfolio Configuration
       │   ├── Ticker Input
       │   ├── Period Selector
       │   └── Position Slider
       ├── Performance Metrics Cards
       │   ├── Sharpe Ratio
       │   ├── Annual Return
       │   ├── Max Drawdown
       │   └── Sortino Ratio
       ├── Portfolio Allocation
       │   ├── Pie Chart (Recharts)
       │   └── Bar Chart (Recharts)
       ├── Risk Analysis
       │   └── Volatility/Correlation Display
       └── CDPR Validation
           └── Diversification Metrics
```

### Key Frontend Logic

#### Optimization Flow

```javascript
const runOptimization = async () => {
  setLoading(true);
  
  try {
    // 1. Parse tickers
    const tickerList = tickers
      .split(',')
      .map(t => t.trim().toUpperCase())
      .filter(t => t);
    
    // 2. Call API
    const response = await axios.post(`${API}/optimize`, {
      tickers: tickerList,
      period: period,
      position_max: positionMax  // From slider
    });
    
    // 3. Update state
    setResult(response.data);
    
  } catch (err) {
    setError(err.response?.data?.detail || err.message);
  } finally {
    setLoading(false);
  }
};
```

#### Position Slider

```javascript
const [positionMax, setPositionMax] = useState(0.20); // Default 20%

<input
  type="range"
  min="0.15"
  max="0.50"
  step="0.05"
  value={positionMax}
  onChange={(e) => setPositionMax(parseFloat(e.target.value))}
/>

// Dynamic risk warning
{positionMax <= 0.20 ? 
  "Balanced (20% limit): Good risk/return tradeoff" :
  positionMax <= 0.30 ?
  "Moderate (25-30% limit): Higher returns, moderate risk" :
  "Aggressive (35-50% limit): Maximum returns, significantly higher risk"}
```

---

## Optimization Algorithm

### Mathematical Formulation

**Objective Function:**
```
f(w) = risk_weight × ½w'Σw - lambda_return × w'μ + lambda_tc × ||w - w_prev||₁
```

**Terms:**
1. **Risk Term**: `½w'Σw` (portfolio variance)
2. **Return Term**: `-w'μ` (negative expected return, to maximize)
3. **Transaction Cost**: `||w - w_prev||₁` (L1 norm of weight changes)

**Constraints:**
```
1. sum(w_i) = 1           (fully invested)
2. w_i >= 0, ∀i           (long-only)
3. w_i <= position_max, ∀i (position limits)
```

### Solver: CLARABEL

**Why CLARABEL?**
- ✅ Handles conic constraints (quadratic objective)
- ✅ Faster than OSQP/SCS for portfolio problems
- ✅ Rust-based (high performance)
- ✅ Open-source

**Solver Parameters:**
```python
problem.solve(
    solver=cp.CLARABEL,
    verbose=True,
    max_iter=200,
    tol_feas=1e-6,
    tol_gap_abs=1e-6,
    tol_gap_rel=1e-6
)
```

**Typical Performance:**
- **10 assets**: <1ms
- **50 assets**: 2-5ms
- **100 assets**: 10-20ms

---

## Data Flow

### End-to-End Request

```
1. User Input (Frontend)
   ├── Tickers: ["AAPL", "GOOGL", "MSFT"]
   ├── Period: "1y"
   └── Position Max: 0.20

2. API Request
   POST /api/optimize
   Body: {tickers, period, position_max}

3. Backend Processing
   ├── Fetch Data (Yahoo Finance)
   │   └── Returns: (252 x 3) matrix
   ├── Compute Risk Parameters
   │   ├── mu: [0.0012, 0.0015, 0.0010]
   │   └── Sigma: (3 x 3) covariance matrix
   ├── Run Optimizer (CVXPY)
   │   └── Solve time: ~0.5ms
   └── Calculate Metrics
       ├── Sharpe Ratio
       ├── Max Drawdown
       └── Sortino Ratio

4. API Response
   {
     weights: {AAPL: 0.33, GOOGL: 0.33, MSFT: 0.34},
     metrics: {...},
     risk_analysis: {...}
   }

5. Frontend Display
   ├── Update Charts
   ├── Show Metrics
   └── Display Risk Analysis
```

---

## Performance Optimization

### Backend

1. **Data Caching** (future enhancement)
   ```python
   @lru_cache(maxsize=128)
   def fetch_cached_returns(tickers_tuple, period):
       return fetch_returns(list(tickers_tuple), period)
   ```

2. **Async Operations**
   ```python
   async def optimize_portfolio(request):
       # Non-blocking I/O for data fetch
       returns_df = await asyncio.to_thread(
           fetcher.fetch_returns, request.tickers
       )
   ```

3. **Connection Pooling**
   - Reuse HTTP connections to Yahoo Finance
   - Reduce latency by 50-100ms

### Frontend

1. **Debounced Slider**
   ```javascript
   const debouncedSetPosition = useMemo(
     () => debounce(setPositionMax, 300),
     []
   );
   ```

2. **Lazy Loading**
   - Charts load only when result available
   - Reduces initial bundle size

3. **Memoization**
   ```javascript
   const weightData = useMemo(
     () => result ? prepareChartData(result.weights) : [],
     [result]
   );
   ```

---

## Security Considerations

### Input Validation

```python
# Backend validation
if len(request.tickers) < 3:
    raise HTTPException(400, "Minimum 3 tickers required")

if len(request.tickers) > 200:
    raise HTTPException(400, "Maximum 200 tickers allowed")

if not 0.10 <= request.position_max <= 1.0:
    raise HTTPException(400, "Invalid position_max")
```

### Rate Limiting (future)

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/optimize")
@limiter.limit("10/minute")
async def optimize(request):
    ...
```

### CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"]
)
```

---

## Deployment

### Architecture

```
Kubernetes Cluster
  ├── Frontend Pod (React)
  │   └── Port: 3000
  ├── Backend Pod (FastAPI)
  │   └── Port: 8001
  └── MongoDB Pod (optional)
      └── Port: 27017

Supervisor (Process Manager)
  ├── frontend.conf
  └── backend.conf
```

### Environment Variables

**Backend:**
```bash
MONGO_URL=mongodb://localhost:27017
PORT=8001
WORKERS=4
```

**Frontend:**
```bash
REACT_APP_BACKEND_URL=https://api.example.com
PORT=3000
```

### Scaling

**Horizontal:**
- Add more backend pods
- Load balance with Nginx/Traefik

**Vertical:**
- Increase pod CPU/memory limits
- Optimize CVXPY solver threads

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_optimizer.py
def test_weights_sum_to_one():
    optimizer = PortfolioOptimizer()
    returns = np.random.normal(0.001, 0.02, (252, 10))
    weights = optimizer.optimize(returns)
    assert np.isclose(weights.sum(), 1.0, atol=1e-3)

def test_long_only():
    optimizer = PortfolioOptimizer()
    returns = np.random.normal(0.001, 0.02, (252, 10))
    weights = optimizer.optimize(returns)
    assert np.all(weights >= 0)
```

### Integration Tests

```python
# tests/integration/test_crisis_2008.py
def test_sharpe_improvement():
    # Fetch real 2008 crisis data
    returns_df = fetcher.fetch_returns(
        ['AAPL', 'MSFT', 'GOOGL'],
        start_date='2007-01-01',
        end_date='2009-12-31'
    )
    
    # Optimize
    optimizer = PortfolioOptimizer()
    weights = optimizer.optimize(returns_df.values)
    
    # Compute Sharpe
    portfolio_returns = returns_df.values @ weights
    sharpe = PerformanceMetrics.sharpe_ratio(portfolio_returns)
    
    # Compare to equal-weight
    equal_weights = np.ones(len(weights)) / len(weights)
    equal_returns = returns_df.values @ equal_weights
    sharpe_baseline = PerformanceMetrics.sharpe_ratio(equal_returns)
    
    assert sharpe > sharpe_baseline
```

---

## Future Enhancements

### Phase 1 (Next)
- ✅ Preset portfolio buttons
- ✅ Cryptocurrency support (BTC-USD, ETH-USD)
- ✅ Forex pairs (EURUSD=X, GBPUSD=X)

### Phase 2
- Portfolio comparison (before/after)
- Export to PDF/CSV
- Historical optimization tracking

### Phase 3
- Real-time market data
- Alert system
- Multi-currency support

---

**For usage instructions, see [QUICKSTART.md](QUICKSTART.md)**
