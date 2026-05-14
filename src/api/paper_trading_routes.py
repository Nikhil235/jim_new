"""
Paper Trading API Routes - Phase 6B Implementation (COMPLETE)
=============================================================

REST API endpoints for paper trading control, monitoring, and real-time updates.

Endpoints (10 total):
- POST /paper-trading/start          - Initialize and start paper trading engine
- GET  /paper-trading/status         - Get current engine status
- GET  /paper-trading/performance    - Get performance metrics
- POST /paper-trading/stop           - Stop engine and close positions
- GET  /paper-trading/trades         - Get trade history (paginated)
- GET  /paper-trading/portfolio      - Get portfolio snapshot
- GET  /paper-trading/risk-report    - Comprehensive risk analysis
- POST /paper-trading/signal         - Inject a trading signal
- POST /paper-trading/config         - Update engine configuration
- POST /paper-trading/reset-daily    - Reset daily P&L and counters
"""

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
import asyncio
import json

# Import paper trading modules
try:
    from src.paper_trading.engine import (
        PaperTradingEngine,
        PaperTradingConfig,
        TradeExecution,
        ModelSignal,
        SignalType,
        TradeStatus,
    )
    from src.paper_trading.risk_manager import RiskManager, RiskLimits
    from src.paper_trading.live_inference import (
        LiveInferenceLoop,
        LIVE_MODEL_SIGNALS,
        CURRENT_GOLD_PRICE,
        LAST_PRICE_UPDATE,
    )
    PAPER_TRADING_AVAILABLE = True
except ImportError:
    logger.warning("Paper trading modules not available")
    PaperTradingEngine = None
    RiskManager = None
    LiveInferenceLoop = None
    PAPER_TRADING_AVAILABLE = False


# ============================================================================
# PYDANTIC MODELS FOR REQUEST/RESPONSE
# ============================================================================

class PaperTradingStartRequest(BaseModel):
    """Request to start paper trading."""
    initial_capital: float = Field(default=100000.0, gt=0, description="Starting capital in USD")
    kelly_fraction: float = Field(default=0.25, ge=0.05, le=1.0, description="Kelly criterion fraction")
    max_position_pct: float = Field(default=0.10, ge=0.01, le=0.50, description="Max position as % of capital")
    max_daily_loss_pct: float = Field(default=0.02, ge=0.005, le=0.10, description="Max daily loss %")
    max_drawdown_pct: float = Field(default=0.15, ge=0.05, le=0.50, description="Max drawdown %")
    min_confidence: float = Field(default=0.60, ge=0.0, le=1.0, description="Min signal confidence to trade")


