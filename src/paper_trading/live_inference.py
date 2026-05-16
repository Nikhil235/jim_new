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
from typing import Optional, Dict, Callable, Any
import numpy as np
import pandas as pd
from loguru import logger
from src.models.nlp_sentiment import run_nlp_sentiment

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
    for model in ["wavelet", "hmm", "lstm", "tft", "genetic", "nlp", "ensemble"]
}

# Current gold price (updated on each fetch)
CURRENT_GOLD_PRICE: float = 0.0
LAST_PRICE_UPDATE: Optional[datetime] = None


# ============================================================================
# GOLD DATA FETCHER
# ============================================================================

def fetch_live_gold_data(period: str = "5d", interval: str = "15m") -> Optional[pd.DataFrame]:
    """
    Fetch latest gold futures OHLCV data AND macro indicators (DXY, US10Y) via yfinance.
    Returns DataFrame with columns: open, high, low, close, volume, returns, dxy, us10y, dxy_returns, us10y_returns
    """
    try:
        import yfinance as yf
        # Group download is faster and aligns timestamps perfectly
        tickers = "GC=F DX-Y.NYB ^TNX"
        df_all = yf.download(tickers, period=period, interval=interval, group_by="ticker", progress=False)

        if df_all.empty:
            logger.warning("yfinance returned empty dataframe")
            return None

        # Extract Gold
        df = df_all["GC=F"].copy()
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].copy()
        
        # Extract DXY and US10Y closes (Forward fill to handle slightly misaligned ticks)
        df["dxy"] = df_all["DX-Y.NYB"]["Close"].ffill()
        df["us10y"] = df_all["^TNX"]["Close"].ffill()
        
        df.dropna(inplace=True)

        # Add returns
        df["returns"] = df["close"].pct_change()
        df["dxy_returns"] = df["dxy"].pct_change()
        df["us10y_returns"] = df["us10y"].pct_change()
        
        df.dropna(inplace=True)

        logger.debug(f"Data fetched: {len(df)} bars. Gold: ${df['close'].iloc[-1]:.2f}, DXY: {df['dxy'].iloc[-1]:.2f}, US10Y: {df['us10y'].iloc[-1]:.2f}%")
        return df

    except Exception as e:
        logger.error(f"Failed to fetch gold data: {e}")
        return None


# ============================================================================
# MODEL RUNNERS — each returns (signal: str, confidence: float, reasoning: str)
# ============================================================================

def run_wavelet(df: pd.DataFrame) -> Dict:
    """Wavelet denoiser signal: trend direction from denoised price series."""
    try:
        prices = df["close"].values

        # Need at least 32 samples (2^5 for 5-level decomposition)
        if len(prices) < 32:
            return {"signal": "HOLD", "confidence": 0.0, "reasoning": "Insufficient data"}

        try:
            import pywt
            coeffs = pywt.wavedec(prices, "db4", level=5)
            # Zero out detail coefficients to denoise
            coeffs[1:] = [np.zeros_like(v) for v in coeffs[1:]]
            trend = pywt.waverec(coeffs, "db4")
            confidence = 0.75
        except ImportError:
            # Proxy if pywt is unavailable
            trend = pd.Series(prices).rolling(window=10).mean().bfill().values
            confidence = 0.5

        # Signal: compare last 3 denoised values to determine trend
        if len(trend) >= 3:
            slope = (trend[-1] - trend[-3]) / (abs(trend[-3]) + 1e-8)
            if slope > 0.0001:
                signal = "LONG"
                reasoning = f"Wavelet trend slope +{slope:.4f} → uptrend detected"
            elif slope < -0.0001:
                signal = "SHORT"
                reasoning = f"Wavelet trend slope {slope:.4f} → downtrend detected"
            else:
                signal = "HOLD"
                reasoning = f"Wavelet trend flat (slope={slope:.6f})"
        else:
            signal = "HOLD"
            reasoning = "Insufficient trend data"

        return {"signal": signal, "confidence": round(confidence, 3), "reasoning": reasoning}

    except Exception as e:
        logger.warning(f"Wavelet model error: {e}")
        return {"signal": "HOLD", "confidence": 0.0, "reasoning": f"Error: {str(e)[:80]}"}


