"""
Configuration Loader
====================
Loads YAML config with environment variable substitution.
Single source of truth — everything reads from configs/base.yaml.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel
from loguru import logger


# Project root = two levels up from this file (src/utils/config.py → project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class DatabaseConfig(BaseModel):
    """Database connection settings."""
    class QuestDB(BaseModel):
        host: str = "localhost"
        port: int = 9009
        http_port: int = 9000
        database: str = "medallion"

    class Redis(BaseModel):
        host: str = "localhost"
        port: int = 6379
        db: int = 0
        password: str = ""

    class MinIO(BaseModel):
        host: str = "localhost"
        port: int = 9100
        access_key: str = "minioadmin"
        secret_key: str = "minioadmin"
        bucket: str = "medallion-data"

    questdb: QuestDB = QuestDB()
    redis: Redis = Redis()
    minio: MinIO = MinIO()


class RiskConfig(BaseModel):
    """Risk management parameters."""
    class Kelly(BaseModel):
        fraction: float = 0.5
        max_position_pct: float = 0.05
        crisis_fraction: float = 0.25

    class CircuitBreakers(BaseModel):
        daily_loss_limit: float = 0.02
        drawdown_reduce: float = 0.05
        drawdown_stop: float = 0.10
        model_disagreement: float = 0.70
        max_latency_ms: int = 500

    class MetaLabel(BaseModel):
        confidence_threshold: float = 0.65
        model: str = "xgboost"

    kelly: Kelly = Kelly()
    circuit_breakers: CircuitBreakers = CircuitBreakers()
    meta_label: MetaLabel = MetaLabel()


def _substitute_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} with environment variable values."""
    pattern = re.compile(r'\$\{(\w+)\}')
    def replacer(match):
        var_name = match.group(1)
        env_val = os.environ.get(var_name, "")
        if not env_val:
            logger.warning(f"Environment variable {var_name} not set")
        return env_val
    return pattern.sub(replacer, value) if isinstance(value, str) else value


def _deep_substitute(obj: Any) -> Any:
    """Recursively substitute env vars in nested dicts/lists."""
    if isinstance(obj, dict):
        return {k: _deep_substitute(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_deep_substitute(item) for item in obj]
    elif isinstance(obj, str):
        return _substitute_env_vars(obj)
    return obj


def load_config(config_path: Optional[str] = None) -> dict:
    """
    Load configuration from YAML file with env var substitution.

    Args:
        config_path: Path to config file. Defaults to configs/base.yaml.

    Returns:
        Configuration dictionary with env vars resolved.
    """
    if config_path is None:
        config_path = PROJECT_ROOT / "configs" / "base.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Load .env file if it exists
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        logger.info(f"Loaded environment from {env_file}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Substitute environment variables
    config = _deep_substitute(config)

    logger.info(f"Configuration loaded from {config_path}")
    return config


def get_config() -> dict:
    """Get the global configuration (cached singleton)."""
    if not hasattr(get_config, "_cache"):
        get_config._cache = load_config()
    return get_config._cache


def get_section(section: str) -> dict:
    """Get a specific section from the config."""
    config = get_config()
    if section not in config:
        raise KeyError(f"Config section '{section}' not found")
    return config[section]
