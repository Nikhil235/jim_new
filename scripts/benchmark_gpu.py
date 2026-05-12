"""
GPU Benchmark Script
====================
Benchmark cuDF vs Pandas performance on large tick data.
Validates GPU setup and provides performance metrics.

Usage:
    python scripts/benchmark_gpu.py --size 100 --iterations 3
"""

import time
import click
import numpy as np
from loguru import logger
from typing import Dict, Tuple

from src.utils.gpu import detect_gpu, print_gpu_summary


def generate_tick_data(n_rows: int) -> Dict:
    """Generate synthetic gold tick data."""
    np.random.seed(42)
    return {
        "timestamp": np.arange(n_rows, dtype=np.int64),
        "bid": 2000 + np.cumsum(np.random.randn(n_rows) * 0.5),
        "ask": 2000.5 + np.cumsum(np.random.randn(n_rows) * 0.5),
        "bid_size": np.random.uniform(1, 100, n_rows),
        "ask_size": np.random.uniform(1, 100, n_rows),
        "volume": np.random.uniform(10, 1000, n_rows),
    }


def benchmark_pandas(data: Dict, iterations: int = 3) -> Tuple[float, float]:
    """Benchmark Pandas operations on tick data."""
    import pandas as pd
    
    times = []
    for _ in range(iterations):
        # Create DataFrame
        df = pd.DataFrame(data)
        
        start = time.time()
        
        # Operations: rolling mean, volume-weighted mid, momentum
        df["mid_price"] = (df["bid"] + df["ask"]) / 2
        df["spread"] = df["ask"] - df["bid"]
        df["vwap"] = (df["bid"] * df["ask_size"] + df["ask"] * df["bid_size"]) / (df["bid_size"] + df["ask_size"])
        df["momentum_5"] = df["mid_price"].rolling(window=5).mean()
        df["momentum_20"] = df["mid_price"].rolling(window=20).mean()
        df["volume_sma"] = df["volume"].rolling(window=10).mean()
        
        # Aggregation
        groupby_result = df.groupby(pd.cut(df["timestamp"], bins=100)).agg({
            "volume": "sum",
            "mid_price": "mean",
            "spread": "mean"
        })
        
        elapsed = time.time() - start
        times.append(elapsed)
    
    mean_time = np.mean(times)
    std_time = np.std(times)
    return mean_time, std_time


def benchmark_cudf(data: Dict, iterations: int = 3) -> Tuple[float, float]:
    """Benchmark cuDF operations on tick data."""
    try:
        import cudf
    except ImportError:
        logger.error("cuDF not installed — cannot benchmark GPU")
        return None, None
    
    times = []
    for _ in range(iterations):
        # Create GPU DataFrame
        df = cudf.DataFrame(data)
        
        start = time.time()
        
        # Operations: rolling mean, volume-weighted mid, momentum
        df["mid_price"] = (df["bid"] + df["ask"]) / 2
        df["spread"] = df["ask"] - df["bid"]
        df["vwap"] = (df["bid"] * df["ask_size"] + df["ask"] * df["bid_size"]) / (df["bid_size"] + df["ask_size"])
        df["momentum_5"] = df["mid_price"].rolling(window=5).mean()
        df["momentum_20"] = df["mid_price"].rolling(window=20).mean()
        df["volume_sma"] = df["volume"].rolling(window=10).mean()
        
        # Aggregation (cuDF has different binning API)
        groupby_result = df.groupby(df["timestamp"] // (df["timestamp"].max() // 100)).agg({
            "volume": "sum",
            "mid_price": "mean",
            "spread": "mean"
        })
        
        elapsed = time.time() - start
        times.append(elapsed)
    
    mean_time = np.mean(times)
    std_time = np.std(times)
    return mean_time, std_time


@click.command()
@click.option("--size", default=10, type=int, help="Dataset size in millions of rows (default: 10M = ~1GB)")
@click.option("--iterations", default=3, type=int, help="Number of benchmark iterations (default: 3)")
@click.option("--gpu-only", is_flag=True, help="Skip CPU benchmark (faster, no baseline)")
def main(size: int, iterations: int, gpu_only: bool):
    """Benchmark GPU vs CPU performance on synthetic tick data."""
    
    logger.info("=" * 70)
    logger.info("MINI-MEDALLION GPU BENCHMARK")
    logger.info("=" * 70)
    logger.info("")
    
    # Detect GPU
    gpu_info = detect_gpu()
    print_gpu_summary(gpu_info)
    logger.info("")
    
    # Generate data
    n_rows = size * 1_000_000
    logger.info(f"Generating {n_rows:,} rows of synthetic tick data ({size}M rows)...")
    data = generate_tick_data(n_rows)
    logger.info(f"✓ Data generated ({n_rows:,} rows)")
    logger.info("")
    
    # Benchmark CPU
    if not gpu_only:
        logger.info("BENCHMARKING PANDAS (CPU)")
        logger.info("-" * 70)
        pandas_mean, pandas_std = benchmark_pandas(data, iterations)
        logger.info(f"Pandas: {pandas_mean:.3f}s ± {pandas_std:.3f}s (avg of {iterations} runs)")
        logger.info("")
    else:
        pandas_mean = None
    
    # Benchmark GPU
    if gpu_info["rapids_available"]:
        logger.info("BENCHMARKING CUDF (GPU)")
        logger.info("-" * 70)
        cudf_mean, cudf_std = benchmark_cudf(data, iterations)
        if cudf_mean is not None:
            logger.info(f"cuDF: {cudf_mean:.3f}s ± {cudf_std:.3f}s (avg of {iterations} runs)")
            
            if pandas_mean is not None:
                speedup = pandas_mean / cudf_mean
                logger.info("")
                logger.info("=" * 70)
                logger.info(f"SPEEDUP: {speedup:.1f}x faster on GPU")
                logger.info("=" * 70)
        else:
            logger.error("GPU benchmark failed")
    else:
        logger.warning("RAPIDS/cuDF not available — skipping GPU benchmark")
        logger.info("Install with: conda install -c rapidsai rapids=24.04")


if __name__ == "__main__":
    main()
