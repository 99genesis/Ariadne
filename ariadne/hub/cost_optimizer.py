"""ProviderCostOptimizer tracking token usage, budget limits, and cost-aware routing."""

import asyncio
from typing import Any, Dict, List, Optional
from ariadne.core.interfaces import ILogger, IMetricsRegistry, IProvider


class ProviderCostOptimizer:
    """Tracks token consumption, estimated financial costs, and budget limits."""

    def __init__(self, logger: Optional[ILogger] = None, metrics_registry: Optional[IMetricsRegistry] = None) -> None:
        """Initialize ProviderCostOptimizer."""
        self.logger = logger
        self.metrics_registry = metrics_registry
        self._lock = asyncio.Lock()
        # Key: provider_id -> {cost_units: float, tokens_used: int, requests: int}
        self._usage: Dict[str, Dict[str, Any]] = {}

    def _get_usage(self, provider_id: str) -> Dict[str, Any]:
        if provider_id not in self._usage:
            self._usage[provider_id] = {"cost_units": 0.0, "tokens_used": 0, "requests": 0}
        return self._usage[provider_id]

    async def record_cost(self, provider_id: str, cost_units: float, tokens_used: int = 0) -> None:
        """Record cost units and token counts for a provider request."""
        async with self._lock:
            usage = self._get_usage(provider_id)
            usage["cost_units"] += float(cost_units)
            usage["tokens_used"] += int(tokens_used)
            usage["requests"] += 1

        if self.metrics_registry:
            self.metrics_registry.increment_counter("provider_tokens_total", {"provider": provider_id})
            self.metrics_registry.record_histogram("provider_cost_units", cost_units, {"provider": provider_id})

    async def get_cost_summary(self) -> Dict[str, Any]:
        """Return total aggregated costs across all providers."""
        async with self._lock:
            total_cost = sum(u["cost_units"] for u in self._usage.values())
            total_tokens = sum(u["tokens_used"] for u in self._usage.values())
            return {
                "total_cost_units": total_cost,
                "total_tokens_used": total_tokens,
                "provider_breakdown": dict(self._usage),
            }

    async def select_optimal_providers(
        self,
        candidates: List[IProvider],
        budget_units_remaining: Optional[float] = None,
    ) -> List[IProvider]:
        """Filter and order providers to optimize cost and remaining budget."""
        if not candidates:
            return []
        if budget_units_remaining is not None and budget_units_remaining <= 0:
            if self.logger:
                self.logger.warning("[CostOptimizer] Budget exhausted; filtering out paid AI providers")
            # Return only local/free providers (e.g. Ollama or OSINT tools)
            return [p for p in candidates if "ollama" in p.provider_id.lower() or "free" in p.provider_id.lower()]
        return list(candidates)
