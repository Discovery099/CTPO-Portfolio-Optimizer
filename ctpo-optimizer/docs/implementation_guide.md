# CTPO Implementation Guide

## Project Structure

### Core Modules

#### `ctpo/core/`
- **optimizer.py**: Main CTPO optimization engine
- **constraints.py**: CDPR force balance and portfolio constraints
- **objective.py**: VaR-based objective function

#### `ctpo/risk/`
- **garch.py**: GARCH(1,1) volatility forecasting
- **correlation.py**: Stress-adjusted correlation estimation
- **capm.py**: CAPM expected returns

#### `ctpo/data/`
- **fetcher.py**: Yahoo Finance data retrieval
- **preprocessor.py**: Data cleaning and alignment

#### `ctpo/execution/`
- **backtester.py**: Historical simulation
- **paper_trader.py**: Simulated live trading
- **alpaca_broker.py**: Mock broker integration

#### `ctpo/metrics/`
- **performance.py**: Sharpe, drawdown, turnover metrics

#### `ctpo/utils/`
- **matrix_ops.py**: Covariance conditioning
- **validators.py**: Constraint validation

## Installation

### Prerequisites

- Python 3.8+
- pip or conda

### Setup

```bash
# Clone repository (if using git)
cd ctpo-optimizer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

## Configuration

### Default Parameters

Configuration is stored in `config/default_params.yaml`.

Key parameters:

```yaml
optimization:
  convergence_tolerance: 1e-6
  max_iterations: 1000
  solver: 'ECOS'

constraints:
  min_weight: 0.01      # 1% minimum
  max_weight: 0.25      # 25% maximum
  min_assets: 20        # Diversification

cdpr:
  tension_min: 0.01
  tension_max: 0.25
  force_balance_tol: 1e-4

risk:
  var_confidence: 0.95
  lookback_period: 252  # 1 year
```

### Custom Configuration

```python
from ctpo import CTPOOptimizer

# Load custom config
optimizer = CTPOOptimizer(config_path='config/my_config.yaml')
```

## Basic Usage

### 1. Fetch Data

```python
from ctpo.data.fetcher import DataFetcher

fetcher = DataFetcher()
tickers = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'META']

# Fetch returns
returns = fetcher.fetch_returns(tickers, period='1y')
print(returns.head())
```

### 2. Optimize Portfolio

```python
from ctpo import CTPOOptimizer

optimizer = CTPOOptimizer()
weights = optimizer.optimize(returns.values)

print(f"Optimal weights: {weights}")
print(f"Sum: {weights.sum()}")
```

### 3. Calculate Metrics

```python
from ctpo.metrics.performance import PerformanceMetrics

# Portfolio returns
portfolio_returns = returns.values @ weights

# Calculate performance
sharpe = PerformanceMetrics.sharpe_ratio(portfolio_returns)
max_dd = PerformanceMetrics.max_drawdown(portfolio_returns)

print(f"Sharpe: {sharpe:.4f}")
print(f"Max Drawdown: {max_dd:.4f}")
```

### 4. Backtest

```python
from ctpo.execution.backtester import Backtester

backtester = Backtester(initial_capital=1000000)

def weight_function(returns_history):
    optimizer = CTPOOptimizer()
    return optimizer.optimize(returns_history)

results = backtester.run(returns, weight_function, rebalance_frequency='monthly')
print(backtester.get_summary())
```

## Testing

### Run All Tests

```bash
# From project root
pytest tests/ -v
```

### Run Specific Test

```bash
pytest tests/unit/test_optimizer.py -v
```

### Run Import Test

```bash
pytest tests/test_imports.py -v
```

## Development Workflow

### CHUNK 1 (Complete) ✅

- Project structure created
- Skeleton implementations
- Basic tests
- Configuration files

### CHUNK 2 (Upcoming)

- Full CDPR optimization algorithm
- CVXPY integration
- Risk model implementations
- Data preprocessing pipeline

### CHUNK 3 (Upcoming)

- Crisis period backtesting
- Performance benchmarking
- Parameter sensitivity analysis
- Live demo notebook

## Troubleshooting

### Import Errors

```bash
# Ensure package is installed
pip install -e .

# Verify imports
python -c "from ctpo import CTPOOptimizer; print('OK')"
```

### Dependency Issues

```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Test Failures

```bash
# Run with verbose output
pytest tests/ -v -s
```

## Next Steps

1. Wait for CHUNK 2 instructions
2. Implement full optimization logic
3. Add GARCH and correlation models
4. Create crisis backtests

---

**Current Status**: CHUNK 1 Complete - Structure & Skeleton Ready
