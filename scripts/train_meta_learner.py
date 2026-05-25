import os
import sys
import numpy as np
import pandas as pd
from loguru import logger
import joblib
from datetime import datetime, timedelta
import yfinance as yf
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.paper_trading.live_inference import run_wavelet, run_hmm, run_lstm, run_tft, run_genetic
from src.models.nlp_sentiment import run_nlp_sentiment

def fetch_historical_data(years: int = 2) -> pd.DataFrame:
    """Fetch historical daily data for training the meta-learner."""
    logger.info(f"Fetching {years} years of historical daily data...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * years)
    
    tickers = "GC=F DX-Y.NYB ^TNX SI=F ^GVZ TIP"
    df_all = yf.download(tickers, start=start_date, end=end_date, interval="1d", group_by="ticker", progress=False)
    
    if df_all.empty or "GC=F" not in df_all:
        raise ValueError("Failed to fetch historical data")

    df = df_all["GC=F"].copy()
    df.columns = [c.lower() for c in df.columns]
    df = df[["open", "high", "low", "close", "volume"]].copy()
    
    # Filter 0 volume
    df = df[df["volume"] > 0].copy()
    
    # Extract macro data
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
    logger.info(f"Fetched {len(df)} days of historical data.")
    return df

def generate_signals_and_labels(df: pd.DataFrame) -> tuple:
    """Run models to generate signals and create forward return labels."""
    logger.info("Generating signals and labels...")
    
    # Target label: forward 1-day return
    df["target_return"] = df["close"].pct_change().shift(-1)
    
    features = []
    labels = []
    
    # We need a rolling window to run models correctly, simulating live inference
    # Let's start from day 100 to have enough history for models (like LSTM proxy, HMM, etc.)
    start_idx = 100
    
    total_bars = len(df) - 1 # -1 because we shifted target_return
    
    for i in range(start_idx, total_bars):
        if i % 100 == 0:
            logger.info(f"Processing day {i}/{total_bars}")
            
        # Get historical slice up to current day
        current_df = pd.DataFrame(df.iloc[:i+1].copy())
        
        # Run individual models
        wavelet_res = run_wavelet(current_df)
        lstm_res = run_lstm(current_df)
        tft_res = run_tft(current_df)
        genetic_res = run_genetic(current_df)
        
        # Fast proxy for HMM regime to avoid 5-second retrain on every bar
        recent_return = float(current_df["returns"].iloc[-1])
        recent_vol = float(current_df["returns"].rolling(10).std().iloc[-1])
        
        if recent_vol < 0.005:
            regime = "GROWTH"
            hmm_sig = "LONG" if recent_return > -0.005 else "HOLD"
        elif recent_vol > 0.015:
            regime = "CRISIS"
            hmm_sig = "SHORT" if recent_return < -0.005 else "HOLD"
        else:
            regime = "NORMAL"
            hmm_sig = "LONG" if recent_return > 0.002 else ("SHORT" if recent_return < -0.002 else "HOLD")
            
        hmm_res = {"signal": hmm_sig, "confidence": 0.65, "regime": regime}
        
        # Fast proxy for NLP to avoid loading FinBERT model in loop
        nlp_res = {"signal": "HOLD", "confidence": 0.0, "regime": "NORMAL"}
        
        individual = {
            "wavelet": wavelet_res,
            "hmm": hmm_res,
            "lstm": lstm_res,
            "tft": tft_res,
            "genetic": genetic_res,
            "nlp": nlp_res,
        }
        
        # Build feature vector matching live_inference.py line 458
        regime = hmm_res.get("regime", "NORMAL")
        
        feature_vec = []
        for model in ["wavelet", "hmm", "lstm", "tft", "genetic", "nlp"]:
            sig = individual.get(model, {})
            direction = 1 if sig.get("signal") == "LONG" else (-1 if sig.get("signal") == "SHORT" else 0)
            feature_vec.append(direction * float(sig.get("confidence", 0.0)))
            
        feature_vec.append(1 if regime == "GROWTH" else (-1 if regime in ["CRISIS", "HIGH_VOLATILITY"] else 0))
        
        # Macro data
        dxy_mom = float(current_df["dxy_returns"].iloc[-3:].sum() * 100) if "dxy_returns" in current_df.columns else 0.0
        yield_mom = float(current_df["us10y_returns"].iloc[-3:].sum() * 100) if "us10y_returns" in current_df.columns else 0.0
        feature_vec.append(dxy_mom)
        feature_vec.append(yield_mom)
        
        features.append(feature_vec)
        
        # Target Label
        fwd_ret = df["target_return"].iloc[i]
        if fwd_ret > 0.001:   # > 0.1% return -> LONG
            labels.append(2)
        elif fwd_ret < -0.001: # < -0.1% return -> SHORT
            labels.append(0)
        else:                  # HOLD
            labels.append(1)

    return np.array(features), np.array(labels)

def train_meta_learner(X: np.ndarray, y: np.ndarray):
    """Train the RandomForest meta-learner with Walk-Forward CV."""
    logger.info("Training meta-learner with Walk-Forward CV...")
    
    # TimeSeriesSplit for Walk-Forward CV
    tscv = TimeSeriesSplit(n_splits=5, gap=20)
    
    fold_accuracies = []
    
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, y_train = X[train_idx], y[train_idx]
        X_test, y_test = X[test_idx], y[test_idx]
        
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        fold_accuracies.append(acc)
        
        logger.info(f"Fold {fold+1} Accuracy: {acc:.4f}")
    
    logger.info(f"Average CV Accuracy: {np.mean(fold_accuracies):.4f}")
    
    # Train final model on all data
    logger.info("Training final model on full dataset with Confidence Calibration...")
    from sklearn.calibration import CalibratedClassifierCV
    base_model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    final_model = CalibratedClassifierCV(base_model, method="isotonic", cv=5)
    final_model.fit(X, y)
    
    # Print training report
    y_pred_all = final_model.predict(X)
    logger.info(f"Final Model Training Accuracy: {accuracy_score(y, y_pred_all):.4f}")
    logger.info(f"\n{classification_report(y, y_pred_all, target_names=['SHORT', 'HOLD', 'LONG'])}")
    
    return final_model

if __name__ == "__main__":
    logger.info("Starting meta-learner training pipeline...")
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'models'), exist_ok=True)
    
    try:
        # 1. Fetch data
        df = fetch_historical_data(years=2)
        
        # 2. Generate signals and labels
        X, y = generate_signals_and_labels(df)
        logger.info(f"Generated {len(X)} training samples.")
        
        # 3. Train
        model = train_meta_learner(X, y)
        
        # 4. Save
        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models', 'meta_learner.joblib'))
        joblib.dump(model, model_path)
        logger.info(f"Meta-learner successfully saved to {model_path}")
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
