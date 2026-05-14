"""
GPU Helpers
===========
Detect GPU availability and provide fallback to CPU.
Follows the Simons principle: use maximum compute available.
"""

import os
import sys
import subprocess
from loguru import logger
from typing import Dict, Optional, List


def _detect_hardware_gpu_via_nvidiasmi() -> Dict:
    """
    Detect NVIDIA GPU hardware via nvidia-smi even when PyTorch CUDA is unavailable.
    Returns dict with 'detected' bool and 'names' list.
    """
    result = {"detected": False, "names": []}
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if proc.returncode == 0:
            names = [n.strip() for n in proc.stdout.strip().splitlines() if n.strip()]
            if names:
                result["detected"] = True
                result["names"] = names
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return result


def detect_gpu() -> Dict:
    """
    Detect available GPU resources (comprehensive).

    Returns:
        Dict with:
            - gpu_available: bool
            - device_count: int
            - device_names: List[str]
            - device_memory_gb: List[float] (total VRAM per GPU)
            - cuda_version: Optional[str]
            - cudnn_version: Optional[str]
            - rapids_available: bool
            - cupy_available: bool
            - cusignal_available: bool
            - compute_capability: List[str] (CUDA compute capability per GPU)
    """
    info = {
        "gpu_available": False,
        "device_count": 0,
        "device_names": [],
        "device_memory_gb": [],
        "cuda_version": None,
        "cudnn_version": None,
        "rapids_available": False,
        "cupy_available": False,
        "cusignal_available": False,
        "compute_capability": [],
        # Hardware detection (independent of PyTorch CUDA)
        "hardware_gpu_detected": False,
        "hardware_gpu_names": [],
    }

    # Check PyTorch CUDA
    try:
        import torch
        if torch.cuda.is_available():
            info["gpu_available"] = True
            info["device_count"] = torch.cuda.device_count()
            info["cuda_version"] = torch.version.cuda
            info["cudnn_version"] = torch.backends.cudnn.version() if hasattr(torch.backends.cudnn, "version") else None
            
            for i in range(info["device_count"]):
                info["device_names"].append(torch.cuda.get_device_name(i))
                # Get GPU memory in GB
                props = torch.cuda.get_device_properties(i)
                memory_gb = props.total_memory / 1e9
                info["device_memory_gb"].append(memory_gb)
                # Get compute capability
                info["compute_capability"].append(f"{props.major}.{props.minor}")
            
            logger.info(
                f"GPU detected: {info['device_count']} device(s) "
                f"({', '.join(info['device_names'])}) | "
                f"CUDA {info['cuda_version']} | cuDNN {info['cudnn_version']} | "
                f"Memory: {sum(info['device_memory_gb']):.1f}GB total"
            )
        else:
            logger.warning("PyTorch CUDA not available — falling back to CPU")
    except ImportError:
        logger.warning("PyTorch not installed")
    except Exception as e:
        logger.warning(f"GPU detection failed: {e}")

    # Always probe hardware via nvidia-smi (works even with CPU-only PyTorch)
    hw = _detect_hardware_gpu_via_nvidiasmi()
    info["hardware_gpu_detected"] = hw["detected"]
    info["hardware_gpu_names"] = hw["names"]
    if hw["detected"] and not info["gpu_available"]:
        logger.info(
            f"Hardware GPU detected via nvidia-smi: {', '.join(hw['names'])} "
            f"— but PyTorch is CPU-only. Install CUDA PyTorch to enable acceleration."
        )

    # Check RAPIDS
    try:
        import cudf
        info["rapids_available"] = True
        logger.info("RAPIDS cuDF available — GPU-accelerated DataFrames enabled")
    except ImportError:
        logger.debug("RAPIDS not available — using Pandas (CPU) fallback")

    # Check CuPy
    try:
        import cupy
        info["cupy_available"] = True
        logger.info("CuPy available — GPU-accelerated array operations enabled")
    except ImportError:
        logger.debug("CuPy not available — using NumPy (CPU) fallback")

    # Check cuSignal
    try:
        import cusignal
        info["cusignal_available"] = True
        logger.info("cuSignal available — GPU-accelerated signal processing enabled")
    except ImportError:
        logger.debug("cuSignal not available — using SciPy (CPU) fallback")

    return info


