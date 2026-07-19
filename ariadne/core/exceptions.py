"""Domain exception hierarchy for Ariadne OSINT Framework.

All domain, configuration, provider, plugin, and storage exceptions must inherit
from AriadneException to ensure clean exception handling across layers.
"""

from typing import Any, Dict, Optional


class AriadneException(Exception):
    """Base exception class for all Ariadne framework exceptions."""

    def __init__(
        self,
        message: str,
        error_code: str = "ARIADNE_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize Ariadne exception.

        Args:
            message: Human-readable error explanation.
            error_code: Unique machine-readable error code.
            details: Optional dictionary containing context or metadata.
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ConfigurationException(AriadneException):
    """Raised when configuration validation or resolution fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message=message, error_code="CONFIG_ERROR", details=details)


class SecurityException(AriadneException):
    """Raised when secrets retrieval, authentication, or validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message=message, error_code="SECURITY_ERROR", details=details)


class ProviderException(AriadneException):
    """Raised when an AI or OSINT provider encounters an error."""

    def __init__(
        self,
        message: str,
        provider_id: str,
        error_code: str = "PROVIDER_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details_dict = details or {}
        details_dict["provider_id"] = provider_id
        super().__init__(message=message, error_code=error_code, details=details_dict)


class ProviderRateLimitException(ProviderException):
    """Raised when a provider hits rate limits or API quota exhaustion (HTTP 429)."""

    def __init__(self, provider_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=f"Provider '{provider_id}' rate limit or quota exceeded.",
            provider_id=provider_id,
            error_code="PROVIDER_RATE_LIMIT",
            details=details,
        )


class ProviderAuthenticationException(ProviderException):
    """Raised when provider API key validation or auth fails."""

    def __init__(self, provider_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=f"Authentication failed for provider '{provider_id}'.",
            provider_id=provider_id,
            error_code="PROVIDER_AUTH_ERROR",
            details=details,
        )


class PluginException(AriadneException):
    """Raised when a plugin fails during discovery, initialization, or execution."""

    def __init__(
        self,
        message: str,
        plugin_id: str,
        error_code: str = "PLUGIN_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details_dict = details or {}
        details_dict["plugin_id"] = plugin_id
        super().__init__(message=message, error_code=error_code, details=details_dict)


class StorageException(AriadneException):
    """Raised when disk, SQLite, or cache storage operations fail."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message=message, error_code="STORAGE_ERROR", details=details)


class VaultNotFoundException(StorageException):
    """Raised when a specified vault folder or its .obsidian folder does not exist."""

    def __init__(self, vault_name: str, details: Optional[Dict[str, Any]] = None) -> None:
        details_dict = details or {}
        details_dict["vault_name"] = vault_name
        super().__init__(
            message=f"Obsidian vault '{vault_name}' not found or invalid (.obsidian missing).",
            details=details_dict,
        )


class DependencyResolutionException(AriadneException):
    """Raised when the DI Container cannot resolve a requested service."""

    def __init__(self, service_name: str) -> None:
        super().__init__(
            message=f"Failed to resolve service '{service_name}' from DI container.",
            error_code="DI_RESOLUTION_ERROR",
            details={"service_name": service_name},
        )
