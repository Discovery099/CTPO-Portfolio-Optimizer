import { useState } from 'react';
import axios from 'axios';
import { Play, TrendingUp, PieChart, Activity, AlertCircle, CheckCircle2, Download } from 'lucide-react';
import { PieChart as RePieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from 'recharts';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];

const Dashboard = () => {
  const [tickers, setTickers] = useState('AAPL,GOOGL,MSFT,AMZN,META,TSLA,NVDA,JPM,V,WMT');
  const [period, setPeriod] = useState('1y');
  const [positionMax, setPositionMax] = useState(0.20);  // NEW: Default 20%
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activePreset, setActivePreset] = useState(null);  // Track selected preset
  const [validationError, setValidationError] = useState(null);  // NEW: Validation error
  
  // Preset portfolios
  const presetPortfolios = {
    conservative: {
      name: 'Conservative',
      description: 'Stable blue-chip stocks with low volatility',
      tickers: ['JPM', 'JNJ', 'PG', 'KO', 'WMT', 'T', 'VZ', 'PFE', 'MCD', 'XOM'],
      icon: '🛡️'
    },
    growthTech: {
      name: 'Growth Tech',
      description: 'High-growth technology companies',
      tickers: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'AMD', 'CRM', 'ADBE'],
      icon: '🚀'
    },
    dividend: {
      name: 'Dividend',
      description: 'High dividend-paying stocks',
      tickers: ['T', 'VZ', 'XOM', 'CVX', 'KO', 'PEP', 'JNJ', 'PG', 'MO', 'IBM'],
      icon: '💰'
    },
    balanced: {
      name: 'Balanced',
      description: 'Mix of growth and value stocks',
      tickers: ['AAPL', 'MSFT', 'JPM', 'JNJ', 'V', 'WMT', 'PG', 'NVDA', 'UNH', 'HD'],
      icon: '⚖️'
    },
    crypto: {
      name: 'Crypto',
      description: 'Major cryptocurrencies (via Yahoo Finance)',
      tickers: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD', 'MATIC-USD', 'AVAX-USD', 'DOT-USD', 'LINK-USD'],
      icon: '₿'
    },
    forex: {
      name: 'Forex',
      description: 'Major currency pairs',
      tickers: ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'USDCAD=X', 'USDCHF=X'],
      icon: '💱'
    }
  };
  
  // Handle preset selection
  const handlePresetClick = (presetKey) => {
    const preset = presetPortfolios[presetKey];
    setTickers(preset.tickers.join(','));
    setActivePreset(presetKey);
    setError(null);
    setResult(null);
    setValidationError(null);  // Clear validation error
  };
  
  // NEW: Validate ticker input
  const validateTickers = (tickerString) => {
    const tickerList = tickerString.split(',').map(t => t.trim()).filter(t => t);
    
    if (tickerList.length === 0) {
      return "Please enter at least one ticker";
    }
    
    if (tickerList.length < 2) {
      return "Need at least 2 assets for portfolio optimization";
    }
    
    return null;
  };
  
  // NEW: Handle ticker input change with validation
  const handleTickersChange = (value) => {
    setTickers(value);
    setActivePreset(null); // Clear preset when manually editing
    const error = validateTickers(value);
    setValidationError(error);
  };
  
  // Export results to CSV
  const exportToCSV = () => {
    if (!result) return;
    
    const timestamp = new Date().toISOString().split('T')[0].replace(/-/g, '');
    const portfolioName = activePreset ? presetPortfolios[activePreset].name.replace(/\s+/g, '_') : 'Custom';
    const filename = `CTPO_Results_${portfolioName}_${timestamp}.csv`;
    
    // Build CSV content
    let csv = '--- METADATA ---\n';
    csv += 'Generated Date,' + new Date().toISOString().split('T')[0] + '\n';
    csv += 'Portfolio Type,' + (activePreset ? presetPortfolios[activePreset].name : 'Custom') + '\n';
    csv += 'Time Period,' + period + '\n';
    csv += 'Position Limit,' + (positionMax * 100).toFixed(0) + '%\n';
    csv += 'Risk Free Rate,4.2%\n';
    csv += '\n';
    
    csv += '--- PORTFOLIO WEIGHTS ---\n';
    csv += 'Symbol,Weight (%),Dollar Allocation (per $100k)\n';
    Object.entries(result.weights)
      .sort((a, b) => b[1] - a[1])
      .forEach(([symbol, weight]) => {
        csv += `${symbol},${(weight * 100).toFixed(2)}%,$${(weight * 100000).toFixed(2)}\n`;
      });
    csv += '\n';
    
    csv += '--- PERFORMANCE METRICS ---\n';
    csv += 'Metric,Value\n';
    csv += 'Sharpe Ratio,' + (result.metrics?.sharpe_ratio || result.performance?.sharpe_ratio || 0).toFixed(3) + '\n';
    csv += 'Annual Return,' + ((result.metrics?.annual_return || result.performance?.annual_return || 0) * 100).toFixed(2) + '%\n';
    csv += 'Max Drawdown,' + ((result.metrics?.max_drawdown || result.performance?.max_drawdown || 0) * 100).toFixed(2) + '%\n';
    csv += 'Sortino Ratio,' + (result.metrics?.sortino_ratio || result.performance?.sortino_ratio || 0).toFixed(3) + '\n';
    csv += 'Effective N Assets,' + (result.metrics?.effective_n_assets || 0).toFixed(2) + '\n';
    csv += '\n';
    
    csv += '--- RISK ANALYSIS ---\n';
    csv += 'Metric,Value\n';
    csv += 'Market Volatility,' + (result.risk_analysis?.market_volatility || 0).toFixed(2) + '%\n';
    csv += 'Portfolio Volatility,' + (result.risk_analysis?.portfolio_volatility || 0).toFixed(2) + '%\n';
    csv += 'Average Correlation,' + (result.risk_analysis?.avg_correlation || 0).toFixed(3) + '\n';
    csv += 'Stress Level,' + (result.risk_analysis?.stress_level || 0).toFixed(3) + '\n';
    csv += 'Covariance Condition Number,' + (result.risk_analysis?.covariance_condition || 0).toFixed(0) + '\n';
    csv += '\n';
    
    csv += '--- DIVERSIFICATION ---\n';
    csv += 'Metric,Value\n';
    csv += 'Effective N Assets (ENP),' + (result.cdpr_analysis?.effective_n_assets || 0).toFixed(2) + '\n';
    csv += 'Diversification Ratio,' + (result.cdpr_analysis?.diversification_ratio || 0).toFixed(2) + '\n';
    csv += '\n';
    
    csv += '--- SYSTEM INFO ---\n';
    csv += 'Optimizer,Mean-Variance Portfolio Optimization\n';
    csv += 'Solver,CLARABEL (Conic Solver)\n';
    csv += 'Data Source,Yahoo Finance\n';
    csv += 'Generated By,CTPO Portfolio Optimizer\n';
    
    // Create download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const runOptimization = async () => {
    // Validate before running
    const validationErr = validateTickers(tickers);
    if (validationErr) {
      setValidationError(validationErr);
      setError(validationErr);
      return;
    }
    
    setLoading(true);
    setError(null);
    setValidationError(null);
    
    try {
      const tickerList = tickers.split(',').map(t => t.trim().toUpperCase()).filter(t => t);
      
      const response = await axios.post(`${API}/optimize`, {
        tickers: tickerList,
        period: period,
        target_return: 0.08,
        max_risk: 0.15,
        min_effective_assets: Math.min(10, tickerList.length),
        position_max: positionMax  // NEW: Pass user's position limit
      });
      
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Optimization failed');
    } finally {
      setLoading(false);
    }
  };

  // Prepare chart data
  const weightData = result ? Object.entries(result.weights)
    .map(([ticker, weight]) => ({ name: ticker, value: (weight * 100) }))
    .sort((a, b) => b.value - a.value) : [];

  // Simplified metrics data (no betas/volatilities in new API)
  const metricsData = result ? Object.entries(result.weights)
    .map(([ticker, weight]) => ({
      ticker,
      weight: weight * 100
    }))
    .sort((a, b) => b.weight - a.weight) : [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white py-6 md:py-8 px-4 md:px-6 shadow-lg">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl md:text-4xl font-bold mb-2 flex items-center gap-2 md:gap-3">
            <Activity className="w-8 h-8 md:w-10 md:h-10" />
            CTPO Portfolio Optimizer
          </h1>
          <p className="text-blue-100 text-sm md:text-lg">Cable-Driven Parallel Robot Portfolio Optimization System</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 md:px-6 py-4 md:py-8">
        {/* Input Section */}
        <Card className="mb-8 shadow-lg border-0">
          <CardHeader className="bg-gradient-to-r from-slate-50 to-blue-50">
            <CardTitle className="flex items-center gap-2">
              <PieChart className="w-5 h-5" />
              Portfolio Configuration
            </CardTitle>
            <CardDescription>Enter stock tickers and parameters</CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Stock Tickers (comma-separated)
                </label>
                <Input
                  data-testid="tickers-input"
                  value={tickers}
                  onChange={(e) => handleTickersChange(e.target.value)}
                  placeholder="AAPL,GOOGL,MSFT..."
                  className={`font-mono ${validationError ? 'border-red-500 border-2 focus:ring-red-500' : ''}`}
                />
                <p className={`mt-1 text-sm ${validationError ? 'text-red-600' : 'text-gray-500'}`}>
                  {validationError || 'Enter 2+ tickers separated by commas (e.g., AAPL,MSFT,GOOGL)'}
                </p>
                
                {/* Preset Portfolio Buttons */}
                <div className="mt-3">
                  <p className="text-xs text-gray-500 mb-2">Quick Select Portfolios:</p>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
                    {Object.entries(presetPortfolios).map(([key, preset]) => (
                      <button
                        key={key}
                        onClick={() => handlePresetClick(key)}
                        className={`
                          px-3 py-2 text-sm font-medium rounded-lg border-2 transition-all
                          ${activePreset === key 
                            ? 'border-blue-500 bg-blue-50 text-blue-700' 
                            : 'border-gray-200 bg-white text-gray-700 hover:border-blue-300 hover:bg-blue-50'
                          }
                        `}
                        title={preset.description}
                      >
                        <span className="text-lg mr-1">{preset.icon}</span>
                        <span className="block text-xs">{preset.name}</span>
                      </button>
                    ))}
                  </div>
                  {activePreset && (
                    <p className="mt-2 text-xs text-blue-600 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" />
                      {presetPortfolios[activePreset].description} ({presetPortfolios[activePreset].tickers.length} assets)
                    </p>
                  )}
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Time Period
                  </label>
                  <select 
                    data-testid="period-select"
                    value={period} 
                    onChange={(e) => setPeriod(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="3mo">3 Months</option>
                    <option value="6mo">6 Months</option>
                    <option value="1y">1 Year</option>
                    <option value="2y">2 Years</option>
                    <option value="5y">5 Years</option>
                  </select>
                </div>
              </div>
              
              {/* NEW: Position Limit Slider */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Maximum Position Size: {(positionMax * 100).toFixed(0)}%
                  <span className="text-xs text-gray-500 ml-2">
                    (Higher = More concentration = Higher risk/return)
                  </span>
                </label>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-gray-500">Conservative<br/>15%</span>
                  <input
                    type="range"
                    min="0.15"
                    max="0.50"
                    step="0.05"
                    value={positionMax}
                    onChange={(e) => setPositionMax(parseFloat(e.target.value))}
                    className="flex-1 h-2 bg-blue-100 rounded-lg appearance-none cursor-pointer"
                  />
                  <span className="text-xs text-gray-500">Aggressive<br/>50%</span>
                </div>
                <div className="mt-2 p-3 bg-amber-50 border border-amber-200 rounded-md">
                  <p className="text-xs text-amber-800 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    {positionMax <= 0.20 ? 
                      "Balanced (20% limit): Good risk/return tradeoff" :
                      positionMax <= 0.30 ?
                      "Moderate (25-30% limit): Higher returns, moderate risk increase" :
                      "Aggressive (35-50% limit): Maximum returns but significantly higher risk"}
                  </p>
                </div>
              </div>

              <Button 
                data-testid="optimize-button"
                onClick={runOptimization} 
                disabled={loading || validationError !== null}
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold py-6 text-lg shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <div className="w-5 h-5 border-3 border-white border-t-transparent rounded-full animate-spin" />
                    Optimizing...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Play className="w-5 h-5" />
                    Run CTPO Optimization
                  </span>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Error Display */}
        {error && (
          <Card className="mb-8 border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3 text-red-800">
                <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-semibold">Optimization Error</p>
                  <p className="text-sm mt-1">{error}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-8">
            {/* Performance Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card className="shadow-lg border-0">
                <CardContent className="pt-6">
                  <div className="text-sm text-gray-500 mb-1">Sharpe Ratio</div>
                  <div className="text-3xl font-bold text-blue-600">
                    {result.performance.sharpe_ratio.toFixed(2)}
                  </div>
                </CardContent>
              </Card>
              
              <Card className="shadow-lg border-0">
                <CardContent className="pt-6">
                  <div className="text-sm text-gray-500 mb-1">Annual Return</div>
                  <div className="text-3xl font-bold text-green-600">
                    {(result.performance.annual_return * 100).toFixed(1)}%
                  </div>
                </CardContent>
              </Card>
              
              <Card className="shadow-lg border-0">
                <CardContent className="pt-6">
                  <div className="text-sm text-gray-500 mb-1">Max Drawdown</div>
                  <div className="text-3xl font-bold text-red-600">
                    {(result.performance.max_drawdown * 100).toFixed(1)}%
                  </div>
                </CardContent>
              </Card>
              
              <Card className="shadow-lg border-0">
                <CardContent className="pt-6">
                  <div className="text-sm text-gray-500 mb-1">Sortino Ratio</div>
                  <div className="text-3xl font-bold text-purple-600">
                    {result.performance.sortino_ratio.toFixed(2)}
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* Export Button */}
            <div className="flex justify-center">
              <Button 
                onClick={exportToCSV}
                className="bg-green-600 hover:bg-green-700 text-white px-8 py-3 text-lg shadow-lg"
              >
                <Download className="w-5 h-5 mr-2" />
                Export Results to CSV
              </Button>
            </div>

            {/* Portfolio Weights */}
            <Card className="shadow-lg border-0">
              <CardHeader className="bg-gradient-to-r from-slate-50 to-blue-50">
                <CardTitle>Portfolio Allocation</CardTitle>
                <CardDescription>Optimized weights using CDPR force balance</CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <RePieChart>
                        <Pie
                          data={weightData}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
                          outerRadius={100}
                          fill="#8884d8"
                          dataKey="value"
                        >
                          {weightData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value) => `${value.toFixed(2)}%`} />
                      </RePieChart>
                    </ResponsiveContainer>
                  </div>
                  
                  <div className="space-y-2">
                    {weightData.map((item, idx) => (
                      <div key={idx} className="flex items-center gap-3">
                        <div 
                          className="w-4 h-4 rounded" 
                          style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                        />
                        <span className="font-semibold w-16">{item.name}</span>
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div 
                            className="h-2 rounded-full" 
                            style={{ 
                              width: `${item.value}%`, 
                              backgroundColor: COLORS[idx % COLORS.length] 
                            }}
                          />
                        </div>
                        <span className="text-sm font-medium w-16 text-right">
                          {item.value.toFixed(2)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Risk Metrics */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="shadow-lg border-0">
                <CardHeader className="bg-gradient-to-r from-slate-50 to-blue-50">
                  <CardTitle>Risk Analysis</CardTitle>
                  <CardDescription>Volatility and correlation metrics</CardDescription>
                </CardHeader>
                <CardContent className="pt-6 space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Market Volatility</span>
                    <Badge variant="secondary" className="text-base px-3 py-1">
                      {result.risk_analysis.market_volatility.toFixed(2)}%
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Portfolio Volatility</span>
                    <Badge variant="secondary" className="text-base px-3 py-1">
                      {result.risk_analysis.portfolio_volatility.toFixed(2)}%
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Avg Correlation</span>
                    <Badge variant="secondary" className="text-base px-3 py-1">
                      {result.risk_analysis.avg_correlation.toFixed(3)}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Stress Level (α)</span>
                    <Badge 
                      variant={result.risk_analysis.stress_level > 0.5 ? "destructive" : "secondary"}
                      className="text-base px-3 py-1"
                    >
                      {result.risk_analysis.stress_level.toFixed(3)}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Condition Number</span>
                    <Badge variant="secondary" className="text-base px-3 py-1">
                      {result.risk_analysis.covariance_condition.toFixed(0)}
                    </Badge>
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow-lg border-0">
                <CardHeader className="bg-gradient-to-r from-slate-50 to-blue-50">
                  <CardTitle>CDPR Validation</CardTitle>
                  <CardDescription>Force balance and diversification</CardDescription>
                </CardHeader>
                <CardContent className="pt-6 space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Force Balance</span>
                    {result.cdpr_analysis.force_balance_satisfied ? (
                      <Badge className="bg-green-500 text-white text-base px-3 py-1">
                        <CheckCircle2 className="w-4 h-4 mr-1" />
                        N/A (CDPR Removed)
                      </Badge>
                    ) : (
                      <Badge variant="secondary" className="text-base px-3 py-1">
                        <AlertCircle className="w-4 h-4 mr-1" />
                        N/A (CDPR Removed)
                      </Badge>
                    )}
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Force Residual</span>
                    <Badge variant="secondary" className="text-base px-3 py-1">
                      {result.cdpr_analysis.force_residual_norm.toFixed(6)}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Effective N Assets (ENP)</span>
                    <Badge variant="secondary" className="text-base px-3 py-1">
                      {result.cdpr_analysis.effective_n_assets.toFixed(1)}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Diversification Ratio</span>
                    <Badge variant="secondary" className="text-base px-3 py-1">
                      {result.cdpr_analysis.diversification_ratio.toFixed(2)}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Asset Metrics */}
            <Card className="shadow-lg border-0">
              <CardHeader className="bg-gradient-to-r from-slate-50 to-blue-50">
                <CardTitle>Portfolio Allocation Details</CardTitle>
                <CardDescription>Weight distribution across assets</CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={metricsData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="ticker" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="weight" fill="#3b82f6" name="Portfolio Weight (%)" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
