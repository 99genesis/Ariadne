"""ProviderHealthMonitor tracking latency, error rates, quota limits, and circuit breaker status."""

import asyncio
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from ariadne.core.interfaces import IAuditLogger, IEventBus, ILogger, IMetricsRegistry
from ariadne.providers.health.circuit_breaker import ProviderCircuitBreaker


class ProviderHealthSnapshot(BaseModel):
    """Snapshot of a provider's current health metrics."""
    provider_id: str = Field(...)
    is_healthy: bool = Field(...)
    circuit_state: str = Field(...)
    total_requests: int = Field(default=0)
    total_failures: int = Field(default=0)
    error_rate: float = Field(default=0.0)
    avg_latency_ms: float = Field(default=0.0)
    last_error: Optional[str] = Field(default=None)


class ProviderHealthMonitor:
    """Tracks latency, error rate, rate limits (429), and coordinates with circuit breaker."""

    def __init__(
        self,
        circuit_breaker: Optional[ProviderCircuitBreaker] = None,
        event_bus: Optional[IEventBus] = None,
        logger: Optional[ILogger] = None,
        audit_logger: Optional[IAuditLogger] = None,
        metrics_registry: Optional[IMetricsRegistry] = None,
    ) -> None:
        """Initialize ProviderHealthMonitor."""
        self.circuit_breaker = circuit_breaker or ProviderCircuitBreaker(logger=logger, audit_logger=audit_logger, metrics_registry=metrics_registry)
        self.event_bus = event_bus
        self.logger = logger
        self.audit_logger = audit_logger
        self.metrics_registry = metrics_registry
        self._lock = asyncio.Lock()
        # Key: provider_id -> stats dict
        self._stats: Dict[str, Dict[str, Any]] = {}

    def _get_stats(self, provider_id: str) -> Dict[str, Any]:
        if provider_id not in self._stats:
            self._stats[provider_id] = {
                "total_requests": 0,
                "total_failures": 0,
                "latency_sum_ms": 0.0,
                "last_error": None,
            }
        return self._stats[provider_id]

    async def is_provider_healthy(self, provider_id: str) -> bool:
        """Check if provider is healthy and circuit breaker permits execution."""
        can_exec = await self.circuit_breaker.can_execute(provider_id)
        if not can_exec:
            return False
        async with self._lock:
            stats = self._get_stats(provider_id)
            if stats["total_requests"] > 10 and (stats["total_failures"] / stats["total_requests"]) > 0.60:
                return False
        return True

    async def record_success(self, provider_id: str, latency_ms: float) -> None:
        """Record successful call metrics and notify circuit breaker."""
        async with self._lock:
            stats = self._get_stats(provider_id)
            stats["total_requests"] += 1
            stats["latency_sum_ms"] += float(latency_ms)

        await self.circuit_breaker.record_success(provider_id)
        if self.metrics_registry:
            self.metrics_registry.increment_counter("provider_requests_total", {"provider": provider_id, "status": "success"})
            self.metrics_registry.record_histogram("provider_latency_ms", latency_ms, {"provider": provider_id})

    async def record_failure(self, provider_id: str, error_type: str, status_code: Optional[int] = None) -> None:
        """Record failure call metrics, check for 429 rate limits, and trip circuit breaker if threshold exceeded."""
        async with self._lock:
            stats = self._get_stats(provider_id)
            stats["total_requests"] += 1
            stats["total_failures"] += 1
            stats["last_error"] = f"{error_type} (HTTP {status_code})" if status_code else error_type

        await self.circuit_breaker.record_failure(provider_id, error_reason=error_type)
        if self.metrics_registry:
            status_lbl = str(status_code) if status_code else "error"
            self.metrics_registry.increment_counter("provider_requests_total", {"provider": provider_id, "status": status_lbl})

        if status_code == 429 and self.logger:
            self.logger.warning(f"[HealthMonitor] Provider '{provider_id}' hit Rate Limit (HTTP 429)")

    async def get_snapshot(self, provider_id: str) -> ProviderHealthSnapshot:
        """Retrieve real-time health snapshot for a provider."""
        async with self._lock:
            stats = self._get_stats(provider_id)
            reqs = stats["total_requests"]
            fails = stats["total_failures"]
            err_rate = (fails / reqs) if reqs > 0 else 0.0
            avg_lat = (stats["latency_sum_ms"] / reqs) if reqs > 0 else 0.0
            last_err = stats["last_error"]

        healthy = await self.is_provider_healthy(provider_id)
        breaker = self.circuit_breaker._get_breaker(provider_id)
        return ProviderHealthSnapshot(
            provider_id=provider_id,
            is_healthy=healthy,
            circuit_state=breaker.state.value,
            total_requests=reqs,
            total_failures=fails,
            error_rate=err_rate,
            avg_latency_ms=avg_lat,
            last_error=last_err,
        )
