"""
SurakshaEdge - API security (bearer token auth, replay protection)
"""
from __future__ import annotations

import os
import time
from functools import lru_cache
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_TOKEN_ENV = "SURAKSHA_API_TOKEN"
REPLAY_WINDOW_S = 30.0

bearer_scheme = HTTPBearer(auto_error=False)


def _get_expected_token() -> str:
    return os.environ.get(_TOKEN_ENV, "demo-token")


async def require_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    expected = _get_expected_token()
    if credentials is None or credentials.credentials != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
        )
    return credentials.credentials


def check_replay(ts_utc: str) -> bool:
    """Return True if the timestamp is within the replay window."""
    import datetime
    try:
        ts = datetime.datetime.fromisoformat(ts_utc.replace("Z", "+00:00"))
        age_s = (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds()
        return abs(age_s) <= REPLAY_WINDOW_S
    except Exception:
        return False
