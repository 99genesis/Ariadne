"""Pydantic schema definitions for Ariadne layered configuration.

Enforces strict schema validation, type checking, and boundary rules
for all user settings stored in config.json or vault overrides.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ValidationInfo  # noqa: F401


class SystemConfig(BaseModel):
    """System-wide core options."""

    language: str = Field(default="en", description="Default UI language (en, ru, zh, tr)")
    vault_root: Path = Field(
        default=Path("Ariadne_Workspace"), description="Root directory containing all vaults"
    )
    theme: str = Field(default="dark_cyber", description="Terminal color palette theme")
    check_updates_on_startup: bool = Field(default=True)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        supported_languages = ["en", "ru", "zh", "tr"]
        if value.lower() not in supported_languages:
            raise ValueError(f"Language '{value}' not supported. Must be one of: {supported_languages}")
        return value.lower()

    @field_validator("*", mode="before")
    @classmethod
    def coerce_path_fields(cls, v: Any, info: Any) -> Any:
        """Coerce plain strings to Path for any field annotated as Path.

        pydantic_core.ValidationInfo does NOT expose `.annotation`, so we
        look up the field definition through cls.model_fields instead.
        """
        if isinstance(v, str) and info.field_name:
            field_def = cls.model_fields.get(info.field_name)
            if field_def is not None and field_def.annotation is Path:
                return Path(v)
        return v


class NetworkProxyConfig(BaseModel):
    """Network proxy configurations."""

    enabled: bool = Field(default=False)
    url: Optional[str] = Field(default=None, description="Proxy URL e.g. http://127.0.0.1:8080")
    use_tor: bool = Field(default=False, description="Route traffic through local Tor SOCKS5")


class NetworkConfig(BaseModel):
    """HTTP client and networking options."""

    proxy: NetworkProxyConfig = NetworkProxyConfig()
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    max_concurrent_requests: int = Field(default=50, ge=1, le=200)
    user_agent_strategy: str = Field(default="random_desktop")


class ProvidersConfig(BaseModel):
    """AI model and external OSINT provider settings."""

    active_ai_provider: str = Field(default="google_ai", description="Primary AI text/reasoning provider")
    active_vision_model: str = Field(
        default="gemini-flash-latest", description="Primary Vision model ID"
    )
    fallback_models: List[str] = Field(
        default_factory=lambda: ["gemini-3.5-flash", "gemini-3-flash-preview", "gemini-2.5-pro", "gemini-2.0-flash"],
        description="Fallback models if primary vision model hits rate limits or is not found",
    )
    fallback_providers: List[str] = Field(
        default_factory=lambda: ["openrouter", "ollama"],
        description="Ordered fallback providers if primary hits rate limits or offline",
    )
    api_keys_storage: str = Field(
        default="secrets_manager", description="Storage backend ('secrets_manager' or 'encrypted_file')"
    )


class TTLConfig(BaseModel):
    """Time-To-Live expiration seconds for cache entries."""

    http_requests: int = Field(default=86400, description="24 hours")
    ai_analysis: int = Field(default=604800, description="7 days")
    dns_records: int = Field(default=3600, description="1 hour")


class CacheConfig(BaseModel):
    """Cache manager options."""

    disk_cache_enabled: bool = Field(default=True)
    memory_cache_max_mb: int = Field(default=512, ge=64, le=8192)
    ttl_seconds: TTLConfig = TTLConfig()


class LoggingConfig(BaseModel):
    """Central logging configuration."""

    level: str = Field(default="INFO", description="DEBUG, INFO, WARNING, ERROR, CRITICAL")
    console_output: bool = Field(default=True)
    file_rotation_max_mb: int = Field(default=20, ge=1, le=500)
    backup_count: int = Field(default=5, ge=1, le=50)
    mask_sensitive_data: bool = Field(default=True)


class SecurityConfig(BaseModel):
    """Security and encryption boundaries."""

    verify_ssl: bool = Field(default=True)
    allow_local_network_scans: bool = Field(default=False)
    encrypt_local_database: bool = Field(default=False)


class ObsidianOutputConfig(BaseModel):
    """Obsidian export and Graph View preferences."""

    create_graph_links: bool = Field(default=True)
    use_daily_notes_folder: bool = Field(default=False)
    folder_organization: str = Field(default="by_category")


class ReportsOutputConfig(BaseModel):
    """Report export options."""

    auto_generate_pdf: bool = Field(default=False)
    include_raw_json: bool = Field(default=True)


class OutputConfig(BaseModel):
    """Combined output options."""

    obsidian: ObsidianOutputConfig = ObsidianOutputConfig()
    reports: ReportsOutputConfig = ReportsOutputConfig()


class AriadneGlobalConfig(BaseModel):
    """Root configuration schema aggregating all settings."""

    system: SystemConfig = SystemConfig()
    providers: ProvidersConfig = ProvidersConfig()
    network: NetworkConfig = NetworkConfig()
    cache: CacheConfig = CacheConfig()
    logging: LoggingConfig = LoggingConfig()
    security: SecurityConfig = SecurityConfig()
    modules: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "username_intel": {"timeout_per_engine": 15, "include_nsfw_sites": False},
            "image_intel": {"max_image_dimension": 2048, "exif_extract_gps_only": False},
        }
    )
    output: OutputConfig = OutputConfig()
