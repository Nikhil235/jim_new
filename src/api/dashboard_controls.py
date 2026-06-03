"""
DASHBOARD CONTROLS API
Live controls to toggle filters, adjust thresholds, pause models.
Writes to SharedStateManager — inference loop reads from it.
"""

from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel
from loguru import logger

from src.utils.shared_state import state_manager, get_gate_stats

try:
    from fastapi import APIRouter, HTTPException
    router = APIRouter(prefix="/controls", tags=["controls"])
    _has_fastapi = True
except ImportError:
    _has_fastapi = False
    router = None


# ── Pydantic request models ────────────────────────────────────────

class ToggleModelRequest(BaseModel):
    model_name: str
    paused: bool

class UpdateFilterRequest(BaseModel):
    filter_name: str
    enabled: bool
    params: Optional[Dict] = None

class UpdateThresholdRequest(BaseModel):
    threshold_name: str
    value: float

class TradingControlRequest(BaseModel):
    trading_enabled: bool

class GateUpdateRequest(BaseModel):
    gate_name: str
    value: float
    enabled: bool = True


# ── Routes (all delegate to SharedStateManager) ────────────────────

if _has_fastapi:

    @router.get("/status")
    async def get_platform_status():
        cfg = state_manager.get_config()
        from src.paper_trading.live_inference import SYSTEM_HEALTH
        health = dict(SYSTEM_HEALTH)
        health["model_errors"] = dict(health.get("model_errors", {}))
        return {**cfg.to_dict(), "health": health}

    @router.post("/models/toggle")
    async def toggle_model(req: ToggleModelRequest):
        state_manager.toggle_model(req.model_name, req.paused)
        return {
            "model_name": req.model_name,
            "status": "paused" if req.paused else "running",
            "success": True,
            "version": state_manager.get_config().config_version,
        }

    @router.post("/models/pause_all")
    async def pause_all():
        state_manager.pause_all_models()
        return {"success": True, "version": state_manager.get_config().config_version}

    @router.post("/models/resume_all")
    async def resume_all():
        state_manager.resume_all_models()
        return {"success": True, "version": state_manager.get_config().config_version}

    @router.post("/filters/rsi")
    async def update_rsi_filter(req: UpdateFilterRequest):
        threshold = req.params.get("threshold") if req.params else None
        state_manager.update_rsi_filter(enabled=req.enabled, threshold=threshold)
        return {
            "filter": "rsi_filter",
            "enabled": req.enabled,
            "threshold": threshold,
            "success": True,
            "version": state_manager.get_config().config_version,
        }

    @router.post("/filters/seasonal")
    async def update_seasonal_filter(req: UpdateFilterRequest):
        state_manager.update_seasonal_filter(enabled=req.enabled)
        return {
            "filter": "seasonal_filter",
            "enabled": req.enabled,
            "success": True,
            "version": state_manager.get_config().config_version,
        }

    @router.post("/filters/triangle")
    async def update_triangle_filter(req: UpdateFilterRequest):
        min_confidence = req.params.get("min_confidence") if req.params else None
        state_manager.update_triangle_pattern(enabled=req.enabled, min_confidence=min_confidence)
        return {
            "filter": "triangle_pattern",
            "enabled": req.enabled,
            "min_confidence": min_confidence,
            "success": True,
            "version": state_manager.get_config().config_version,
        }

    @router.post("/thresholds/update")
    async def update_threshold(req: UpdateThresholdRequest):
        valid = {"min_confidence", "max_position_size", "stop_loss_pct"}
        if req.threshold_name not in valid:
            raise HTTPException(404, f"Unknown threshold '{req.threshold_name}'. Valid: {valid}")
        state_manager.update_threshold(req.threshold_name, req.value)
        return {
            "threshold_name": req.threshold_name,
            "value": req.value,
            "success": True,
            "version": state_manager.get_config().config_version,
        }

    @router.post("/trading/toggle")
    async def toggle_trading(req: TradingControlRequest):
        state_manager.toggle_trading(req.trading_enabled)
        return {
            "trading_enabled": req.trading_enabled,
            "status": "enabled" if req.trading_enabled else "disabled",
            "success": True,
            "version": state_manager.get_config().config_version,
        }

    @router.post("/gates/update")
    async def update_gate(req: GateUpdateRequest):
        if req.gate_name == "rsi_overbought":
            state_manager.update_rsi_filter(enabled=req.enabled, threshold=req.value)
        elif req.gate_name == "rsi_oversold":
            state_manager.update_rsi_filter(enabled=req.enabled, threshold=100.0 - req.value)
        elif req.gate_name == "min_confidence":
            state_manager.update_threshold("min_confidence", req.value)
        elif req.gate_name == "min_bars_between_trades":
            state_manager.update_threshold("min_bars_between_trades", req.value)
        elif req.gate_name == "seasonal_enabled":
            state_manager.update_seasonal_filter(enabled=req.enabled)
        elif req.gate_name == "triangle_enabled":
            state_manager.update_triangle_pattern(enabled=req.enabled)
        else:
            raise HTTPException(404, f"Unknown gate '{req.gate_name}'")
        return {
            "success": True,
            "gate": req.gate_name,
            "value": req.value,
            "enabled": req.enabled,
            "version": state_manager.get_config().config_version,
        }

    @router.get("/gates/stats")
    async def get_gates_stats():
        return get_gate_stats()

    @router.get("/health")
    async def health_check():
        from src.paper_trading.live_inference import SYSTEM_HEALTH, CURRENT_GOLD_PRICE, LAST_PRICE_UPDATE, LIVE_MODEL_SIGNALS
        errors = SYSTEM_HEALTH.get("model_errors", {})
        dead_models = [m for m, c in errors.items() if c > 5]
        stale = SYSTEM_HEALTH.get("data_feed_stale", False)
        price_age = None
        if LAST_PRICE_UPDATE:
            price_age = (datetime.now() - LAST_PRICE_UPDATE).total_seconds()
        return {
            "status": "degraded" if (stale or dead_models) else "healthy",
            "running": SYSTEM_HEALTH.get("running", False),
            "total_cycles": SYSTEM_HEALTH.get("total_cycles", 0),
            "consecutive_failures": SYSTEM_HEALTH.get("consecutive_failures", 0),
            "data_feed_stale": stale,
            "last_data_update": SYSTEM_HEALTH.get("last_data_update"),
            "price_age_seconds": price_age,
            "last_price": CURRENT_GOLD_PRICE,
            "dead_models": dead_models,
            "model_errors": dict(errors),
        }


# ── Standalone entry point ─────────────────────────────────────────

def create_app():
    from fastapi import FastAPI
    app = FastAPI(title="Dashboard Controls")
    app.include_router(router)
    return app


if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)
