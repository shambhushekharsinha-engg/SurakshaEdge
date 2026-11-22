"""
SurakshaEdge - Production middleware
  1. Structured JSON request logging (trace-ID, latency)
  2. Token-bucket rate limiter (60 req/min per IP, burst=10)
  3. Security headers (CSP, HSTS, X-Frame-Options, etc.)
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("surakshaedge.access")

# ---------------------------------------------------------------------------
# 1 — Structured JSON access logger
# ---------------------------------------------------------------------------

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        trace_id = str(uuid.uuid4())[:8]
        request.state.trace_id = trace_id
        t0 = time.perf_counter()
        try:
            response = await call_next(request)
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            logger.info(json.dumps({
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": latency_ms,
                "client": request.client.host if request.client else "unknown",
            }))
            response.headers["X-Trace-ID"] = trace_id
            return response
        except Exception as exc:
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            logger.error(json.dumps({
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "error": str(exc),
                "latency_ms": latency_ms,
            }))
            raise


# ---------------------------------------------------------------------------
# 2 — Token-bucket rate limiter
# ---------------------------------------------------------------------------

class _Bucket:
    """Single token-bucket state for one IP."""
    __slots__ = ("tokens", "last_refill")

    def __init__(self, capacity: float):
        self.tokens: float = capacity
        self.last_refill: float = time.monotonic()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token-bucket rate limiter.
    Default: 60 tokens/min refill rate, burst capacity 10.
    Applies only to mutating / high-cost paths.
    """

    RATE_PATHS = {"/events", "/simulate", "/events/"}

    def __init__(self, app: ASGIApp, rate_per_min: int = 60, burst: int = 10):
        super().__init__(app)
        self._rate_per_s = rate_per_min / 60.0
        self._burst = float(burst)
        self._buckets: dict[str, _Bucket] = defaultdict(lambda: _Bucket(self._burst))

    def _check(self, ip: str) -> bool:
        b = self._buckets[ip]
        now = time.monotonic()
        elapsed = now - b.last_refill
        b.tokens = min(self._burst, b.tokens + elapsed * self._rate_per_s)
        b.last_refill = now
        if b.tokens >= 1.0:
            b.tokens -= 1.0
            return True
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if any(path.startswith(p) for p in self.RATE_PATHS):
            ip = request.client.host if request.client else "unknown"
            if not self._check(ip):
                return Response(
                    content=json.dumps({"detail": "Rate limit exceeded — 60 req/min"}),
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": "10"},
                )
        return await call_next(request)


# ---------------------------------------------------------------------------
# 3 — Security headers
# ---------------------------------------------------------------------------

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",    # Changed from DENY to allow Swagger iframe
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
        "https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com "
        "https://fastapi.tiangolo.com; "
        "style-src 'self' 'unsafe-inline' "
        "https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com "
        "https://fastapi.tiangolo.com; "
        "img-src 'self' data: blob: "
        "https://tile.openstreetmap.org https://*.tile.openstreetmap.org https://*.openstreetmap.org "
        "https://*.arcgisonline.com https://server.arcgisonline.com https://services.arcgisonline.com "
        "https://*.mapbox.com https://api.mapbox.com https://*.maptiler.com https://api.maptiler.com; "
        "connect-src 'self' wss: ws: https:; "
        "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
        "worker-src 'self' blob:;"
    ),
}

# Paths that get relaxed headers (Swagger UI, ReDoc need less restrictive CSP)
_SWAGGER_PATHS = {"/docs", "/redoc", "/openapi.json"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        path = request.url.path
        # For Swagger/ReDoc: skip CSP (they need external CDN assets) but keep other headers
        for header, value in _SECURITY_HEADERS.items():
            if header == "Content-Security-Policy" and path in _SWAGGER_PATHS:
                continue  # Let Swagger load its own CDN assets freely
            if header == "X-Frame-Options" and path in _SWAGGER_PATHS:
                continue  # Swagger uses iframes internally
            response.headers[header] = value
        return response
