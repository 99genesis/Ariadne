"""Plugin Discovery engine.

Scans both built-in core plugin directories and external user workspace directories
for valid manifest.yaml files without importing code before verification.
"""

from pathlib import Path
from typing import List, Optional, Union
import yaml
from pydantic import BaseModel, Field, ValidationError

from ariadne.core.exceptions import PluginException
from ariadne.core.interfaces import ILogger


class PluginEventsManifest(BaseModel):
    """Subscribed and published event topics declared by the plugin."""

    subscribes: List[str] = Field(default_factory=list)
    publishes: List[str] = Field(default_factory=list)


class PluginManifest(BaseModel):
    """Strict schema for manifest.yaml inside any Ariadne plugin folder."""

    id: str = Field(..., description="Unique plugin ID (e.g. ariadne.builtin.username_intel)")
    name: str = Field(..., description="Human-readable plugin title")
    version: str = Field(default="1.0.0")
    author: str = Field(default="Ariadne Team")
    description: str = Field(default="")
    supported_targets: List[str] = Field(
        default_factory=list, description="Target types accepted e.g. ['username', 'person']"
    )
    supported_command: Union[str, List[str]] = Field(
        default_factory=list, description="Command routing identifier e.g. 'username', 'image', or ['phone', 'email']"
    )
    required_capabilities: List[str] = Field(
        default_factory=list, description="Required capabilities e.g. ['http_client', 'event_bus']"
    )
    events: PluginEventsManifest = PluginEventsManifest()
    python_dependencies: List[str] = Field(default_factory=list)

    # Runtime path attached by discovery
    plugin_dir: Optional[Path] = Field(default=None, exclude=True)

    def get_supported_commands(self) -> List[str]:
        """Return normalized list of supported command names."""
        if isinstance(self.supported_command, str):
            return [self.supported_command.strip().lower()] if self.supported_command.strip() else []
        elif isinstance(self.supported_command, list):
            return [str(c).strip().lower() for c in self.supported_command if str(c).strip()]
        return []


class PluginDiscovery:
    """Discovers and validates plugin manifest.yaml files across search directories."""

    def __init__(self, search_paths: Optional[List[Path]] = None, logger: Optional[ILogger] = None) -> None:
        """Initialize plugin discovery.

        Args:
            search_paths: List of root directories to scan for plugin subdirectories.
            logger: Optional logger instance.
        """
        self.search_paths = search_paths or [
            Path(__file__).parent / "builtin",
            Path("Ariadne_Workspace") / "Plugins",
        ]
        self.logger = logger

    def discover_manifests(self) -> List[PluginManifest]:
        """Scan configured directories for manifest.yaml files and parse them into PluginManifest objects."""
        discovered: List[PluginManifest] = []

        for root_dir in self.search_paths:
            if not root_dir.exists() or not root_dir.is_dir():
                if self.logger:
                    self.logger.debug(f"Plugin search path does not exist or not a directory: {root_dir}")
                continue

            for sub_dir in root_dir.iterdir():
                if not sub_dir.is_dir():
                    continue
                manifest_file = sub_dir / "manifest.yaml"
                if not manifest_file.exists():
                    manifest_file = sub_dir / "manifest.yml"

                if not manifest_file.exists():
                    continue

                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        raw_data = yaml.safe_load(f) or {}

                    manifest = PluginManifest.model_validate(raw_data)
                    manifest.plugin_dir = sub_dir
                    discovered.append(manifest)
                    if self.logger:
                        self.logger.debug(f"Discovered plugin manifest: {manifest.id} at {sub_dir}")
                except (ValidationError, Exception) as exc:
                    if self.logger:
                        self.logger.warning(
                            f"Invalid plugin manifest at {manifest_file}: {exc}"
                        )

        return discovered
