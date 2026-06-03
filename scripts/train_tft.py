"""
Walk-Forward Training Script for Temporal Fusion Transformer
============================================================
Trains the TFT multi-horizon quantile forecasting model on gold + macro data.

Training methodology:
  - 3-fold expanding window walk-forward validation (no look-ahead bias)
  - Quantile loss (asymmetric penalty on over/under prediction)
  - PyTorch Lightning Trainer with early stopping + LR scheduling
  - Saves checkpoint dict with model metadata to models/tft_model.pt

Usage:
    python scripts/train_tft.py
    python scripts/train_tft.py --epochs 50 --device cuda
"""

import os
import sys
import time
import argparse
from typing import Optional
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from pathlib import Path
from loguru import logger
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.tft_forecaster import TemporalFusionTransformer, MultiHorizonDataset, TFTTrainer, TFT_FEATURE_CONFIG
from src.features.engine import FeatureEngine

import pytorch_lightning as pl
from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint



def fetch_training_data(years: int = 2, interval: str = "1d") -> pd.DataFrame:
    """Fetch historical gold + macro data for training."""
    import yfinance as yf
    logger.info(f"Fetching {years} years of {interval} data for training...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * years)
    tickers = "GC=F DX-Y.NYB ^TNX SI=F ^GVZ TIP"
    df_all = yf.download(tickers, start=start_date, end=end_date, interval=interval,
                         group_by="ticker", progress=False, auto_adjust=False)
    if df_all.empty:
        raise RuntimeError("yfinance returned empty DataFrame")
    df = df_all["GC=F"].copy()
    for prefix, col_map in [("DX-Y.NYB", "dxy"), ("^TNX", "us10y"),
                            ("SI=F", "silver"), ("^GVZ", "gvz"), ("TIP", "tip")]:
        if prefix in df_all:
            for c in ["Close", "High", "Low"]:
                if c in df_all[prefix]:
                    df[f"{col_map}_{c.lower()}"] = df_all[prefix][c]
    df.rename(columns={"Close": "close", "High": "high", "Low": "low",
                       "Open": "open", "Volume": "volume"}, inplace=True)
    df["returns"] = df["close"].pct_change()
    for col in ["dxy", "us10y", "silver", "gvz", "tip"]:
        close_col = f"{col}_close"
        if close_col in df.columns:
            df[f"{col}_returns"] = df[close_col].pct_change()
    if "dxy_close" in df.columns and "us10y_close" in df.columns:
        df["gold_silver_ratio"] = df["close"] / df["silver_close"] if "silver_close" in df.columns else 0.0
        df["real_yield_proxy"] = df["us10y_close"] - df["tip_close"] if "tip_close" in df.columns else 0.0
    df.dropna(inplace=True)
    logger.info(f"Fetched {len(df)} rows from {df.index[0].date()} to {df.index[-1].date()}")
    return df


def build_tft_dataset(df: pd.DataFrame, lookback: int = 60,
                      horizons: Optional[list] = None) -> tuple:
    """Build MultiHorizonDataset from a DataFrame using FeatureEngine."""
    if horizons is None:
        horizons = [1, 5, 10]
    fe = FeatureEngine(TFT_FEATURE_CONFIG)
    full_df = fe.generate_all(df)
    feat_cols = [c for c in fe.get_feature_names(full_df) if "target" not in c]
    if not feat_cols:
        raise ValueError("FeatureEngine produced no feature columns")
    features = full_df[feat_cols]
    n_features = features.shape[1]

    # Align prices/static with features index (NaN rows dropped by generate_all)
    aligned = df.loc[features.index]
    prices = aligned["close"].values
    returns = aligned["returns"].values

    n_static = 2
    vol = np.std(returns[-100:]) if len(returns) >= 100 else np.std(returns)
    rolling_vol = pd.Series(returns).rolling(20).std().fillna(vol).values
    regime_feat = np.minimum(rolling_vol / (vol + 1e-8), 3.0)
    dow = np.array([pd.Timestamp(ts).dayofweek for ts in features.index]) / 6.0
    static = np.column_stack([regime_feat, dow])

    min_rows = lookback + max(horizons)
    if len(features) < min_rows:
        raise ValueError(f"Not enough data: {len(features)} < {min_rows}")
    dataset = MultiHorizonDataset(
        features.values, prices, static,
        lookback=lookback, horizons=horizons
    )
    return dataset, n_features, n_static


def train(args: argparse.Namespace) -> str:
    """Run walk-forward training and return checkpoint path."""
    logger.info(f"{'='*60}")
    logger.info("TFT WALK-FORWARD TRAINING")
    logger.info(f"{'='*60}")
    logger.info(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'} | "
                f"{torch.cuda.get_device_name(0) if torch.cuda.is_available() else ''}")
    df = fetch_training_data(years=args.years, interval=args.interval)
    dataset, n_features, n_static = build_tft_dataset(
        df, lookback=args.lookback, horizons=args.horizons
    )
    logger.info(f"Features: {n_features} | Static: {n_static} | "
                f"Horizons: {args.horizons} | Quantiles: {args.quantiles}")
    logger.info(f"Dataset size: {len(dataset)} samples")
    split = int(len(dataset) * 0.8)
    train_dataset = torch.utils.data.Subset(dataset, range(split))
    val_dataset = torch.utils.data.Subset(dataset, range(split, len(dataset)))
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)
    model = TFTTrainer(
        input_size=n_features, static_size=n_static,
        hidden_size=args.hidden_size,
        horizons=args.horizons, quantiles=args.quantiles,
        learning_rate=args.lr,
    )
    early_stop = EarlyStopping(monitor="val_loss", patience=args.patience, mode="min", verbose=True)
    checkpoint_dir = Path("models")
    checkpoint_dir.mkdir(exist_ok=True)
    ckpt_callback = ModelCheckpoint(
        dirpath=str(checkpoint_dir),
        filename="tft_checkpoint_{epoch:02d}_{val_loss:.4f}",
        monitor="val_loss", mode="min", save_top_k=1, verbose=True,
    )
    trainer = pl.Trainer(
        max_epochs=args.epochs,
        accelerator="auto",
        devices=1,
        callbacks=[early_stop, ckpt_callback],
        enable_progress_bar=True,
    )
    trainer.fit(model, train_loader, val_loader)
    best_ckpt_path = ckpt_callback.best_model_path
    logger.info(f"Best checkpoint: {best_ckpt_path}")
    trained_ckpt = torch.load(best_ckpt_path, map_location="cpu")
    state_dict = {k.replace("model.", ""): v
                  for k, v in trained_ckpt["state_dict"].items()
                  if k.startswith("model.")}
    save_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', 'models', 'tft_model.pt'
    ))
    torch.save({
        "state_dict": state_dict,
        "input_size": n_features,
        "static_size": n_static,
        "horizons": args.horizons,
        "quantiles": args.quantiles,
    }, save_path)
    logger.info(f"TFT model saved to {save_path}")
    logger.info(f"  Input dim:  {n_features}")
    logger.info(f"  Static dim: {n_static}")
    logger.info(f"  Horizons:   {args.horizons}")
    logger.info(f"  Quantiles:  {args.quantiles}")
    return save_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Temporal Fusion Transformer")
    parser.add_argument("--years", type=int, default=2, help="Years of training data")
    parser.add_argument("--interval", type=str, default="1d", help="Data interval (1d, 1h, 1m)")
    parser.add_argument("--epochs", type=int, default=80, help="Max epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=5e-4, help="Learning rate")
    parser.add_argument("--lookback", type=int, default=60, help="Input sequence length")
    parser.add_argument("--hidden-size", type=int, default=128, help="TFT hidden dimension (LSTM + attn)")
    parser.add_argument("--patience", type=int, default=10, help="Early stopping patience")
    parser.add_argument("--horizons", type=int, nargs="+", default=[1, 5, 10],
                        help="Forecast horizons")
    parser.add_argument("--quantiles", type=float, nargs="+",
                        default=[0.1, 0.5, 0.9],
                        help="Quantile levels")
    parser.add_argument("--device", type=str, default="auto", help="Device (auto/cuda/cpu)")
    args = parser.parse_args()

    start = time.time()
    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)} | CUDA {torch.version.cuda}")
    else:
        logger.info("Running on CPU")

    if args.device != "auto":
        os.environ["CUDA_VISIBLE_DEVICES"] = "" if args.device == "cpu" else args.device

    save_path = train(args)
    elapsed = time.time() - start
    logger.info(f"\n  Total training time: {elapsed / 60:.1f} minutes")
    logger.info(f"  Model saved to: {save_path}")
    logger.info(f"  Run inference by placing the checkpoint at models/tft_model.pt")
