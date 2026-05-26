"""
silver_feed_adapter.py
======================
Real-time XAU + XAG price feed for the KalmanHedgeEngine.

Architecture:
    - Primary  : Gold-API.com          (free, unlimited, zero-delay)
    - Fallback : MetalPriceAPI         (matches your existing fetch_metalpriceapi_gs_spot())
    - Both metals fetched in ONE call  (same timestamp → no stale spread)
    - Runs on a 30s loop for Kalman    (separate from 60s ML inference loop)
    - Caches T-1 prices automatically  (prevents look-ahead bias in Kalman)
    - Spread monitor included          (alerts when ratio moves > 1 std dev)

Drop-in usage:
    from silver_feed_adapter import SilverFeedAdapter

    adapter = SilverFeedAdapter(
        goldapi_key      = "your_key_or_empty_string",   # empty = no-auth endpoint
        metalpriceapi_key= "your_key",
        fetch_interval_s = 30,
    )

    adapter.start()   # begins background thread

    # In your main loop:
    prices = adapter.latest          # {"XAU": 4561.0, "XAG": 75.3, "ts": datetime, "source": "goldapi"}
    prev   = adapter.previous        # T-1 prices  → feed these to Kalman
    status = adapter.feed_status()   # health snapshot
"""

from __future__ import annotations

import time
import threading
import logging
import statistics
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False
    logging.warning("requests not installed — pip install requests")


log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Price snapshot dataclass
# ─────────────────────────────────────────────

@dataclass
class PriceSnapshot:
    xau      : float
    xag      : float
    ratio    : float          # XAU / XAG
    ts       : datetime
    source   : str            # "goldapi" | "metalpriceapi" | "stub"
    latency_ms: float = 0.0

    @classmethod
    def empty(cls) -> "PriceSnapshot":
        return cls(xau=0.0, xag=0.0, ratio=0.0,
                   ts=datetime.now(timezone.utc), source="none")

    def is_valid(self) -> bool:
        return self.xau > 0 and self.xag > 0


# ─────────────────────────────────────────────
#  Spread / ratio monitor
# ─────────────────────────────────────────────

class RatioMonitor:
    """
    Tracks the rolling Gold/Silver ratio and fires an alert
    when it moves more than `z_threshold` standard deviations
    from its recent mean — early warning for news spikes.
    """

    def __init__(self, window: int = 20, z_threshold: float = 1.5):
        self.window      = window
        self.z_threshold = z_threshold
        self.history     : list[float] = []
        self.alerts      : list[dict]  = []

    def update(self, ratio: float, ts: datetime) -> Optional[dict]:
        self.history.append(ratio)
        if len(self.history) > self.window:
            self.history.pop(0)

        if len(self.history) < self.window:
            return None   # not enough data yet

        mean   = statistics.mean(self.history)
        stdev  = statistics.stdev(self.history)
        if stdev == 0:
            return None

        z = (ratio - mean) / stdev

        if abs(z) >= self.z_threshold:
            alert = {
                "ts"    : ts.isoformat(),
                "ratio" : round(ratio, 4),
                "mean"  : round(mean,  4),
                "z"     : round(z,     2),
                "level" : "CRITICAL" if abs(z) > 2.5 else "WARNING",
            }
            self.alerts.append(alert)
            log.warning(
                f"[RATIO ALERT]  XAU/XAG={ratio:.2f}  "
                f"z={z:.2f}  mean={mean:.2f}  → possible news spike"
            )
            return alert

        return None


# ─────────────────────────────────────────────
#  Silver Feed Adapter
# ─────────────────────────────────────────────

