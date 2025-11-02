"""
Mock Alpaca broker integration
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MockAlpacaBroker:
    """
    Mock Alpaca broker for testing without API keys.
    
    This is a placeholder implementation that simulates
    Alpaca API calls without actually connecting to Alpaca.
    """
    
    def __init__(self, paper: bool = True):
        """
        Initialize mock broker.
        
        Args:
            paper: Use paper trading mode
        """
        self.paper = paper
        self.connected = False
        self.positions = {}
        self.orders = []
        self.account = {
            'cash': 100000.0,
            'portfolio_value': 100000.0,
            'buying_power': 100000.0
        }
        
        logger.info("📋 MockAlpacaBroker initialized")
        logger.info(f"   Mode: {'Paper' if paper else 'Live'} Trading")
        logger.info(f"   Status: Simulation only (no real trades)")
    
    def connect(self) -> bool:
        """
        Mock connection to Alpaca.
        
        Returns:
            True if connected (always succeeds in mock)
        """
        logger.info("[MOCK] Connecting to Alpaca (simulated)...")
        self.connected = True
        return True
    
    def get_account(self) -> Dict:
        """
        Get mock account information.
        
        Returns:
            Mock account dictionary
        """
        return self.account.copy()
    
    async def place_order(self,
                          symbol: str,
                          qty: int,
                          side: str,
                          order_type: str = 'market',
                          time_in_force: str = 'day',
                          limit_price: Optional[float] = None) -> Dict:
        """
        Submit a mock order.
        
        Args:
            symbol: Stock symbol
            qty: Quantity
            side: 'buy' or 'sell'
            order_type: Order type
            time_in_force: Time in force
            limit_price: Limit price (if applicable)
            
        Returns:
            Mock order dictionary
        """
        order = {
            'id': f'mock_order_{len(self.orders)}',
            'symbol': symbol,
            'qty': qty,
            'side': side,
            'type': order_type,
            'time_in_force': time_in_force,
            'limit_price': limit_price,
            'status': 'filled',  # Mock: always filled
            'filled_avg_price': 100.0,  # Mock price
            'created_at': datetime.now().isoformat()
        }
        
        self.orders.append(order)
        logger.info(f"[MOCK] Order submitted: {side.upper()} {qty} shares of {symbol}")
        
        # Update positions
        current_qty = self.positions.get(symbol, 0)
        if side == 'buy':
            self.positions[symbol] = current_qty + qty
        else:
            self.positions[symbol] = current_qty - qty
        
        return order
    
    def get_positions(self) -> List[Dict]:
        """
        Get current positions.
        
        Returns:
            List of mock positions
        """
        return [
            {'symbol': symbol, 'qty': qty, 'market_value': qty * 100.0}
            for symbol, qty in self.positions.items()
            if qty != 0
        ]
    
    def close_position(self, symbol: str) -> bool:
        """
        Close a position.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if closed successfully
        """
        if symbol in self.positions:
            del self.positions[symbol]
            logger.info(f"[MOCK] Closed position: {symbol}")
            return True
        return False
    
    def cancel_all_orders(self):
        """Cancel all pending orders."""
        self.orders = []
        logger.info("[MOCK] All orders cancelled")
    
    def get_bars(self,
                 symbols: List[str],
                 timeframe: str = '1Day',
                 start: Optional[str] = None,
                 end: Optional[str] = None) -> Dict:
        """
        Get mock bar data.
        
        Args:
            symbols: List of symbols
            timeframe: Bar timeframe
            start: Start date
            end: End date
            
        Returns:
            Mock bar data
        """
        logger.info(f"[MOCK] Fetching bars for {symbols}")
        return {symbol: [] for symbol in symbols}
