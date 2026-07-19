"""Rate Limiter and Concurrency Controller for Username Intelligence Providers.

Implements asyncio.Semaphore-based concurrency restrictions and Exponential Backoff
retry logic for handling HTTP 429 errors, connection timeouts, and network instability.
"""

import asyncio
import time
from typing import Any, Callable, Coroutine, Optional
import aiohttp

from ariadne.core.interfaces import ILogger


class RateLimiter:
    """Manages rate limiting delays, retry backoffs, and concurrent execution restrictions."""

    _shared_semaphore: Optional[asyncio.Semaphore] = None
    _host_last_seen: dict[str, float] = {}
    _lock = asyncio.Lock()

    @classmethod
    def get_semaphore(cls, max_concurrency: int = 10) -> asyncio.Semaphore:
        """Get or initialize shared semaphore controlling max parallel HTTP connections."""
        if cls._shared_semaphore is None:
            cls._shared_semaphore = asyncio.Semaphore(max_concurrency)
        return cls._shared_semaphore

    def __init__(
        self,
        host: str = "default",
        min_delay_seconds: float = 0.3,
        max_retries: int = 3,
        base_backoff: float = 1.0,
        logger: Optional[ILogger] = None,
    ) -> None:
        """Initialize RateLimiter for a specific host/provider."""
        self.host = host
        self.min_delay_seconds = min_delay_seconds
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.logger = logger

    async def _enforce_min_delay(self) -> None:
        async with self._lock:
            now = time.time()
            last = self._host_last_seen.get(self.host, 0.0)
            elapsed = now - last
            if elapsed < self.min_delay_seconds:
                delay = self.min_delay_seconds - elapsed
                await asyncio.sleep(delay)
            self._host_last_seen[self.host] = time.time()

    async def execute_with_retry(
        self,
        coro_func: Callable[[], Coroutine[Any, Any, Any]],
        semaphore: Optional[asyncio.Semaphore] = None,
    ) -> Any:
        """Execute an async operation with concurrency limiting and exponential backoff retry."""
        sem = semaphore or self.get_semaphore()

        for attempt in range(1, self.max_retries + 1):
            try:
                async with sem:
                    await self._enforce_min_delay()
                    return await coro_func()
            except (aiohttp.ClientResponseError, aiohttp.ClientError, asyncio.TimeoutError, Exception) as exc:
                from ariadne.core.exceptions import ProviderRateLimitException, ProviderAuthenticationException
                is_rate_limit = (
                    (isinstance(exc, aiohttp.ClientResponseError) and exc.status == 429) or
                    isinstance(exc, ProviderRateLimitException)
                )
                if isinstance(exc, ProviderAuthenticationException):
                    raise # Never retry authentication errors

                if attempt == self.max_retries:
                    if self.logger:
                        self.logger.debug(f"[{self.host}] Exceeded max retries ({self.max_retries}): {exc}")
                    raise

                # Calculate exponential backoff: 1s -> 2s -> 4s (plus slight jitter for rate limit)
                backoff = self.base_backoff * (2 ** (attempt - 1))
                if is_rate_limit:
                    backoff *= 2.0  # Extra backoff on explicit 429
                    if self.logger:
                        self.logger.warning(
                            f"[{self.host}] HTTP 429 Rate Limit encountered. Backing off for {backoff:.1f}s (Attempt {attempt}/{self.max_retries})..."
                        )
                else:
                    if self.logger:
                        self.logger.debug(
                            f"[{self.host}] Network error ({exc}). Retrying in {backoff:.1f}s (Attempt {attempt}/{self.max_retries})..."
                        )

                await asyncio.sleep(backoff)
            except Exception:
                raise
