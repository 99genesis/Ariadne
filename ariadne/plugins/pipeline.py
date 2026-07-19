"""Asynchronous Execution Pipeline for running intelligence plugins concurrently."""

import asyncio
from typing import Dict, List, Optional
from ariadne.core.interfaces import IEventBus, ILogger, IPlugin, IProvider
from ariadne.core.models import IntelligenceResult, TargetEntity
from ariadne.plugins.registry import PluginRegistry
from ariadne.plugins.sandbox import PluginSandbox
from ariadne.providers.provider_manager import ProviderManager


class ExecutionPipeline:
    """Runs capable plugins concurrently against a target entity with error isolation."""

    def __init__(
        self,
        registry: PluginRegistry,
        provider_manager: ProviderManager,
        event_bus: IEventBus,
        logger: Optional[ILogger] = None,
    ) -> None:
        self.registry = registry
        self.provider_manager = provider_manager
        self.event_bus = event_bus
        self.logger = logger
        self.sandbox = PluginSandbox(timeout_seconds=60.0, logger=logger)

    async def _safe_execute_plugin(
        self,
        plugin: IPlugin,
        target: TargetEntity,
        providers_map: Dict[str, IProvider],
    ) -> List[IntelligenceResult]:
        """Execute a single plugin safely with error boundaries via PluginSandbox."""
        res = await self.sandbox.execute_plugin(plugin, target, providers_map)
        if not res.success and res.error:
            print(f"\n❌ [bold red]Plugin Hatası ({plugin.plugin_id})[/bold red]")
            print(f"Hata detayı: {res.error}\n")
        return res.results

    async def run(self, target: TargetEntity, command_name: Optional[str] = None) -> List[IntelligenceResult]:
        """Run all active capable plugins concurrently for the target entity.

        Args:
            target: The TargetEntity under investigation.
            command_name: Optional CLI command triggered e.g. 'username' or 'image'.

        Returns:
            Aggregated list of all IntelligenceResult objects produced across all plugins.
        """
        if command_name:
            active_plugins = self.registry.list_active_plugins_for_command(command_name, target)
        else:
            active_plugins = self.registry.list_active_plugins_for_target(target)

        if not active_plugins:
            if self.logger:
                self.logger.warning(
                    f"No active plugins found capable of handling target '{target.target_id}' (command: {command_name or target.target_type})"
                )
            return []

        providers_list = self.provider_manager.list_registered_providers()
        providers_map: Dict[str, IProvider] = {p.provider_id: p for p in providers_list}

        if self.logger:
            self.logger.info(
                f"Starting Execution Pipeline for '{target.target_id}' across {len(active_plugins)} plugin(s)..."
            )

        tasks = [
            self._safe_execute_plugin(plugin, target, providers_map)
            for plugin in active_plugins
        ]
        results_nested: List[List[IntelligenceResult]] = await asyncio.gather(
            *tasks, return_exceptions=False
        )

        aggregated_results: List[IntelligenceResult] = []
        for r_list in results_nested:
            aggregated_results.extend(r_list)

        if self.logger:
            self.logger.info(
                f"Execution Pipeline finished for '{target.target_id}'. Total findings: {len(aggregated_results)}"
            )

        return aggregated_results
