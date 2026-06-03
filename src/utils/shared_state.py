"""
SHARED STATE MANAGER
Thread-safe singleton that bridges dashboard controls → live inference.
API writes to it, inference loop reads from it — no config reloading needed.
"""

import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Callable


@dataclass
class RuntimeConfig:
    """Runtime configuration updated dynamically by dashboard controls."""

    # Filters
    rsi_filter_enabled: bool = False
    rsi_threshold: float = 75.0  # tuned: gold trends strongly, 70 blocks too many

    seasonal_filter_enabled: bool = False

    triangle_pattern_enabled: bool = True
    triangle_min_confidence: float = 0.7

    # Thresholds
    min_confidence: float = 0.25  # tuned: ensemble generates signal every cycle, let most through
    max_position_size: float = 0.1
    stop_loss_pct: float = 0.02
    min_bars_between_trades: int = 10  # tuned: gold follow-through lasts 10-15 bars

    # Trading control
    trading_enabled: bool = True

    # Model controls
    models_paused: Dict[str, bool] = field(default_factory=dict)

    # Monotonically increasing version for cache invalidation
    config_version: int = 0

    # ── Convenience query methods (used by inference loop) ────────────

    def passes_rsi_filter(self, signal_type: str, rsi_value: float) -> bool:
        """Check if signal passes RSI filter — returns True if filter disabled or passing."""
        if not self.rsi_filter_enabled:
            return True
        if signal_type in ("LONG", "BUY"):
            return rsi_value < self.rsi_threshold
        elif signal_type in ("SHORT", "SELL"):
            return rsi_value > (100.0 - self.rsi_threshold)
        return True

    def passes_confidence_gate(self, confidence: float) -> bool:
        """Check if signal meets minimum confidence threshold."""
        return confidence >= self.min_confidence

    def is_model_paused(self, model_name: str) -> bool:
        """Check if a specific model is paused via dashboard."""
        return self.models_paused.get(model_name, False)

    def to_dict(self) -> Dict:
        return {
            "filters": {
                "rsi_filter": {"enabled": self.rsi_filter_enabled, "threshold": self.rsi_threshold},
                "seasonal_filter": {"enabled": self.seasonal_filter_enabled},
                "triangle_pattern": {"enabled": self.triangle_pattern_enabled, "min_confidence": self.triangle_min_confidence},
            },
            "thresholds": {
                "min_confidence": self.min_confidence,
                "max_position_size": self.max_position_size,
                "stop_loss_pct": self.stop_loss_pct,
                "min_bars_between_trades": self.min_bars_between_trades,
            },
            "trading_enabled": self.trading_enabled,
            "models_paused": dict(self.models_paused),
            "version": self.config_version,
        }


class SharedStateManager:
    """Thread-safe singleton bridging dashboard controls ↔ inference loop."""

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._config = RuntimeConfig()
        self._lock = threading.RLock()
        self._subscribers: List[Callable] = []
        self._initialized = True

    # ── Readers (lock-free — attribute access is thread-safe in CPython) ──

    def get_config(self) -> RuntimeConfig:
        """Return a snapshot of the current config (lock-free read)."""
        # No lock needed: CPython GIL protects individual attribute reads
        # We return a copy to prevent external mutation
        return RuntimeConfig(
            rsi_filter_enabled=self._config.rsi_filter_enabled,
            rsi_threshold=self._config.rsi_threshold,
            seasonal_filter_enabled=self._config.seasonal_filter_enabled,
            triangle_pattern_enabled=self._config.triangle_pattern_enabled,
            triangle_min_confidence=self._config.triangle_min_confidence,
            min_confidence=self._config.min_confidence,
            max_position_size=self._config.max_position_size,
            stop_loss_pct=self._config.stop_loss_pct,
            min_bars_between_trades=self._config.min_bars_between_trades,
            trading_enabled=self._config.trading_enabled,
            models_paused=dict(self._config.models_paused),
            config_version=self._config.config_version,
        )

    # ── Writers (RLock ensures atomic multi-field updates) ──────────

    def update_rsi_filter(self, enabled: bool, threshold: Optional[float] = None):
        if threshold is not None:
            with self._lock:
                self._config.rsi_filter_enabled = enabled
                self._config.rsi_threshold = threshold
                self._config.config_version += 1
                self._notify()
        else:
            with self._lock:
                self._config.rsi_filter_enabled = enabled
                self._config.config_version += 1
                self._notify()

    def update_seasonal_filter(self, enabled: bool):
        with self._lock:
            self._config.seasonal_filter_enabled = enabled
            self._config.config_version += 1
            self._notify()

    def update_triangle_pattern(self, enabled: bool, min_confidence: Optional[float] = None):
        with self._lock:
            self._config.triangle_pattern_enabled = enabled
            if min_confidence is not None:
                self._config.triangle_min_confidence = min_confidence
            self._config.config_version += 1
            self._notify()

    def update_threshold(self, threshold_name: str, value: float):
        with self._lock:
            if threshold_name == "min_confidence":
                self._config.min_confidence = value
            elif threshold_name == "max_position_size":
                self._config.max_position_size = value
            elif threshold_name == "stop_loss_pct":
                self._config.stop_loss_pct = value
            elif threshold_name == "min_bars_between_trades":
                self._config.min_bars_between_trades = int(value)
            self._config.config_version += 1
            self._notify()

    def toggle_model(self, model_name: str, paused: bool):
        with self._lock:
            self._config.models_paused[model_name] = paused
            self._config.config_version += 1
            self._notify()

    def toggle_trading(self, enabled: bool):
        with self._lock:
            self._config.trading_enabled = enabled
            self._config.config_version += 1
            self._notify()

    def pause_all_models(self):
        with self._lock:
            for k in self._config.models_paused:
                self._config.models_paused[k] = True
            self._config.config_version += 1
            self._notify()

    def resume_all_models(self):
        with self._lock:
            for k in self._config.models_paused:
                self._config.models_paused[k] = False
            self._config.config_version += 1
            self._notify()

    # ── Subscriptions ──────────────────────────────────────────────

    def subscribe(self, callback: Callable):
        self._subscribers.append(callback)

    def _notify(self):
        cfg = self._config
        for cb in self._subscribers:
            try:
                cb(cfg)
            except Exception as e:
                print(f"[SharedState] subscriber error: {e}")


# Global singleton — import this directly
state_manager = SharedStateManager()


def get_shared_state() -> SharedStateManager:
    """Factory accessor matching project conventions."""
    return state_manager


# ── Gate rejection stats (written by LiveInferenceLoop, read by dashboard API) ──

GATE_REJECTION_STATS: Dict[str, int] = {}


def reset_gate_stats():
    GATE_REJECTION_STATS.clear()


def record_gate_rejection(gate_name: str):
    GATE_REJECTION_STATS[gate_name] = GATE_REJECTION_STATS.get(gate_name, 0) + 1


def get_gate_stats() -> Dict:
    total = sum(GATE_REJECTION_STATS.values())
    return {
        "total_rejections": total,
        "by_gate": {
            gate: {"count": count, "pct": round(count / total * 100, 1) if total > 0 else 0.0}
            for gate, count in sorted(GATE_REJECTION_STATS.items(), key=lambda x: x[1], reverse=True)
        },
    }
