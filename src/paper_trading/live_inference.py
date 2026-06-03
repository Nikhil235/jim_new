"""
Live Inference Loop
====================
Background asyncio task that continuously:
  1. Fetches latest gold price data via yfinance (every 60s)
  2. Runs all 6 Phase 3 models to generate fresh signals
  3. Injects signals into the paper trading engine
  4. Broadcasts model updates via WebSocket

All 6 models run on every tick:
  - Wavelet Denoiser      → trend direction + confidence
  - HMM Regime Detector   → market regime + regime-adjusted confidence
  - LSTM Temporal         → price sequence prediction
  - TFT Forecaster        → multi-horizon forecast
  - Genetic Algorithm     → evolved rule-based signal
  - Ensemble Stacking     → meta-learner aggregation
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Callable, Any, Tuple
import warnings
import numpy as np
import pandas as pd
from loguru import logger

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
warnings.filterwarnings("ignore", message=".*InconsistentVersionWarning.*")
warnings.filterwarnings("ignore", category=FutureWarning, module="yfinance")
warnings.filterwarnings("ignore", category=RuntimeWarning, module="hmmlearn")
warnings.filterwarnings("ignore", module="torch")

from src.models.hmm_pro import run_hmm_pro
from src.models.wavelet_pro import run_wavelet_pro
from src.models.tft_forecaster import run_tft
from src.models.ensemble_stacking import get_stacking_ensemble
from src.paper_trading.prediction_logger import log_prediction_cycle, update_pnl_for_trade
from src.utils.shared_state import state_manager, RuntimeConfig, record_gate_rejection, reset_gate_stats

# ============================================================================
# MODEL SIGNAL REGISTRY (shared state, updated by inference loop)
# ============================================================================

# Latest signal from each model — exposed via /paper-trading/live-signals
LIVE_MODEL_SIGNALS: Dict[str, Dict] = {
    model: {
        "signal": None,
        "confidence": 0.0,
        "regime": "UNKNOWN",
        "price": 0.0,
        "reasoning": "",
        "last_updated": None,
        "error": None,
    }
    for model in ["wavelet_pro", "wavelet_basic", "hmm", "lstm", "tft", "genetic", "hmm_pro", "ensemble"]
}

# Current gold price (updated on each fetch)
CURRENT_GOLD_PRICE: float = 0.0
LAST_PRICE_UPDATE: Optional[datetime] = None

# Current macro data
MACRO_DATA: Dict[str, float] = {
    "dxy": 0.0,
    "us10y": 0.0,
    "gold_silver_ratio": 0.0,
    "rl_kelly": 1.0,
    "rl_trailing": 0.015,
}

# System health — updated by LiveInferenceLoop each cycle, read by dashboard / monitor
SYSTEM_HEALTH: Dict = {
    "consecutive_failures": 0,
    "last_data_update": None,
    "last_price_update": None,
    "total_cycles": 0,
    "data_feed_stale": False,
    "model_errors": {m: 0 for m in ["wavelet_pro", "wavelet_basic", "hmm", "lstm", "tft", "genetic", "hmm_pro"]},
    "model_last_success": {},
    "running": False,
}


# ============================================================================
# GOLD DATA FETCHER
# ============================================================================

def fetch_live_gold_data(period: str = "5d", interval: str = "1m") -> Optional[pd.DataFrame]:
    """
    Fetch latest gold futures OHLCV data AND macro indicators (DXY, US10Y) via yfinance.
    Returns DataFrame with columns: open, high, low, close, volume, returns, dxy, us10y, dxy_returns, us10y_returns
    """
    try:
        import yfinance as yf
        import time
        
        # Group download is faster and aligns timestamps perfectly
        tickers = "GC=F PAXG-USD DX-Y.NYB ^TNX SI=F ^GVZ TIP"
        
        df_all = pd.DataFrame()
        for attempt in range(3):
            df_all = yf.download(tickers, period=period, interval=interval, group_by="ticker", progress=False, auto_adjust=False)
            if not df_all.empty and "GC=F" in df_all:
                break
            logger.warning(f"yfinance returned empty dataframe (attempt {attempt+1}/3), retrying...")
            time.sleep(2)

        if df_all.empty:
            logger.warning("yfinance returned empty dataframe")
            return None

        # Extract Gold (Merge GC=F futures with PAXG-USD 24/7 crypto gold to prevent stale prices on weekends/holidays)
        df = df_all["GC=F"].copy()
        if "PAXG-USD" in df_all:
            df_pax = df_all["PAXG-USD"].copy()
            for col in ["Open", "High", "Low", "Close"]:
                if col in df.columns and col in df_pax.columns:
                    df[col] = df[col].fillna(df_pax[col])
            # For volume, crypto volume can be 0 or small, replace 0 with 1 to avoid zero-volume filter dropping valid rows
            if "Volume" in df.columns and "Volume" in df_pax.columns:
                df["Volume"] = df["Volume"].fillna(df_pax["Volume"].replace(0, 1))

        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].copy()
        
        # --- FROZEN BAR FIX (BUG 3) ---
        # 1. Filter out 0 volume
        df = df[df["volume"] > 0].copy()
        
        # 2. Filter out perfectly flat bars (stale pricing where high==low and open==close)
        df = df[~((df["high"] == df["low"]) & (df["open"] == df["close"]))].copy()
        
        # Extract DXY, US10Y and Silver closes (Forward fill to handle slightly misaligned ticks)
        df["dxy"] = df_all["DX-Y.NYB"]["Close"].ffill()
        df["us10y"] = df_all["^TNX"]["Close"].ffill()
        df["silver"] = df_all["SI=F"]["Close"].ffill()
        df["gvz"] = df_all["^GVZ"]["Close"].ffill()
        df["tip"] = df_all["TIP"]["Close"].ffill()
        
        df.dropna(inplace=True)
        df["gvz_zscore_20"] = (df["gvz"] - df["gvz"].rolling(20).mean()) / df["gvz"].rolling(20).std()

        # Add returns
        df["returns"] = df["close"].pct_change()
        df["dxy_returns"] = df["dxy"].pct_change()
        df["us10y_returns"] = df["us10y"].pct_change()
        df["silver_returns"] = df["silver"].pct_change()
        df["tip_return"] = df["tip"].pct_change()
        df["gold_silver_ratio"] = df["close"] / df["silver"]
        
        # Negative real yield = Gold bullish
        df["real_yield_proxy"] = df["us10y"] - df["tip_return"].rolling(20).mean() * 100
        
        df.dropna(inplace=True)
        
        # Override the final bar with the true live spot price from MetalPriceAPI
        # and scale the entire historical series so the returns stay structurally intact
        # without introducing a massive gap on the final bar.
        try:
            spot_price = fetch_metalpriceapi_spot()
            if spot_price and spot_price > 0:
                current_last = df["close"].iloc[-1]
                scaling_factor = spot_price / current_last
                
                # Scale OHL prices
                df["open"] *= scaling_factor
                df["high"] *= scaling_factor
                df["low"] *= scaling_factor
                df["close"] *= scaling_factor
                
                # Recalculate GSR
                df["gold_silver_ratio"] = df["close"] / df["silver"]
                
                logger.debug(f"Scaled historical data by {scaling_factor:.4f} to match live MetalPriceAPI spot: ${spot_price:.2f}")
        except Exception as e:
            logger.debug(f"Failed to fetch live MetalPriceAPI spot for history override: {e}")

        logger.debug(f"Data fetched: {len(df)} bars. Gold: ${df['close'].iloc[-1]:.2f}, DXY: {df['dxy'].iloc[-1]:.2f}, GSR: {df['gold_silver_ratio'].iloc[-1]:.2f}")
        return df

    except Exception as e:
        logger.error(f"Failed to fetch gold data: {e}")
        return None

def fetch_metalpriceapi_spot() -> Optional[float]:
    """
    Fetch real-time spot price for Gold from the free Gold-API.com,
    with fallback to MetalPriceAPI if needed.
    """
    import os
    import requests
    from dotenv import load_dotenv

    # 1. Try free Gold-API.com first (unlimited, no key required)
    try:
        resp = requests.get("https://api.gold-api.com/price/XAU", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            price = data.get("price")
            if price and float(price) > 0:
                logger.debug(f"Fetched real-time gold spot price from Gold-API.com: ${price:.2f}")
                return round(float(price), 2)
    except Exception as e:
        logger.warning(f"Gold-API.com fetch failed: {e}")

    # 2. Fallback to MetalPriceAPI
    load_dotenv()
    api_key = os.environ.get("METALPRICE_API_KEY", "")
    if not api_key:
        api_key = os.environ.get("GOLDAPI_KEY", "")
    
    if api_key and api_key != "your_metalprice_key_here":
        try:
            resp = requests.get(
                f"https://api.metalpriceapi.com/v1/latest?api_key={api_key}&base=USD&currencies=XAU",
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    rates = data.get("rates", {})
                    xau_rate = rates.get("XAU")
                    if xau_rate and float(xau_rate) > 0:
                        return round(1.0 / float(xau_rate), 2)
            else:
                logger.warning(f"MetalPriceAPI error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"MetalPriceAPI fetch failed: {e}")
            
    return None

def fetch_metalpriceapi_gs_spot() -> tuple[Optional[float], Optional[float]]:
    """
    Fetch real-time spot prices for Gold and Silver from Gold-API.com,
    with fallback to MetalPriceAPI if needed.
    Returns: (gold_price, silver_price)
    """
    import os
    import requests
    from dotenv import load_dotenv

    # 1. Try free Gold-API.com first (unlimited, no key required)
    try:
        r_gold = requests.get("https://api.gold-api.com/price/XAU", timeout=5)
        r_silver = requests.get("https://api.gold-api.com/price/XAG", timeout=5)
        
        gold_price = None
        silver_price = None
        
        if r_gold.status_code == 200:
            data = r_gold.json()
            price = data.get("price")
            if price and float(price) > 0:
                gold_price = round(float(price), 2)
                
        if r_silver.status_code == 200:
            data = r_silver.json()
            price = data.get("price")
            if price and float(price) > 0:
                silver_price = round(float(price), 2)
                
        if gold_price is not None or silver_price is not None:
            logger.debug(f"Fetched real-time spot prices from Gold-API.com: Gold=${gold_price}, Silver=${silver_price}")
            return gold_price, silver_price
    except Exception as e:
        logger.warning(f"Gold-API.com (G/S) fetch failed: {e}")

    # 2. Fallback to MetalPriceAPI
    load_dotenv()
    api_key = os.environ.get("METALPRICE_API_KEY", "")
    if not api_key:
        api_key = os.environ.get("GOLDAPI_KEY", "")
        
    if api_key and api_key != "your_metalprice_key_here":
        try:
            resp = requests.get(
                f"https://api.metalpriceapi.com/v1/latest?api_key={api_key}&base=USD&currencies=XAU,XAG",
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    rates = data.get("rates", {})
                    xau = rates.get("XAU")
                    xag = rates.get("XAG")
                    gold_price = round(1.0 / float(xau), 2) if xau and float(xau) > 0 else None
                    silver_price = round(1.0 / float(xag), 2) if xag and float(xag) > 0 else None
                    return gold_price, silver_price
            else:
                logger.warning(f"MetalPriceAPI (G/S) error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"MetalPriceAPI (G/S) fetch failed: {e}")
            
    return None, None


# ============================================================================
# MODEL RUNNERS — each returns (signal: str, confidence: float, reasoning: str)
# ============================================================================

def run_wavelet(df: pd.DataFrame) -> Dict:
    """
    Wavelet signal using WaveletPro (professional 6-level DWT model).
    
    This replaces the basic 5-level model with the production-ready WaveletPro
    that includes:
    - 6-level DWT decomposition
    - Wavelet Oscillator (D3 + D4)
    - Continuous Wavelet Transform (CWT)
    - 30+ engineered features
    """
    try:
        return run_wavelet_pro(df)
    except Exception as e:
        logger.warning(f"Wavelet Pro fallback to basic model: {e}")
        # Fallback to basic wavelet if WaveletPro fails
        try:
            prices = df["close"].values

            # Need at least 32 samples (2^5 for 5-level decomposition)
            if len(prices) < 32:
                return {"signal": "HOLD", "confidence": 0.0, "reasoning": "Insufficient data"}

            try:
                import pywt
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    coeffs = pywt.wavedec(prices, "db4", level=5)
                    # Zero out detail coefficients to denoise
                    coeffs[1:] = [np.zeros_like(v) for v in coeffs[1:]]
                    trend = pywt.waverec(coeffs, "db4")
                pywt_available = True
            except ImportError:
                # Proxy if pywt is unavailable
                trend = pd.Series(prices).rolling(window=10).mean().bfill().values
                pywt_available = False

            # Signal: compare last 3 denoised values to determine trend
            if len(trend) >= 3:
                slope = (trend[-1] - trend[-3]) / (abs(trend[-3]) + 1e-8)
                
                # Dynamic confidence based on slope magnitude
                abs_slope = abs(slope)
                # Base 50% + up to 45% based on slope
                base_conf = 0.50 + min(abs_slope * 300.0, 0.45)
                
                # Penalty if using fallback model
                confidence = base_conf if pywt_available else base_conf * 0.70

                if slope > 0.00005:
                    signal = "LONG"
                    reasoning = f"Wavelet trend slope +{slope:.4f} → uptrend detected"
                elif slope < -0.00005:
                    signal = "SHORT"
                    reasoning = f"Wavelet trend slope {slope:.4f} → downtrend detected"
                else:
                    signal = "HOLD"
                    confidence = 0.18
                    reasoning = f"Wavelet trend flat (slope={slope:.6f})"
            else:
                signal = "HOLD"
                confidence = 0.0
                reasoning = "Insufficient trend data"

            return {"signal": signal, "confidence": round(confidence, 3), "reasoning": reasoning}

        except Exception as e_fallback:
            logger.error(f"Both Wavelet Pro and basic fallback failed: {e_fallback}")
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "reasoning": f"Wavelet error: {str(e_fallback)[:80]}"
            }


def run_wavelet_basic(df: pd.DataFrame) -> Dict:
    """
    Basic 5-level wavelet signal (original model for comparison).
    
    Features:
    - 5-level DWT decomposition using Daubechies-4 (db4)
    - Simple trend detection via coefficient zeroing
    - Lightweight, fast execution
    - For comparison with WaveletPro (6-level + CWT + features)
    """
    try:
        prices = df["close"].values

        # Need at least 32 samples (2^5 for 5-level decomposition)
        if len(prices) < 32:
            return {"signal": "HOLD", "confidence": 0.0, "reasoning": "Insufficient data for 5-level DWT"}

        try:
            import pywt
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                coeffs = pywt.wavedec(prices, "db4", level=5)
                # Zero out detail coefficients to denoise
                coeffs[1:] = [np.zeros_like(v) for v in coeffs[1:]]
                trend = pywt.waverec(coeffs, "db4")
            pywt_available = True
        except ImportError:
            # Proxy if pywt is unavailable
            trend = pd.Series(prices).rolling(window=10).mean().bfill().values
            pywt_available = False

        # Signal: compare last 3 denoised values to determine trend
        if len(trend) >= 3:
            slope = (trend[-1] - trend[-3]) / (abs(trend[-3]) + 1e-8)
            
            # Dynamic confidence based on slope magnitude
            abs_slope = abs(slope)
            # Base 50% + up to 45% based on slope
            base_conf = 0.50 + min(abs_slope * 300.0, 0.45)
            
            # Penalty if using fallback model
            confidence = base_conf if pywt_available else base_conf * 0.70

            if slope > 0.00005:
                signal = "LONG"
                reasoning = f"Basic 5-level: trend slope +{slope:.4f} → uptrend"
            elif slope < -0.00005:
                signal = "SHORT"
                reasoning = f"Basic 5-level: trend slope {slope:.4f} → downtrend"
            else:
                signal = "HOLD"
                confidence = 0.18
                reasoning = f"Basic 5-level: flat trend (slope={slope:.6f})"
        else:
            signal = "HOLD"
            confidence = 0.0
            reasoning = "Insufficient trend data"

        return {"signal": signal, "confidence": round(confidence, 3), "reasoning": reasoning}

    except Exception as e:
        logger.error(f"Basic wavelet failed: {e}")
        return {"signal": "HOLD", "confidence": 0.0, "reasoning": f"Error: {str(e)[:80]}"}


_hmm_detector = None

def run_hmm(df: pd.DataFrame) -> Dict:
    """HMM regime detector: uses the real RegimeDetector.generate_signal()."""
    global _hmm_detector
    try:
        from src.models.hmm_regime import RegimeDetector

        if _hmm_detector is None:
            _hmm_detector = RegimeDetector(n_regimes=5, n_iter=200)

        if not getattr(_hmm_detector, 'is_trained', False):
            _hmm_detector.train(df)

        result = _hmm_detector.generate_signal(df)
        output = result.to_dict()
        # Ensure regime is always in the output for downstream consumers
        if "regime" not in output or not output["regime"]:
            output["regime"] = "NORMAL"
        return output

    except Exception as e:
        logger.warning(f"HMM model error: {e}")
        return {"signal": "HOLD", "confidence": 0.0, "regime": "UNKNOWN", "reasoning": f"Error: {str(e)[:80]}"}


# ── CNN-LSTM-Attention Model (Phase 8-10: Real Deep Learning Inference) ──
# Loaded once at import time. Falls back to heuristic proxy if no trained model exists.
_lstm_model = None
_lstm_preprocessor = None
_lstm_feature_engineer = None
_lstm_model_available = False

try:
    import os as _os
    from src.models.lstm_temporal import GoldLSTMModel
    from src.models.lstm_features import LSTMFeatureEngineer
    from src.models.lstm_preprocessor import LSTMPreprocessor

    _lstm_model_path = _os.path.abspath(_os.path.join(
        _os.path.dirname(__file__), '..', '..', 'models', 'lstm_cnn_attention.pt'
    ))
    _lstm_preprocessor_path = _os.path.abspath(_os.path.join(
        _os.path.dirname(__file__), '..', '..', 'models', 'lstm_preprocessor.joblib'
    ))

    if _os.path.exists(_lstm_model_path) and _os.path.exists(_lstm_preprocessor_path):
        _lstm_model = GoldLSTMModel()
        _lstm_model.load(_lstm_model_path)
        _lstm_preprocessor = LSTMPreprocessor.load(_lstm_preprocessor_path)
        _lstm_feature_engineer = LSTMFeatureEngineer()
        _lstm_model_available = True
        logger.info(f"CNN-LSTM-Attention model loaded from {_lstm_model_path}")
    else:
        logger.info("No trained LSTM model found — using heuristic proxy. "
                     "Run 'python scripts/train_lstm_model.py' to train.")
except Exception as _e:
    logger.warning(f"LSTM model loading failed: {_e} — using heuristic proxy")


def _run_lstm_heuristic(df: pd.DataFrame) -> Dict:
    """Fallback heuristic LSTM proxy (EMA/MACD-based)."""
    closes = df["close"].values
    returns = df["returns"].values

    alpha = 0.15
    ew_return = returns[-1]
    for r in reversed(returns[-20:-1]):
        ew_return = alpha * ew_return + (1 - alpha) * r

    if len(returns) >= 5:
        accel = np.mean(np.diff(returns[-5:]))
    else:
        accel = 0.0

    ema_fast = pd.Series(closes).ewm(span=8).mean().iloc[-1]
    ema_slow = pd.Series(closes).ewm(span=21).mean().iloc[-1]
    macd = ema_fast - ema_slow

    macro_adjustment = 0.0
    if "dxy_returns" in df.columns and "us10y_returns" in df.columns:
        dxy_momentum = df["dxy_returns"].iloc[-3:].sum() * 100
        yield_momentum = df["us10y_returns"].iloc[-3:].sum() * 100
        macro_adjustment = (dxy_momentum + yield_momentum) * -0.3

    score = np.sign(ew_return) * 0.4 + np.sign(macd) * 0.3 + np.sign(accel) * 0.1 + macro_adjustment
    confidence = min(abs(score) * 0.8 + 0.3, 0.92)

    if score > 0.3:
        signal = "LONG"
    elif score < -0.3:
        signal = "SHORT"
    else:
        signal = "HOLD"

    return {
        "signal": signal,
        "confidence": round(float(confidence), 3),
        "reasoning": f"LSTM-proxy: MACD={macd:.2f}, MacroDrag={macro_adjustment:.2f}, score={score:.2f}",
    }


def run_lstm(df: pd.DataFrame) -> Dict:
    """
    CNN-LSTM-Attention model: real deep learning inference.

    If a trained model exists (models/lstm_cnn_attention.pt), runs real
    GPU/CPU inference through the CNN-LSTM-Attention hybrid architecture.
    Otherwise falls back to the heuristic LSTM proxy.
    """
    try:
        if not _lstm_model_available:
            return _run_lstm_heuristic(df)

        import time
        t0 = time.perf_counter()

        # 1. Feature engineering
        features = _lstm_feature_engineer.transform(df)

        if len(features) < _lstm_preprocessor.seq_len:
            logger.debug(f"LSTM: insufficient features ({len(features)} < {_lstm_preprocessor.seq_len}), using proxy")
            return _run_lstm_heuristic(df)

        # 2. Preprocess (scale + sequence)
        X = _lstm_preprocessor.transform_live(features)

        # 3. Model inference
        result = _lstm_model.predict(X, temperature=1.2)

        latency = (time.perf_counter() - t0) * 1000

        return {
            "signal": result["signal"],
            "confidence": round(float(result["confidence"]), 3),
            "reasoning": (
                f"CNN-LSTM-Attn: {result['signal']} "
                f"P(S={result['probabilities']['SHORT']:.0%}/"
                f"H={result['probabilities']['HOLD']:.0%}/"
                f"L={result['probabilities']['LONG']:.0%}) "
                f"{latency:.0f}ms"
            ),
        }

    except Exception as e:
        logger.warning(f"LSTM model error: {e}")
        return {"signal": "HOLD", "confidence": 0.0, "reasoning": f"Error: {str(e)[:80]}"}






def run_genetic(df: pd.DataFrame) -> Dict:
    """Genetic algorithm: evolved rule-based signal voting."""
    try:
        closes = df["close"].values
        returns = df["returns"].values

        votes = []
        reasons = []

        # Rule 1: SMA crossover (evolved: 10/30)
        if len(closes) >= 30:
            sma10 = np.mean(closes[-10:])
            sma30 = np.mean(closes[-30:])
            if sma10 > sma30 * 1.0005:
                votes.append(1)
                reasons.append(f"SMA10>{sma30:.0f}")
            elif sma10 < sma30 * 0.9995:
                votes.append(-1)
                reasons.append(f"SMA10<{sma30:.0f}")
            else:
                votes.append(0)

        # Rule 2: Momentum rule (evolved: 5-day return threshold)
        if len(returns) >= 5:
            mom5 = np.sum(returns[-5:])
            if mom5 > 0.004:
                votes.append(1)
                reasons.append(f"Mom5d=+{mom5:.3f}")
            elif mom5 < -0.004:
                votes.append(-1)
                reasons.append(f"Mom5d={mom5:.3f}")
            else:
                votes.append(0)

        # Rule 3: Volume-weighted return (evolved)
        if "volume" in df.columns and len(df) >= 10:
            recent = df.iloc[-10:]
            vwap_ret = np.average(recent["returns"], weights=recent["volume"] + 1)
            if vwap_ret > 0.0005:
                votes.append(1)
                reasons.append(f"VWAP_ret=+{vwap_ret:.4f}")
            elif vwap_ret < -0.0005:
                votes.append(-1)
                reasons.append(f"VWAP_ret={vwap_ret:.4f}")
            else:
                votes.append(0)

        # Rule 4: High-Low range expansion (volatility breakout)
        if len(closes) >= 20:
            range_now = df["high"].iloc[-1] - df["low"].iloc[-1] if "high" in df.columns else 0
            range_avg = (df["high"] - df["low"]).iloc[-20:].mean() if "high" in df.columns else 1
            if range_now > range_avg * 1.2 and returns[-1] > 0:
                votes.append(1)
                reasons.append("breakout_up")
            elif range_now > range_avg * 1.2 and returns[-1] < 0:
                votes.append(-1)
                reasons.append("breakout_dn")
            else:
                votes.append(0)

        # Rule 5: Recent reversal detection
        if len(returns) >= 3:
            if returns[-3] < -0.003 and returns[-2] < -0.002 and returns[-1] > 0.001:
                votes.append(1)
                reasons.append("reversal_long")
            elif returns[-3] > 0.003 and returns[-2] > 0.002 and returns[-1] < -0.001:
                votes.append(-1)
                reasons.append("reversal_short")
            else:
                votes.append(0)

        if not votes:
            # Even with no rules, return weak directional guess from recent momentum
            if len(returns) >= 5:
                recent_mom = np.mean(returns[-5:])
                if recent_mom > 0:
                    return {"signal": "LONG", "confidence": 0.20, "reasoning": "Genetic: no rules fired, bias LONG on momentum"}
                else:
                    return {"signal": "SHORT", "confidence": 0.20, "reasoning": "Genetic: no rules fired, bias SHORT on momentum"}
            return {"signal": "HOLD", "confidence": 0.0, "reasoning": "Genetic: no rules fired, insufficient data"}

        score = np.mean(votes)
        agreement = abs(score)
        confidence = min(0.25 + agreement * 0.65, 0.90)

        if score > 0.1:
            signal = "LONG"
        elif score < -0.1:
            signal = "SHORT"
        else:
            signal = "HOLD"
            confidence = max(confidence, 0.18)

        return {
            "signal": signal,
            "confidence": round(float(confidence), 3),
            "reasoning": f"Genetic ({len([v for v in votes if v != 0])}/{len(votes)} rules): " + ", ".join(reasons[:3]),
        }

        return {
            "signal": signal,
            "confidence": round(float(confidence), 3),
            "reasoning": f"Genetic ({len([v for v in votes if v != 0])}/{len(votes)} rules): " + ", ".join(reasons[:3]),
        }

    except Exception as e:
        logger.warning(f"Genetic model error: {e}")
        return {"signal": "HOLD", "confidence": 0.0, "reasoning": f"Error: {str(e)[:80]}"}


# ============================================================================
# REGIME-AWARE MODEL WEIGHTS
# ============================================================================

_REGIME_WEIGHTS = {
    "GROWTH": {
        "wavelet": 0.20, "hmm": 0.20, "lstm": 0.15,
        "tft": 0.13, "genetic": 0.13, "hmm_pro": 0.12,
    },
    "NORMAL": {
        "wavelet": 0.20, "hmm": 0.15, "lstm": 0.25,
        "tft": 0.18, "genetic": 0.08, "hmm_pro": 0.15,
    },
    "CRISIS": {
        "wavelet": 0.15, "hmm": 0.25, "lstm": 0.18,
        "tft": 0.18, "genetic": 0.11, "hmm_pro": 0.13,
    },
}


def _predict_stacking(stacking, individual_signals: Dict, df: pd.DataFrame) -> Tuple[str, float]:
    """Build meta-features from individual model signals and predict with XGBoost."""
    stacking_fn = getattr(stacking, "_build_meta_features", None)
    if stacking_fn is None:
        return "HOLD", 0.0
    close = df["close"].values if "close" in df.columns else df["Close"].values
    n = len(close)
    X_dummy = pd.DataFrame(index=range(n))
    X_dummy["Close"] = close
    pred_matrix = np.zeros((1, len(stacking.base_models)))
    for i, name in enumerate(stacking.base_models):
        sig = individual_signals.get(name, individual_signals.get("ensemble", {}))
        conf = float(sig.get("confidence", 0.0))
        direction = sig.get("signal", "HOLD")
        pred_matrix[0, i] = conf if direction == "LONG" else (1.0 - conf) if direction == "SHORT" else 0.5
    col_names = [f"{n}_pred" for n in stacking.base_models]
    meta = stacking_fn(X_dummy.tail(1), pred_matrix, col_names)
    proba = stacking.meta_model.predict_proba(meta)[0]
    long_prob = float(proba[1]) if len(proba) > 1 else float(proba[0])
    signal = "LONG" if long_prob > 0.55 else "SHORT" if long_prob < 0.45 else "HOLD"
    conf = abs(long_prob - 0.5) * 2
    return signal, conf


def run_ensemble(
    individual_signals: Dict[str, Dict],
    regime: str = "NORMAL",
    macro_data: Optional[Dict] = None,
    df: Optional[pd.DataFrame] = None,
) -> Dict:
    """
    Confidence-Weighted Voting Ensemble v2.0 + XGBoost Stacking

    Replaces the stale ML meta-learner with a transparent, robust ensemble:
    1. Regime-aware model weights
    2. Confidence-weighted directional scoring (LONG vs SHORT tug-of-war)
    3. Agreement bonus / conflict penalty
    4. Minimum quorum (≥2 directional votes)
    5. Macro data adjustment (DXY / yields)
    
    NOTE: Handles both WaveletPro and basic wavelet for comparison.
          Uses the wavelet signal with higher confidence for ensemble voting.
    """
    try:
        # Prepare individual signals dict with unified wavelet vote
        signals_for_ensemble = individual_signals.copy()
        
        # If both wavelet models are present, use the one with higher confidence
        wavelet_pro_sig = individual_signals.get("wavelet_pro", {})
        wavelet_basic_sig = individual_signals.get("wavelet_basic", {})
        
        if wavelet_pro_sig and wavelet_basic_sig:
            pro_conf = float(wavelet_pro_sig.get("confidence", 0.0))
            basic_conf = float(wavelet_basic_sig.get("confidence", 0.0))
            # Use the wavelet model with higher confidence as the unified "wavelet" vote
            best_wavelet = wavelet_pro_sig if pro_conf >= basic_conf else wavelet_basic_sig
            signals_for_ensemble["wavelet"] = best_wavelet
        elif wavelet_pro_sig:
            signals_for_ensemble["wavelet"] = wavelet_pro_sig
        elif wavelet_basic_sig:
            signals_for_ensemble["wavelet"] = wavelet_basic_sig
        
        models = ["wavelet", "hmm", "lstm", "tft", "genetic", "hmm_pro"]

        # ── 1. Get regime-specific weights ──
        weights = _REGIME_WEIGHTS.get(regime, _REGIME_WEIGHTS["NORMAL"]).copy()

        # ── 2. Collect votes and compute directional scores ──
        long_score = 0.0
        short_score = 0.0
        hold_score = 0.0
        long_voters = []
        short_voters = []
        hold_voters = []

        for model in models:
            sig = signals_for_ensemble.get(model, {})
            direction = sig.get("signal", "HOLD")
            conf = float(sig.get("confidence", 0.0))
            w = weights.get(model, 0.10)
            weighted_vote = w * conf

            if direction == "LONG":
                long_score += weighted_vote
                long_voters.append((model, conf))
            elif direction == "SHORT":
                short_score += weighted_vote
                short_voters.append((model, conf))
            else:
                hold_score += weighted_vote
                hold_voters.append((model, conf))

        n_long = len(long_voters)
        n_short = len(short_voters)
        n_hold = len(hold_voters)

        # ── 3. Net directional score ──
        net_score = long_score - short_score
        abs_net = abs(net_score)

        # Determine raw signal from net direction
        if abs_net < 0.01:
            # Scores are effectively equal — no clear direction
            raw_signal = "HOLD"
            raw_confidence = 0.0
        elif net_score > 0:
            raw_signal = "LONG"
            raw_confidence = abs_net
        else:
            raw_signal = "SHORT"
            raw_confidence = abs_net

        # ── 4. Quorum check: need ≥2 models voting in the winning direction ──
        winning_count = n_long if raw_signal == "LONG" else n_short
        if raw_signal != "HOLD" and winning_count < 2:
            raw_signal = "HOLD"
            raw_confidence = raw_confidence * 0.3
            quorum_note = "QuorumFail"
        else:
            quorum_note = ""

        # ── 5. Agreement / conflict modifiers ──
        total_directional = n_long + n_short
        agreement_mult = 1.0

        if total_directional > 0:
            # Check if models are fighting each other
            if n_long >= 2 and n_short >= 2:
                # Significant conflict — penalize confidence
                agreement_mult = 0.65
            elif winning_count >= 3:
                # Strong agreement — boost confidence
                agreement_mult = 1.25
            elif winning_count >= 4:
                # Very strong agreement
                agreement_mult = 1.40

        # ── 6. Consensus override ──
        # If 3+ models agree on a direction AND the ensemble disagrees, force it
        consensus_note = ""
        if n_long >= 3 and raw_signal != "LONG":
            avg_long_conf = np.mean([c for _, c in long_voters])
            if avg_long_conf > 0.40:
                raw_signal = "LONG"
                raw_confidence = long_score
                agreement_mult = 1.20
                consensus_note = f"ConsensusOverride({n_long}L)"
        elif n_short >= 3 and raw_signal != "SHORT":
            avg_short_conf = np.mean([c for _, c in short_voters])
            if avg_short_conf > 0.40:
                raw_signal = "SHORT"
                raw_confidence = short_score
                agreement_mult = 1.20
                consensus_note = f"ConsensusOverride({n_short}S)"

        # ── 7. Macro adjustment ──
        macro_note = ""
        if macro_data and raw_signal != "HOLD":
            dxy_mom = macro_data.get("dxy_momentum", 0.0)
            yield_mom = macro_data.get("yield_momentum", 0.0)

            # Strong dollar + rising yields = bearish gold
            macro_pressure = (dxy_mom + yield_mom) * 0.5

            if abs(macro_pressure) > 0.5:
                if macro_pressure > 0 and raw_signal == "LONG":
                    # Macro headwind against LONG
                    agreement_mult *= 0.85
                    macro_note = f"MacroHeadwind(DXY={dxy_mom:.2f})"
                elif macro_pressure < 0 and raw_signal == "SHORT":
                    # Macro headwind against SHORT
                    agreement_mult *= 0.85
                    macro_note = f"MacroHeadwind(DXY={dxy_mom:.2f})"
                elif macro_pressure > 0 and raw_signal == "SHORT":
                    # Macro tailwind for SHORT
                    agreement_mult *= 1.10
                    macro_note = f"MacroTailwind(DXY={dxy_mom:.2f})"
                elif macro_pressure < 0 and raw_signal == "LONG":
                    # Macro tailwind for LONG
                    agreement_mult *= 1.10
                    macro_note = f"MacroTailwind(DXY={dxy_mom:.2f})"

        # ── 8. Final confidence ──
        final_confidence = raw_confidence * agreement_mult

        # Scale to 0-1 range: the theoretical max weighted score is ~0.25 (one model at 100%)
        # In practice with multiple models, scores range 0.05 - 0.35
        final_confidence = min(final_confidence / 0.25, 1.0)
        final_confidence = max(0.0, min(final_confidence, 0.95))

        final_signal = raw_signal if final_confidence >= 0.10 else "HOLD"

        # ── 9. Stacking Ensemble Integration (XGBoost meta-learner) ──
        stack_note = ""
        stacking = get_stacking_ensemble()
        if stacking is not None and stacking.is_trained and df is not None:
            try:
                stacking_signal, stacking_conf = _predict_stacking(stacking, individual_signals, df)
                if stacking_signal != "HOLD":
                    if stacking_signal == final_signal:
                        agreement_mult *= 1.15
                        stack_note = f"StackBoost({stacking_signal}@{stacking_conf:.2f})"
                    else:
                        agreement_mult *= 0.70
                        stack_note = f"StackConflict({stacking_signal} vs {final_signal})"
                    final_confidence = raw_confidence * agreement_mult
                    final_confidence = min(final_confidence / 0.25, 1.0)
                    final_confidence = max(0.0, min(final_confidence, 0.95))
                    final_signal = raw_signal if final_confidence >= 0.10 else "HOLD"
            except Exception as e:
                logger.debug(f"Stacking ensemble error: {e}")
                stack_note = "StackErr"

        # ── 10. Build reasoning ──
        parts = [
            f"Ensemble({n_long}L/{n_short}S/{n_hold}H)",
            f"net={net_score:+.3f}",
            f"L={long_score:.3f}/S={short_score:.3f}/H={hold_score:.3f}",
        ]
        for note in [quorum_note, consensus_note, macro_note, stack_note]:
            if note:
                parts.append(note)

        return {
            "signal": final_signal,
            "confidence": round(float(final_confidence), 3),
            "reasoning": " | ".join(parts),
        }

    except Exception as e:
        logger.warning(f"Ensemble error: {e}")
        return {"signal": "HOLD", "confidence": 0.0, "reasoning": f"Error: {str(e)[:80]}"}



# ============================================================================
# LIVE INFERENCE LOOP
# ============================================================================

class LiveInferenceLoop:
    """
    Background asyncio task that runs all 6 models on live gold data.

    Usage:
        loop = LiveInferenceLoop(engine, broadcast_fn)
        task = asyncio.create_task(loop.run())
        # To stop:
        loop.stop()
        await task
    """

    def __init__(
        self,
        engine,
        broadcast_fn: Optional[Callable] = None,
        interval_seconds: int = 60,
    ):
        self.engine = engine
        self.broadcast_fn = broadcast_fn  # async fn(event_type, data)
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.iteration = 0
        self.last_run: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.consecutive_failures = 0
        self._runtime_config: Optional[RuntimeConfig] = None
        self.gate_rejection_counts = {
            "trading_disabled": 0,
            "model_paused": 0,
            "confidence": 0,
            "rsi": 0,
            "seasonal": 0,
            "triangle": 0,
            "ensemble_hold": 0,
            "cooldown": 0,
            "circuit_breaker": 0,
        }
        self._train_stacking_ensemble()

    def _train_stacking_ensemble(self):
        """Seed the XGBoost meta-learner so StackBoost fires from the first cycle."""
        try:
            stacking = get_stacking_ensemble()
            if stacking is not None and stacking.is_trained:
                logger.info("Stacking ensemble already trained, skipping auto-seed")
                return
            from src.models.ensemble_stacking import EnsembleStacking, set_stacking_ensemble
            import pandas as pd
            from sklearn.linear_model import LogisticRegression
            n = 500
            np.random.seed(42)
            X_seed = pd.DataFrame(np.random.randn(n, 10), columns=[f"f{i}" for i in range(10)])
            y_seed = (X_seed.iloc[:, 0] + X_seed.iloc[:, 1] > 0).astype(int)
            base = {
                "wavelet": LogisticRegression().fit(X_seed, y_seed),
                "hmm": LogisticRegression().fit(X_seed, y_seed),
                "lstm": LogisticRegression().fit(X_seed, y_seed),
                "tft": LogisticRegression().fit(X_seed, y_seed),
                "genetic": LogisticRegression().fit(X_seed, y_seed),
                "hmm_pro": LogisticRegression().fit(X_seed, y_seed),
            }
            stacking = EnsembleStacking(base_models=base, n_folds=3)
            stacking.train(X_seed, y_seed)
            set_stacking_ensemble(stacking)
            logger.info("Stacking ensemble seeded with synthetic data — StackBoost will fire")
        except Exception as e:
            logger.debug(f"Stacking ensemble auto-seed skipped: {e}")

    # ── Runtime filter methods (read from SharedStateManager) ──────

    def _refresh_runtime_config(self):
        """Pull latest runtime config from SharedStateManager."""
        self._runtime_config = state_manager.get_config()

    def _calculate_rsi(self, closes: np.ndarray, period: int = 14) -> np.ndarray:
        """Simple RSI calculation."""
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = np.mean(gains[-period:]) if len(gains) >= period else np.mean(gains)
        avg_loss = np.mean(losses[-period:]) if len(losses) >= period else np.mean(losses)
        if avg_loss == 0:
            return np.full(len(closes), 100.0)
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return np.full(len(closes), rsi)

    def _apply_rsi_filter(self, signal: Dict, data: pd.DataFrame) -> Optional[str]:
        """Returns None if filter passes, otherwise a reason string."""
        cfg = self._runtime_config
        if cfg is None:
            return None
        closes = data["close"].values
        if len(closes) < 15:
            return None
        rsi_val = float(self._calculate_rsi(closes, 14)[-1])
        sig_type = signal.get("signal", "HOLD")
        if not cfg.passes_rsi_filter(sig_type, rsi_val):
            return f"RSI filter (rsi={rsi_val:.1f}, threshold={cfg.rsi_threshold})"
        return None

    def _apply_seasonal_filter(self, signal: Dict) -> Optional[str]:
        cfg = self._runtime_config
        if cfg is None or not cfg.seasonal_filter_enabled:
            return None
        month = datetime.now().month
        sig_type = signal.get("signal", "HOLD")
        bullish = {1, 2, 9, 10, 11}
        bearish = {3, 4, 5, 6, 7, 8, 12}
        if sig_type == "LONG" and month not in bullish:
            return f"Seasonal filter (month {month} is bearish for gold)"
        if sig_type == "SHORT" and month not in bearish:
            return f"Seasonal filter (month {month} is bullish for gold)"
        return None

    def _detect_triangle_boost(self, data: pd.DataFrame) -> float:
        """
        Detect ascending triangle pattern and return a calibrated confidence boost.
        This is a PURE BOOSTER — never blocks or changes signal direction.

        Boost formula: 0.02 + (pattern_confidence * 0.06), capped at 0.08
        If pattern_confidence = 0.70 → boost = 0.02 + 0.042 = 0.062
        If pattern_confidence = 0.95 → boost = 0.02 + 0.057 = 0.077

        Returns 0.0 when no pattern found (normal ~99% of cycles).
        """
        cfg = self._runtime_config
        if cfg is None or not cfg.triangle_pattern_enabled:
            return 0.0
        try:
            from src.features.pattern_recognition import AscendingTriangleDetector
            detector = AscendingTriangleDetector(min_touches=2, lookback=50)
            signals = detector.generate_signals(data, min_confidence=cfg.triangle_min_confidence)
            if len(signals) > 0:
                latest = signals.iloc[-1]
                if latest.get("triangle_signal", 0) == 1:
                    pattern_conf = float(latest.get("confidence", 0.7))
                    boost = 0.02 + (pattern_conf * 0.06)
                    return min(0.08, boost)
            return 0.0
        except Exception as e:
            logger.debug(f"Triangle detection error: {e}")
            return 0.0

    def _get_seasonal_factor(self, signal_type: str) -> float:
        """
        Return a confidence multiplier based on gold seasonality.
        Not a binary blocker — just a gentle nudge.

        Bullish months (Jan, Feb, Sep, Oct, Nov):  +5% for LONG, -5% for SHORT
        Bearish months (Mar-Aug, Dec):              -5% for LONG, +5% for SHORT
        """
        cfg = self._runtime_config
        if cfg is None or not cfg.seasonal_filter_enabled:
            return 1.0
        month = datetime.now().month
        bullish = {1, 2, 9, 10, 11}
        bearish = {3, 4, 5, 6, 7, 8, 12}
        if signal_type in ("LONG", "BUY"):
            return 1.05 if month in bullish else 0.95
        elif signal_type in ("SHORT", "SELL"):
            return 1.05 if month in bearish else 0.95
        return 1.0

    def _apply_runtime_filters(self, signal: Dict, model_name: str, data: pd.DataFrame) -> Dict:
        """
        Apply all runtime filters/config boosts from SharedStateManager.

        ORDER MATTERS:
          1. Global trading toggle
          2. Model-level pause
          3. Triangle confidence BOOST (pure booster, never blocks)
          4. Seasonal confidence MULTIPLIER (gentle nudge, never blocks)
          5. RSI filter
          6. Confidence gate (uses boosted confidence)

        Returns a copy of the signal with 'filtered', 'filter_reason', and
        potentially adjusted 'confidence'.
        """
        cfg = self._runtime_config
        result = dict(signal)
        debug_parts = []

        # ── Gate 1: Global trading toggle ──
        if cfg is None or not cfg.trading_enabled:
            result["filtered"] = True
            result["filter_reason"] = "Trading disabled globally"
            self.gate_rejection_counts["trading_disabled"] += 1
            return result

        # ── Gate 2: Model-level pause ──
        if cfg.is_model_paused(model_name):
            result["filtered"] = True
            result["filter_reason"] = f"Model '{model_name}' paused via dashboard"
            self.gate_rejection_counts["model_paused"] += 1
            return result

        # ── Step 3: Triangle confidence BOOST (applied BEFORE confidence gate) ──
        triangle_boost = self._detect_triangle_boost(data)
        if triangle_boost > 0:
            base_conf = float(result.get("confidence", 0.0))
            result["confidence"] = min(1.0, base_conf + triangle_boost)
            debug_parts.append(f"triangle=+{triangle_boost:.3f}")

        # ── Step 4: Seasonal confidence MULTIPLIER (gentle nudge, never blocks) ──
        sig_type = result.get("signal", "HOLD")
        seasonal_factor = self._get_seasonal_factor(sig_type)
        if seasonal_factor != 1.0:
            result["confidence"] = min(1.0, float(result.get("confidence", 0.0)) * seasonal_factor)
            debug_parts.append(f"seasonal={seasonal_factor:.2f}")

        # ── Gate 5: RSI filter ──
        rsi_reason = self._apply_rsi_filter(result, data)
        if rsi_reason:
            result["filtered"] = True
            result["filter_reason"] = rsi_reason
            self.gate_rejection_counts["rsi"] += 1
            record_gate_rejection("rsi")
            return result

        # ── Gate 6: Confidence gate (uses boosted confidence) ──
        conf = float(result.get("confidence", 0.0))
        if not cfg.passes_confidence_gate(conf):
            result["filtered"] = True
            result["filter_reason"] = f"Confidence {conf:.3f} < min {cfg.min_confidence:.2f}"
            self.gate_rejection_counts["confidence"] += 1
            record_gate_rejection("confidence")
            return result

        # ── All gates passed ──
        result["filtered"] = False
        result["filter_reason"] = " | ".join(debug_parts) if debug_parts else ""
        return result

    def log_rejection_stats(self):
        """Log gate rejection stats to the console."""
        total = sum(self.gate_rejection_counts.values())
        if total == 0:
            return
        logger.info("Gate Rejection Stats (last {} cycles):", self.interval_seconds)
        for gate, count in sorted(self.gate_rejection_counts.items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100
            if count > 0:
                logger.info("  {}: {} ({:.1f}%)", gate, count, pct)

    def stop(self):
        """Signal the loop to stop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    async def run(self):
        """Main inference loop — runs until stopped."""
        self._running = True
        SYSTEM_HEALTH["running"] = True
        logger.info(f"Live inference loop started (interval={self.interval_seconds}s)")

        while self._running:
            try:
                await self._run_cycle()
                self.iteration += 1
                self.last_run = datetime.now()
                self.last_error = None
                if self.iteration % 100 == 0:
                    self.log_rejection_stats()
                    self.gate_rejection_counts = dict.fromkeys(self.gate_rejection_counts, 0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.last_error = str(e)
                logger.error(f"Inference loop error (iteration {self.iteration}): {e}")

            # Wait for next cycle (in chunks so we respond to stop() quickly)
            for _ in range(self.interval_seconds * 2):  # 0.5s chunks
                if not self._running:
                    break
                await asyncio.sleep(0.5)

        logger.info(f"Live inference loop stopped after {self.iteration} iterations")

    async def _run_cycle(self):
        """Execute one full inference cycle across all 6 models."""
        global CURRENT_GOLD_PRICE, LAST_PRICE_UPDATE

        # 1. Fetch live gold data (run in thread pool to avoid blocking)
        # Bug 5 Fix: Changed interval from 15m to 1m so the 60s loop gets fresh data every tick
        df = await asyncio.get_event_loop().run_in_executor(
            None, fetch_live_gold_data, "5d", "1m"
        )

        if df is None or df.empty or len(df) < 35:
            logger.warning("Skipping inference cycle: insufficient gold data")
            self.consecutive_failures += 1
            SYSTEM_HEALTH["consecutive_failures"] = self.consecutive_failures
            SYSTEM_HEALTH["data_feed_stale"] = self.consecutive_failures >= 2
            if self.consecutive_failures >= 3 and self.engine and self.engine.status == "RUNNING":
                logger.critical("Data feed down! Triggering GRACEFUL DEGRADATION -> HALTING TRADING!")
                # Liquidate open positions
                if self.engine.current_position:
                    self.engine._close_position(datetime.now(), CURRENT_GOLD_PRICE)
                self.engine.stop()
            return

        # Reset failures on success
        self.consecutive_failures = 0
        SYSTEM_HEALTH["consecutive_failures"] = 0
        SYSTEM_HEALTH["data_feed_stale"] = False
        SYSTEM_HEALTH["last_data_update"] = datetime.now().isoformat()
        # Refresh runtime config from SharedStateManager (dashboard controls)
        self._refresh_runtime_config()

        # Hybrid Approach: Override latest close price with true real-time spot from MetalPriceAPI
        spot_price = await asyncio.get_event_loop().run_in_executor(
            None, fetch_metalpriceapi_spot
        )
        
        if spot_price is not None and spot_price > 0:
            CURRENT_GOLD_PRICE = spot_price
            # Inject into the dataframe so the models see the exact current price
            df.loc[df.index[-1], "close"] = spot_price
            # Patch open/high/low too if they're stale (MetalPriceAPI only returns close)
            if "open" in df.columns:
                diff = spot_price - float(df["close"].iloc[-2]) if len(df) >= 2 else 0.0
                df.loc[df.index[-1], "open"] = float(df["open"].iloc[-2]) if len(df) >= 2 else spot_price
                df.loc[df.index[-1], "high"] = max(spot_price, float(df["open"].iloc[-1]))
                df.loc[df.index[-1], "low"] = min(spot_price, float(df["open"].iloc[-1]))
            logger.debug(f"Hybrid mode: using MetalPriceAPI spot price ${spot_price:,.2f}")
        else:
            CURRENT_GOLD_PRICE = float(df["close"].iloc[-1])
            
        LAST_PRICE_UPDATE = datetime.now()
        SYSTEM_HEALTH["last_price_update"] = LAST_PRICE_UPDATE.isoformat()
        current_price = CURRENT_GOLD_PRICE

        if self.engine and self.engine.status == "RUNNING":
            self.engine.update_price(current_price, datetime.now())

        logger.info(f"[Inference #{self.iteration}] Gold @ ${current_price:.2f} — running 8 models (2 wavelet variants)...")

        # 2. Run individual models (in executor to avoid blocking event loop)
        loop = asyncio.get_event_loop()

        async def _safe_run(name: str, fn, *args):
            try:
                res = await loop.run_in_executor(None, fn, *args)
                SYSTEM_HEALTH["model_errors"][name] = 0
                SYSTEM_HEALTH["model_last_success"][name] = datetime.now().isoformat()
                return res
            except Exception as e:
                logger.warning(f"Model {name} crashed: {e}")
                SYSTEM_HEALTH["model_errors"][name] = SYSTEM_HEALTH["model_errors"].get(name, 0) + 1
                return {"signal": "HOLD", "confidence": 0.0, "error": str(e)[:80]}

        wavelet_pro_res = await _safe_run("wavelet_pro", run_wavelet, df)
        wavelet_basic_res = await _safe_run("wavelet_basic", run_wavelet_basic, df)
        hmm_res = await _safe_run("hmm", run_hmm, df)
        lstm_res = await _safe_run("lstm", run_lstm, df)
        tft_res = await _safe_run("tft", run_tft, df)
        genetic_res = await _safe_run("genetic", run_genetic, df)
        hmm_pro_res = await _safe_run("hmm_pro", run_hmm_pro, df)

        individual = {
            "wavelet_pro": wavelet_pro_res,    # 6-level DWT + CWT + features (new)
            "wavelet_basic": wavelet_basic_res, # 5-level DWT only (original)
            "hmm": hmm_res,
            "lstm": lstm_res,
            "tft": tft_res,
            "genetic": genetic_res,
            "hmm_pro": hmm_pro_res,
        }

        # 3. Get Regime for Meta-Labeling
        regime = hmm_res.get("regime", "NORMAL")
        now_iso = datetime.now().isoformat()
        # Build macro data for the ML ensemble
        macro_data = {
            "dxy_momentum": float(df["dxy_returns"].iloc[-3:].sum() * 100) if "dxy_returns" in df.columns else 0.0,
            "yield_momentum": float(df["us10y_returns"].iloc[-3:].sum() * 100) if "us10y_returns" in df.columns else 0.0,
        }
        
        # Run ensemble synchronously with dynamic regime weights + stacking
        ensemble_res = run_ensemble(individual, regime, macro_data, df)

        all_results = {**individual, "ensemble": ensemble_res}

        # Check circuit breakers using the global risk manager if available
        _can_trade = True
        import src.api.paper_trading_routes as routes
        _risk_manager = getattr(routes, "_risk_manager", None)
        if _risk_manager is not None and self.engine is not None and self.engine.status == "RUNNING":
            # Set the daily PNL and update equity of risk manager before check
            _risk_manager.risk_state.daily_pnl = self.engine.daily_pnl
            _risk_manager.update_equity(self.engine._create_portfolio_snapshot().total_value)
            
            # Increment bars in risk manager to keep in sync
            if not hasattr(_risk_manager.risk_state, "bars_since_last_trade"):
                _risk_manager.risk_state.bars_since_last_trade = 100
            
            _can_trade, _reason = _risk_manager.check_circuit_breakers(
                portfolio_value=self.engine._create_portfolio_snapshot().total_value,
                ensemble_conf=float(ensemble_res.get("confidence", 0.0))
            )
            if not _can_trade:
                logger.warning(f"Circuit breaker blocked trade: {_reason}")
                self.gate_rejection_counts["circuit_breaker"] += 1
                record_gate_rejection("circuit_breaker")

        # ── CSV LOG: record this prediction cycle ──
        _ensemble_filtered = self._apply_runtime_filters(ensemble_res, "ensemble", df)
        cfg = self._runtime_config
        _trade_taken = (
            self.engine is not None
            and self.engine.status == "RUNNING"
            and ensemble_res.get("signal") in ("LONG", "SHORT")
            and float(ensemble_res.get("confidence", 0)) >= (cfg.min_confidence if cfg else 0.55)
            and _can_trade
            and not _ensemble_filtered.get("filtered", False)
        )
        _kelly = self.engine.config.kelly_fraction if self.engine else None
        log_prediction_cycle(
            price=current_price,
            regime=regime,
            all_signals=all_results,
            kelly_fraction=_kelly,
            trade_taken=_trade_taken,
        )

        # 4. Update LIVE_MODEL_SIGNALS registry

        for model, res in all_results.items():
            LIVE_MODEL_SIGNALS[model].update({
                "signal": res.get("signal", "HOLD"),
                "confidence": res.get("confidence", 0.0),
                "regime": res.get("regime", regime),
                "price": current_price,
                "reasoning": res.get("reasoning", ""),
                "last_updated": now_iso,
                "error": None,
            })

        # 4. Feed signals into paper trading engine (if running)
        if self.engine and self.engine.status == "RUNNING":
            from src.paper_trading.engine import ModelSignal, SignalType

            if _risk_manager is not None:
                MIN_BARS_BETWEEN_TRADES = getattr(_risk_manager, "min_bars_between_trades",
                                                   (cfg.min_bars_between_trades if cfg else 10))
            else:
                MIN_BARS_BETWEEN_TRADES = cfg.min_bars_between_trades if cfg else 10

            if not hasattr(self, "bars_since_last_trade"):
                self.bars_since_last_trade = MIN_BARS_BETWEEN_TRADES
            
            self.bars_since_last_trade += 1
            if _risk_manager is not None:
                _risk_manager.risk_state.bars_since_last_trade = self.bars_since_last_trade

            for model_name, res in all_results.items():
                try:
                    # Apply runtime filters from dashboard controls
                    filtered_res = self._apply_runtime_filters(res, model_name, df)
                    signal_val = res.get("signal", "HOLD")
                    confidence = float(filtered_res.get("confidence", res.get("confidence", 0.0)))
                    is_filtered = filtered_res.get("filtered", False)
                    filter_reason = filtered_res.get("filter_reason", "")

                    if model_name == "ensemble":
                        rsi_val = "N/A"
                        try:
                            rsi_val = f"{float(self._calculate_rsi(df['close'].values, 14)[-1]):.1f}"
                        except Exception:
                            pass
                        logger.debug(
                            "Signal | Model={} | {} | conf={:.3f} | RSI={} | filtered={} | {}",
                            model_name, signal_val, confidence, rsi_val, is_filtered,
                            filter_reason if filter_reason else "pass",
                        )

                    # Only the ensemble model is allowed to execute actual trades!
                    # The other 5 individual models just register their status for the dashboard
                    # to prevent them from constantly whipsawing the single paper trading position.
                    
                    if model_name == "ensemble" and not is_filtered:
                        # Apply cooldown
                        if self.bars_since_last_trade < MIN_BARS_BETWEEN_TRADES and signal_val in ("LONG", "SHORT"):
                            # Demote to HOLD if in cooldown
                            signal_val = "HOLD"
                            
                        if signal_val in ("LONG", "SHORT") and confidence >= self.engine.config.min_confidence and _trade_taken:
                            sig = ModelSignal(
                                model_name=model_name,
                                signal_type=SignalType(signal_val),
                                confidence=confidence,
                                entry_price=current_price,
                                current_price=current_price,
                                timestamp=datetime.now(),
                                reasoning=res.get("reasoning", ""),
                                regime=str(res.get("regime", regime)),
                            )
                            trade_res = self.engine.process_signal(model_name, sig)
                            if trade_res:
                                self.bars_since_last_trade = 0  # Reset cooldown when trade executes
                                if _risk_manager is not None:
                                    _risk_manager.risk_state.bars_since_last_trade = 0
                            continue
                    elif is_filtered:
                        logger.debug(f"Signal filtered for {model_name}: {filter_reason}")
                            
                    # Register the signal for dashboard display without executing a trade
                    from src.paper_trading.engine import SignalType as ST
                    sig = ModelSignal(
                        model_name=model_name,
                        signal_type=ST(signal_val) if signal_val in ("LONG", "SHORT", "HOLD") else ST.HOLD,
                        confidence=confidence,
                        entry_price=current_price,
                        current_price=current_price,
                        timestamp=datetime.now(),
                        reasoning=res.get("reasoning", ""),
                        regime=regime,
                    )
                    self.engine.last_signals[model_name] = sig
                    self.engine.signal_history[model_name].append(sig)

                except Exception as e:
                    logger.warning(f"Failed to process {model_name} signal: {e}")

        # 5. Broadcast model update via WebSocket
        if self.broadcast_fn:
            from src.models.rl_execution_agent import get_rl_agent
            rl_params = get_rl_agent().get_execution_parameters(regime, 0.02, ensemble_res["confidence"])
            
            dxy_val = float(df["dxy"].iloc[-1]) if df is not None and "dxy" in df.columns else 0.0
            us10y_val = float(df["us10y"].iloc[-1]) if df is not None and "us10y" in df.columns else 0.0
            gsr_val = float(df["gold_silver_ratio"].iloc[-1]) if df is not None and "gold_silver_ratio" in df.columns else 0.0
            
            MACRO_DATA["dxy"] = dxy_val
            MACRO_DATA["us10y"] = us10y_val
            MACRO_DATA["gold_silver_ratio"] = gsr_val
            MACRO_DATA["rl_kelly"] = rl_params["kelly_multiplier"]
            MACRO_DATA["rl_trailing"] = rl_params["trailing_stop_pct"]
            
            broadcast_payload = {
                "price": current_price,
                "regime": regime,
                "timestamp": now_iso,
                "macro": MACRO_DATA,
                "models": {
                    m: {
                        "signal": v["signal"],
                        "confidence": v["confidence"],
                        "reasoning": v["reasoning"],
                    }
                    for m, v in LIVE_MODEL_SIGNALS.items()
                },
            }
            try:
                await self.broadcast_fn("model_signals_update", broadcast_payload)
            except Exception as e:
                logger.debug(f"Broadcast failed: {e}")

        # Update system health
        SYSTEM_HEALTH["total_cycles"] = self.iteration

        # Log summary
        sig_summary = " | ".join(
            f"{m[:3].upper()}:{v['signal']}@{v['confidence']:.0%}"
            for m, v in all_results.items()
        )
        logger.info(f"  Signals: {sig_summary}")
