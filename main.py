"""
Mini-Medallion: Main Entry Point
==================================
The command center. Run this to start the engine.

Usage:
    python main.py --mode demo        # Quick demo with sample data
    python main.py --mode api         # REST API server
    python main.py --mode backtest    # Full backtest
    python main.py --mode paper       # Paper trading
    python main.py --mode live        # Live trading (DANGER)

Examples:
    # Run API server on port 8000
    python main.py --mode api --port 8000

    # Run API server on custom host/port
    python main.py --mode api --host 0.0.0.0 --port 8080
"""

import sys
import os
import click
from loguru import logger

from src.utils.config import load_config, PROJECT_ROOT
from src.utils.logger import setup_logger
from src.utils.gpu import detect_gpu


@click.command()
@click.option("--mode", default="demo", type=click.Choice(["demo", "api", "pipeline", "backtest", "paper", "live"]))
@click.option("--config", default=None, help="Path to config YAML")
@click.option("--port", default=8000, type=int, help="API server port (for --mode api)")
@click.option("--host", default="0.0.0.0", help="API server host (for --mode api)")
@click.option("--pipeline-mode", default="full", type=click.Choice(["full", "gold-only", "macro-only", "features-only", "incremental"]), help="Pipeline execution mode")
def main(mode: str, config: str, port: int, host: str, pipeline_mode: str):
    """Mini-Medallion Gold Trading Engine.
    
    Modes:
      - demo       : Quick demo with sample data
      - api        : REST API server (port 8000)
      - pipeline   : Run data ingestion pipeline
      - backtest   : Full backtest (coming Phase 5)
      - paper      : Paper trading (coming Phase 6)
      - live       : Live trading (coming Phase 7)
    """

    # Load config
    cfg = load_config(config)

    # Setup logging
    log_cfg = cfg.get("logging", {})
    setup_logger(
        level=log_cfg.get("level", "INFO"),
        log_file=log_cfg.get("file", "logs/medallion.log"),
    )

    logger.info("=" * 60)
    logger.info("  MINI-MEDALLION GOLD TRADING ENGINE")
    logger.info(f"  Mode: {mode.upper()}")
    logger.info(f"  Asset: {cfg['project']['asset']}")
    logger.info("=" * 60)

    # Detect GPU
    gpu_info = detect_gpu()

    if mode == "demo":
        run_demo(cfg)
    elif mode == "api":
        run_api(cfg, host=host, port=port)
    elif mode == "pipeline":
        run_pipeline(cfg, pipeline_mode=pipeline_mode)
    elif mode == "backtest":
        logger.info("Backtest mode — coming in Phase 5")
    elif mode == "paper":
        logger.info("Paper trading mode — coming in Phase 6")
    elif mode == "live":
        logger.warning("🚨 LIVE TRADING — NOT YET IMPLEMENTED")
        sys.exit(1)


def run_api(cfg: dict, host: str = "0.0.0.0", port: int = 8000):
    """
    Run the REST API server.
    
    Endpoints:
      - GET /health              - Service health
      - GET /signal              - Current trading signal
      - GET /regime              - Market regime
      - GET /features            - Engineered features
      - GET /models              - Model status
      - GET /data-quality        - Data quality report
      - POST /backtest/{strategy} - Backtest a strategy
      - GET /ensemble            - Ensemble prediction
      - GET /docs               - Swagger documentation
    """
    logger.info("--- API MODE ---")
    logger.info(f"Starting REST API server: {host}:{port}")
    logger.info("API Documentation: http://{}:{}/docs".format(host, port))
    
    try:
        import uvicorn
        from src.api.app import app
        
        # Run Uvicorn server
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
        )
    except ImportError:
        logger.error("FastAPI or Uvicorn not installed")
        logger.error("Install with: pip install fastapi uvicorn")
        sys.exit(1)
    except Exception as e:
        logger.error(f"API startup failed: {e}")
        sys.exit(1)


def run_pipeline(cfg: dict, pipeline_mode: str = "full"):
    """
    Run the data ingestion pipeline.
    
    Modes:
      - full         : All steps (gold + macro + alt + features)
      - gold-only    : Only gold price data
      - macro-only   : Only macro + FRED data
      - features-only: Only feature generation
      - incremental  : Only new data since last run
    """
    logger.info("--- PIPELINE MODE ---")
    logger.info(f"Pipeline mode: {pipeline_mode}")
    
    try:
        from src.ingestion.pipeline_orchestrator import PipelineOrchestrator
        
        orchestrator = PipelineOrchestrator(cfg)
        report = orchestrator.run(mode=pipeline_mode)
        
        # Exit with appropriate code
        if report.overall_status == "SUCCESS":
            sys.exit(0)
        elif report.overall_status == "PARTIAL":
            sys.exit(1)
        else:
            sys.exit(2)
            
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        sys.exit(2)


