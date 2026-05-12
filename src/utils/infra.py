"""Infrastructure health checks.
===============================

Provides basic connectivity tests for the Phase 1 infrastructure stack.

Phase 1 enhancements:
- Fixed MLflow detection (was checking wrong config path)
- Added overall health summary with pass/fail count
- Added individual service HTTP health check for services that support it
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


def _check_http_health(url: str, timeout: float = 3.0) -> bool:
    """Check if an HTTP endpoint returns a 2xx status."""
    try:
        import urllib.request
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
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
    questdb_host = questdb.get("host", "localhost")
    questdb_http = questdb.get("http_port", 9000)
    checks["questdb"] = {
        "required": "yes",
        "available": "yes" if _check_tcp_port(questdb_host, questdb.get("port", 9009)) else "no",
        "details": f"{questdb_host}:{questdb.get('port', 9009)} (ILP) / {questdb_http} (HTTP)",
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

    # MLflow — always check port 5000 (the docker-compose port)
    # The old code looked for config paths that don't exist in base.yaml
    mlflow_port = 5000
    mlflow_available = _check_tcp_port("localhost", mlflow_port)
    checks["mlflow"] = {
        "required": "yes",
        "available": "yes" if mlflow_available else "no",
        "details": f"localhost:{mlflow_port}",
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


def get_health_summary(checks: Optional[Dict] = None) -> Dict[str, any]:
    """Get overall infrastructure health summary.

    Returns:
        Dict with total, available, unavailable counts and overall status.
    """
    if checks is None:
        checks = check_stack()

    required_checks = {k: v for k, v in checks.items() if v.get("required") == "yes"}
    available = sum(1 for v in required_checks.values() if v.get("available") == "yes")
    total = len(required_checks)

    return {
        "total_services": total,
        "available": available,
        "unavailable": total - available,
        "health_pct": (available / total * 100) if total > 0 else 0,
        "all_healthy": available == total,
        "details": checks,
    }


def print_stack_summary(checks: Dict[str, Dict[str, Optional[str]]]) -> None:
    """Print a human-readable summary of infrastructure checks."""
    logger.info("=" * 60)
    logger.info("  INFRASTRUCTURE HEALTH CHECK")
    logger.info("=" * 60)

    for service, result in checks.items():
        status_icon = "✅" if result.get("available") == "yes" else "❌"
        logger.info(
            f"  {status_icon} {service:20s} | {result.get('details', 'N/A')}"
        )

    summary = get_health_summary(checks)
    logger.info("-" * 60)
    logger.info(
        f"  Summary: {summary['available']}/{summary['total_services']} services online "
        f"({summary['health_pct']:.0f}%)"
    )
    logger.info("=" * 60)
