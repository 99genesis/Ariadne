"""Plugin Registry holding active manifests and plugin instances."""

from typing import Dict, List, Optional, Tuple
from ariadne.core.interfaces import ILogger, IPlugin
from ariadne.core.models import TargetEntity
from ariadne.plugins.discovery import PluginManifest


class PluginRegistry:
    """Registry maintaining active plugin manifests and instantiated modules."""

    def __init__(self, logger: Optional[ILogger] = None) -> None:
        self.logger = logger
        self._entries: Dict[str, Tuple[PluginManifest, IPlugin]] = {}
        self._disabled_ids: Dict[str, bool] = {}

    def register(self, manifest: PluginManifest, plugin: IPlugin) -> None:
        """Register a validated manifest and plugin instance."""
        self._entries[manifest.id] = (manifest, plugin)
        if self.logger:
            self.logger.info(f"Registered plugin in registry: {manifest.id} (v{manifest.version})")

    def unregister(self, plugin_id: str) -> None:
        """Remove a plugin from the registry."""
        self._entries.pop(plugin_id, None)

    def set_enabled(self, plugin_id: str, enabled: bool) -> None:
        """Enable or disable a plugin by ID."""
        self._disabled_ids[plugin_id] = not enabled

    def is_enabled(self, plugin_id: str) -> bool:
        """Check if a plugin is currently enabled."""
        if plugin_id not in self._entries:
            return False
        return not self._disabled_ids.get(plugin_id, False)

    def get_plugin(self, plugin_id: str) -> Optional[IPlugin]:
        """Get plugin instance by ID."""
        entry = self._entries.get(plugin_id)
        return entry[1] if entry else None

    def get_manifest(self, plugin_id: str) -> Optional[PluginManifest]:
        """Get plugin manifest by ID."""
        entry = self._entries.get(plugin_id)
        return entry[0] if entry else None

    def list_all_manifests(self) -> List[PluginManifest]:
        """List all registered manifests."""
        return [entry[0] for entry in self._entries.values()]

    def list_active_plugins_for_target(self, target: TargetEntity) -> List[IPlugin]:
        """List all enabled plugins whose manifest supported_targets matches target type."""
        active_plugins: List[IPlugin] = []
        for pid, (manifest, plugin) in self._entries.items():
            if not self.is_enabled(pid):
                continue

            target_type_str = target.target_type.value if hasattr(target.target_type, "value") else str(target.target_type)
            if (
                target_type_str in manifest.supported_targets
                or "all" in manifest.supported_targets
                or target.target_id in manifest.supported_targets
            ):
                active_plugins.append(plugin)
        return active_plugins

    def list_active_plugins_for_command(self, command_name: str, target: Optional[TargetEntity] = None) -> List[IPlugin]:
        """List all enabled plugins assigned to the specified CLI command (or fallback to target matching)."""
        active_plugins: List[IPlugin] = []
        cmd_lower = command_name.strip().lower()
        for pid, (manifest, plugin) in self._entries.items():
            if not self.is_enabled(pid):
                continue

            supported_cmds = manifest.get_supported_commands()
            if cmd_lower in ("profile", "fusion"):
                # Profile and fusion commands aggregate holistic intelligence from all enabled plugins
                active_plugins.append(plugin)
                continue

            if supported_cmds:
                if cmd_lower in supported_cmds or "all" in supported_cmds:
                    active_plugins.append(plugin)
            elif target:
                # Fallback to supported_targets if supported_command not specified in manifest
                target_type_str = target.target_type.value if hasattr(target.target_type, "value") else str(target.target_type)
                if target_type_str in manifest.supported_targets or "all" in manifest.supported_targets:
                    active_plugins.append(plugin)
        return active_plugins

    def clear(self) -> None:
        """Clear all registry entries."""
        self._entries.clear()
        self._disabled_ids.clear()