def run_hmm(df: pd.DataFrame) -> Dict:
    """HMM regime detector: market regime → regime-aware signal."""
    try:
        from src.models.hmm_regime import RegimeDetector
        detector = RegimeDetector(n_regimes=3, n_iter=200)
        detector.train(df)
        regime_name, confidence = detector.get_current_regime(df)

        # Regime → directional signal mapping
        recent_return = float(df["returns"].iloc[-1])
        recent_vol = float(df["returns"].rolling(10).std().iloc[-1])

        if regime_name == "GROWTH":
            signal = "LONG"
            confidence = min(confidence * 1.1, 1.0)  # Boost in growth regime
            reasoning = f"HMM regime: GROWTH | Recent return: {recent_return:.4f}"
        elif regime_name == "CRISIS":
            signal = "SHORT" if recent_return < 0 else "HOLD"
            confidence = confidence * 0.8  # More conservative in crisis
            reasoning = f"HMM regime: CRISIS | Vol: {recent_vol:.4f}"
        else:  # NORMAL
            signal = "LONG" if recent_return > 0 else "HOLD"
            reasoning = f"HMM regime: NORMAL | Return: {recent_return:.4f}"

        return {
            "signal": signal,
            "confidence": round(float(confidence), 3),
            "regime": regime_name,
            "reasoning": reasoning,
        }

    except Exception as e:
        logger.warning(f"HMM model error: {e}")
        return {"signal": "HOLD", "confidence": 0.0, "regime": "UNKNOWN", "reasoning": f"Error: {str(e)[:80]}"}


def run_lstm(df: pd.DataFrame) -> Dict:
    """LSTM temporal model: sequence-based price direction prediction."""
    try:
        # LSTM requires significant training time — use a lightweight proxy
        # that captures sequential momentum with exponential weighting
        closes = df["close"].values
        returns = df["returns"].values

        # Exponentially weighted momentum (approximates LSTM's temporal weighting)
        alpha = 0.15
        ew_return = returns[-1]
        for r in reversed(returns[-20:-1]):
            ew_return = alpha * ew_return + (1 - alpha) * r

        # Acceleration (2nd derivative)
        if len(returns) >= 5:
            accel = np.mean(np.diff(returns[-5:]))
        else:
            accel = 0.0

        # MACD-style signal
        ema_fast = pd.Series(closes).ewm(span=8).mean().iloc[-1]
        ema_slow = pd.Series(closes).ewm(span=21).mean().iloc[-1]
        macd = ema_fast - ema_slow

        # Macro Leading Indicators (DXY and US10Y)
        macro_adjustment = 0.0
        if "dxy_returns" in df.columns and "us10y_returns" in df.columns:
            # Gold is inversely correlated to both DXY and Treasury Yields
            dxy_momentum = df["dxy_returns"].iloc[-3:].sum() * 100
            yield_momentum = df["us10y_returns"].iloc[-3:].sum() * 100
            
            # If DXY spikes OR Yields spike -> Strong Bearish pressure for Gold
            macro_adjustment = (dxy_momentum + yield_momentum) * -0.3 
            
        # Combine signals
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

    except Exception as e:
        logger.warning(f"LSTM model error: {e}")
        return {"signal": "HOLD", "confidence": 0.0, "reasoning": f"Error: {str(e)[:80]}"}