def print_gpu_summary(gpu_info: Optional[Dict] = None) -> None:
    """
    Print a formatted summary of GPU capabilities.
    
    Args:
        gpu_info: Dict from detect_gpu(). If None, calls detect_gpu() first.
    """
    if gpu_info is None:
        gpu_info = detect_gpu()
    
    logger.info("=" * 70)
    logger.info("GPU HARDWARE SUMMARY")
    logger.info("=" * 70)
    
    if not gpu_info["gpu_available"]:
        if gpu_info.get("hardware_gpu_detected"):
            hw_names = ', '.join(gpu_info['hardware_gpu_names'])
            logger.info(f"⚠ Hardware GPU detected: {hw_names}")
            logger.info("  But PyTorch is installed WITHOUT CUDA support (CPU-only build)")
            logger.info("  ➜ Fix: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128")
            logger.info("  RTX 50-series requires CUDA 12.8+ and PyTorch 2.7+")
        else:
            logger.info("❌ No GPU detected — running on CPU only")
            logger.info("   To enable GPU: install PyTorch with CUDA support")
            logger.info("   Command: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128")
    else:
        logger.info(f"✓ GPU Available: {gpu_info['device_count']} device(s)")
        logger.info(f"  CUDA Version: {gpu_info['cuda_version']}")
        logger.info(f"  cuDNN Version: {gpu_info['cudnn_version'] or 'N/A'}")
        
        for i, (name, memory, cc) in enumerate(zip(
            gpu_info["device_names"], 
            gpu_info["device_memory_gb"], 
            gpu_info["compute_capability"]
        )):
            logger.info(f"  Device {i}: {name} | {memory:.1f}GB | CC {cc}")
    
    logger.info("")
    logger.info("ACCELERATED LIBRARIES")
    logger.info("=" * 70)
    
    rapids = "✓ Available" if gpu_info["rapids_available"] else "✗ Not installed"
    logger.info(f"RAPIDS (cuDF/cuML): {rapids}")
    
    cupy = "✓ Available" if gpu_info["cupy_available"] else "✗ Not installed"
    logger.info(f"CuPy (GPU arrays): {cupy}")
    
    cusignal = "✓ Available" if gpu_info["cusignal_available"] else "✗ Not installed"
    logger.info(f"cuSignal (signal processing): {cusignal}")
    
    logger.info("=" * 70)


def get_dataframe_engine():
    """
    Get the best available DataFrame engine.

    Returns cuDF if GPU available, otherwise Pandas.
    """
    try:
        import cudf
        logger.debug("Using cuDF (GPU) as DataFrame engine")
        return cudf
    except ImportError:
        import pandas
        logger.debug("Using Pandas (CPU) as DataFrame engine")
        return pandas


def get_array_engine():
    """
    Get the best available array engine.

    Returns CuPy if GPU available, otherwise NumPy.
    """
    try:
        import cupy
        logger.debug("Using CuPy (GPU) as array engine")
        return cupy
    except ImportError:
        import numpy
        logger.debug("Using NumPy (CPU) as array engine")
        return numpy


def get_device():
    """Get the PyTorch device (cuda or cpu)."""
    try:
        import torch
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.debug(f"PyTorch device: {device}")
        return device
    except ImportError:
        logger.warning("PyTorch not installed, returning 'cpu'")
        return "cpu"


def log_gpu_memory():
    """Log current GPU memory usage."""
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                allocated = torch.cuda.memory_allocated(i) / 1e9
                reserved = torch.cuda.memory_reserved(i) / 1e9
                total = torch.cuda.get_device_properties(i).total_mem / 1e9
                logger.info(
                    f"GPU {i}: {allocated:.2f}GB allocated, "
                    f"{reserved:.2f}GB reserved, {total:.2f}GB total"
                )
    except ImportError:
        pass
