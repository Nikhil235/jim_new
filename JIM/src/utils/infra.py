"""Infrastructure health checks.
===============================

Provides basic connectivity tests for the Phase 1 infrastructure stack.
"""

import socket
import subprocess
from typing import Dict, Optional
from loguru import logger

from src.utils.config import get_config


def _check_tcp_port(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _command_available(command: str) -> bool:
    try:
        subprocess.run([command, "--version"], capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_stack(config: Optional[dict] = None) -> Dict[str, Dict[str, Optional[str]]]:
    """Check connectivity for infrastructure services."""
    config = config or get_config()
    checks = {}

    checks["docker-compose"] = {
        "required": "yes",
        "available": "yes" if _command_available("docker-compose") or _command_available("docker") else "no",
        "details": "docker-compose or docker CLI available",
    }

    questdb = config.get("database", {}).get("questdb", {})
    checks["questdb"] = {
        "required": "yes",
        "available": "yes" if _check_tcp_port(questdb.get("host", "localhost"), questdb.get("port", 9009)) else "no",
        "details": f"{questdb.get('host', 'localhost')}:{questdb.get('port', 9009)}",
    }

    redis = config.get("database", {}).get("redis", {})
    checks["redis"] = {
        "required": "yes",
        "available": "yes" if _check_tcp_port(redis.get("host", "localhost"), redis.get("port", 6379)) else "no",
        "details": f"{redis.get('host', 'localhost')}:{redis.get('port', 6379)}",
    }

    minio = config.get("database", {}).get("minio", {})
    checks["minio"] = {
        "required": "yes",
        "available": "yes" if _check_tcp_port(minio.get("host", "localhost"), minio.get("port", 9100)) else "no",
        "details": f"{minio.get('host', 'localhost')}:{minio.get('port', 9100)}",
    }

    mlflow_uri = config.get("mlflow", {}).get("tracking_uri") or config.get("project", {}).get("mlflow_tracking_uri")
    if mlflow_uri and mlflow_uri.startswith("http"):
        checks["mlflow"] = {
            "required": "yes",
            "available": "yes" if _check_tcp_port("localhost", 5000) else "no",
            "details": mlflow_uri,
        }
    else:
        checks["mlflow"] = {
            "required": "optional",
            "available": "unknown",
            "details": "No MLflow URI configured",
        }

    monitoring = config.get("monitoring", {})
    prometheus_port = monitoring.get("prometheus", {}).get("port", 9090)
    grafana_port = monitoring.get("grafana", {}).get("port", 3000)

    checks["prometheus"] = {
        "required": "yes",
        "available": "yes" if _check_tcp_port("localhost", prometheus_port) else "no",
        "details": f"localhost:{prometheus_port}",
    }

    checks["grafana"] = {
        "required": "yes",
        "available": "yes" if _check_tcp_port("localhost", grafana_port) else "no",
        "details": f"localhost:{grafana_port}",
    }

    return checks


def print_stack_summary(checks: Dict[str, Dict[str, Optional[str]]]) -> None:
    """Print a human-readable summary of infrastructure checks."""
    logger.info("Infrastructure health summary:")
    for service, result in checks.items():
        logger.info(
            f"  - {service}: required={result.get('required')} "
            f"available={result.get('available')} details={result.get('details')}"
        )
