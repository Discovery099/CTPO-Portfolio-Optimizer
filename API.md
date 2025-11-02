# API Reference

**REST API documentation for the Portfolio Optimizer backend.**

Base URL: `http://localhost:8001/api`

---

## Endpoints

### 1. Optimize Portfolio

**POST** `/api/optimize`

Run portfolio optimization on selected assets.

#### Request Body

```json
{
  "tickers": ["AAPL", "GOOGL", "MSFT", "AMZN", "META"],
  "period": "1y",
  "target_return": 0.08,
  "max_risk": 0.15,
  "min_effective_assets": 10,
  "position_max": 0.20
}
```

#### Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `tickers` | `string[]` | ✅ Yes | - | Asset tickers (Yahoo Finance format) |
| `period` | `string` | No | `"1y"` | Time period: `3mo`, `6mo`, `1y`, `2y`, `5y` |
| `target_return` | `float` | No | `0.08` | Target annual return (not enforced, informational) |
| `max_risk` | `float` | No | `0.15` | Maximum risk tolerance (not enforced) |
| `min_effective_assets` | `int` | No | `10` | Desired diversification level |
| `position_max` | `float` | No | `0.20` | **Maximum position size per asset (15-50%)** |

#### Response (200 OK)

```json
{
  "weights": {
    "AAPL": 0.20,
    "GOOGL": 0.15,
    "MSFT": 0.20,
    "AMZN": 0.20,
    "META": 0.25
  },
  "metrics": {
    "sharpe_ratio": 1.55,
    "max_drawdown": -0.297,
    "sortino_ratio": 2.36,
    "annual_return": 0.597,
    "effective_n_assets": 5.6
  },
  "risk_analysis": {
    "portfolio_volatility": 0.27,
    "market_volatility": 1.27,
    "avg_correlation": 0.465,
    "stress_level": 0.000,
    "covariance_condition": 35
  },
  "cdpr_analysis": {
    "force_balance_satisfied": true,
    "force_residual_norm": 0.0,
    "effective_n_assets": 5.6,
    "diversification_ratio": 5.6
  },
  "performance": {
    "sharpe_ratio": 1.55,
    "max_drawdown": -0.297,
    "sortino_ratio": 2.36,
    "annual_return": 0.597
  }
}
```

#### Response Fields

**weights** (`object`)
- Portfolio allocation per asset
- Keys: Ticker symbols
- Values: Weight (0.0-1.0, sum = 1.0)

**metrics** (`object`)
- `sharpe_ratio`: Risk-adjusted return (higher = better)
- `max_drawdown`: Maximum peak-to-trough decline (negative %)
- `sortino_ratio`: Downside risk-adjusted return
- `annual_return`: Expected annual return (0.597 = 59.7%)
- `effective_n_assets`: Diversification level (ENP)

**risk_analysis** (`object`)
- `portfolio_volatility`: Portfolio standard deviation (%)
- `market_volatility`: Market benchmark volatility (%)
- `avg_correlation`: Average pairwise correlation
- `stress_level`: Market stress indicator (0-1)
- `covariance_condition`: Matrix condition number

**cdpr_analysis** (`object`)
- Legacy fields (not used after CDPR removal)
- `effective_n_assets`: Same as metrics.effective_n_assets
- `force_balance_satisfied`: Always true (not applicable)

**performance** (`object`)
- Duplicate of key metrics for convenience

#### Error Responses

**400 Bad Request**
```json
{
  "detail": "Insufficient data for optimization"
}
```

**Causes:**
- Invalid tickers
- Insufficient historical data (< 50 days)
- Period too short

**500 Internal Server Error**
```json
{
  "detail": "Optimization failed: <error message>"
}
```

**Causes:**
- Numerical instability
- Solver failure
- Data fetch error

---

### 2. Get Popular Tickers

**GET** `/api/tickers/popular`

Retrieve preset ticker lists.

#### Response (200 OK)

```json
{
  "tech": ["AAPL", "GOOGL", "MSFT", "NVDA", "META", "TSLA"],
  "stable": ["JPM", "JNJ", "PG", "KO", "WMT", "T"],
  "sp500_top": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B", "UNH", "JNJ"]
}
```

---

### 3. Health Check

**GET** `/api/`

Verify API is running.

#### Response (200 OK)

```json
{
  "message": "CTPO Portfolio Optimizer API"
}
```

---

## Usage Examples

### Python (requests)

```python
import requests

response = requests.post(
    "http://localhost:8001/api/optimize",
    json={
        "tickers": ["AAPL", "GOOGL", "MSFT"],
        "period": "1y",
        "position_max": 0.20
    }
)

data = response.json()
print(f"Sharpe Ratio: {data['metrics']['sharpe_ratio']:.2f}")
print(f"Weights: {data['weights']}")
```

### JavaScript (axios)

```javascript
import axios from 'axios';

const response = await axios.post(
  'http://localhost:8001/api/optimize',
  {
    tickers: ['AAPL', 'GOOGL', 'MSFT'],
    period: '1y',
    position_max: 0.20
  }
);

console.log('Sharpe Ratio:', response.data.metrics.sharpe_ratio);
console.log('Weights:', response.data.weights);
```

### cURL

```bash
curl -X POST http://localhost:8001/api/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": ["AAPL", "GOOGL", "MSFT"],
    "period": "1y",
    "position_max": 0.20
  }' | jq
```

---

## Rate Limits

**Yahoo Finance (data source):**
- ~2000 requests/hour
- ~48,000 requests/day

**Recommendations:**
- Cache optimization results
- Avoid rapid repeated requests
- Consider adding Redis for caching

---

## Supported Tickers

### US Stocks
- Format: `AAPL`, `GOOGL`, `MSFT`
- Must be listed on Yahoo Finance

### Cryptocurrencies
- Format: `BTC-USD`, `ETH-USD`, `SOL-USD`
- Suffix `-USD` required

### Forex Pairs
- Format: `EURUSD=X`, `GBPUSD=X`
- Suffix `=X` required

### ETFs
- Format: `SPY`, `QQQ`, `VTI`
- Same as stocks

---

## Best Practices

### 1. Ticker Validation

Always validate tickers before sending:
```python
valid_tickers = ['AAPL', 'GOOGL', 'MSFT']
invalid_tickers = ['INVALID', 'FAKE']

# Only send valid ones
response = requests.post(url, json={"tickers": valid_tickers})
```

### 2. Error Handling

```python
try:
    response = requests.post(url, json=payload)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.HTTPError as e:
    print(f"API Error: {e.response.json()['detail']}")
except requests.exceptions.RequestException as e:
    print(f"Network Error: {e}")
```

### 3. Position Limit Selection

```python
# Conservative
position_max = 0.20  # Default, balanced

# Moderate
position_max = 0.30  # Higher concentration

# Aggressive
position_max = 0.50  # Maximum returns, higher risk
```

### 4. Period Selection

```python
# Short-term trends
period = "3mo"  # Recent market behavior

# Medium-term
period = "1y"   # Default, good balance

# Long-term stability
period = "5y"   # Smoother, more stable
```

---

## API Versioning

**Current Version:** v1 (implicit)

**Future versions** will use URL prefixes:
- v1: `/api/v1/optimize`
- v2: `/api/v2/optimize`

---

## OpenAPI Documentation

**Interactive API docs:**
http://localhost:8001/docs

**OpenAPI spec (JSON):**
http://localhost:8001/openapi.json

---

**For more details, see [ARCHITECTURE.md](ARCHITECTURE.md)**