def run_tft(df: pd.DataFrame) -> Dict:
    """TFT forecaster: multi-scale attention-based signal."""
    try:
        closes = df["close"].values
        returns = df["returns"].values
        highs = df["high"].values if "high" in df.columns else closes
        lows = df["low"].values if "low" in df.columns else closes

        # Multi-window RSI (approximates TFT's multi-horizon attention)
        def rsi(series, period=14):
            delta = np.diff(series)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            avg_gain = np.mean(gain[-period:]) + 1e-10
            avg_loss = np.mean(loss[-period:]) + 1e-10
            rs = avg_gain / avg_loss
            return 100 - 100 / (1 + rs)

        rsi_14 = rsi(closes, 14)
        rsi_7 = rsi(closes, 7)

        # ATR-normalized momentum
        atr = np.mean(np.abs(highs[-14:] - lows[-14:]))
        momentum_14 = (closes[-1] - closes[-14]) / (atr + 1e-8)

        # Bollinger band position
        bb_mean = np.mean(closes[-20:])
        bb_std = np.std(closes[-20:])
        bb_pos = (closes[-1] - bb_mean) / (2 * bb_std + 1e-8)  # -1 to 1

        # TFT attention-inspired weighting across time scales
        short_signal = np.sign(rsi_7 - 50) * (abs(rsi_7 - 50) / 50)
        long_signal = np.sign(rsi_14 - 50) * (abs(rsi_14 - 50) / 50)
        trend_signal = np.sign(momentum_14) * min(abs(momentum_14) / 5, 1.0)

        combined = short_signal * 0.3 + long_signal * 0.4 + trend_signal * 0.3
        # Contrarian adjustment from BB position
        combined -= bb_pos * 0.15
        
        # TFT Macro Attention: Yield & DXY Curve Inversion
        macro_reasoning = ""
        if "dxy_returns" in df.columns and "us10y_returns" in df.columns:
            dxy_roc = df["dxy_returns"].iloc[-5:].mean() * 1000
            yield_roc = df["us10y_returns"].iloc[-5:].mean() * 1000
            
            if dxy_roc > 1.5 or yield_roc > 1.5:
                combined -= 0.4 # Severe bearish override
                macro_reasoning = f" (MACRO FEAR: DXY/US10Y Spiking)"
            elif dxy_roc < -1.5 or yield_roc < -1.5:
                combined += 0.4 # Severe bullish override
                macro_reasoning = f" (MACRO GREED: DXY/US10Y Dropping)"

        confidence = min(abs(combined) * 0.9 + 0.25, 0.94)

        if combined > 0.2:
            signal = "LONG"
        elif combined < -0.2:
            signal = "SHORT"
        else:
            signal = "HOLD"

        return {
            "signal": signal,
            "confidence": round(float(confidence), 3),
            "reasoning": f"TFT-proxy: RSI14={rsi_14:.1f}, RSI7={rsi_7:.1f}, BB_pos={bb_pos:.2f}, score={combined:.3f}{macro_reasoning}",
        }

    except Exception as e:
        logger.warning(f"TFT model error: {e}")
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
            if sma10 > sma30 * 1.001:
                votes.append(1)
                reasons.append(f"SMA10>{sma30:.0f}")
            elif sma10 < sma30 * 0.999:
                votes.append(-1)
                reasons.append(f"SMA10<{sma30:.0f}")
            else:
                votes.append(0)

        # Rule 2: Momentum rule (evolved: 5-day return threshold)
        if len(returns) >= 5:
            mom5 = np.sum(returns[-5:])
            if mom5 > 0.008:
                votes.append(1)
                reasons.append(f"Mom5d=+{mom5:.3f}")
            elif mom5 < -0.008:
                votes.append(-1)
                reasons.append(f"Mom5d={mom5:.3f}")
            else:
                votes.append(0)

        # Rule 3: Volume-weighted return (evolved)
        if "volume" in df.columns and len(df) >= 10:
            recent = df.iloc[-10:]
            vwap_ret = np.average(recent["returns"], weights=recent["volume"] + 1)
            if vwap_ret > 0.001:
                votes.append(1)
                reasons.append(f"VWAP_ret=+{vwap_ret:.4f}")
            elif vwap_ret < -0.001:
                votes.append(-1)
                reasons.append(f"VWAP_ret={vwap_ret:.4f}")
            else:
                votes.append(0)

        # Rule 4: High-Low range expansion (volatility breakout)
        if len(closes) >= 20:
            range_now = df["high"].iloc[-1] - df["low"].iloc[-1] if "high" in df.columns else 0
            range_avg = (df["high"] - df["low"]).iloc[-20:].mean() if "high" in df.columns else 1
            if range_now > range_avg * 1.3 and returns[-1] > 0:
                votes.append(1)
                reasons.append("breakout_up")
            elif range_now > range_avg * 1.3 and returns[-1] < 0:
                votes.append(-1)
                reasons.append("breakout_dn")
            else:
                votes.append(0)

        # Rule 5: Recent reversal detection
        if len(returns) >= 3:
            if returns[-3] < -0.005 and returns[-2] < -0.003 and returns[-1] > 0.002:
                votes.append(1)
                reasons.append("reversal_long")
            elif returns[-3] > 0.005 and returns[-2] > 0.003 and returns[-1] < -0.002:
                votes.append(-1)
                reasons.append("reversal_short")
            else:
                votes.append(0)

        if not votes:
            return {"signal": "HOLD", "confidence": 0.0, "reasoning": "No rules fired"}

        score = np.mean(votes)
        # Confidence = agreement among rules
        agreement = abs(score)
        confidence = min(agreement * 0.85 + 0.20, 0.90)

        if score > 0.2:
            signal = "LONG"
        elif score < -0.2:
            signal = "SHORT"
        else:
            signal = "HOLD"

        return {
            "signal": signal,
            "confidence": round(float(confidence), 3),
            "reasoning": f"Genetic ({len([v for v in votes if v != 0])}/{len(votes)} rules): " + ", ".join(reasons[:3]),
        }

    except Exception as e:
        logger.warning(f"Genetic model error: {e}")
        return {"signal": "HOLD", "confidence": 0.0, "reasoning": f"Error: {str(e)[:80]}"}