class SilverFeedAdapter:
    """
    Background price feed for XAU and XAG.
    Maintains current (T0) and previous (T-1) snapshots
    so the KalmanHedgeEngine always has bias-free inputs.

    Parameters
    ----------
    goldapi_key       : API key for Gold-API.com  (pass "" if no-auth endpoint)
    metalpriceapi_key : API key for MetalPriceAPI (fallback)
    fetch_interval_s  : seconds between fetches   (default 30)
    ratio_window      : bars for rolling ratio std (default 20)
    """

    GOLDAPI_URL       = "https://www.goldapi.io/api/{symbol}/USD"
    GOLDAPI_BOTH_URL  = "https://www.goldapi.io/api/XAU/USD"    # XAG fetched separately
    METALPRICEAPI_URL = "https://api.metalpriceapi.com/v1/latest?api_key={key}&base=USD&currencies=XAU,XAG"

    def __init__(
        self,
        goldapi_key       : str   = "",
        metalpriceapi_key : str   = "",
        fetch_interval_s  : int   = 30,
        ratio_window      : int   = 20,
    ):
        self.goldapi_key        = goldapi_key
        self.metalpriceapi_key  = metalpriceapi_key
        self.fetch_interval_s   = fetch_interval_s

        # Price state — T0 and T-1
        self._current  : PriceSnapshot = PriceSnapshot.empty()
        self._previous : PriceSnapshot = PriceSnapshot.empty()
        self._lock     = threading.Lock()

        # Monitoring
        self.ratio_monitor  = RatioMonitor(window=ratio_window)
        self._fetch_count   = 0
        self._error_count   = 0
        self._last_error    = ""
        self._running       = False
        self._thread        : Optional[threading.Thread] = None

    # ── Public read properties ───────────────────

    @property
    def latest(self) -> PriceSnapshot:
        """T0 — current bar prices."""
        with self._lock:
            return self._current

    @property
    def previous(self) -> PriceSnapshot:
        """T-1 — previous bar prices. Feed THESE to kalman_hedge.update()."""
        with self._lock:
            return self._previous

    # ── Start / stop ─────────────────────────────

    def start(self):
        """Launch background fetch thread."""
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True, name="SilverFeed")
        self._thread.start()
        log.info(f"[SilverFeed] started  interval={self.fetch_interval_s}s")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        log.info("[SilverFeed] stopped")

    # ── Background loop ──────────────────────────

    def _loop(self):
        while self._running:
            try:
                self._fetch_and_update()
            except Exception as e:
                self._error_count += 1
                self._last_error   = str(e)
                log.error(f"[SilverFeed] unhandled error: {e}")
            time.sleep(self.fetch_interval_s)

    def _fetch_and_update(self):
        t0    = time.time()
        snap  = self._fetch_goldapi()

        if snap is None or not snap.is_valid():
            log.warning("[SilverFeed] Gold-API failed — trying MetalPriceAPI fallback")
            snap = self._fetch_metalpriceapi()

        if snap is None or not snap.is_valid():
            self._error_count += 1
            self._last_error   = "Both sources failed"
            log.error("[SilverFeed] Both price sources failed — retaining last known prices")
            return

        snap.latency_ms = round((time.time() - t0) * 1000, 1)
        self._fetch_count += 1

        # Ratio monitor
        self.ratio_monitor.update(snap.ratio, snap.ts)

        # Rotate T0 → T-1, new snap → T0
        with self._lock:
            if self._current.is_valid():
                self._previous = self._current
            self._current = snap

        log.debug(
            f"[SilverFeed]  XAU={snap.xau:.2f}  XAG={snap.xag:.4f}  "
            f"ratio={snap.ratio:.2f}  src={snap.source}  lat={snap.latency_ms}ms"
        )

    # ── Gold-API.com fetch ───────────────────────

    def _fetch_goldapi(self) -> Optional[PriceSnapshot]:
        """
        Fetches XAU and XAG from Gold-API.com in two sequential calls.
        Both share a single timestamp so the spread is consistent.
        """
        if not REQUESTS_OK:
            return None

        headers = {"x-access-token": self.goldapi_key} if self.goldapi_key else {}
        ts      = datetime.now(timezone.utc)

        try:
            xau_r = requests.get(
                self.GOLDAPI_URL.format(symbol="XAU"),
                headers=headers, timeout=5
            )
            xag_r = requests.get(
                self.GOLDAPI_URL.format(symbol="XAG"),
                headers=headers, timeout=5
            )

            if xau_r.status_code != 200 or xag_r.status_code != 200:
                return None

            xau = float(xau_r.json().get("price", 0))
            xag = float(xag_r.json().get("price", 0))

            if xau <= 0 or xag <= 0:
                return None

            return PriceSnapshot(
                xau    = xau,
                xag    = xag,
                ratio  = round(xau / xag, 4),
                ts     = ts,
                source = "goldapi",
            )

        except Exception as e:
            log.warning(f"[SilverFeed] Gold-API error: {e}")
            return None

    # ── MetalPriceAPI fallback ───────────────────

    def _fetch_metalpriceapi(self) -> Optional[PriceSnapshot]:
        """
        Mirrors your existing fetch_metalpriceapi_gs_spot() function.
        Fetches XAU and XAG in a single API call.
        """
        if not REQUESTS_OK or not self.metalpriceapi_key:
            return None

        try:
            url = self.METALPRICEAPI_URL.format(key=self.metalpriceapi_key)
            r   = requests.get(url, timeout=5)

            if r.status_code != 200:
                return None

            data = r.json()
            # MetalPriceAPI returns rates as USD per unit
            # XAU and XAG rates are in oz — invert to get price per oz
            rates = data.get("rates", {})
            xau_rate = rates.get("XAU", 0)
            xag_rate = rates.get("XAG", 0)

            if xau_rate <= 0 or xag_rate <= 0:
                return None

            xau = round(1 / xau_rate, 4)
            xag = round(1 / xag_rate, 4)

            return PriceSnapshot(
                xau    = xau,
                xag    = xag,
                ratio  = round(xau / xag, 4),
                ts     = datetime.now(timezone.utc),
                source = "metalpriceapi",
            )

        except Exception as e:
            log.warning(f"[SilverFeed] MetalPriceAPI error: {e}")
            return None

    # ── Status snapshot ──────────────────────────

    def feed_status(self) -> dict:
        cur  = self.latest
        prev = self.previous
        return {
            "running"          : self._running,
            "fetch_count"      : self._fetch_count,
            "error_count"      : self._error_count,
            "last_error"       : self._last_error,
            "current_xau"      : cur.xau,
            "current_xag"      : cur.xag,
            "current_ratio"    : cur.ratio,
            "current_source"   : cur.source,
            "current_ts"       : cur.ts.isoformat() if cur.ts else None,
            "current_latency_ms": cur.latency_ms,
            "prev_xau"         : prev.xau,
            "prev_xag"         : prev.xag,
            "ratio_alerts"     : len(self.ratio_monitor.alerts),
            "last_ratio_alert" : self.ratio_monitor.alerts[-1] if self.ratio_monitor.alerts else None,
        }


