"""
Live trading system for real-time portfolio optimization
"""

import asyncio
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiveTradingSystem:
    """
    Real-time portfolio optimization and paper trading system.
    """
    
    def __init__(self,
                 symbols: List[str],
                 initial_capital: float = 1000000,
                 update_interval: int = 300,  # seconds (5 minutes default)
                 lookback_periods: int = 252):
        """
        Initialize live trading system.
        
        Args:
            symbols: List of ticker symbols
            initial_capital: Starting portfolio value
            update_interval: Seconds between optimization cycles
            lookback_periods: Historical periods for risk estimation
        """
        self.symbols = symbols
        self.n_assets = len(symbols)
        self.capital = initial_capital
        self.update_interval = update_interval
        self.lookback_periods = lookback_periods
        
        # Initialize components
        from ctpo.core.optimizer import CTPOOptimizer
        from ctpo.risk.risk_model import RiskModel
        from ctpo.metrics.performance import PerformanceMetrics
        
        self.optimizer = CTPOOptimizer()
        self.risk_model = RiskModel()
        self.metrics = PerformanceMetrics()
        
        # State tracking
        self.current_weights = np.ones(self.n_assets) / self.n_assets
        self.current_prices = np.zeros(self.n_assets)
        self.returns_buffer = []
        self.trade_log = []
        self.performance_log = []
        
        # Control flags
        self.running = False
        self.last_rebalance = None
        self.rebalance_cooldown = 300  # 5 minutes between rebalances
        
        logger.info(f"🚀 LiveTradingSystem initialized")
        logger.info(f"   Symbols: {', '.join(symbols)}")
        logger.info(f"   Update Interval: {update_interval}s")
        logger.info(f"   Initial Capital: ${initial_capital:,.0f}")
    
    async def start(self, duration_hours: Optional[float] = None):
        """
        Start live trading loop.
        
        Args:
            duration_hours: Run for specified hours (None = indefinite)
        """
        self.running = True
        start_time = datetime.now()
        
        logger.info(f"\n{'='*70}")
        logger.info(f"▶️  Starting live trading at {start_time}")
        logger.info(f"{'='*70}\n")
        
        try:
            cycle = 0
            while self.running:
                cycle += 1
                
                # Check duration limit
                if duration_hours:
                    elapsed = (datetime.now() - start_time).total_seconds() / 3600
                    if elapsed > duration_hours:
                        logger.info(f"⏱️  Duration limit reached: {duration_hours} hours")
                        break
                
                logger.info(f"\n--- Cycle {cycle} at {datetime.now().strftime('%H:%M:%S')} ---")
                
                # 1. Fetch latest market data
                await self._update_market_data()
                
                # 2. Check if rebalancing needed
                if self._should_rebalance():
                    await self._rebalance_portfolio()
                
                # 3. Log performance
                self._log_performance()
                
                # 4. Wait for next cycle
                await asyncio.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            logger.info("\n⏹️  Manual stop requested")
        except Exception as e:
            logger.error(f"❌ Error in trading loop: {e}", exc_info=True)
        finally:
            self.running = False
            await self._shutdown()
    
    async def _update_market_data(self):
        """Fetch latest prices and update returns buffer."""
        try:
            # Fetch recent data
            data = yf.download(
                self.symbols,
                period='5d',
                interval='1d',
                progress=False
            )
            
            if data.empty:
                logger.warning("⚠️  No data received")
                return
            
            # Extract latest prices
            if len(self.symbols) > 1:
                if isinstance(data.columns, pd.MultiIndex):
                    latest_prices = data['Adj Close'].iloc[-1].values
                else:
                    latest_prices = data['Adj Close'].values
            else:
                latest_prices = np.array([data['Adj Close'].iloc[-1]])
            
            # Calculate returns if we have previous prices
            if not np.all(self.current_prices == 0):
                returns = (latest_prices - self.current_prices) / self.current_prices
                
                self.returns_buffer.append({
                    'timestamp': datetime.now(),
                    'returns': returns,
                    'prices': latest_prices
                })
                
                # Keep only recent history
                if len(self.returns_buffer) > self.lookback_periods:
                    self.returns_buffer.pop(0)
                
                logger.info(f"   Market data updated: {len(self.returns_buffer)} periods")
            
            self.current_prices = latest_prices
            
        except Exception as e:
            logger.error(f"❌ Error fetching market data: {e}")
    
    def _should_rebalance(self) -> bool:
        """Determine if portfolio should be rebalanced."""
        # Need sufficient data
        if len(self.returns_buffer) < 50:
            logger.info(f"   Insufficient data: {len(self.returns_buffer)}/50")
            return False
        
        # Respect cooldown period
        if self.last_rebalance:
            seconds_since = (datetime.now() - self.last_rebalance).total_seconds()
            if seconds_since < self.rebalance_cooldown:
                logger.info(f"   Cooldown active: {seconds_since:.0f}s / {self.rebalance_cooldown}s")
                return False
        
        logger.info("   ✅ Ready to rebalance")
        return True
    
    async def _rebalance_portfolio(self):
        """Execute portfolio rebalancing."""
        try:
            logger.info(f"\n{'='*70}")
            logger.info("⚖️  REBALANCING PORTFOLIO")
            logger.info(f"{'='*70}")
            
            # 1. Prepare returns dataframe
            returns_data = [r['returns'] for r in self.returns_buffer]
            returns_df = pd.DataFrame(returns_data, columns=self.symbols)
            
            logger.info(f"   Using {len(returns_df)} periods of data")
            
            # 2. Update risk model
            risk_update = self.risk_model.update(returns_df, market_return=0.10)
            
            logger.info(f"   Market Vol: {risk_update['sigma_market']:.3f}")
            logger.info(f"   Stress Level (α): {risk_update['alpha_stress']:.3f}")
            logger.info(f"   Avg Correlation: {risk_update['avg_correlation']:.3f}")
            
            # 3. Run optimization
            tic = datetime.now()
            market_returns = returns_df.mean(axis=1).values
            
            target_weights = self.optimizer.optimize(
                returns_df.values,
                covariance=risk_update['Sigma'],
                expected_returns=risk_update['mu'],
                market_returns=market_returns
            )
            
            solve_time = (datetime.now() - tic).total_seconds() * 1000
            metrics = self.optimizer.get_metrics()
            
            logger.info(f"   Solve Time: {solve_time:.1f} ms")
            logger.info(f"   Status: {metrics.get('status', 'N/A')}")
            
            # 4. Calculate trades
            weight_changes = target_weights - self.current_weights
            total_turnover = np.sum(np.abs(weight_changes))
            
            logger.info(f"\n   Portfolio Changes (turnover: {total_turnover:.2%}):")
            for i, symbol in enumerate(self.symbols):
                if abs(weight_changes[i]) > 0.01:  # 1% threshold
                    logger.info(f"     {symbol:6s}: {self.current_weights[i]:>6.2%} → "
                              f"{target_weights[i]:>6.2%} ({weight_changes[i]:>+6.2%})")
            
            # 5. Update weights (simulation mode)
            self.current_weights = target_weights
            
            # 6. Log trade
            self.trade_log.append({
                'timestamp': datetime.now(),
                'weights': target_weights.copy(),
                'turnover': total_turnover,
                'solve_time_ms': solve_time
            })
            
            self.last_rebalance = datetime.now()
            logger.info("✅ Rebalancing complete\n")
            
        except Exception as e:
            logger.error(f"❌ Rebalancing failed: {e}", exc_info=True)
    
    def _calculate_portfolio_return(self) -> float:
        """Calculate current portfolio return."""
        if len(self.returns_buffer) < 2:
            return 0.0
        
        returns = np.array([r['returns'] for r in self.returns_buffer])
        portfolio_returns = returns @ self.current_weights
        
        return np.sum(portfolio_returns)
    
    def _log_performance(self):
        """Log current performance metrics."""
        if len(self.returns_buffer) < 2:
            return
        
        portfolio_return = self._calculate_portfolio_return()
        portfolio_value = self.capital * (1 + portfolio_return)
        
        self.performance_log.append({
            'timestamp': datetime.now(),
            'value': portfolio_value,
            'return': portfolio_return,
            'weights': self.current_weights.copy()
        })
        
        logger.info(f"   💰 Portfolio: ${portfolio_value:,.2f} ({portfolio_return:+.2%})")
    
    async def _shutdown(self):
        """Clean shutdown and final report."""
        logger.info(f"\n{'='*70}")
        logger.info("🛑 SHUTTING DOWN LIVE TRADING SYSTEM")
        logger.info(f"{'='*70}\n")
        
        if len(self.performance_log) > 1:
            # Calculate final metrics
            returns = [p['return'] for p in self.performance_log[1:]]
            returns_diff = np.diff([p['return'] for p in self.performance_log])
            
            final_return = self.performance_log[-1]['return']
            final_value = self.performance_log[-1]['value']
            
            logger.info(f"Final Performance:")
            logger.info(f"  Portfolio Value: ${final_value:,.2f}")
            logger.info(f"  Total Return: {final_return:+.2%}")
            logger.info(f"  Total Trades: {len(self.trade_log)}")
            
            # Save logs
            self._save_logs()
        
        logger.info("\n✅ Shutdown complete")
    
    def _save_logs(self):
        """Save performance and trade logs."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            # Save performance log
            if self.performance_log:
                perf_df = pd.DataFrame(self.performance_log)
                filename = f'performance_log_{timestamp}.csv'
                perf_df.to_csv(filename, index=False)
                logger.info(f"   💾 Performance log saved: {filename}")
            
            # Save trade log
            if self.trade_log:
                trade_df = pd.DataFrame(self.trade_log)
                filename = f'trade_log_{timestamp}.csv'
                trade_df.to_csv(filename, index=False)
                logger.info(f"   💾 Trade log saved: {filename}")
                
        except Exception as e:
            logger.error(f"❌ Failed to save logs: {e}")


def run_paper_trading(symbols: List[str],
                      duration_hours: float = 1,
                      initial_capital: float = 1000000):
    """
    Convenience function to run paper trading.
    
    Args:
        symbols: List of ticker symbols
        duration_hours: Hours to run
        initial_capital: Starting capital
    """
    system = LiveTradingSystem(
        symbols=symbols,
        initial_capital=initial_capital,
        update_interval=60  # 1 minute for testing
    )
    
    # Run async loop
    asyncio.run(system.start(duration_hours=duration_hours))
