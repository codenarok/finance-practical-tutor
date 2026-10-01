"""In-memory sliding-window rate limiting.

Counts live in this process only, which is right for a single-worker app.
Behind a reverse proxy, run uvicorn with --proxy-headers so the client
address is the real one.
"""
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status

from app.config import get_settings


class RateLimiter:
    """Allow at most `limit` hits per key in any `window_seconds` span."""

    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        """Record a hit for `key`, raising 429 once the limit is passed."""

        now = monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window_seconds:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = int(self.window_seconds - (now - hits[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts. Please wait a minute and try again.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    def reset(self) -> None:
        """Forget all recorded hits."""

        with self._lock:
            self._hits.clear()


settings = get_settings()
auth_limiter = RateLimiter(settings.auth_rate_limit_per_minute)
chat_limiter = RateLimiter(settings.chat_rate_limit_per_minute)


def limit_auth_attempts(request: Request) -> None:
    """FastAPI dependency that rate-limits login and registration per client address."""

    client_host = request.client.host if request.client else "unknown"
    auth_limiter.check(client_host)
