"""
Paper Trading API Client Examples - Phase 6B

Demonstrates how to interact with the paper trading REST API
for real-world use cases:

1. Python synchronous client
2. Python async client  
3. WebSocket real-time monitoring
4. Integration with external signals
5. Performance monitoring
"""

import requests
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any
import websockets


# ============================================================================
# 1. PYTHON SYNCHRONOUS CLIENT
# ============================================================================

class PaperTradingClient:
    """Synchronous Python client for Paper Trading API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 10):
        """
        Initialize the client.
        
        Args:
            base_url: API base URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
    
    def start_engine(
        self,
        initial_capital: float = 100000,
        kelly_fraction: float = 0.25,
        max_position_pct: float = 0.10,
        max_daily_loss_pct: float = 0.02,
        max_drawdown_pct: float = 0.15,
        min_confidence: float = 0.60,
    ) -> Dict[str, Any]:
        """Start paper trading engine."""
        payload = {
            "initial_capital": initial_capital,
            "kelly_fraction": kelly_fraction,
            "max_position_pct": max_position_pct,
            "max_daily_loss_pct": max_daily_loss_pct,
            "max_drawdown_pct": max_drawdown_pct,
            "min_confidence": min_confidence,
        }
        response = self.session.post(
            f"{self.base_url}/paper-trading/start",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current engine status."""
        response = self.session.get(
            f"{self.base_url}/paper-trading/status",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def get_performance(self) -> Dict[str, Any]:
        """Get performance metrics."""
        response = self.session.get(
            f"{self.base_url}/paper-trading/performance",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def get_portfolio(self) -> Dict[str, Any]:
        """Get portfolio snapshot."""
        response = self.session.get(
            f"{self.base_url}/paper-trading/portfolio",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def get_trades(self, limit: int = 50, offset: int = 0, status_filter: Optional[str] = None) -> list:
        """Get trade history with pagination."""
        params = {"limit": limit, "offset": offset}
        if status_filter:
            params["status_filter"] = status_filter
        
        response = self.session.get(
            f"{self.base_url}/paper-trading/trades",
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def get_risk_report(self) -> Dict[str, Any]:
        """Get comprehensive risk report."""
        response = self.session.get(
            f"{self.base_url}/paper-trading/risk-report",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def inject_signal(
        self,
        model_name: str,
        signal_type: str,  # LONG, SHORT, CLOSE, HOLD
        confidence: float,
        price: float,
        regime: str = "NORMAL",
        reasoning: str = "",
    ) -> Dict[str, Any]:
        """Inject a trading signal."""
        payload = {
            "model_name": model_name,
            "signal_type": signal_type,
            "confidence": confidence,
            "price": price,
            "regime": regime,
            "reasoning": reasoning,
        }
        response = self.session.post(
            f"{self.base_url}/paper-trading/signal",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def update_config(
        self,
        kelly_fraction: Optional[float] = None,
        max_position_pct: Optional[float] = None,
        max_daily_loss_pct: Optional[float] = None,
        max_drawdown_pct: Optional[float] = None,
        min_confidence: Optional[float] = None,
        trading_enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update engine configuration."""
        payload = {}
        if kelly_fraction is not None:
            payload["kelly_fraction"] = kelly_fraction
        if max_position_pct is not None:
            payload["max_position_pct"] = max_position_pct
        if max_daily_loss_pct is not None:
            payload["max_daily_loss_pct"] = max_daily_loss_pct
        if max_drawdown_pct is not None:
            payload["max_drawdown_pct"] = max_drawdown_pct
        if min_confidence is not None:
            payload["min_confidence"] = min_confidence
        if trading_enabled is not None:
            payload["trading_enabled"] = trading_enabled
        
        response = self.session.post(
            f"{self.base_url}/paper-trading/config",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def reset_daily(self) -> Dict[str, Any]:
        """Reset daily counters."""
        response = self.session.post(
            f"{self.base_url}/paper-trading/reset-daily",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def stop_engine(self) -> Dict[str, Any]:
        """Stop paper trading engine."""
        response = self.session.post(
            f"{self.base_url}/paper-trading/stop",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def close(self):
        """Close session."""
        self.session.close()


# ============================================================================
# 2. PYTHON ASYNC CLIENT
# ============================================================================

class AsyncPaperTradingClient:
    """Asynchronous Python client for Paper Trading API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 10):
        """Initialize async client."""
        self.base_url = base_url
        self.timeout = timeout
        # Note: Requires httpx for async HTTP
        try:
            import httpx
            self.client = httpx.AsyncClient(timeout=timeout)
        except ImportError:
            raise ImportError("httpx required for async client: pip install httpx")
    
    async def start_engine(
        self,
        initial_capital: float = 100000,
        kelly_fraction: float = 0.25,
        **kwargs
    ) -> Dict[str, Any]:
        """Start paper trading engine (async)."""
        payload = {
            "initial_capital": initial_capital,
            "kelly_fraction": kelly_fraction,
            **kwargs
        }
        response = await self.client.post(
            f"{self.base_url}/paper-trading/start",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def get_status(self) -> Dict[str, Any]:
        """Get status (async)."""
        response = await self.client.get(
            f"{self.base_url}/paper-trading/status"
        )
        response.raise_for_status()
        return response.json()
    
    async def inject_signal(
        self,
        model_name: str,
        signal_type: str,
        confidence: float,
        price: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Inject signal (async)."""
        payload = {
            "model_name": model_name,
            "signal_type": signal_type,
            "confidence": confidence,
            "price": price,
            **kwargs
        }
        response = await self.client.post(
            f"{self.base_url}/paper-trading/signal",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close session."""
        await self.client.aclose()


# ============================================================================
# 3. WEBSOCKET REAL-TIME MONITORING
# ============================================================================

class PaperTradingMonitor:
    """WebSocket client for real-time portfolio monitoring."""
    
    def __init__(self, base_url: str = "ws://localhost:8000", on_update=None):
        """
        Initialize monitor.
        
        Args:
            base_url: WebSocket base URL
            on_update: Callback function for updates (optional)
        """
        self.base_url = base_url
        self.on_update = on_update or self._default_handler
        self.ws = None
        self.running = False
    
    async def connect(self):
        """Connect to WebSocket."""
        url = f"{self.base_url}/paper-trading/ws"
        self.ws = await websockets.connect(url)
        self.running = True
        print(f"Connected to {url}")
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.ws:
            await self.ws.close()
            self.running = False
            print("Disconnected")
    
    async def listen(self):
        """Listen for updates."""
        try:
            while self.running and self.ws:
                message = await self.ws.recv()
                data = json.loads(message)
                await self.on_update(data)
        except Exception as e:
            print(f"Error listening: {e}")
            self.running = False
    
    async def send_ping(self):
        """Send ping to keep alive."""
        if self.ws:
            await self.ws.send(json.dumps({"type": "ping"}))
    
    async def request_status(self):
        """Request status update."""
        if self.ws:
            await self.ws.send(json.dumps({"type": "get_status"}))
    
    @staticmethod
    async def _default_handler(data: Dict[str, Any]):
        """Default message handler."""
        event_type = data.get("event", "unknown")
        timestamp = data.get("timestamp", "")
        print(f"[{timestamp}] Event: {event_type}")
        if "data" in data:
            print(f"  Data: {json.dumps(data['data'], indent=2)}")


# ============================================================================
# 4. USAGE EXAMPLES
# ============================================================================

def example_basic_workflow():
    """Example: Basic paper trading workflow."""
    print("=" * 70)
    print("Example 1: Basic Paper Trading Workflow")
    print("=" * 70)
    
    client = PaperTradingClient()
    
    try:
        # Start engine
        print("\n1. Starting engine with $100k capital...")
        result = client.start_engine(initial_capital=100000)
        print(f"   ✓ Engine started: {result['status']}")
        
        # Get status
        print("\n2. Checking status...")
        status = client.get_status()
        print(f"   Portfolio value: ${status['portfolio']['total_value']:,.2f}")
        print(f"   Cash: ${status['portfolio']['cash']:,.2f}")
        
        # Get performance
        print("\n3. Checking performance metrics...")
        perf = client.get_performance()
        print(f"   Total value: ${perf['total_value']:,.2f}")
        print(f"   P&L: ${perf['pnl_total']:,.2f}")
        print(f"   Sharpe ratio: {perf['sharpe_ratio']:.2f}")
        
        # Inject signal
        print("\n4. Injecting LONG signal...")
        signal_result = client.inject_signal(
            model_name="ensemble",
            signal_type="LONG",
            confidence=0.85,
            price=2045.50,
            regime="GROWTH",
            reasoning="Strong uptrend across multiple models"
        )
        print(f"   Signal processed: {signal_result['signal_processed']}")
        
        # Get trades
        print("\n5. Retrieving trade history...")
        trades = client.get_trades(limit=10)
        print(f"   Total trades: {len(trades)}")
        
        # Get portfolio
        print("\n6. Getting portfolio snapshot...")
        portfolio = client.get_portfolio()
        print(f"   Timestamp: {portfolio['timestamp']}")
        print(f"   Return: {portfolio['return_pct']:.2f}%")
        
        # Stop engine
        print("\n7. Stopping engine...")
        stop_result = client.stop_engine()
        print(f"   ✓ Engine stopped")
        print(f"   Final P&L: ${stop_result['details']['total_pnl']:,.2f}")
        
    finally:
        client.close()


def example_signal_injection():
    """Example: Injecting signals from external models."""
    print("\n" + "=" * 70)
    print("Example 2: Injecting Signals from External Models")
    print("=" * 70)
    
    client = PaperTradingClient()
    
    try:
        # Start engine
        client.start_engine()
        
        # Simulate signals from different models
        models = ["wavelet", "hmm", "lstm", "tft", "genetic", "ensemble"]
        signals = ["LONG", "SHORT", "HOLD"]
        
        print("\nInjecting signals from multiple models...")
        for model in models[:3]:  # First 3 models
            signal_type = "LONG"
            confidence = 0.70 + (models.index(model) * 0.05)
            
            result = client.inject_signal(
                model_name=model,
                signal_type=signal_type,
                confidence=confidence,
                price=2045.50,
                regime="NORMAL",
                reasoning=f"Signal from {model} model"
            )
            print(f"   {model:12} → {signal_type:6} @ confidence {confidence:.2f}")
        
        # Check consolidated status
        perf = client.get_performance()
        print(f"\n   Portfolio P&L: ${perf['pnl_total']:,.2f}")
        
        client.stop_engine()
        
    finally:
        client.close()


def example_configuration_update():
    """Example: Updating engine configuration dynamically."""
    print("\n" + "=" * 70)
    print("Example 3: Dynamic Configuration Updates")
    print("=" * 70)
    
    client = PaperTradingClient()
    
    try:
        # Start engine
        client.start_engine(kelly_fraction=0.25)
        print("\n1. Initial configuration: Kelly fraction = 0.25")
        
        # Update Kelly fraction
        print("\n2. Increasing Kelly fraction to 0.35...")
        result = client.update_config(kelly_fraction=0.35)
        print(f"   ✓ Configuration updated")
        print(f"   Fields updated: {result['updated_fields']}")
        
        # Reduce risk
        print("\n3. Reducing max position size from 10% to 5%...")
        result = client.update_config(max_position_pct=0.05)
        print(f"   ✓ Position size reduced")
        
        # Lower drawdown limit
        print("\n4. Lowering max drawdown limit from 15% to 10%...")
        result = client.update_config(max_drawdown_pct=0.10)
        print(f"   ✓ Drawdown limit lowered")
        
        client.stop_engine()
        
    finally:
        client.close()


async def example_async_monitoring():
    """Example: Async monitoring with real-time updates."""
    print("\n" + "=" * 70)
    print("Example 4: Async Real-Time Monitoring")
    print("=" * 70)
    
    client = AsyncPaperTradingClient()
    
    try:
        # Start engine
        print("\n1. Starting engine...")
        await client.start_engine()
        print("   ✓ Engine started")
        
        # Periodic status checks
        for i in range(3):
            status = await client.get_status()
            print(f"\n   Check {i+1}: Portfolio value = ${status['portfolio']['total_value']:,.2f}")
            await asyncio.sleep(1)
        
        await client.stop_engine()
        
    finally:
        await client.close()


async def example_websocket_monitoring():
    """Example: WebSocket real-time monitoring."""
    print("\n" + "=" * 70)
    print("Example 5: WebSocket Real-Time Monitoring")
    print("=" * 70)
    
    # Define custom handler
    async def handle_update(data):
        event_type = data.get("event")
        if event_type == "portfolio_update":
            pnl = data.get("data", {}).get("pnl_total", 0)
            print(f"   Portfolio Update: P&L = ${pnl:,.2f}")
        elif event_type == "trade_executed":
            trade_id = data.get("data", {}).get("trade_id", "?")
            print(f"   Trade Executed: {trade_id}")
        else:
            print(f"   Event: {event_type}")
    
    monitor = PaperTradingMonitor(on_update=handle_update)
    
    try:
        print("\nConnecting to WebSocket...")
        await monitor.connect()
        
        # Listen for 10 seconds
        listen_task = asyncio.create_task(monitor.listen())
        
        for i in range(10):
            await asyncio.sleep(1)
            # Periodically request status
            if i % 3 == 0:
                await monitor.request_status()
        
        await monitor.disconnect()
        
    finally:
        if listen_task:
            listen_task.cancel()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\nPaper Trading API - Client Examples")
    print("=" * 70)
    
    # Run synchronous examples
    try:
        example_basic_workflow()
        example_signal_injection()
        example_configuration_update()
    except Exception as e:
        print(f"\nError running synchronous examples: {e}")
        print("Make sure API server is running: python main.py --mode api")
    
    # Run async examples
    try:
        print("\n" + "=" * 70)
        print("Running Async Examples...")
        asyncio.run(example_async_monitoring())
        # Note: WebSocket example requires server, skip in standalone
        # asyncio.run(example_websocket_monitoring())
    except Exception as e:
        print(f"\nNote: Async examples require httpx and running server")
        print(f"To use async client: pip install httpx")
    
    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