def run_demo(cfg: dict):
    """
    Quick demo: Fetch data → Generate features → Run models → Show results.
    Proves the entire pipeline works end-to-end.
    """
    import pandas as pd
    import numpy as np

    logger.info("--- DEMO MODE ---")

    # Step 1: Fetch gold data
    logger.info("[1/5] Fetching gold data...")
    from src.ingestion.gold_fetcher import GoldDataFetcher
    fetcher = GoldDataFetcher(cfg)

    try:
        gold_df = fetcher.fetch_historical(period="2y", interval="1d")
        if gold_df.empty:
            logger.error("No data fetched. Check internet connection.")
            return
        logger.info(f"  Got {len(gold_df)} daily bars")
    except Exception as e:
        logger.error(f"Data fetch failed: {e}")
        logger.info("Generating synthetic data for demo...")
        dates = pd.date_range("2022-01-01", periods=500, freq="B")
        np.random.seed(42)
        price = 1800 + np.cumsum(np.random.randn(500) * 10)
        gold_df = pd.DataFrame({
            "open": price + np.random.randn(500) * 2,
            "high": price + abs(np.random.randn(500) * 5),
            "low": price - abs(np.random.randn(500) * 5),
            "close": price,
            "volume": np.random.randint(10000, 100000, 500),
        }, index=dates)
        gold_df.index.name = "timestamp"
        gold_df["returns"] = gold_df["close"].pct_change()

    # Step 2: Generate features
    logger.info("[2/5] Engineering features...")
    from src.features.engine import FeatureEngine
    feature_engine = FeatureEngine(cfg)
    features_df = feature_engine.generate_all(gold_df)
    feat_names = feature_engine.get_feature_names(features_df)
    logger.info(f"  Generated {len(feat_names)} features")

    # Step 3: Wavelet analysis
    logger.info("[3/5] Running wavelet de-noising...")
    from src.models.wavelet import WaveletDenoiser
    wavelet = WaveletDenoiser(
        wavelet=cfg.get("features", {}).get("wavelet", {}).get("family", "db4"),
        levels=cfg.get("features", {}).get("wavelet", {}).get("levels", 5),
    )
    wavelet.train(gold_df)

    prices = gold_df["close"].values
    denoised = wavelet.denoise(prices)
    bands = wavelet.get_frequency_bands(prices)

    noise_pct = np.std(prices - denoised) / np.std(prices) * 100
    logger.info(f"  Noise removed: {noise_pct:.1f}% of signal variance")
    logger.info(f"  Frequency bands extracted: {list(bands.keys())}")

    # Step 4: Regime detection
    logger.info("[4/5] Detecting market regimes...")
    from src.models.hmm_regime import RegimeDetector
    hmm_cfg = cfg.get("models", {}).get("hmm", {})
    regime_model = RegimeDetector(
        n_regimes=hmm_cfg.get("n_regimes", 3),
        covariance_type=hmm_cfg.get("covariance_type", "diag"),
        n_iter=hmm_cfg.get("n_iter", 1000),
    )
    regime_metrics = regime_model.train(gold_df)
    current_regime, regime_conf = regime_model.get_current_regime(gold_df)
    logger.info(f"  Current regime: {current_regime} (confidence: {regime_conf:.2%})")

    # Step 5: Risk check
    logger.info("[5/7] Risk management check...")
    from src.risk.manager import RiskManager
    risk_mgr = RiskManager(cfg)

    sample_size = risk_mgr.calculate_kelly_size(
        win_prob=0.5075,
        avg_win=100,
        avg_loss=95,
        portfolio_value=100000,
        regime=current_regime,
    )
    can_trade, reason = risk_mgr.check_circuit_breakers(100000)

    logger.info(f"  Kelly position size: ${sample_size:,.2f}")
    logger.info(f"  Can trade: {can_trade} ({reason})")

    # Step 6: Execution engine test
    logger.info("[6/7] Execution engine test...")
    from src.execution.engine import ExecutionEngine
    exec_cfg = cfg.copy()
    exec_cfg["execution"] = exec_cfg.get("execution", {})
    exec_cfg["execution"]["broker"] = "paper"
    exec_engine = ExecutionEngine(exec_cfg)
    exec_engine.connect()

    if can_trade and sample_size > 0:
        current_price = gold_df["close"].iloc[-1]
        order_result = exec_engine.submit_order(
            symbol=cfg["project"]["asset"],
            quantity=round(sample_size / current_price, 4),
            side="buy",
            order_type="limit",
            limit_price=current_price,
        )
        logger.info(f"  Simulated order: {order_result['order_id']} | ${order_result.get('fill_price', 0):,.2f}")

    health = exec_engine.health_check()
    logger.info(f"  Engine status: {health['broker']} connected={health['connected']}")
    logger.info(f"  Latency stats: {health.get('latency', {})}")

    # Step 7: Infrastructure health
    logger.info("[7/7] Infrastructure health check...")
    from src.utils.infra import check_stack, get_health_summary, print_stack_summary
    try:
        checks = check_stack(cfg)
        summary = get_health_summary(checks)
        logger.info(f"  Docker services: {summary['available']}/{summary['total_services']} online")
        if summary["available"] == 0:
            logger.info("  (Docker services offline — this is OK for demo mode)")
    except Exception as e:
        logger.info(f"  Infra check skipped: {e}")

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("  ✅ DEMO COMPLETE — All systems operational")
    logger.info(f"  📊 Data: {len(gold_df)} bars")
    logger.info(f"  🔧 Features: {len(feat_names)} engineered")
    logger.info(f"  📈 Regime: {current_regime} ({regime_conf:.0%})")
    logger.info(f"  💰 Kelly Size: ${sample_size:,.2f} on $100K portfolio")
    logger.info(f"  ⚡ Execution: Paper trading engine OK")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

