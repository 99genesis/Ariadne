"""Username Provider Registry supporting automatic discovery and dynamic registration.

Uses pkgutil and importlib to discover platform providers in subpackages without modifying
central code (`Open/Closed Principle`).
"""

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Set

from ariadne.core.interfaces import ILogger
from ariadne.plugins.builtin.username_intel.providers.base import BaseUsernameProvider, IUsernameProvider


class UsernameProviderRegistry:
    """Central registry maintaining active username providers with dynamic package discovery."""

    def __init__(self, logger: Optional[ILogger] = None) -> None:
        self.logger = logger
        self._providers: Dict[str, IUsernameProvider] = {}
        self._disabled_names: Set[str] = set()

    def register(self, provider: IUsernameProvider) -> None:
        """Register a username provider instance."""
        name = provider.provider_name.strip().lower()
        self._providers[name] = provider
        if self.logger:
            self.logger.debug(f"Registered username provider: {provider.provider_name} [{provider.category}]")

    def discover(self, providers_package_path: Optional[Path] = None, package_prefix: str = "ariadne.plugins.builtin.username_intel.providers") -> int:
        """Dynamically discover and register all IUsernameProvider subclasses across subdirectories."""
        if not providers_package_path:
            providers_package_path = Path(__file__).parent / "providers"

        discovered_count = 0
        if not providers_package_path.exists():
            return discovered_count

        # Iterate over category packages inside providers/ (e.g., developer, social, gaming, forum)
        for _, pkg_name, is_pkg in pkgutil.iter_modules([str(providers_package_path)]):
            full_pkg_name = f"{package_prefix}.{pkg_name}"
            sub_path = providers_package_path / pkg_name

            if is_pkg and sub_path.exists():
                for _, mod_name, _ in pkgutil.iter_modules([str(sub_path)]):
                    full_mod_name = f"{full_pkg_name}.{mod_name}"
                    try:
                        module = importlib.import_module(full_mod_name)
                        for attr_name, obj in inspect.getmembers(module, inspect.isclass):
                            if (
                                issubclass(obj, BaseUsernameProvider)
                                and obj is not BaseUsernameProvider
                                and not inspect.isabstract(obj)
                            ):
                                instance = obj()
                                self.register(instance)
                                discovered_count += 1
                    except Exception as exc:
                        if self.logger:
                            self.logger.warning(f"Failed to load provider module '{full_mod_name}': {exc}")
            else:
                # Direct module under providers/
                try:
                    module = importlib.import_module(full_pkg_name)
                    for attr_name, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, BaseUsernameProvider)
                            and obj is not BaseUsernameProvider
                            and not inspect.isabstract(obj)
                        ):
                            instance = obj()
                            self.register(instance)
                            discovered_count += 1
                except Exception as exc:
                    if self.logger:
                        self.logger.warning(f"Failed to load provider module '{full_pkg_name}': {exc}")

        if self.logger:
            self.logger.info(f"Discovered and registered {discovered_count} username providers from {providers_package_path}")
        return discovered_count

    def disable(self, name: str) -> bool:
        """Disable a provider by name."""
        key = name.strip().lower()
        if key in self._providers:
            self._disabled_names.add(key)
            if self.logger:
                self.logger.info(f"Disabled username provider: {name}")
            return True
        return False

    def enable(self, name: str) -> bool:
        """Enable a disabled provider by name."""
        key = name.strip().lower()
        if key in self._disabled_names:
            self._disabled_names.remove(key)
            if self.logger:
                self.logger.info(f"Enabled username provider: {name}")
            return True
        return False

    def get_provider(self, name: str) -> Optional[IUsernameProvider]:
        """Get provider by exact or case-insensitive name if enabled."""
        key = name.strip().lower()
        if key in self._disabled_names:
            return None
        return self._providers.get(key)

    def list_providers(self, enabled_only: bool = True) -> List[IUsernameProvider]:
        """List registered providers sorted by category and name."""
        results = []
        for key, p in self._providers.items():
            if enabled_only and key in self._disabled_names:
                continue
            results.append(p)
        return sorted(results, key=lambda p: (p.category, p.provider_name))

    def get_by_category(self, category: str, enabled_only: bool = True) -> List[IUsernameProvider]:
        """List providers matching specific category e.g. developer."""
        cat_clean = category.strip().lower()
        return [
            p for p in self.list_providers(enabled_only=enabled_only)
            if p.category.lower() == cat_clean
        ]

    def get_all_categories(self) -> List[str]:
        """Return sorted unique categories."""
        return sorted({p.category for p in self.list_providers(enabled_only=True)})
