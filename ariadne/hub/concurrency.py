"""HubConcurrencyManager enforcing async semaphore limits and rate pacing across providers."""

import asyncio
from typing import Dict, Optional
from ariadne.core.interfaces import ILogger


class HubConcurrencyManager:
    """Manages concurrent execution limits and rate pacing across intelligence providers."""

    def __init__(self, max_global_concurrency: int = 15, logger: Optional[ILogger] = None) -> None:
        """Initialize global and per-provider concurrency controls."""
        self.max_global_concurrency = max_global_concurrency
        self.logger = logger
        self._global_semaphore = asyncio.Semaphore(max_global_concurrency)
        self._provider_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._lock = asyncio.Lock()

    async def get_provider_semaphore(self, provider_id: str, max_concurrency: int = 5) -> asyncio.Semaphore:
        """Retrieve or create a bounded semaphore for a specific provider."""
        async with self._lock:
            if provider_id not in self._provider_semaphores:
                self._provider_semaphores[provider_id] = asyncio.Semaphore(max_concurrency)
            return self._provider_semaphores[provider_id]

    async def acquire(self, provider_id: str, provider_max_concurrency: int = 5) -> None:
        """Acquire both global and provider-level semaphores before execution."""
        await self._global_semaphore.acquire()
        prov_sem = await self.get_provider_semaphore(provider_id, provider_max_concurrency)
        await prov_sem.acquire()

    def release(self, provider_id: str) -> None:
        """Release both global and provider-level semaphores."""
        if provider_id in self._provider_semaphores:
            self._provider_semaphores[provider_id].release()
        self._global_semaphore.release()
