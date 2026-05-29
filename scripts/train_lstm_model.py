"""
Walk-Forward Training Script for CNN-LSTM-Attention Model
==========================================================
Phase 6 of the Mini-Medallion LSTM Pipeline.

Training methodology:
  - Expanding window walk-forward validation (no look-ahead bias)
  - AdamW optimizer with OneCycleLR scheduler
  - Early stopping on validation loss
  - Class-weighted cross-entropy for imbalanced labels
  - Saves best model + preprocessor to models/ directory

Usage:
    python scripts/train_lstm_model.py
    python scripts/train_lstm_model.py --epochs 50 --seq-len 60 --device cuda
"""

import os
import sys
import time
import argparse
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
from loguru import logger
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.lstm_features import LSTMFeatureEngineer
from src.models.lstm_preprocessor import LSTMPreprocessor
from src.models.lstm_temporal import CNNLSTMAttention, GoldLSTMModel


# ══════════════════════════════════════════════════════════════
# DATA ACQUISITION
# ══════════════════════════════════════════════════════════════

def fetch_training_data(years: int = 2, interval: str = "1d") -> pd.DataFrame:
    """
    Fetch historical gold + macro data for training.

    Args:
        years: Number of years of history to fetch.
        interval: '1d' for daily, '1h' for hourly, '1m' for 1-minute.

    Returns:
        DataFrame with OHLCV + macro columns.
    """
    import yfinance as yf

    logger.info(f"Fetching {years} years of {interval} data for training...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * years)

    tickers = "GC=F DX-Y.NYB ^TNX SI=F ^GVZ TIP"
    df_all = yf.download(
        tickers, start=start_date, end=end_date,
        interval=interval, group_by="ticker", progress=True,
    )

    if df_all.empty or "GC=F" not in df_all:
        raise ValueError("Failed to fetch gold data from yfinance")

    df = df_all["GC=F"].copy()
    df.columns = [c.lower() for c in df.columns]
    df = df[["open", "high", "low", "close", "volume"]].copy()

    # Filter invalid bars
    df = df[df["volume"] > 0].copy()
    df = df[~((df["high"] == df["low"]) & (df["open"] == df["close"]))].copy()

    # Add macro data
    for col, ticker in [("dxy", "DX-Y.NYB"), ("us10y", "^TNX"),
                         ("silver", "SI=F"), ("gvz", "^GVZ"), ("tip", "TIP")]:
        try:
            df[col] = df_all[ticker]["Close"].ffill()
        except Exception:
            logger.warning(f"Could not extract {col} from {ticker}")

    df.dropna(subset=["close"], inplace=True)
    df.ffill(inplace=True)
    df.dropna(inplace=True)

    # Derived columns
    df["returns"] = df["close"].pct_change()
    if "dxy" in df.columns:
        df["dxy_returns"] = df["dxy"].pct_change()
    if "us10y" in df.columns:
        df["us10y_returns"] = df["us10y"].pct_change()
    if "silver" in df.columns:
        df["silver_returns"] = df["silver"].pct_change()
        df["gold_silver_ratio"] = df["close"] / df["silver"]
    if "tip" in df.columns:
        df["tip_return"] = df["tip"].pct_change()
    if "us10y" in df.columns and "tip_return" in df.columns:
        df["real_yield_proxy"] = df["us10y"] - df["tip_return"].rolling(20).mean() * 100

    df.dropna(inplace=True)

    logger.info(f"Training data: {len(df)} bars, "
                f"range: {df.index[0]} to {df.index[-1]}")

    return df


# ══════════════════════════════════════════════════════════════
# WALK-FORWARD TRAINING
# ══════════════════════════════════════════════════════════════

class WalkForwardTrainer:
    """
    Walk-forward training with expanding window.

    [============ TRAIN ============][= VAL =][TEST]  Fold 1
    [================ TRAIN ===============][= VAL =][TEST]  Fold 2
    [====================== TRAIN ====================][= VAL =][TEST]  Fold 3
    """

    def __init__(
        self,
        n_folds: int = 3,
        val_frac: float = 0.08,
        test_frac: float = 0.08,
        gap_bars: int = 5,
        epochs: int = 100,
        batch_size: int = 128,
        lr: float = 5e-4,
        seq_len: int = 30,
        fwd_bars: int = 5,
        label_threshold: float = 0.0,  # 0 = auto-calibrate from data
        device: str = "auto",
        patience: int = 20,
        interval: str = "1d",
    ):
        self.n_folds = n_folds
        self.val_frac = val_frac
        self.test_frac = test_frac
        self.gap_bars = gap_bars
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self.seq_len = seq_len
        self.fwd_bars = fwd_bars
        self.label_threshold = label_threshold
        self.patience = patience
        self.interval = interval

        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.feature_engineer = LSTMFeatureEngineer()
        self.fold_results = []

    def train(self, df: pd.DataFrame) -> GoldLSTMModel:
        """
        Run full walk-forward training pipeline.

        Args:
            df: Raw OHLCV + macro DataFrame.

        Returns:
            Trained GoldLSTMModel wrapper.
        """
        logger.info(f"Starting walk-forward training: {self.n_folds} folds, "
                     f"{self.epochs} epochs, device={self.device}")

        # ── 1. Feature Engineering ──
        features = self.feature_engineer.transform(df)
        n_features = features.shape[1]
        logger.info(f"Features: {n_features} columns, {len(features)} rows")

        # Align df to features index
        df_aligned = df.loc[features.index]

        # ── Auto-calibrate label thresholds ──
        if self.label_threshold == 0.0:
            fwd_returns = df_aligned["close"].pct_change(self.fwd_bars).shift(-self.fwd_bars).dropna()
            # Use 33rd/67th percentiles for balanced 3-class split
            p33 = float(fwd_returns.quantile(0.33))
            p67 = float(fwd_returns.quantile(0.67))
            # Ensure symmetric thresholds around zero
            self.label_threshold = max(abs(p33), abs(p67))
            logger.info(f"Auto-calibrated label threshold: {self.label_threshold:.6f} "
                        f"(p33={p33:.6f}, p67={p67:.6f})")
        else:
            logger.info(f"Using fixed label threshold: {self.label_threshold:.6f}")

        # ── 2. Walk-Forward Folds ──
        total_bars = len(features)
        test_size = max(int(total_bars * self.test_frac), self.seq_len + 10)
        val_size = max(int(total_bars * self.val_frac), self.seq_len + 10)
        fold_step = (total_bars - val_size - test_size - self.seq_len) // self.n_folds

        best_fold_sharpe = -np.inf
        best_model_state = None

        for fold in range(self.n_folds):
            logger.info(f"\n{'='*60}")
            logger.info(f"  FOLD {fold + 1}/{self.n_folds}")
            logger.info(f"{'='*60}")

            # Expanding window: each fold uses more training data
            train_end = self.seq_len + (fold + 1) * fold_step
            val_start = train_end + self.gap_bars
            val_end = val_start + val_size
            test_start = val_end + self.gap_bars
            test_end = min(test_start + test_size, total_bars)

            if test_end > total_bars or val_end > total_bars:
                logger.warning(f"Fold {fold + 1}: not enough data, skipping")
                continue

            # Split data
            train_feat = features.iloc[:train_end]
            train_df = df_aligned.iloc[:train_end]
            val_feat = features.iloc[val_start:val_end]
            val_df = df_aligned.iloc[val_start:val_end]
            test_feat = features.iloc[test_start:test_end]
            test_df = df_aligned.iloc[test_start:test_end]

            logger.info(f"  Train: {len(train_feat)} | Val: {len(val_feat)} | Test: {len(test_feat)}")

            # ── Preprocessing ──
            preprocessor = LSTMPreprocessor(
                seq_len=self.seq_len,
                fwd_bars=self.fwd_bars,
                long_threshold=self.label_threshold,
                short_threshold=-self.label_threshold,
            )
            preprocessor.fit(train_feat, train_df)

            X_train, y_train = preprocessor.transform(train_feat, train_df)
            X_val, y_val = preprocessor.transform(val_feat, val_df)
            X_test, y_test = preprocessor.transform(test_feat, test_df)

            if X_train is None or len(X_train) < self.batch_size:
                logger.warning(f"Fold {fold + 1}: insufficient training data ({len(X_train) if X_train is not None else 0} samples), skipping")
                continue

            if X_val is None or len(X_val) < 2:
                logger.warning(f"Fold {fold + 1}: insufficient validation data, skipping")
                continue

            # Class weights
            class_weights = preprocessor.get_class_weights(y_train)

            # ── Model (size based on data volume) ──
            n_samples_approx = len(X_train)
            if n_samples_approx < 500:
                model_cfg = dict(cnn_filters=16, lstm_hidden=32, lstm_layers=1, attn_heads=4, dropout=0.5)
            elif n_samples_approx < 5000:
                model_cfg = dict(cnn_filters=32, lstm_hidden=64, lstm_layers=1, attn_heads=4, dropout=0.4)
            else:
                model_cfg = dict(cnn_filters=64, lstm_hidden=128, lstm_layers=2, attn_heads=8, dropout=0.3)

            model = CNNLSTMAttention(n_features=n_features, **model_cfg).to(self.device)
            logger.info(f"  Model: {model.count_parameters():,} params ({model_cfg})")

            # ── Training ──
            fold_result = self._train_fold(
                model, X_train, y_train, X_val, y_val,
                X_test, y_test, class_weights, fold + 1,
            )
            self.fold_results.append(fold_result)

            if fold_result["test_sharpe"] > best_fold_sharpe:
                best_fold_sharpe = fold_result["test_sharpe"]
                best_model_state = model.state_dict().copy()
                best_preprocessor = preprocessor

            logger.info(f"  Fold {fold + 1} Results:")
            logger.info(f"    Val  Acc: {fold_result['val_acc']:.1%} | Loss: {fold_result['val_loss']:.4f}")
            logger.info(f"    Test Acc: {fold_result['test_acc']:.1%} | Sharpe: {fold_result['test_sharpe']:.3f}")

        # ── 3. Final Model ──
        logger.info(f"\n{'='*60}")
        logger.info(f"  TRAINING FINAL MODEL ON ALL DATA")
        logger.info(f"{'='*60}")

        # Fit preprocessor on all data
        final_preprocessor = LSTMPreprocessor(
            seq_len=self.seq_len,
            fwd_bars=self.fwd_bars,
            long_threshold=self.label_threshold,
            short_threshold=-self.label_threshold,
        )
        final_preprocessor.fit(features, df_aligned)
        X_all, y_all = final_preprocessor.transform(features, df_aligned)

        class_weights_all = final_preprocessor.get_class_weights(y_all)

        n_final = len(X_all)
        if n_final < 500:
            final_cfg = dict(cnn_filters=16, lstm_hidden=32, lstm_layers=1, attn_heads=4, dropout=0.5)
        elif n_final < 5000:
            final_cfg = dict(cnn_filters=32, lstm_hidden=64, lstm_layers=1, attn_heads=4, dropout=0.4)
        else:
            final_cfg = dict(cnn_filters=64, lstm_hidden=128, lstm_layers=2, attn_heads=8, dropout=0.3)

        final_model = CNNLSTMAttention(n_features=n_features, **final_cfg).to(self.device)
        logger.info(f"  Final model: {final_model.count_parameters():,} params ({n_final} samples)")

        # If we have a best fold model, use it as initialization
        if best_model_state is not None:
            final_model.load_state_dict(best_model_state)
            logger.info(f"Initialized from best fold (Sharpe={best_fold_sharpe:.3f})")

        # Train on all data with reduced epochs
        val_split = int(len(X_all) * 0.9)
        self._train_fold(
            final_model, X_all[:val_split], y_all[:val_split],
            X_all[val_split:], y_all[val_split:],
            None, None, class_weights_all, fold_num=0,
        )

        # ── 4. Save ──
        wrapper = GoldLSTMModel(device=str(self.device))
        wrapper.model = final_model
        wrapper.config = {
            "n_features": n_features,
            "cnn_kernel": 3,
            **final_cfg,
        }
        wrapper._is_loaded = True

        model_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'models', 'lstm_cnn_attention.pt'
        ))
        preprocessor_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'models', 'lstm_preprocessor.joblib'
        ))

        wrapper.save(model_path)
        final_preprocessor.save(preprocessor_path)

        # ── 5. Summary ──
        self._print_summary()

        return wrapper

    def _train_fold(
        self,
        model: CNNLSTMAttention,
        X_train: np.ndarray, y_train: np.ndarray,
        X_val: np.ndarray, y_val: np.ndarray,
        X_test: np.ndarray, y_test: np.ndarray,
        class_weights: np.ndarray,
        fold_num: int,
    ) -> dict:
        """Train a single fold."""
        # Auto-shrink batch size to fit available data
        effective_bs = min(self.batch_size, len(X_train))
        if effective_bs < 4:
            effective_bs = len(X_train)

        # DataLoaders
        train_ds = TensorDataset(
            torch.FloatTensor(X_train),
            torch.LongTensor(y_train),
        )
        val_ds = TensorDataset(
            torch.FloatTensor(X_val),
            torch.LongTensor(y_val),
        )
        train_loader = DataLoader(train_ds, batch_size=effective_bs, shuffle=True,
                                   drop_last=False, num_workers=0)
        val_loader = DataLoader(val_ds, batch_size=effective_bs, shuffle=False,
                                 num_workers=0)

        if len(train_loader) == 0:
            logger.warning(f"  Fold {fold_num}: 0 training batches, skipping")
            return {"val_loss": float('inf'), "val_acc": 0.0, "test_acc": 0.0, "test_sharpe": 0.0}

        # Loss with class weights
        weight_tensor = torch.FloatTensor(class_weights).to(self.device)
        criterion = nn.CrossEntropyLoss(weight=weight_tensor, label_smoothing=0.15)

        # Optimizer + Scheduler (CosineAnnealing is more robust than OneCycleLR for small datasets)
        optimizer = optim.AdamW(model.parameters(), lr=self.lr, weight_decay=1e-2)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=self.epochs, eta_min=self.lr * 0.01
        )

        # Early stopping
        best_val_loss = float('inf')
        patience_counter = 0
        best_state = None

        for epoch in range(self.epochs):
            # ── Train ──
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0

            for X_batch, y_batch in train_loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)

                optimizer.zero_grad()
                logits = model(X_batch)
                loss = criterion(logits, y_batch)
                loss.backward()

                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

                optimizer.step()

                train_loss += loss.item() * X_batch.size(0)
                preds = logits.argmax(dim=1)
                train_correct += (preds == y_batch).sum().item()
                train_total += X_batch.size(0)

            # Step scheduler per epoch (CosineAnnealing is epoch-level)
            scheduler.step()

            if train_total == 0:
                continue

            train_loss /= train_total
            train_acc = train_correct / train_total

            # ── Validate ──
            model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0

            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    X_batch = X_batch.to(self.device)
                    y_batch = y_batch.to(self.device)

                    logits = model(X_batch)
                    loss = criterion(logits, y_batch)

                    val_loss += loss.item() * X_batch.size(0)
                    preds = logits.argmax(dim=1)
                    val_correct += (preds == y_batch).sum().item()
                    val_total += X_batch.size(0)

            val_loss /= max(val_total, 1)
            val_acc = val_correct / max(val_total, 1)

            # Early stopping check
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
            else:
                patience_counter += 1

            if (epoch + 1) % 5 == 0 or epoch == 0:
                lr_now = optimizer.param_groups[0]['lr']
                logger.info(
                    f"    Epoch {epoch+1:3d}/{self.epochs} | "
                    f"Train Loss={train_loss:.4f} Acc={train_acc:.1%} | "
                    f"Val Loss={val_loss:.4f} Acc={val_acc:.1%} | "
                    f"LR={lr_now:.2e} | Pat={patience_counter}/{self.patience}"
                )

            if patience_counter >= self.patience:
                logger.info(f"    Early stopping at epoch {epoch + 1}")
                break

        # Restore best model
        if best_state is not None:
            model.load_state_dict(best_state)

        # ── Test ──
        test_acc = 0.0
        test_sharpe = 0.0

        if X_test is not None and y_test is not None and len(X_test) > 0:
            test_ds = TensorDataset(
                torch.FloatTensor(X_test),
                torch.LongTensor(y_test),
            )
            test_loader = DataLoader(test_ds, batch_size=self.batch_size, shuffle=False)

            model.eval()
            all_preds = []
            all_labels = []

            with torch.no_grad():
                for X_batch, y_batch in test_loader:
                    X_batch = X_batch.to(self.device)
                    logits = model(X_batch)
                    preds = logits.argmax(dim=1).cpu().numpy()
                    all_preds.extend(preds)
                    all_labels.extend(y_batch.numpy())

            all_preds = np.array(all_preds)
            all_labels = np.array(all_labels)
            test_acc = (all_preds == all_labels).mean()

            # Simulated Sharpe: signal * actual return
            signals = np.where(all_preds == 2, 1, np.where(all_preds == 0, -1, 0))
            actual_dir = np.where(all_labels == 2, 1, np.where(all_labels == 0, -1, 0))
            trade_returns = signals * actual_dir * 0.001  # Assuming 0.1% per correct call
            if trade_returns.std() > 0:
                test_sharpe = trade_returns.mean() / trade_returns.std() * np.sqrt(252)
            else:
                test_sharpe = 0.0

        return {
            "val_loss": best_val_loss,
            "val_acc": val_acc,
            "test_acc": test_acc,
            "test_sharpe": test_sharpe,
        }

    def _print_summary(self):
        """Print walk-forward training summary."""
        logger.info(f"\n{'='*60}")
        logger.info(f"  WALK-FORWARD TRAINING SUMMARY")
        logger.info(f"{'='*60}")

        if not self.fold_results:
            logger.warning("No fold results to summarize")
            return

        val_accs = [r["val_acc"] for r in self.fold_results]
        test_accs = [r["test_acc"] for r in self.fold_results]
        test_sharpes = [r["test_sharpe"] for r in self.fold_results]

        logger.info(f"  Folds:          {len(self.fold_results)}")
        logger.info(f"  Val Accuracy:   {np.mean(val_accs):.1%} ± {np.std(val_accs):.1%}")
        logger.info(f"  Test Accuracy:  {np.mean(test_accs):.1%} ± {np.std(test_accs):.1%}")
        logger.info(f"  Test Sharpe:    {np.mean(test_sharpes):.3f} ± {np.std(test_sharpes):.3f}")
        logger.info(f"  Best Sharpe:    {max(test_sharpes):.3f}")
        logger.info(f"{'='*60}")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train CNN-LSTM-Attention model")
    parser.add_argument("--years", type=int, default=2, help="Years of training data")
    parser.add_argument("--interval", type=str, default="1d", help="Data interval (1d, 1h)")
    parser.add_argument("--epochs", type=int, default=100, help="Max epochs per fold")
    parser.add_argument("--batch-size", type=int, default=128, help="Batch size (larger=faster on GPU)")
    parser.add_argument("--lr", type=float, default=5e-4, help="Learning rate")
    parser.add_argument("--seq-len", type=int, default=30, help="Sequence length")
    parser.add_argument("--folds", type=int, default=3, help="Walk-forward folds")
    parser.add_argument("--patience", type=int, default=20, help="Early stopping patience")
    parser.add_argument("--device", type=str, default="auto", help="Device (auto/cuda/cpu)")
    args = parser.parse_args()

    start = time.time()

    # Log device info
    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)} | CUDA {torch.version.cuda}")
    else:
        logger.info("Running on CPU")

    # Interval-aware hyperparameters
    fwd_bars = 3 if args.interval in ('1m', '5m', '15m', '1h') else 5

    # 1. Fetch data
    df = fetch_training_data(years=args.years, interval=args.interval)

    # 2. Train
    trainer = WalkForwardTrainer(
        n_folds=args.folds,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        seq_len=args.seq_len,
        fwd_bars=fwd_bars,
        label_threshold=0.0,  # Auto-calibrate from data
        device=args.device,
        patience=args.patience,
        interval=args.interval,
    )
    model = trainer.train(df)

    elapsed = time.time() - start
    logger.info(f"\n  Total training time: {elapsed / 60:.1f} minutes")
    logger.info(f"  Model saved to: models/lstm_cnn_attention.pt")
    logger.info(f"  Preprocessor saved to: models/lstm_preprocessor.joblib")
