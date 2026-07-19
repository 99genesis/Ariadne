"""Abstract base classes and helper utilities for AI and OSINT providers.

Enforces September 2026 authentication standards, error boundaries, rate limit handling,
and dynamic list_models capabilities without hardcoding model names.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import aiohttp

from ariadne.core.exceptions import (
    ProviderAuthenticationException,
    ProviderException,
    ProviderRateLimitException,
)
from ariadne.core.interfaces import ILogger, IProvider, ISecretsManager
from ariadne.core.models import ProviderModelInfo


class BaseProvider(ABC, IProvider):
    """Abstract base class for all providers."""

    def __init__(
        self,
        secrets_manager: Optional[ISecretsManager] = None,
        logger: Optional[ILogger] = None,
    ) -> None:
        """Initialize provider with optional secrets manager and logger."""
        self.secrets_manager = secrets_manager
        self.logger = logger
        self._cached_models: List[ProviderModelInfo] = []

    @property
    @abstractmethod
    def provider_id(self) -> str:
        ...

    @property
    @abstractmethod
    def provider_type(self) -> str:
        ...

    @abstractmethod
    async def validate_credentials(self, api_key: Optional[str] = None) -> bool:
        ...

    @abstractmethod
    async def list_models(self) -> List[ProviderModelInfo]:
        ...

    async def _get_api_key(self, explicit_key: Optional[str] = None) -> Optional[str]:
        """Retrieve API key from explicit argument or secrets manager."""
        if explicit_key:
            return explicit_key
        if self.secrets_manager:
            return await self.secrets_manager.get_secret(f"{self.provider_id}_api_key")
        return None

    def _handle_http_error(self, status: int, body: str, endpoint: str) -> None:
        """Raise appropriate domain exception based on HTTP status code."""
        if status in (401, 403):
            raise ProviderAuthenticationException(
                provider_id=self.provider_id,
                details={"status": status, "endpoint": endpoint, "response": body[:200]},
            )
        elif status == 429:
            raise ProviderRateLimitException(
                provider_id=self.provider_id,
                details={"status": status, "endpoint": endpoint, "response": body[:200]},
            )
        elif status >= 400:
            raise ProviderException(
                message=f"Provider '{self.provider_id}' API error at {endpoint} (HTTP {status})",
                provider_id=self.provider_id,
                details={"status": status, "response": body[:300]},
            )


class BaseAIProvider(BaseProvider):
    """Base class for AI text and reasoning providers."""

    @property
    def provider_type(self) -> str:
        return "ai"


class BaseVisionProvider(BaseProvider):
    """Base class for AI Vision capable providers."""

    @property
    def provider_type(self) -> str:
        return "vision"
