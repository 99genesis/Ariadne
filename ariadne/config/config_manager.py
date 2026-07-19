"""Central Configuration Manager supporting 4-tier layered resolution.

Resolution Priority:
1. CLI Arguments (passed at runtime)
2. OS Environment Variables (ARIADNE_*)
3. Active Vault specific config (.obsidian/ariadne.json)
4. Global system config.json
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import ValidationError

from ariadne.config.schema import AriadneGlobalConfig
from ariadne.core.exceptions import ConfigurationException
from ariadne.core.interfaces import ILogger


class ConfigManager:
    """Manages loading, layered overrides, validation, and saving of configurations."""

    def __init__(self, config_file: Optional[Path] = None, logger: Optional[ILogger] = None) -> None:
        """Initialize configuration manager.

        Args:
            config_file: Path to global config.json. Defaults to config.json in working directory.
            logger: Optional logger instance.
        """
        self.config_file = Path(config_file) if config_file is not None else Path("config.json")
        self.logger = logger
        self._current_config: AriadneGlobalConfig = AriadneGlobalConfig()
        self._cli_overrides: Dict[str, Any] = {}
        self._vault_overrides: Dict[str, Any] = {}

    @property
    def config(self) -> AriadneGlobalConfig:
        """Get the current resolved Pydantic global configuration model."""
        return self._current_config

    def set_cli_overrides(self, overrides: Dict[str, Any]) -> None:
        """Apply highest-priority CLI runtime argument overrides."""
        self._cli_overrides = overrides
        self.resolve_and_validate()

    def set_vault_overrides(self, vault_config_path: Path) -> None:
        """Apply vault-specific configuration overrides (.obsidian/ariadne.json)."""
        vault_config_path = Path(vault_config_path)
        if vault_config_path.exists():
            try:
                with open(vault_config_path, "r", encoding="utf-8") as f:
                    self._vault_overrides = json.load(f)
            except Exception as exc:
                if self.logger:
                    self.logger.warning(f"Failed to load vault config at {vault_config_path}: {exc}")
        else:
            self._vault_overrides = {}
        self.resolve_and_validate()

    def load_global_config(self) -> AriadneGlobalConfig:
        """Load global config.json from disk, creating default if not found."""
        if not self.config_file.exists():
            default_config = AriadneGlobalConfig()
            self.save_global_config(default_config)
            self._current_config = default_config
            return default_config

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                if self.config_file.suffix in (".yaml", ".yml"):
                    raw_dict = yaml.safe_load(f) or {}
                else:
                    raw_dict = json.load(f) or {}
        except Exception as exc:
            raise ConfigurationException(
                message=f"Failed to read config file {self.config_file}: {exc}", details={"error": str(exc)}
            )

        self.resolve_and_validate(base_dict=raw_dict)
        return self._current_config

    def _get_env_overrides(self) -> Dict[str, Any]:
        """Extract ARIADNE_* environment variable overrides into nested dictionary."""
        env_overrides: Dict[str, Any] = {}
        prefix = "ARIADNE_"
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            cleaned_key = key[len(prefix):].lower()
            # Handle specific known env overrides
            if cleaned_key == "proxy_url":
                env_overrides.setdefault("network", {}).setdefault("proxy", {})["url"] = value
                env_overrides["network"]["proxy"]["enabled"] = True
            elif cleaned_key == "theme":
                env_overrides.setdefault("system", {})["theme"] = value
            elif cleaned_key == "language":
                env_overrides.setdefault("system", {})["language"] = value
            elif cleaned_key == "ai_provider":
                env_overrides.setdefault("providers", {})["active_ai_provider"] = value
            elif cleaned_key == "vault_root":
                env_overrides.setdefault("system", {})["vault_root"] = value
        return env_overrides

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge dictionary overrides into base dictionary."""
        merged = base.copy()
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._deep_merge(merged[key], value)
            elif value is not None:
                merged[key] = value
        return merged

    def resolve_and_validate(self, base_dict: Optional[Dict[str, Any]] = None) -> AriadneGlobalConfig:
        """Resolve 4-tier overrides and validate against Pydantic schema."""
        if base_dict is None:
            base_dict = self._current_config.model_dump()

        # 4. Global config (base_dict)
        merged = base_dict

        # 3. Vault overrides
        if self._vault_overrides:
            merged = self._deep_merge(merged, self._vault_overrides)

        # 2. Environment overrides
        env_overrides = self._get_env_overrides()
        if env_overrides:
            merged = self._deep_merge(merged, env_overrides)

        # 1. CLI arguments overrides
        if self._cli_overrides:
            merged = self._deep_merge(merged, self._cli_overrides)

        try:
            resolved = AriadneGlobalConfig.model_validate(merged)
            self._current_config = resolved
            return resolved
        except ValidationError as exc:
            raise ConfigurationException(
                message="Configuration schema validation failed during resolution.",
                details={"errors": exc.errors()},
            )

    def save_global_config(self, config_model: Optional[AriadneGlobalConfig] = None) -> None:
        """Save the global configuration back to config.json."""
        to_save = config_model or self._current_config
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json_str = to_save.model_dump_json(indent=2)
                f.write(json_str)
            self._current_config = to_save
        except Exception as exc:
            raise ConfigurationException(
                message=f"Failed to save global config to {self.config_file}: {exc}",
                details={"error": str(exc)},
            )
