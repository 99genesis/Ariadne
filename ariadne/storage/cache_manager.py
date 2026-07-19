"""Two-tier cache manager (Memory + Async Disk Cache with TTL support).

Accelerates OSINT network lookups, WHOIS queries, and AI prompt embeddings
by preventing redundant external requests across sessions.
"""

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional
import aiofiles

from ariadne.core.exceptions import StorageException
from ariadne.core.interfaces import ICacheManager, ILogger


class CacheEntry:
    """Memory cache entry wrapper with timestamp."""

    def __init__(self, value: Any, ttl_seconds: Optional[int] = None) -> None:
        self.value = value
        self.expires_at: Optional[float] = (
            time.time() + ttl_seconds if ttl_seconds is not None else None
        )

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class TwoTierCacheManager(ICacheManager):
    """Memory (dict LRU) and Disk (async JSON files) dual-layer cache manager."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        disk_enabled: bool = True,
        max_memory_mb: int = 512,
        logger: Optional[ILogger] = None,
    ) -> None:
        """Initialize cache manager."""
        self.cache_dir = Path(cache_dir) if cache_dir is not None else Path("Ariadne_Workspace") / "Cache"
        self.disk_enabled = disk_enabled
        self.max_memory_mb = max_memory_mb
        self.logger = logger
        self._memory_cache: Dict[str, Dict[str, CacheEntry]] = {}
        self._lock = asyncio.Lock()

    def set_target_cache_dir(self, cache_dir: Path) -> None:
        """Dynamically scope disk cache storage to target workspace directory."""
        cache_dir = Path(cache_dir)
        if self.cache_dir != cache_dir:
            self.cache_dir = cache_dir
            self._memory_cache.clear()

    def _get_disk_path(self, namespace: str, key: str) -> Path:
        """Get hashed filename path for disk cache item."""
        ns_dir = self.cache_dir / namespace
        ns_dir.mkdir(parents=True, exist_ok=True)
        key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return ns_dir / f"{key_hash}.json"

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """Retrieve value from memory first, then disk if available and valid."""
        async with self._lock:
            # Check memory cache
            ns_cache = self._memory_cache.get(namespace, {})
            if key in ns_cache:
                entry = ns_cache[key]
                if not entry.is_expired():
                    return entry.value
                else:
                    del ns_cache[key]

        # Check disk cache
        if not self.disk_enabled:
            return None

        disk_path = self._get_disk_path(namespace, key)
        if not disk_path.exists():
            return None

        try:
            async with aiofiles.open(disk_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

            expires_at = data.get("expires_at")
            if expires_at is not None and time.time() > expires_at:
                try:
                    disk_path.unlink(missing_ok=True)
                except Exception:
                    pass
                return None

            value = data.get("value")
            # Populate back to memory
            async with self._lock:
                self._memory_cache.setdefault(namespace, {})[key] = CacheEntry(
                    value=value,
                    ttl_seconds=int(expires_at - time.time()) if expires_at else None,
                )
            return value

        except Exception as exc:
            if self.logger:
                self.logger.debug(f"Cache read failed for {namespace}/{key}: {exc}")
            return None

    async def set(
        self, namespace: str, key: str, value: Any, ttl_seconds: Optional[int] = None
    ) -> None:
        """Store item in both memory and disk cache."""
        async with self._lock:
            self._memory_cache.setdefault(namespace, {})[key] = CacheEntry(
                value=value, ttl_seconds=ttl_seconds
            )

        if not self.disk_enabled:
            return

        disk_path = self._get_disk_path(namespace, key)
        expires_at = time.time() + ttl_seconds if ttl_seconds is not None else None
        payload = {"key": key, "value": value, "expires_at": expires_at}

        try:
            async with aiofiles.open(disk_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception as exc:
            if self.logger:
                self.logger.warning(f"Failed to write disk cache {disk_path}: {exc}")

    async def invalidate(self, namespace: str, key: Optional[str] = None) -> None:
        """Clear specific key or entire namespace from memory and disk."""
        async with self._lock:
            if key is None:
                self._memory_cache.pop(namespace, None)
            elif namespace in self._memory_cache and key in self._memory_cache[namespace]:
                del self._memory_cache[namespace][key]

        if not self.disk_enabled:
            return

        ns_dir = self.cache_dir / namespace
        if not ns_dir.exists():
            return

        if key is None:
            for file_path in ns_dir.glob("*.json"):
                try:
                    file_path.unlink(missing_ok=True)
                except Exception:
                    pass
        else:
            disk_path = self._get_disk_path(namespace, key)
            try:
                disk_path.unlink(missing_ok=True)
            except Exception:
                pass
