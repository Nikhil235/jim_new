import os
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address

import sys

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Auto-detect if we are running under pytest to bypass rate limits
is_testing = "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv) or os.getenv("TESTING") == "True"
limiter = Limiter(key_func=get_remote_address, enabled=not is_testing)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    FastAPI dependency to verify X-API-Key header against the API_ACCESS_KEY env variable.
    Falls back to a default secret key if API_ACCESS_KEY is not defined.
    """
    expected_key = os.getenv("API_ACCESS_KEY", "medallion_secret_key")
    if not api_key or api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials"
        )
