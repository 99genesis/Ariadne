"""HubCacheManager coordinating Two-Tier caching for provider intelligence queries."""

import hashlib
import json
from typing import Any, Dict, List, Optional
from ariadne.core.interfaces import ICacheManager, ILogger
from ariadne.core.models import IntelligenceResult


class HubCacheManager:
    """Caching wrapper for provider queries ensuring TTL compliance and fast response."""

    def __init__(self, cache_manager: Optional[ICacheManager] = None, logger: Optional[ILogger] = None) -> None:
        """Initialize HubCacheManager."""
        self.cache_manager = cache_manager
        self.logger = logger

    @staticmethod
    def _make_key(provider_id: str, target_id: str, query_params: Optional[Dict[str, Any]] = None) -> str:
        raw = f"{provider_id}:{target_id}:{json.dumps(query_params or {}, sort_keys=True)}"
        return "hub_cache_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def get_cached_results(
        self,
        provider_id: str,
        target_id: str,
        query_params: Optional[Dict[str, Any]] = None,
    ) -> Optional[List[IntelligenceResult]]:
        """Retrieve cached results if available and unexpired."""
        if not self.cache_manager:
            return None
        key = self._make_key(provider_id, target_id, query_params)
        try:
            data = await self.cache_manager.get(key)
            if data and isinstance(data, list):
                if self.logger:
                    self.logger.debug(f"[HubCache] Cache HIT for provider '{provider_id}' on target '{target_id}'")
                return [IntelligenceResult.model_validate(item) if isinstance(item, dict) else item for item in data]
        except Exception as exc:
            if self.logger:
                self.logger.warning(f"[HubCache] Cache read error for key '{key}': {exc}")
        return None

    async def store_cached_results(
        self,
        provider_id: str,
        target_id: str,
        results: List[IntelligenceResult],
        ttl_seconds: int = 3600,
        query_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store results into two-tier cache with TTL expiration."""
        if not self.cache_manager or not results:
            return
        key = self._make_key(provider_id, target_id, query_params)
        try:
            payload = [r.model_dump(mode="json") for r in results]
            await self.cache_manager.set(key, payload, ttl=ttl_seconds)
            if self.logger:
                self.logger.debug(f"[HubCache] Cached {len(results)} results for '{provider_id}' (TTL={ttl_seconds}s)")
        except Exception as exc:
            if self.logger:
                self.logger.warning(f"[HubCache] Cache store error for key '{key}': {exc}")