def run_ensemble(individual_signals: Dict[str, Dict], regime: str = "NORMAL") -> Dict:
    """
    Ensemble meta-learner: weighted aggregation of all 5 individual models.
    Dynamic weighting based on current market regime.
    """
    try:
        # Base weights
        weights = {
            "wavelet": 0.10,
            "hmm": 0.10,
            "lstm": 0.15,
            "tft": 0.20,
            "genetic": 0.20,
            "nlp": 0.25, # NLP gets high weight for macro edge
        }
        
        # Regime-Conditioned Dynamic Weighting
        if regime in ("HIGH_VOLATILITY", "CRASH"):
            # Decrease trend-following, increase mean-reversion and NLP
            weights["wavelet"] = 0.25
            weights["hmm"] = 0.20
            weights["tft"] = 0.05
            weights["lstm"] = 0.05
            weights["genetic"] = 0.15
            weights["nlp"] = 0.30
        elif regime in ("LOW_VOLATILITY", "TRENDING"):
            # Increase deep learning / trend models
            weights["tft"] = 0.25
            weights["lstm"] = 0.25
            weights["genetic"] = 0.15
            weights["nlp"] = 0.15
            weights["wavelet"] = 0.10
            weights["hmm"] = 0.10

        signal_scores = {"LONG": 0.0, "SHORT": 0.0, "HOLD": 0.0}
        total_weight = 0.0

        for model, w in weights.items():
            sig = individual_signals.get(model, {})
            s = sig.get("signal", "HOLD")
            c = float(sig.get("confidence", 0.0))
            signal_scores[s] += w * c
            total_weight += w

        # Normalize
        if total_weight > 0:
            for k in signal_scores:
                signal_scores[k] /= total_weight

        # Pick best signal
        best = max(signal_scores, key=lambda k: signal_scores[k])
        best_score = signal_scores[best]

        # Apply threshold: need at least 0.25 weighted confidence to act
        if best_score < 0.25 or best == "HOLD":
            final_signal = "HOLD"
        else:
            final_signal = best

        confidence = min(best_score * 1.2, 0.95)  # Slight boost for ensemble

        longs = sum(1 for m in weights if individual_signals.get(m, {}).get("signal") == "LONG")
        shorts = sum(1 for m in weights if individual_signals.get(m, {}).get("signal") == "SHORT")

        return {
            "signal": final_signal,
            "confidence": round(float(confidence), 3),
            "reasoning": f"Ensemble ({longs}L/{shorts}S/{len(weights)-longs-shorts}H): scores={signal_scores}",
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

    def stop(self):
        """Signal the loop to stop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    async def run(self):
        """Main inference loop — runs until stopped."""
        self._running = True
        logger.info(f"Live inference loop started (interval={self.interval_seconds}s)")

        while self._running:
            try:
                await self._run_cycle()
                self.iteration += 1
                self.last_run = datetime.now()
                self.last_error = None
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
        df = await asyncio.get_event_loop().run_in_executor(
            None, fetch_live_gold_data, "5d", "15m"
        )

        if df is None or df.empty or len(df) < 35:
            logger.warning("Skipping inference cycle: insufficient gold data")
            self.consecutive_failures += 1
            if self.consecutive_failures >= 3 and self.engine and self.engine.status == "RUNNING":
                logger.critical("Data feed down! Triggering GRACEFUL DEGRADATION -> HALTING TRADING!")
                # Liquidate open positions
                if self.engine.current_position:
                    self.engine._close_position(datetime.now(), CURRENT_GOLD_PRICE)
                self.engine.stop()
            return

        # Reset failures on success
        self.consecutive_failures = 0

        # Update current price
        CURRENT_GOLD_PRICE = float(df["close"].iloc[-1])
        LAST_PRICE_UPDATE = datetime.now()
        current_price = CURRENT_GOLD_PRICE

        logger.info(f"[Inference #{self.iteration}] Gold @ ${current_price:.2f} — running 6 models...")

        # 2. Run individual models (in executor to avoid blocking event loop)
        loop = asyncio.get_event_loop()

        wavelet_res = await loop.run_in_executor(None, run_wavelet, df)
        hmm_res = await loop.run_in_executor(None, run_hmm, df)
        lstm_res = await loop.run_in_executor(None, run_lstm, df)
        tft_res = await loop.run_in_executor(None, run_tft, df)
        genetic_res = await loop.run_in_executor(None, run_genetic, df)
        nlp_res = await loop.run_in_executor(None, run_nlp_sentiment, df)

        individual = {
            "wavelet": wavelet_res,
            "hmm": hmm_res,
            "lstm": lstm_res,
            "tft": tft_res,
            "genetic": genetic_res,
            "nlp": nlp_res,
        }

        # 3. Get Regime for Meta-Labeling
        regime = hmm_res.get("regime", "NORMAL")
        now_iso = datetime.now().isoformat()
        
        # Run ensemble synchronously with dynamic regime weights
        ensemble_res = run_ensemble(individual, regime)

        all_results = {**individual, "ensemble": ensemble_res}

        all_results = {**individual, "ensemble": ensemble_res}

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

            for model_name, res in all_results.items():
                try:
                    signal_val = res.get("signal", "HOLD")
                    confidence = float(res.get("confidence", 0.0))

                    # Only the ensemble model is allowed to execute actual trades!
                    # The other 5 individual models just register their status for the dashboard
                    # to prevent them from constantly whipsawing the single paper trading position.
                    if model_name == "ensemble" and signal_val in ("LONG", "SHORT") and confidence >= self.engine.config.min_confidence:
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
                        self.engine.process_signal(model_name, sig)
                    else:
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
            
            broadcast_payload = {
                "price": current_price,
                "regime": regime,
                "timestamp": now_iso,
                "macro": {
                    "dxy": dxy_val,
                    "us10y": us10y_val,
                    "rl_kelly": rl_params["kelly_multiplier"],
                    "rl_trailing": rl_params["trailing_stop_pct"],
                },
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

        # Log summary
        sig_summary = " | ".join(
            f"{m[:3].upper()}:{v['signal']}@{v['confidence']:.0%}"
            for m, v in all_results.items()
        )
        logger.info(f"  Signals: {sig_summary}")
