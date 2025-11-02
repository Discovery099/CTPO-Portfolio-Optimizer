import { useState } from 'react';
import axios from 'axios';
import { Play, TrendingUp, PieChart, Activity, AlertCircle, CheckCircle2 } from 'lucide-react';
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

  const runOptimization = async () => {
    setLoading(true);
    setError(null);
    
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

  const metricsData = result ? Object.entries(result.metrics.betas)
    .map(([ticker, beta]) => ({
      ticker,
      beta: beta,
      volatility: result.metrics.volatilities[ticker] * 100,
      expected_return: result.metrics.expected_returns[ticker] * 100
    })) : [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white py-8 px-6 shadow-lg">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-4xl font-bold mb-2 flex items-center gap-3">
            <Activity className="w-10 h-10" />
            CTPO Portfolio Optimizer
          </h1>
          <p className="text-blue-100 text-lg">Cable-Driven Parallel Robot Portfolio Optimization System</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
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
                  onChange={(e) => setTickers(e.target.value)}
                  placeholder="AAPL,GOOGL,MSFT..."
                  className="font-mono"
                />
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

              <Button 
                data-testid="optimize-button"
                onClick={runOptimization} 
                disabled={loading}
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold py-6 text-lg shadow-lg"
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
                      {(result.metrics.market_volatility * 100).toFixed(2)}%
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Portfolio Volatility</span>
                    <Badge variant="secondary" className="text-base px-3 py-1">
                      {(result.risk_analysis.portfolio_volatility * 100).toFixed(2)}%
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Avg Correlation</span>
                    <Badge variant="secondary" className="text-base px-3 py-1">
                      {result.metrics.avg_correlation.toFixed(3)}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Stress Level (α)</span>
                    <Badge 
                      variant={result.metrics.stress_level > 0.5 ? "destructive" : "secondary"}
                      className="text-base px-3 py-1"
                    >
                      {result.metrics.stress_level.toFixed(3)}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Condition Number</span>
                    <Badge variant="secondary" className="text-base px-3 py-1">
                      {result.risk_analysis.covariance_condition_number.toFixed(0)}
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
                        Satisfied
                      </Badge>
                    ) : (
                      <Badge variant="destructive" className="text-base px-3 py-1">
                        <AlertCircle className="w-4 h-4 mr-1" />
                        Violated
                      </Badge>
                    )}
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Force Residual</span>
                    <Badge variant="secondary" className="text-base px-3 py-1">
                      {result.cdpr_analysis.force_residual.toFixed(6)}
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
                      {result.risk_analysis.diversification_ratio.toFixed(2)}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Asset Metrics */}
            <Card className="shadow-lg border-0">
              <CardHeader className="bg-gradient-to-r from-slate-50 to-blue-50">
                <CardTitle>Asset Metrics</CardTitle>
                <CardDescription>Beta, volatility, and expected returns</CardDescription>
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
                      <Bar dataKey="beta" fill="#3b82f6" name="Beta" />
                      <Bar dataKey="volatility" fill="#ef4444" name="Volatility (%)" />
                      <Bar dataKey="expected_return" fill="#10b981" name="Expected Return (%)" />
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
