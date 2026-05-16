import redis
from loguru import logger
from src.utils.config import get_config

_redis_pool = None

def get_redis_client():
    """
    Get a global Redis client using a connection pool.
    This ensures we don't open new TCP connections for every request.
    """
    global _redis_pool
    if _redis_pool is None:
        try:
            config = get_config()
            redis_config = config.get("database", {}).get("redis", {})
            # Use fallback if structure is different
            if not redis_config:
                redis_config = config.get("databases", {}).get("redis", {})
            
            _redis_pool = redis.ConnectionPool(
                host=redis_config.get("host", "localhost"),
                port=redis_config.get("port", 6379),
                db=redis_config.get("db", 0),
                password=redis_config.get("password", ""),
                decode_responses=True,
                health_check_interval=30
            )
            logger.info("Initialized Global Redis Connection Pool")
        except Exception as e:
            logger.error(f"Failed to initialize Redis pool: {e}")
            
    return redis.Redis(connection_pool=_redis_pool)
