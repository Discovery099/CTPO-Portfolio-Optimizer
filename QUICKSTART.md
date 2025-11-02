# Quick Start Guide

**Get the Portfolio Optimizer running in 5 minutes.**

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**  
- **Yarn** package manager
- **Git** (for cloning)

---

## Installation Steps

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd portfolio-optimizer
```

### 2. Backend Setup

```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python -c "import cvxpy; print('✅ CVXPY installed')"
```

### 3. Frontend Setup

```bash
cd ../frontend

# Install JavaScript dependencies
yarn install

# Verify installation
yarn --version
```

### 4. Environment Configuration

**Backend** (`backend/.env`):
```bash
MONGO_URL=mongodb://localhost:27017
```

**Frontend** (`frontend/.env`):
```bash
REACT_APP_BACKEND_URL=http://localhost:8001
```

### 5. Start Services

```bash
# From project root
sudo supervisorctl restart all

# Check status
sudo supervisorctl status
```

**Expected output:**
```
backend    RUNNING   pid 12345
frontend   RUNNING   pid 12346
```

---

## First Optimization

### Via Web UI

1. **Open browser**: http://localhost:3000

2. **Enter tickers** (comma-separated):
   ```
   AAPL,GOOGL,MSFT,AMZN,META,TSLA,NVDA,JPM,V,WMT
   ```

3. **Select period**: `1 Year`

4. **Adjust position limit**: 20% (default) or use slider

5. **Click**: "Run CTPO Optimization"

6. **View results**:
   - Performance metrics (Sharpe, Return, Drawdown)
   - Portfolio allocation (pie & bar charts)
   - Risk analysis

### Via API (curl)

```bash
curl -X POST http://localhost:8001/api/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": ["AAPL", "GOOGL", "MSFT", "AMZN", "META"],
    "period": "1y",
    "position_max": 0.20
  }'
```

**Response:**
```json
{
  "weights": {
    "AAPL": 0.20,
    "GOOGL": 0.20,
    "MSFT": 0.20,
    "AMZN": 0.20,
    "META": 0.20
  },
  "metrics": {
    "sharpe_ratio": 1.55,
    "annual_return": 0.597,
    "max_drawdown": -0.297
  }
}
```

---

## Understanding Results

### Performance Metrics

**Sharpe Ratio**
- Measures risk-adjusted returns
- Higher = Better
- > 1.0 is good, > 2.0 is excellent

**Annual Return**
- Expected yearly return %
- Based on historical data

**Max Drawdown**
- Largest peak-to-trough decline
- Lower = Less risk

**Sortino Ratio**
- Like Sharpe, but only penalizes downside volatility
- Higher = Better

### Portfolio Allocation

**Non-Equal Weights = Optimization Working**
- If all weights are 10% → fallback (check logs)
- Variance in weights (0-20%) → optimizer working correctly

**Eliminated Assets (0% weight)**
- Normal behavior
- Optimizer found these assets underperform

---

## Position Limit Slider

### Conservative (15-20%)
- Lower concentration
- More diversification
- Lower risk, moderate returns
- **Recommended for beginners**

### Moderate (25-30%)
- Medium concentration
- Balanced risk/return
- Good for most users

### Aggressive (35-50%)
- High concentration
- Maximum returns
- **Higher drawdown risk**
- Only for experienced investors

---

## Troubleshooting

### Backend won't start

```bash
# Check logs
tail -n 50 /var/log/supervisor/backend.err.log

# Common issue: Missing dependency
pip install cvxpy clarabel numpy pandas yfinance

# Restart
sudo supervisorctl restart backend
```

### Frontend won't start

```bash
# Check logs
tail -n 50 /var/log/supervisor/frontend.err.log

# Common issue: Missing modules
cd frontend
yarn install

# Restart
sudo supervisorctl restart frontend
```

### "Solver fallback" message

**Causes:**
- Insufficient historical data
- Highly correlated assets
- Infeasible constraints

**Solutions:**
- Try different tickers
- Increase position limit (slider)
- Use longer time period (2y or 5y)

### API returns 500 error

**Check:**
1. Are tickers valid? (must be Yahoo Finance compatible)
2. Is period valid? (3mo, 6mo, 1y, 2y, 5y)
3. Backend logs: `tail /var/log/supervisor/backend.err.log`

---

## Next Steps

### Experiment with Parameters

1. **Try different asset sets:**
   - Tech-heavy: AAPL, MSFT, NVDA, GOOGL, AMZN, META
   - Stable: JPM, JNJ, PG, KO, WMT, T
   - Mixed: Combination of both

2. **Adjust position limit:**
   - Start at 20% (default)
   - Increase to 30% for more concentration
   - Compare results

3. **Test different periods:**
   - 1y for recent trends
   - 5y for long-term stability

### Read Documentation

- **[API.md](API.md)** - Full API reference
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - How it works under the hood

### Run Tests

```bash
cd ctpo-optimizer
pytest tests/ -v
```

---

## Getting Help

**Logs:**
```bash
# Backend
tail -f /var/log/supervisor/backend.err.log

# Frontend  
tail -f /var/log/supervisor/frontend.err.log
```

**Service Status:**
```bash
sudo supervisorctl status
```

**Restart All:**
```bash
sudo supervisorctl restart all
```

---

**You're ready to optimize! 🚀**
