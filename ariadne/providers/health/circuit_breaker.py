"""ProviderCircuitBreaker implementing CLOSED -> OPEN -> HALF-OPEN state machine for fault resilience."""

import asyncio
import time
from enum import Enum
from typing import Dict, Optional
from ariadne.core.interfaces import IAuditLogger, ILogger, IMetricsRegistry


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerInstance:
    """Per-provider circuit breaker state object."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 60.0) -> None:
        self.state = CircuitState.CLOSED
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.half_open_successes = 0

    def record_failure(self) -> bool:
        """Record a failure and return True if circuit tripped."""
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            return True
        return False

    def record_success(self) -> bool:
        """Record a success and return True if circuit reset to CLOSED."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            if self.half_open_successes >= 1:
                self.reset()
                return True
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
        return False

    def check_state(self) -> CircuitState:
        """Check and transition OPEN -> HALF_OPEN if cooldown has elapsed."""
        if self.state == CircuitState.OPEN:
            if (time.monotonic() - self.last_failure_time) >= self.cooldown_seconds:
                self.state = CircuitState.HALF_OPEN
                self.half_open_successes = 0
        return self.state

    def reset(self) -> None:
        """Force reset circuit to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_successes = 0


class ProviderCircuitBreaker:
    """Manages circuit breakers across all providers with audit logging and metrics."""

    def __init__(
        self,
        default_failure_threshold: int = 3,
        default_cooldown_seconds: float = 60.0,
        logger: Optional[ILogger] = None,
        audit_logger: Optional[IAuditLogger] = None,
        metrics_registry: Optional[IMetricsRegistry] = None,
    ) -> None:
        """Initialize ProviderCircuitBreaker."""
        self.default_failure_threshold = default_failure_threshold
        self.default_cooldown_seconds = default_cooldown_seconds
        self.logger = logger
        self.audit_logger = audit_logger
        self.metrics_registry = metrics_registry
        self._lock = asyncio.Lock()
        self._breakers: Dict[str, CircuitBreakerInstance] = {}

    def _get_breaker(self, provider_id: str) -> CircuitBreakerInstance:
        if provider_id not in self._breakers:
            self._breakers[provider_id] = CircuitBreakerInstance(
                failure_threshold=self.default_failure_threshold,
                cooldown_seconds=self.default_cooldown_seconds,
            )
        return self._breakers[provider_id]

    async def can_execute(self, provider_id: str) -> bool:
        """Check if provider circuit allows request (CLOSED or HALF_OPEN)."""
        async with self._lock:
            breaker = self._get_breaker(provider_id)
            state = breaker.check_state()
            if state == CircuitState.OPEN:
                if self.logger:
                    self.logger.warning(f"[CircuitBreaker] Request blocked for '{provider_id}' (Circuit is OPEN)")
                return False
            return True

    async def record_failure(self, provider_id: str, error_reason: str = "error") -> None:
        """Record a failure against provider circuit."""
        async with self._lock:
            breaker = self._get_breaker(provider_id)
            old_state = breaker.state
            tripped = breaker.record_failure()
            if tripped and old_state != CircuitState.OPEN:
                if self.logger:
                    self.logger.error(f"[CircuitBreaker] Circuit TRIPPED to OPEN for provider '{provider_id}'")
                if self.metrics_registry:
                    self.metrics_registry.set_gauge("circuit_breaker_state", 1.0, {"provider": provider_id})
                    self.metrics_registry.increment_counter("circuit_breaker_tripped_total", {"provider": provider_id})
                if self.audit_logger:
                    await self.audit_logger.log_event(
                        "CIRCUIT_TRIPPED",
                        session_id=f"cb-{provider_id}",
                        details={"provider_id": provider_id, "reason": error_reason, "failure_count": breaker.failure_count},
                    )

    async def record_success(self, provider_id: str) -> None:
        """Record successful execution against provider circuit."""
        async with self._lock:
            breaker = self._get_breaker(provider_id)
            old_state = breaker.state
            reset = breaker.record_success()
            if reset and old_state == CircuitState.HALF_OPEN:
                if self.logger:
                    self.logger.info(f"[CircuitBreaker] Circuit RESET to CLOSED for provider '{provider_id}'")
                if self.metrics_registry:
                    self.metrics_registry.set_gauge("circuit_breaker_state", 0.0, {"provider": provider_id})
                if self.audit_logger:
                    await self.audit_logger.log_event(
                        "CIRCUIT_RESET",
                        session_id=f"cb-{provider_id}",
                        details={"provider_id": provider_id},
                    )

    async def reset_provider(self, provider_id: str) -> None:
        """Manually reset a provider's circuit breaker to CLOSED."""
        async with self._lock:
            breaker = self._get_breaker(provider_id)
            breaker.reset()
            if self.metrics_registry:
                self.metrics_registry.set_gauge("circuit_breaker_state", 0.0, {"provider": provider_id})
