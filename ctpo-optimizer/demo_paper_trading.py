"""
Demo script for CHUNK 7 - Paper Trading System
"""

import sys
sys.path.insert(0, '/app/ctpo-optimizer')

from ctpo.execution.live_trader import run_paper_trading
import asyncio

print("="*70)
print("CTPO PAPER TRADING DEMONSTRATION")
print("="*70)
print()
print("This demo simulates live portfolio optimization with:")
print("  - Real market data from Yahoo Finance")
print("  - CTPO optimization every 60 seconds")
print("  - Automatic rebalancing when conditions met")
print("  - Performance tracking and logging")
print()
print("Note: This is a SIMULATION - no real trades are executed")
print("="*70)
print()

# Run paper trading for 10 minutes as demonstration
symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN']
duration = 0.17  # ~10 minutes

print(f"Starting paper trading with {len(symbols)} assets...")
print(f"Duration: {duration*60:.0f} minutes")
print(f"Symbols: {', '.join(symbols)}")
print()

try:
    run_paper_trading(
        symbols=symbols,
        duration_hours=duration,
        initial_capital=1000000
    )
except KeyboardInterrupt:
    print("\n\nDemo stopped by user")
except Exception as e:
    print(f"\n\nDemo error: {e}")

print("\n" + "="*70)
print("DEMO COMPLETE")
print("="*70)
