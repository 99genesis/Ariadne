"""Plugin Manager controlling lifecycle, initialization, and cleanup."""

from typing import Dict, List, Optional
from ariadne.config.config_manager import ConfigManager
from ariadne.core.exceptions import PluginException
from ariadne.core.interfaces import IEventBus, ILogger, IPlugin
from ariadne.plugins.discovery import PluginDiscovery, PluginManifest
from ariadne.plugins.loader import PluginLoader
from ariadne.plugins.registry import PluginRegistry


class PluginManager:
    """Manages full lifecycle of plugins from discovery to initialization and shutdown."""

    def __init__(
        self,
        config_manager: ConfigManager,
        event_bus: IEventBus,
        registry: PluginRegistry,
        discovery: Optional[PluginDiscovery] = None,
        loader: Optional[PluginLoader] = None,
        logger: Optional[ILogger] = None,
    ) -> None:
        self.config_manager = config_manager
        self.event_bus = event_bus
        self.registry = registry
        self.discovery = discovery or PluginDiscovery(logger=logger)
        self.loader = loader or PluginLoader(logger=logger)
        self.logger = logger

    async def discover_and_load_all(self) -> int:
        """Discover all manifests, load plugin instances, initialize them, and register in registry."""
        manifests = self.discovery.discover_manifests()
        loaded_count = 0

        for manifest in manifests:
            try:
                plugin = self.loader.load_plugin(manifest)

                # Extract plugin specific config if available
                modules_cfg = self.config_manager.config.modules or {}
                plugin_cfg = modules_cfg.get(manifest.id, {})

                success = await plugin.initialize(config=plugin_cfg, event_bus=self.event_bus)
                if success:
                    self.registry.register(manifest, plugin)
                    loaded_count += 1
                else:
                    if self.logger:
                        self.logger.warning(
                            f"Plugin initialize() returned False for {manifest.id}. Skipping."
                        )
            except Exception as exc:
                if self.logger:
                    self.logger.error(
                        f"Failed to load or initialize plugin '{manifest.id}': {exc}", exc_info=exc
                    )

        if self.logger:
            self.logger.info(f"Plugin lifecycle: Discovered and loaded {loaded_count} plugin(s).")
        return loaded_count

    async def shutdown_all(self) -> None:
        """Call cleanup() on all registered plugins cleanly."""
        for manifest in self.registry.list_all_manifests():
            plugin = self.registry.get_plugin(manifest.id)
            if plugin:
                try:
                    await plugin.cleanup()
                except Exception as exc:
                    if self.logger:
                        self.logger.warning(f"Error during cleanup of plugin '{manifest.id}': {exc}")
        self.registry.clear()