class PaperTradingStatusResponse(BaseModel):
    """Current paper trading status."""
    status: str  # INITIALIZED, RUNNING, STOPPED
    started_at: Optional[str] = None
    current_time: str
    uptime_seconds: Optional[float] = None
    portfolio: Dict
    trading: Dict
    models: Dict


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics for paper trading."""
    total_value: float
    cash: float
    position_quantity: float
    position_value: float
    pnl_total: float
    pnl_realized: float
    pnl_unrealized: float
    pnl_daily: float
    return_pct: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    num_trades: int
    daily_trades: int


class TradeHistoryResponse(BaseModel):
    """Trade record from history."""
    trade_id: str
    model_name: str
    signal_type: str
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    entry_time: str
    exit_time: Optional[str]
    pnl: float
    pnl_pct: float
    status: str
    regime: str = "NORMAL"
    confidence: float = 0.0


class PortfolioSnapshotResponse(BaseModel):
    """Portfolio state at a point in time."""
    timestamp: str
    total_value: float
    cash: float
    position_quantity: float
    position_value: float
    pnl_total: float
    daily_pnl: float
    return_pct: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    num_trades: int = 0


class SignalInjectionRequest(BaseModel):
    """Request to inject a trading signal."""
    model_name: str = Field(..., description="Model name: wavelet, hmm, lstm, tft, genetic, ensemble")
    signal_type: str = Field(..., description="Signal: LONG, SHORT, CLOSE, HOLD")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Signal confidence [0-1]")
    price: float = Field(..., gt=0, description="Current gold price")
    regime: str = Field(default="NORMAL", description="Market regime: GROWTH, NORMAL, CRISIS")
    reasoning: str = Field(default="", description="Signal reasoning")


class ConfigUpdateRequest(BaseModel):
    """Request to update paper trading configuration."""
    kelly_fraction: Optional[float] = Field(None, ge=0.05, le=1.0)
    max_position_pct: Optional[float] = Field(None, ge=0.01, le=0.50)
    max_daily_loss_pct: Optional[float] = Field(None, ge=0.005, le=0.10)
    max_drawdown_pct: Optional[float] = Field(None, ge=0.05, le=0.50)
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    trading_enabled: Optional[bool] = None


# ============================================================================
# GLOBAL STATE
# ============================================================================

_paper_trading_engine: Optional['PaperTradingEngine'] = None
_paper_trading_config: Optional['PaperTradingConfig'] = None
_risk_manager: Optional['RiskManager'] = None
_websocket_clients: List[WebSocket] = []
_inference_loop: Optional['LiveInferenceLoop'] = None
_inference_task: Optional[asyncio.Task] = None


def get_engine():
    """Get the paper trading engine instance (for testing injection)."""
    return _paper_trading_engine


def set_engine(engine, config=None, risk_mgr=None):
    """Set the paper trading engine instance (for testing injection)."""
    global _paper_trading_engine, _paper_trading_config, _risk_manager
    _paper_trading_engine = engine
    _paper_trading_config = config
    _risk_manager = risk_mgr


# ============================================================================
# ROUTER SETUP
# ============================================================================

router = APIRouter(
    prefix="/paper-trading",
    tags=["paper-trading"],
    responses={404: {"description": "Not found"}},
)


# ============================================================================
# WEBSOCKET BROADCAST HELPER
# ============================================================================

async def broadcast_update(event_type: str, data: Dict):
    """Broadcast update to all connected WebSocket clients."""
    message = json.dumps({"event": event_type, "data": data, "timestamp": datetime.now().isoformat()})
    disconnected = []
    for ws in _websocket_clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _websocket_clients.remove(ws)


# ============================================================================
# ROUTE HANDLERS
# ============================================================================

@router.post("/start", response_model=Dict)
async def start_paper_trading(request: PaperTradingStartRequest) -> Dict:
    """
    Start paper trading engine.
    
    Initializes the engine with specified capital, risk limits, and signal
    configuration. Returns initialization details on success.
    """
    global _paper_trading_engine, _paper_trading_config, _risk_manager
    
    if not PAPER_TRADING_AVAILABLE:
        raise HTTPException(status_code=500, detail="Paper trading module not available")
    
    if _paper_trading_engine is not None and _paper_trading_engine.status == "RUNNING":
        raise HTTPException(status_code=409, detail="Paper trading is already running. Stop it first.")
    
    try:
        # Create configuration
        _paper_trading_config = PaperTradingConfig(
            initial_capital=request.initial_capital,
            kelly_fraction=request.kelly_fraction,
            max_position_pct=request.max_position_pct,
            max_daily_loss_pct=request.max_daily_loss_pct,
            max_drawdown_pct=request.max_drawdown_pct,
            min_confidence=request.min_confidence,
        )
        
        # Initialize engine
        _paper_trading_engine = PaperTradingEngine(_paper_trading_config)
        
        # Initialize risk manager
        risk_limits = RiskLimits(
            max_position_pct=request.max_position_pct,
            max_daily_loss_pct=request.max_daily_loss_pct,
            max_drawdown_pct=request.max_drawdown_pct,
        )
        _risk_manager = RiskManager(request.initial_capital, risk_limits)
        
        # Start engine
        result = _paper_trading_engine.start()

        # ── Start live inference loop ──────────────────────────────────────
        global _inference_loop, _inference_task
        if LiveInferenceLoop is not None:
            _inference_loop = LiveInferenceLoop(
                engine=_paper_trading_engine,
                broadcast_fn=broadcast_update,
                interval_seconds=60,
            )
            _inference_task = asyncio.create_task(_inference_loop.run())
            logger.info("Live inference loop started (60s cadence, all 6 models)")
        # ─────────────────────────────────────────────────────────────────

        logger.info(f"Paper trading started with ${request.initial_capital:,.0f} capital")
        
        # Broadcast to WebSocket clients
        await broadcast_update("engine_started", result)
        
        return {
            "status": "success",
            "message": "Paper trading engine started",
            "config": {
                "initial_capital": request.initial_capital,
                "kelly_fraction": request.kelly_fraction,
                "max_position_pct": request.max_position_pct,
                "max_daily_loss_pct": request.max_daily_loss_pct,
                "min_confidence": request.min_confidence,
            },
            "details": result,
        }
    
    except Exception as e:
        logger.error(f"Failed to start paper trading: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start: {str(e)}")


@router.get("/status", response_model=PaperTradingStatusResponse)
async def get_paper_trading_status() -> PaperTradingStatusResponse:
    """
    Get current paper trading status including portfolio, trading stats,
    and per-model signal information.
    """
    global _paper_trading_engine
    
    if _paper_trading_engine is None:
        raise HTTPException(
            status_code=404,
            detail="Paper trading engine not initialized. Call POST /paper-trading/start first."
        )
    
    try:
        status_dict = _paper_trading_engine.get_status()
        
        # Calculate uptime
        uptime = None
        if _paper_trading_engine.started_at:
            uptime = (datetime.now() - _paper_trading_engine.started_at).total_seconds()
        
        return PaperTradingStatusResponse(
            status=status_dict["status"],
            started_at=status_dict["started_at"],
            current_time=status_dict["current_time"],
            uptime_seconds=uptime,
            portfolio=status_dict["portfolio"],
            trading=status_dict["trading"],
            models=status_dict["models"],
        )
    
    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics() -> PerformanceMetricsResponse:
    """
    Get performance metrics including P&L breakdown, Sharpe ratio,
    drawdown, and win rate.
    """
    global _paper_trading_engine
    
    if _paper_trading_engine is None:
        raise HTTPException(status_code=404, detail="Paper trading engine not initialized")
    
    try:
        snapshot = _paper_trading_engine._create_portfolio_snapshot()
        
        return PerformanceMetricsResponse(
            total_value=snapshot.total_value,
            cash=snapshot.cash,
            position_quantity=snapshot.position_quantity,
            position_value=snapshot.position_value,
            pnl_total=snapshot.pnl_total,
            pnl_realized=snapshot.pnl_realized,
            pnl_unrealized=snapshot.pnl_unrealized,
            pnl_daily=snapshot.daily_pnl,
            return_pct=snapshot.return_pct,
            sharpe_ratio=snapshot.sharpe_ratio,
            max_drawdown=snapshot.max_drawdown,
            win_rate=snapshot.win_rate,
            num_trades=snapshot.num_trades,
            daily_trades=len(_paper_trading_engine.daily_trades),
        )
    
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.post("/stop", response_model=Dict)
async def stop_paper_trading() -> Dict:
    """
    Stop paper trading and close all open positions.
    Returns final P&L summary and session statistics.
    """
    global _paper_trading_engine
    
    if _paper_trading_engine is None:
        raise HTTPException(status_code=404, detail="Paper trading engine not initialized")
    
    try:
        result = _paper_trading_engine.stop()

        # ── Stop live inference loop ──────────────────────────────────────
        global _inference_loop, _inference_task
        if _inference_loop is not None:
            _inference_loop.stop()
            _inference_loop = None
            logger.info("Live inference loop stopped")
        # ─────────────────────────────────────────────────────────────────

        logger.info(f"Paper trading stopped. Final P&L: ${result.get('total_pnl', 0):.2f}")
        
        # Broadcast to WebSocket clients
        await broadcast_update("engine_stopped", result)
        
        return {
            "status": "success",
            "message": "Paper trading stopped",
            "details": result,
        }
    
    except Exception as e:
        logger.error(f"Failed to stop paper trading: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop: {str(e)}")


@router.get("/trades", response_model=List[TradeHistoryResponse])
async def get_trade_history(
    limit: int = Query(50, ge=1, le=500, description="Number of trades to return"),
    offset: int = Query(0, ge=0, description="Number of trades to skip"),
    status_filter: Optional[str] = Query(None, description="Filter by status: OPEN, CLOSED, ALL"),
) -> List[TradeHistoryResponse]:
    """
    Get trade history with pagination and optional status filtering.
    """
    global _paper_trading_engine
    
    if _paper_trading_engine is None:
        raise HTTPException(status_code=404, detail="Paper trading engine not initialized")
    
    try:
        trades = _paper_trading_engine.trades
        
        # Apply status filter
        if status_filter and status_filter != "ALL":
            trades = [t for t in trades if t.status.value == status_filter]
        
        # Apply pagination
        trades = trades[offset:offset + limit]
        
        return [
            TradeHistoryResponse(
                trade_id=t.trade_id,
                model_name=t.model_name,
                signal_type=t.signal_type.value,
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                quantity=t.quantity,
                entry_time=t.entry_time.isoformat(),
                exit_time=t.exit_time.isoformat() if t.exit_time else None,
                pnl=t.pnl,
                pnl_pct=t.pnl_pct,
                status=t.status.value,
                regime=t.regime,
                confidence=t.confidence,
            )
            for t in trades
        ]
    
    except Exception as e:
        logger.error(f"Failed to get trade history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get trades: {str(e)}")


@router.get("/portfolio", response_model=PortfolioSnapshotResponse)
async def get_portfolio_snapshot() -> PortfolioSnapshotResponse:
    """
    Get current portfolio snapshot with mark-to-market valuation.
    """
    global _paper_trading_engine
    
    if _paper_trading_engine is None:
        raise HTTPException(status_code=404, detail="Paper trading engine not initialized")
    
    try:
        snapshot = _paper_trading_engine._create_portfolio_snapshot()
        
        return PortfolioSnapshotResponse(
            timestamp=snapshot.timestamp.isoformat(),
            total_value=snapshot.total_value,
            cash=snapshot.cash,
            position_quantity=snapshot.position_quantity,
            position_value=snapshot.position_value,
            pnl_total=snapshot.pnl_total,
            daily_pnl=snapshot.daily_pnl,
            return_pct=snapshot.return_pct,
            sharpe_ratio=snapshot.sharpe_ratio,
            max_drawdown=snapshot.max_drawdown,
            win_rate=snapshot.win_rate,
            num_trades=snapshot.num_trades,
        )
    
    except Exception as e:
        logger.error(f"Failed to get portfolio snapshot: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get portfolio: {str(e)}")


@router.get("/risk-report", response_model=Dict)
async def get_risk_report() -> Dict:
    """
    Get comprehensive risk report with current limits, violations,
    and exposure analysis.
    """
    global _paper_trading_engine, _risk_manager
    
    if _paper_trading_engine is None or _risk_manager is None:
        raise HTTPException(
            status_code=404,
            detail="Paper trading or risk manager not initialized"
        )
    
    try:
        snapshot = _paper_trading_engine._create_portfolio_snapshot()
        
        report = _risk_manager.get_risk_report(
            current_equity=snapshot.total_value,
            daily_pnl=snapshot.daily_pnl
        )
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "risk_report": report,
            "portfolio_summary": {
                "total_value": snapshot.total_value,
                "return_pct": snapshot.return_pct,
                "max_drawdown": snapshot.max_drawdown,
            },
        }
    
    except Exception as e:
        logger.error(f"Failed to get risk report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get risk report: {str(e)}")


@router.post("/signal", response_model=Dict)
async def inject_signal(request: SignalInjectionRequest) -> Dict:
    """
    Inject a trading signal from a model into the paper trading engine.
    The engine will evaluate the signal against risk limits and execute
    if all checks pass.
    """
    global _paper_trading_engine
    
    if _paper_trading_engine is None:
        raise HTTPException(status_code=404, detail="Paper trading engine not initialized")
    
    if _paper_trading_engine.status != "RUNNING":
        raise HTTPException(status_code=409, detail="Paper trading engine is not running")
    
    # Validate model name
    valid_models = ["wavelet", "hmm", "lstm", "tft", "genetic", "ensemble"]
    if request.model_name not in valid_models:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model_name. Must be one of: {valid_models}"
        )
    
    # Validate signal type
    try:
        signal_type = SignalType(request.signal_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid signal_type. Must be one of: LONG, SHORT, CLOSE, HOLD"
        )
    
    try:
        # Create ModelSignal
        signal = ModelSignal(
            model_name=request.model_name,
            signal_type=signal_type,
            confidence=request.confidence,
            entry_price=request.price,
            current_price=request.price,
            timestamp=datetime.now(),
            reasoning=request.reasoning,
            regime=request.regime,
        )
        
        # Process signal through engine
        trade = _paper_trading_engine.process_signal(request.model_name, signal)
        
        result = {
            "status": "success",
            "signal_processed": True,
            "model": request.model_name,
            "signal_type": request.signal_type,
            "confidence": request.confidence,
            "trade_executed": trade is not None,
        }
        
        if trade:
            result["trade"] = {
                "trade_id": trade.trade_id,
                "signal_type": trade.signal_type.value,
                "entry_price": trade.entry_price,
                "quantity": trade.quantity,
                "status": trade.status.value,
            }
            # Broadcast trade to WebSocket clients
            await broadcast_update("trade_executed", result["trade"])
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to process signal: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process signal: {str(e)}")


@router.post("/config", response_model=Dict)
async def update_config(request: ConfigUpdateRequest) -> Dict:
    """
    Update paper trading configuration dynamically.
    Only provided fields are updated; others remain unchanged.
    """
    global _paper_trading_engine, _paper_trading_config
    
    if _paper_trading_engine is None or _paper_trading_config is None:
        raise HTTPException(status_code=404, detail="Paper trading engine not initialized")
    
    try:
        updated_fields = {}
        
        if request.kelly_fraction is not None:
            _paper_trading_config.kelly_fraction = request.kelly_fraction
            _paper_trading_engine.config.kelly_fraction = request.kelly_fraction
            updated_fields["kelly_fraction"] = request.kelly_fraction
        
        if request.max_position_pct is not None:
            _paper_trading_config.max_position_pct = request.max_position_pct
            _paper_trading_engine.config.max_position_pct = request.max_position_pct
            updated_fields["max_position_pct"] = request.max_position_pct
        
        if request.max_daily_loss_pct is not None:
            _paper_trading_config.max_daily_loss_pct = request.max_daily_loss_pct
            _paper_trading_engine.config.max_daily_loss_pct = request.max_daily_loss_pct
            updated_fields["max_daily_loss_pct"] = request.max_daily_loss_pct
        
        if request.max_drawdown_pct is not None:
            _paper_trading_config.max_drawdown_pct = request.max_drawdown_pct
            _paper_trading_engine.config.max_drawdown_pct = request.max_drawdown_pct
            updated_fields["max_drawdown_pct"] = request.max_drawdown_pct
        
        if request.min_confidence is not None:
            _paper_trading_config.min_confidence = request.min_confidence
            _paper_trading_engine.config.min_confidence = request.min_confidence
            updated_fields["min_confidence"] = request.min_confidence
        
        if request.trading_enabled is not None:
            _paper_trading_config.trading_enabled = request.trading_enabled
            _paper_trading_engine.config.trading_enabled = request.trading_enabled
            updated_fields["trading_enabled"] = request.trading_enabled
        
        logger.info(f"Paper trading config updated: {updated_fields}")
        
        return {
            "status": "success",
            "message": "Configuration updated",
            "updated_fields": updated_fields,
        }
    
    except Exception as e:
        logger.error(f"Failed to update config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")


@router.post("/reset-daily", response_model=Dict)
async def reset_daily_counters() -> Dict:
    """
    Reset daily P&L counters and trade limits.
    Called automatically at market open or manually for testing.
    """
    global _paper_trading_engine, _risk_manager
    
    if _paper_trading_engine is None:
        raise HTTPException(status_code=404, detail="Paper trading engine not initialized")
    
    try:
        # Reset engine daily state
        previous_daily_pnl = _paper_trading_engine.daily_pnl
        _paper_trading_engine.daily_pnl = 0.0
        _paper_trading_engine.daily_trades = []
        _paper_trading_engine.day_started_at = datetime.now()
        
        # Reset risk manager daily state
        if _risk_manager:
            _risk_manager.update_daily_state(_paper_trading_engine.portfolio.current_equity)
        
        logger.info(f"Daily counters reset. Previous daily P&L: ${previous_daily_pnl:.2f}")
        
        return {
            "status": "success",
            "message": "Daily counters reset",
            "previous_daily_pnl": previous_daily_pnl,
            "reset_time": datetime.now().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Failed to reset daily counters: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reset: {str(e)}")

# ============================================================================
# LIVE INFERENCE ENDPOINTS
# ============================================================================

@router.get("/live-signals", response_model=Dict)
async def get_live_signals() -> Dict:
    """
    Get the latest signal from every model, updated every 60 seconds by the
    live inference loop running in the background.

    Returns per-model: signal, confidence, regime, price, reasoning, last_updated.
    This is the primary data source for the Models tab live view.
    """
    try:
        import src.paper_trading.live_inference as li
        signals = dict(li.LIVE_MODEL_SIGNALS)
        return {
            "status": "ok",
            "current_price": li.CURRENT_GOLD_PRICE,
            "last_price_update": li.LAST_PRICE_UPDATE.isoformat() if li.LAST_PRICE_UPDATE else None,
            "inference_running": _inference_loop is not None and _inference_loop._running,
            "iteration": _inference_loop.iteration if _inference_loop else 0,
            "models": signals,
        }
    except Exception as e:
        logger.error(f"Failed to get live signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inference-status", response_model=Dict)
async def get_inference_status() -> Dict:
    """
    Get live inference loop health status: running state, cadence, iteration count,
    last run time, and any errors.
    """
    if _inference_loop is None:
        return {
            "running": False,
            "message": "Inference loop not started. Start the paper trading engine first.",
            "iteration": 0,
            "last_run": None,
            "last_error": None,
            "interval_seconds": 60,
        }
    return {
        "running": _inference_loop._running,
        "iteration": _inference_loop.iteration,
        "last_run": _inference_loop.last_run.isoformat() if _inference_loop.last_run else None,
        "last_error": _inference_loop.last_error,
        "interval_seconds": _inference_loop.interval_seconds,
        "message": "Live inference loop running — all 6 models updating every 60s",
    }


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time paper trading updates.
    
    Sends periodic portfolio snapshots and trade notifications.
    Connect at: ws://localhost:8000/paper-trading/ws
    """
    await websocket.accept()
    _websocket_clients.append(websocket)
    logger.info(f"WebSocket client connected. Total clients: {len(_websocket_clients)}")
    
    try:
        # Send initial status
        if _paper_trading_engine:
            status = _paper_trading_engine.get_status()
            await websocket.send_text(json.dumps({
                "event": "connected",
                "data": status,
                "timestamp": datetime.now().isoformat(),
            }))
        
        # Keep connection alive and send periodic updates
        while True:
            try:
                # Wait for client messages (ping/pong or commands)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                
                # Handle client commands
                try:
                    cmd = json.loads(data)
                    if cmd.get("type") == "ping":
                        await websocket.send_text(json.dumps({"event": "pong"}))
                    elif cmd.get("type") == "get_status" and _paper_trading_engine:
                        status = _paper_trading_engine.get_status()
                        await websocket.send_text(json.dumps({
                            "event": "status_update",
                            "data": status,
                            "timestamp": datetime.now().isoformat(),
                        }))
                except (json.JSONDecodeError, KeyError):
                    pass
                    
            except asyncio.TimeoutError:
                # Send periodic snapshot if engine is running
                if _paper_trading_engine and _paper_trading_engine.status == "RUNNING":
                    snapshot = _paper_trading_engine._create_portfolio_snapshot()
                    await websocket.send_text(json.dumps({
                        "event": "portfolio_update",
                        "data": {
                            "total_value": snapshot.total_value,
                            "cash": snapshot.cash,
                            "pnl_total": snapshot.pnl_total,
                            "daily_pnl": snapshot.daily_pnl,
                            "return_pct": snapshot.return_pct,
                            "num_trades": snapshot.num_trades,
                        },
                        "timestamp": datetime.now().isoformat(),
                    }))
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in _websocket_clients:
            _websocket_clients.remove(websocket)
        logger.info(f"WebSocket clients remaining: {len(_websocket_clients)}")
