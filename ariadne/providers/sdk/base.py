"""BaseDynamicProvider and ProviderCapabilityManifest for standardizing dynamic intelligence providers."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ariadne.core.interfaces import ILogger, IProvider, ISecretsManager
from ariadne.core.models import IntelligenceResult, TargetEntity, TargetType


class ProviderCapabilityManifest(BaseModel):
    """Declarative capability manifest describing a dynamic provider's boundaries."""
    provider_id: str = Field(...)
    display_name: str = Field(...)
    supported_target_types: List[TargetType] = Field(...)
    requires_api_key: bool = Field(default=False)
    rate_limit_per_minute: int = Field(default=60)
    cost_units_per_request: float = Field(default=0.0)
    credibility_tier: int = Field(default=4, ge=1, le=7)


class BaseDynamicProvider(IProvider, ABC):
    """Abstract base provider handling capability manifests, exponential backoff, and usage tracking."""

    def __init__(
        self,
        manifest: ProviderCapabilityManifest,
        secrets_manager: Optional[ISecretsManager] = None,
        logger: Optional[ILogger] = None,
    ) -> None:
        """Initialize dynamic base provider."""
        self.manifest = manifest
        self.secrets_manager = secrets_manager
        self.logger = logger
        self.last_tokens_used: int = 0
        self.last_cost_units: float = 0.0

    @property
    def provider_id(self) -> str:
        """Unique provider identifier."""
        return self.manifest.provider_id

    @property
    def is_configured(self) -> bool:
        """Check whether required API keys or secrets are present."""
        if not self.manifest.requires_api_key:
            return True
        if not self.secrets_manager:
            return False
        return self.secrets_manager.get_secret(f"{self.provider_id.upper()}_API_KEY") is not None

    def get_manifest(self) -> ProviderCapabilityManifest:
        """Return provider capability manifest."""
        return self.manifest

    async def _execute_with_retry(
        self,
        coro_fn: Any,
        *args: Any,
        max_retries: int = 2,
        initial_delay: float = 0.5,
        **kwargs: Any,
    ) -> Any:
        """Execute async callable with exponential backoff on transient errors (HTTP 429/5xx)."""
        delay = initial_delay
        last_exc: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                return await coro_fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                status_code = getattr(exc, "status_code", None)
                # Retry on 429 or 5xx server errors
                if status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                    if self.logger:
                        self.logger.warning(
                            f"[{self.provider_id}] Transient error (HTTP {status_code}), retrying in {delay:.1f}s (Attempt {attempt+1}/{max_retries})"
                        )
                    await asyncio.sleep(delay)
                    delay *= 2.0
                else:
                    raise exc
        raise last_exc  # type: ignore

    @abstractmethod
    async def _fetch_target_data(self, target: TargetEntity) -> List[IntelligenceResult]:
        """Subclass implementation logic for retrieving intelligence."""
        ...

    async def collect_intelligence(self, target: TargetEntity) -> List[IntelligenceResult]:
        """Execute provider intelligence collection, enforcing target type validation and cost tracking."""
        if target.target_type not in self.manifest.supported_target_types:
            if self.logger:
                self.logger.debug(
                    f"[{self.provider_id}] Target type '{target.target_type}' not supported by manifest"
                )
            return []

        if not self.is_configured:
            if self.logger:
                self.logger.warning(f"[{self.provider_id}] Provider is not configured (missing API key)")
            return []

        self.last_tokens_used = 0
        self.last_cost_units = self.manifest.cost_units_per_request

        try:
            results = await self._execute_with_retry(self._fetch_target_data, target)
            for res in results:
                if not res.provider_used:
                    res.provider_used = self.provider_id
            return results
        except Exception as exc:
            if self.logger:
                self.logger.error(f"[{self.provider_id}] Collection failed for '{target.target_id}': {exc}")
            raise exc
