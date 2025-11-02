"""
Mock Alpaca broker integration
"""

from typing import Dict, List, Optional
from datetime import datetime


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
    
    def connect(self) -> bool:
        """
        Mock connection to Alpaca.
        
        Returns:
            True if connected (always succeeds in mock)
        """
        print("[MOCK] Connecting to Alpaca (simulated)...")
        self.connected = True
        return True
    
    def get_account(self) -> Dict:
        """
        Get mock account information.
        
        Returns:
            Mock account dictionary
        """
        return {
            'cash': 100000.0,
            'portfolio_value': 100000.0,
            'buying_power': 100000.0,
            'pattern_day_trader': False
        }
    
    def submit_order(self,
                     symbol: str,
                     qty: int,
                     side: str,
                     order_type: str = 'market',
                     time_in_force: str = 'day') -> Dict:
        """
        Submit a mock order.
        
        Args:
            symbol: Stock symbol
            qty: Quantity
            side: 'buy' or 'sell'
            order_type: Order type
            time_in_force: Time in force
            
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
            'status': 'filled',  # Mock: always filled
            'filled_avg_price': 100.0,  # Mock price
            'created_at': datetime.now().isoformat()
        }
        
        self.orders.append(order)
        print(f"[MOCK] Order submitted: {side} {qty} shares of {symbol}")
        
        return order
    
    def get_positions(self) -> List[Dict]:
        """
        Get current positions.
        
        Returns:
            List of mock positions
        """
        return list(self.positions.values())
    
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
            print(f"[MOCK] Closed position: {symbol}")
            return True
        return False
    
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
        print(f"[MOCK] Fetching bars for {symbols}")
        return {symbol: [] for symbol in symbols}