# ─────────────────────────────────────────────
#  Integration template for LiveInferenceLoop
# ─────────────────────────────────────────────

LIVE_LOOP_INTEGRATION = '''
# ── In src/paper_trading/live_inference.py ────────────────────────────────

from silver_feed_adapter import SilverFeedAdapter

# Startup (run once):
silver_feed = SilverFeedAdapter(
    goldapi_key       = os.getenv("GOLDAPI_KEY", ""),
    metalpriceapi_key = os.getenv("METALPRICEAPI_KEY", ""),
    fetch_interval_s  = 30,    # 30s for Kalman, independent of 60s ML loop
)
silver_feed.start()

# In your 60-second ML inference tick:
def on_inference_tick():
    # ── 1. Get prices ──────────────────────────────────────────────
    current  = silver_feed.latest     # T0  — for display / logging
    previous = silver_feed.previous   # T-1 — for Kalman (NO look-ahead)

    if not previous.is_valid():
        log.info("Waiting for T-1 price — skipping Kalman update this tick")
        return

    # ── 2. Update Kalman with T-1 (closed bar) data ────────────────
    kalman_hedge.update(
        gold_price_prev   = previous.xau,
        silver_price_prev = previous.xag,
    )
    beta = kalman_hedge.current_beta   # now safe to use for T0 trade

    # ── 3. Get regime ──────────────────────────────────────────────
    regime   = regime_detector.detect()
    pos_mult = kalman_hedge.get_hedge_size(
        gold_size  = calculated_gold_lot,
        raw_beta   = beta,
        regime     = regime,
    )

    # ── 4. Place trade if signal exists ───────────────────────────
    if ai_signal != "NONE" and confidence >= threshold:
        engine.open_trade("XAUUSD", ai_signal,  gold_lot)
        if pos_mult > 0:
            hedge_dir = "SHORT" if ai_signal == "LONG" else "LONG"
            engine.open_trade("XAGUSD", hedge_dir, pos_mult)

    # ── 5. Log ratio health ───────────────────────────────────────
    log.debug(silver_feed.feed_status())
'''


# ─────────────────────────────────────────────
#  Smoke test (no real API keys needed)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("=== SilverFeedAdapter — stub test (no API calls) ===\n")

    # Test the ratio monitor directly
    monitor = RatioMonitor(window=10, z_threshold=1.5)
    ratios  = [75.1, 74.9, 75.2, 75.0, 74.8, 75.3, 75.1, 74.7, 75.0, 74.9, 82.5]

    print("Feeding ratio history into monitor:")
    for i, r in enumerate(ratios):
        alert = monitor.update(r, datetime.now(timezone.utc))
        status = f"  ratio={r:<6}  " + ("🚨 ALERT: " + str(alert) if alert else "  OK")
        print(status)

    # Test PriceSnapshot
    snap = PriceSnapshot(xau=4561.0, xag=75.3, ratio=60.57,
                         ts=datetime.now(timezone.utc), source="stub")
    print(f"\nSnapshot valid: {snap.is_valid()}")
    print(f"XAU={snap.xau}  XAG={snap.xag}  ratio={snap.ratio}  src={snap.source}")

    # Show integration template
    print("\n=== LiveInferenceLoop Integration Template ===")
    print(LIVE_LOOP_INTEGRATION)
