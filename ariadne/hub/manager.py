"""IntelligenceHub implementing IIntelligenceHub orchestration across all intelligence sub-managers."""

import asyncio
import time
from typing import Any, Dict, List, Optional
from ariadne.core.interfaces import (
    IAuditLogger,
    ICacheManager,
    IEventBus,
    IIntelligenceHub,
    ILogger,
    IMetricsRegistry,
    IProvider,
)
from ariadne.core.models import IntelligenceResult, TargetEntity
from ariadne.hub.cache_manager import HubCacheManager
from ariadne.hub.concurrency import HubConcurrencyManager
from ariadne.hub.cost_optimizer import ProviderCostOptimizer
from ariadne.hub.deduplication import HubDeduplicationManager
from ariadne.hub.incremental import IncrementalScanEngine
from ariadne.hub.priority_manager import SourcePriorityManager
from ariadne.providers.health.monitor import ProviderHealthMonitor


class IntelligenceHub(IIntelligenceHub):
    """Central Intelligence Hub coordinating prioritization, health check, caching, concurrency, and cost optimization."""

    def __init__(
        self,
        health_monitor: Optional[ProviderHealthMonitor] = None,
        priority_manager: Optional[SourcePriorityManager] = None,
        cost_optimizer: Optional[ProviderCostOptimizer] = None,
        cache_manager: Optional[HubCacheManager] = None,
        concurrency_manager: Optional[HubConcurrencyManager] = None,
        deduplication_manager: Optional[HubDeduplicationManager] = None,
        incremental_engine: Optional[IncrementalScanEngine] = None,
        event_bus: Optional[IEventBus] = None,
        logger: Optional[ILogger] = None,
        audit_logger: Optional[IAuditLogger] = None,
        metrics_registry: Optional[IMetricsRegistry] = None,
    ) -> None:
        """Initialize IntelligenceHub and all sub-managers."""
        self.health_monitor = health_monitor or ProviderHealthMonitor(logger=logger, audit_logger=audit_logger, metrics_registry=metrics_registry)
        self.priority_manager = priority_manager or SourcePriorityManager(logger=logger)
        self.cost_optimizer = cost_optimizer or ProviderCostOptimizer(logger=logger, metrics_registry=metrics_registry)
        self.cache_manager = cache_manager or HubCacheManager(logger=logger)
        self.concurrency_manager = concurrency_manager or HubConcurrencyManager(logger=logger)
        self.deduplication_manager = deduplication_manager or HubDeduplicationManager(logger=logger)
        self.incremental_engine = incremental_engine or IncrementalScanEngine(logger=logger)
        self.event_bus = event_bus
        self.logger = logger
        self.audit_logger = audit_logger
        self.metrics_registry = metrics_registry

    async def _safe_execute_provider(
        self,
        provider: IProvider,
        target: TargetEntity,
    ) -> List[IntelligenceResult]:
        """Execute a single provider with caching, concurrency control, health monitoring, and cost tracking."""
        p_id = provider.provider_id
        # 1. Check health & circuit breaker
        healthy = await self.health_monitor.is_provider_healthy(p_id)
        if not healthy:
            if self.logger:
                self.logger.warning(f"[IntelligenceHub] Skipping provider '{p_id}' (Unhealthy or Open Circuit)")
            return []

        # 2. Check cache
        cached = await self.cache_manager.get_cached_results(p_id, target.target_id)
        if cached is not None:
            return cached

        # 3. Concurrency acquire
        await self.concurrency_manager.acquire(p_id, provider_max_concurrency=5)
        start_ts = time.perf_counter()
        try:
            results = await provider.collect_intelligence(target)
            latency_ms = (time.perf_counter() - start_ts) * 1000.0
            await self.health_monitor.record_success(p_id, latency_ms)

            # Estimate token cost if available
            tokens = getattr(provider, "last_tokens_used", 0)
            cost = getattr(provider, "last_cost_units", 0.0)
            if tokens or cost:
                await self.cost_optimizer.record_cost(p_id, cost, tokens)

            # Store in cache
            await self.cache_manager.store_cached_results(p_id, target.target_id, results, ttl_seconds=3600)
            return results
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_ts) * 1000.0
            status_code = getattr(exc, "status_code", None)
            await self.health_monitor.record_failure(p_id, str(exc), status_code=status_code)
            if self.logger:
                self.logger.error(f"[IntelligenceHub] Error executing provider '{p_id}' on '{target.target_id}': {exc}")
            return []
        finally:
            self.concurrency_manager.release(p_id)

    async def orchestrate_collection(
        self,
        target: TargetEntity,
        providers: Dict[str, IProvider],
        budget_remaining: Optional[float] = None,
        previous_results: Optional[List[IntelligenceResult]] = None,
    ) -> List[IntelligenceResult]:
        """Orchestrate multi-source collection with priority sorting, deduplication, early exit, and incremental analysis."""
        if not providers:
            return []

        if self.logger:
            self.logger.info(f"[IntelligenceHub] Starting collection for target '{target.target_id}' across {len(providers)} provider(s)...")

        # Select budget-optimal providers
        selected_providers = await self.cost_optimizer.select_optimal_providers(list(providers.values()), budget_units_remaining=budget_remaining)

        # Execute all selected providers concurrently inside concurrency control
        tasks = [self._safe_execute_provider(p, target) for p in selected_providers]
        nested_results: List[List[IntelligenceResult]] = await asyncio.gather(*tasks, return_exceptions=False)

        raw_results: List[IntelligenceResult] = []
        for r_list in nested_results:
            raw_results.extend(r_list)

        # Deduplicate
        deduped = self.deduplication_manager.deduplicate(raw_results)

        # Sort descending by 7-tier priority and confidence
        sorted_results = self.priority_manager.sort_by_priority(deduped)

        # Check early exit / incremental delta log
        if previous_results is not None:
            new_f, upd_f, unch = self.incremental_engine.compute_delta(previous_results, sorted_results)

        if self.logger:
            self.logger.info(f"[IntelligenceHub] Collection complete for target '{target.target_id}'. Total unique findings: {len(sorted_results)}")

        return sorted_results
