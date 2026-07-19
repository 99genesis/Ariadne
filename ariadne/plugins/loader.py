"""Dynamic Plugin Loader safely loading Python modules from discovered directories.

Ensures that loaded modules implement the IPlugin protocol before returning instances.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Optional

from ariadne.core.exceptions import PluginException
from ariadne.core.interfaces import ILogger, IPlugin
from ariadne.plugins.discovery import PluginManifest


class PluginLoader:
    """Dynamically loads plugin main.py module and retrieves IPlugin instance."""

    def __init__(self, logger: Optional[ILogger] = None) -> None:
        self.logger = logger

    def load_plugin(self, manifest: PluginManifest) -> IPlugin:
        """Dynamically load and verify IPlugin instance from manifest directory.

        Args:
            manifest: Validated PluginManifest with attached plugin_dir path.

        Returns:
            An instantiated object implementing IPlugin.

        Raises:
            PluginException: If module cannot be imported or does not expose get_plugin().
        """
        if not manifest.plugin_dir or not manifest.plugin_dir.exists():
            raise PluginException(
                message=f"Plugin directory missing for manifest {manifest.id}",
                plugin_id=manifest.id,
            )

        main_py = manifest.plugin_dir / "main.py"
        if not main_py.exists():
            raise PluginException(
                message=f"main.py not found inside plugin directory {manifest.plugin_dir}",
                plugin_id=manifest.id,
            )

        module_name = f"ariadne_dynamic_plugin_{manifest.id.replace('.', '_')}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, main_py)
            if not spec or not spec.loader:
                raise PluginException(
                    message=f"Failed to create import spec for {main_py}",
                    plugin_id=manifest.id,
                )

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            if not hasattr(module, "get_plugin"):
                raise PluginException(
                    message=f"Plugin module {main_py} does not expose required function get_plugin() -> IPlugin",
                    plugin_id=manifest.id,
                )

            plugin_instance: IPlugin = module.get_plugin()
            # Verify protocol implementation check
            if not hasattr(plugin_instance, "plugin_id") or not hasattr(plugin_instance, "execute"):
                raise PluginException(
                    message=f"Returned instance from {main_py} does not conform to IPlugin protocol",
                    plugin_id=manifest.id,
                )

            if self.logger:
                self.logger.debug(f"Successfully loaded plugin instance: {plugin_instance.plugin_id}")
            return plugin_instance

        except Exception as exc:
            raise PluginException(
                message=f"Error while dynamically loading module {main_py}: {exc}",
                plugin_id=manifest.id,
                details={"error": str(exc)},
            )
