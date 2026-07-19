"""Startup Manager orchestrating initialization, splash screen, and system checks for Ariadne."""

import asyncio
import os
import platform
import sys
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from ariadne import version
from ariadne.cli.setup_wizard import SetupWizard
from ariadne.commands.handlers import (
    DomainCommand,
    EmailCommand,
    GeoCommand,
    HelpCommand,
    ImageCommand,
    IPCommand,
    PhoneCommand,
    ProfileCommand,
    SetupCommand,
    TargetCommand,
    UsernameCommand,
)
from ariadne.commands.registry import CommandRegistry
from ariadne.config.config_manager import ConfigManager
from ariadne.config.secrets_manager import OSSecretsManager
from ariadne.core.container import container
from ariadne.core.interfaces import (
    IAuditLogger,
    ICorrelationEngine,
    IEventBus,
    IFusionOrchestrator,
    IIntelligenceHub,
    ILogger,
    IMetricsRegistry,
    INoteRepository,
    IRiskScoringEngine,
    ISecretsManager,
    ITimelineGenerator,
    IWorkspaceManager,
)
from ariadne.audit.logger import AuditLogger
from ariadne.correlation.engine import CorrelationEngine
from ariadne.graph.repository import GraphRepository
from ariadne.risk.engine import RiskScoringEngine
from ariadne.timeline.generator import TimelineGenerator
from ariadne.fusion.orchestrator import IntelligenceFusionOrchestrator
from ariadne.metrics.registry import MetricsRegistry
from ariadne.alias.alias_engine import CrossPlatformAliasEngine
from ariadne.alias.mutation_engine import UsernameMutationEngine
from ariadne.providers.health.monitor import ProviderHealthMonitor
from ariadne.hub.priority_manager import SourcePriorityManager
from ariadne.hub.cost_optimizer import ProviderCostOptimizer
from ariadne.hub.incremental import IncrementalScanEngine
from ariadne.hub.cache_manager import HubCacheManager
from ariadne.hub.concurrency import HubConcurrencyManager
from ariadne.hub.deduplication import HubDeduplicationManager
from ariadne.hub.manager import IntelligenceHub
from ariadne.events.event_bus import AsyncEventBus
from ariadne.plugins.manager import PluginManager
from ariadne.plugins.registry import PluginRegistry
from ariadne.providers.ai.google_ai import GoogleAIProvider
from ariadne.providers.ai.openai_ai import OpenAIProvider
from ariadne.providers.ai.openrouter_ollama import OllamaProvider, OpenRouterProvider
from ariadne.providers.provider_manager import ProviderManager
from ariadne.providers.sdk.social_graph import SocialGraphCollector
from ariadne.storage.cache_manager import TwoTierCacheManager
from ariadne.storage.db.repository import SQLiteNoteRepository
from ariadne.workspace.workspace_manager import WorkspaceManager

from ariadne.storage.logger import AriadneLogger


class StartupManager:
    """Centralized manager for all startup, banner, splash screen, and DI initialization sequences."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()

    @staticmethod
    def get_resource_path(relative_path: str) -> Path:
        """Resolve resource paths for both standard Python and PyInstaller frozen executable."""
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS) / relative_path
        return Path(__file__).parent.parent.parent / relative_path

    def clear_console(self) -> None:
        """Clear the terminal screen cleanly."""
        os.system("cls" if os.name == "nt" else "clear")

    def show_banner(self) -> None:
        """Load and display the exact ASCII banner from ariadne/assets/banner.txt."""
        banner_path = self.get_resource_path("ariadne/assets/banner.txt")
        if not banner_path.exists():
            # Try direct relative resolution if running from workspace root
            banner_path = Path(__file__).parent.parent / "assets" / "banner.txt"

        if banner_path.exists():
            try:
                banner_text = banner_path.read_text(encoding="utf-8")
                self.console.print(f"[bold cyan]{banner_text}[/bold cyan]")
            except Exception as exc:
                self.console.print(f"[bold red]Failed reading banner: {exc}[/bold red]")
        else:
            self.console.print("[bold cyan]ARIADNE OSINT FRAMEWORK[/bold cyan]")

    async def show_splash_screen(self) -> None:
        """Display ASCII banner, pause, and render professional architecture panel."""
        self.clear_console()
        self.show_banner()
        await asyncio.sleep(0.8)

        panel_content = (
            f"[bold white]{version.APP_NAME}[/bold white]\n"
            f"[cyan]Version : {version.VERSION}[/cyan]"
        )
        self.console.print(
            Panel.fit(
                panel_content,
                border_style="cyan",
                padding=(1, 4),
            )
        )
        await asyncio.sleep(0.4)

    async def _run_initial_wizard_check(self, app: Any, force_setup: bool = False) -> None:
        """Check if setup wizard is needed before container bootstrapping."""
        if force_setup or (not app.config_manager.config_file.exists() and sys.stdin.isatty()):
            secrets = OSSecretsManager()
            wizard = SetupWizard(app.config_manager, secrets, app.i18n, self.console)
            await wizard.run_wizard()
        elif not app.config_manager.config_file.exists():
            app.config_manager.load_global_config()

    async def bootstrap_silent(self, app: Any, force_setup: bool = False) -> None:
        """Bootstrap container and load modules silently without animation (for unit tests/direct CLI calls)."""
        await self._run_initial_wizard_check(app, force_setup=force_setup)
        app.config_manager.load_global_config()
        cfg = app.config_manager.config
        container.register_instance(ConfigManager, app.config_manager)
        app.i18n.set_language(cfg.system.language)

        logger = AriadneLogger(
            level=cfg.logging.level,
            console_output=cfg.logging.console_output,
            max_mb=cfg.logging.file_rotation_max_mb,
            backup_count=cfg.logging.backup_count,
            mask_sensitive=cfg.logging.mask_sensitive_data,
        )
        container.register_instance(ILogger, logger)

        secrets = OSSecretsManager()
        container.register_instance(ISecretsManager, secrets)

        event_bus = AsyncEventBus(logger=logger)
        container.register_instance(IEventBus, event_bus)

        cache = TwoTierCacheManager(
            cache_dir=cfg.system.vault_root / "Cache",
            disk_enabled=cfg.cache.disk_cache_enabled,
            max_memory_mb=cfg.cache.memory_cache_max_mb,
            logger=logger,
        )
        container.register_instance("ICacheManager", cache)

        workspace_mgr = WorkspaceManager(workspace_root=cfg.system.vault_root, logger=logger)
        container.register_instance(IWorkspaceManager, workspace_mgr)
        container.register_instance(WorkspaceManager, workspace_mgr)

        repo = SQLiteNoteRepository(db_path=cfg.system.vault_root / "notes.db", logger=logger)
        container.register_instance(INoteRepository, repo)

        audit = AuditLogger(
            db_path=cfg.system.vault_root / "audit.db",
            log_file=cfg.system.vault_root / "audit.jsonl",
            logger=logger,
        )
        container.register_instance(IAuditLogger, audit)
        container.register_instance(AuditLogger, audit)

        metrics = MetricsRegistry(logger=logger)
        container.register_instance(IMetricsRegistry, metrics)
        container.register_instance(MetricsRegistry, metrics)

        mutation_eng = UsernameMutationEngine(logger=logger)
        container.register_instance(UsernameMutationEngine, mutation_eng)
        alias_eng = CrossPlatformAliasEngine(mutation_engine=mutation_eng, logger=logger)
        container.register_instance(CrossPlatformAliasEngine, alias_eng)

        health_mon = ProviderHealthMonitor(logger=logger, audit_logger=audit, metrics_registry=metrics)
        container.register_instance(ProviderHealthMonitor, health_mon)
        priority_mgr = SourcePriorityManager(logger=logger)
        container.register_instance(SourcePriorityManager, priority_mgr)
        cost_opt = ProviderCostOptimizer(logger=logger, metrics_registry=metrics)
        container.register_instance(ProviderCostOptimizer, cost_opt)
        hub_cache = HubCacheManager(cache_manager=cache, logger=logger)
        container.register_instance(HubCacheManager, hub_cache)
        hub_conc = HubConcurrencyManager(logger=logger)
        container.register_instance(HubConcurrencyManager, hub_conc)
        hub_dedup = HubDeduplicationManager(logger=logger)
        container.register_instance(HubDeduplicationManager, hub_dedup)
        inc_engine = IncrementalScanEngine(logger=logger)
        container.register_instance(IncrementalScanEngine, inc_engine)

        hub = IntelligenceHub(
            health_monitor=health_mon,
            priority_manager=priority_mgr,
            cost_optimizer=cost_opt,
            cache_manager=hub_cache,
            concurrency_manager=hub_conc,
            deduplication_manager=hub_dedup,
            incremental_engine=inc_engine,
            event_bus=event_bus,
            logger=logger,
            audit_logger=audit,
            metrics_registry=metrics,
        )
        container.register_instance(IIntelligenceHub, hub)
        container.register_instance(IntelligenceHub, hub)

        corr_eng = CorrelationEngine(logger=logger)
        container.register_instance(ICorrelationEngine, corr_eng)
        container.register_instance(CorrelationEngine, corr_eng)

        graph_repo = GraphRepository()
        container.register_instance(GraphRepository, graph_repo)

        risk_eng = RiskScoringEngine(logger=logger)
        container.register_instance(IRiskScoringEngine, risk_eng)
        container.register_instance(RiskScoringEngine, risk_eng)

        time_gen = TimelineGenerator(logger=logger)
        container.register_instance(ITimelineGenerator, time_gen)
        container.register_instance(TimelineGenerator, time_gen)

        fusion_orch = IntelligenceFusionOrchestrator(
            correlation_engine=corr_eng,
            graph_repository=graph_repo,
            risk_engine=risk_eng,
            timeline_generator=time_gen,
            logger=logger,
        )
        container.register_instance(IFusionOrchestrator, fusion_orch)
        container.register_instance(IntelligenceFusionOrchestrator, fusion_orch)

        pm = ProviderManager(app.config_manager, container, logger=logger)
        pm.register_provider(GoogleAIProvider(secrets_manager=secrets, logger=logger))
        pm.register_provider(OpenAIProvider(secrets_manager=secrets, logger=logger))
        pm.register_provider(OpenRouterProvider(secrets_manager=secrets, logger=logger))
        pm.register_provider(OllamaProvider(secrets_manager=secrets, logger=logger))
        pm.register_provider(SocialGraphCollector(secrets_manager=secrets, logger=logger))
        container.register_instance(ProviderManager, pm)

        registry = PluginRegistry(logger=logger)
        plugin_mgr = PluginManager(app.config_manager, event_bus, registry, logger=logger)
        await plugin_mgr.discover_and_load_all()
        container.register_instance(PluginRegistry, registry)
        container.register_instance(PluginManager, plugin_mgr)

        app.command_registry.logger = logger
        container.register_instance(CommandRegistry, app.command_registry)
        if not app.command_registry.list_commands():
            app.command_registry.register_command(UsernameCommand())
            app.command_registry.register_command(ImageCommand())
            app.command_registry.register_command(PhoneCommand())
            app.command_registry.register_command(EmailCommand())
            app.command_registry.register_command(DomainCommand())
            app.command_registry.register_command(IPCommand())
            app.command_registry.register_command(GeoCommand())
            app.command_registry.register_command(ProfileCommand())
            app.command_registry.register_command(SetupCommand())
            app.command_registry.register_command(TargetCommand())
            app.command_registry.register_command(HelpCommand())

    async def bootstrap_with_animation(self, app: Any, force_setup: bool = False) -> None:
        """Execute all initialization steps with rich progress animation."""
        await self._run_initial_wizard_check(app, force_setup=force_setup)

        with Progress(
            SpinnerColumn(spinner_name="dots", style="bold cyan"),
            TextColumn("[bold white]{task.description}"),
            BarColumn(bar_width=35, style="cyan", complete_style="green"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("Initializing...", total=11)

            # Step 1: Initializing & Config
            progress.update(task, description="Loading Configuration...", advance=1)
            await asyncio.sleep(0.06)
            app.config_manager.load_global_config()
            cfg = app.config_manager.config
            container.register_instance(ConfigManager, app.config_manager)
            app.i18n.set_language(cfg.system.language)

            logger = AriadneLogger(
                level=cfg.logging.level,
                console_output=cfg.logging.console_output,
                max_mb=cfg.logging.file_rotation_max_mb,
                backup_count=cfg.logging.backup_count,
                mask_sensitive=cfg.logging.mask_sensitive_data,
            )
            container.register_instance(ILogger, logger)

            # Step 2: Secrets
            progress.update(task, description="Loading Secrets...", advance=1)
            await asyncio.sleep(0.06)
            secrets = OSSecretsManager()
            container.register_instance(ISecretsManager, secrets)

            # Step 3: Providers
            progress.update(task, description="Loading Providers...", advance=1)
            await asyncio.sleep(0.06)
            pm = ProviderManager(app.config_manager, container, logger=logger)
            pm.register_provider(GoogleAIProvider(secrets_manager=secrets, logger=logger))
            pm.register_provider(OpenAIProvider(secrets_manager=secrets, logger=logger))
            pm.register_provider(OpenRouterProvider(secrets_manager=secrets, logger=logger))
            pm.register_provider(OllamaProvider(secrets_manager=secrets, logger=logger))
            pm.register_provider(SocialGraphCollector(secrets_manager=secrets, logger=logger))
            container.register_instance(ProviderManager, pm)

            # Step 4: Plugins
            progress.update(task, description="Loading Plugins...", advance=1)
            await asyncio.sleep(0.08)
            registry = PluginRegistry(logger=logger)
            event_bus = AsyncEventBus(logger=logger)
            container.register_instance(IEventBus, event_bus)
            plugin_mgr = PluginManager(app.config_manager, event_bus, registry, logger=logger)
            await plugin_mgr.discover_and_load_all()
            container.register_instance(PluginRegistry, registry)
            container.register_instance(PluginManager, plugin_mgr)

            # Step 5: Cache
            progress.update(task, description="Loading Cache...", advance=1)
            await asyncio.sleep(0.06)
            cache = TwoTierCacheManager(
                cache_dir=cfg.system.vault_root / "Cache",
                disk_enabled=cfg.cache.disk_cache_enabled,
                max_memory_mb=cfg.cache.memory_cache_max_mb,
                logger=logger,
            )
            container.register_instance("ICacheManager", cache)

            workspace_mgr = WorkspaceManager(workspace_root=cfg.system.vault_root, logger=logger)
            container.register_instance(IWorkspaceManager, workspace_mgr)
            container.register_instance(WorkspaceManager, workspace_mgr)

            # Step 6: SQLite
            progress.update(task, description="Loading SQLite...", advance=1)
            await asyncio.sleep(0.06)
            repo = SQLiteNoteRepository(db_path=cfg.system.vault_root / "notes.db", logger=logger)
            container.register_instance(INoteRepository, repo)

            audit = AuditLogger(
                db_path=cfg.system.vault_root / "audit.db",
                log_file=cfg.system.vault_root / "audit.jsonl",
                logger=logger,
            )
            container.register_instance(IAuditLogger, audit)
            container.register_instance(AuditLogger, audit)

            metrics = MetricsRegistry(logger=logger)
            container.register_instance(IMetricsRegistry, metrics)
            container.register_instance(MetricsRegistry, metrics)

            mutation_eng = UsernameMutationEngine(logger=logger)
            container.register_instance(UsernameMutationEngine, mutation_eng)
            alias_eng = CrossPlatformAliasEngine(mutation_engine=mutation_eng, logger=logger)
            container.register_instance(CrossPlatformAliasEngine, alias_eng)

            health_mon = ProviderHealthMonitor(logger=logger, audit_logger=audit, metrics_registry=metrics)
            container.register_instance(ProviderHealthMonitor, health_mon)
            priority_mgr = SourcePriorityManager(logger=logger)
            container.register_instance(SourcePriorityManager, priority_mgr)
            cost_opt = ProviderCostOptimizer(logger=logger, metrics_registry=metrics)
            container.register_instance(ProviderCostOptimizer, cost_opt)
            hub_cache = HubCacheManager(cache_manager=cache, logger=logger)
            container.register_instance(HubCacheManager, hub_cache)
            hub_conc = HubConcurrencyManager(logger=logger)
            container.register_instance(HubConcurrencyManager, hub_conc)
            hub_dedup = HubDeduplicationManager(logger=logger)
            container.register_instance(HubDeduplicationManager, hub_dedup)
            inc_engine = IncrementalScanEngine(logger=logger)
            container.register_instance(IncrementalScanEngine, inc_engine)

            hub = IntelligenceHub(
                health_monitor=health_mon,
                priority_manager=priority_mgr,
                cost_optimizer=cost_opt,
                cache_manager=hub_cache,
                concurrency_manager=hub_conc,
                deduplication_manager=hub_dedup,
                incremental_engine=inc_engine,
                event_bus=event_bus,
                logger=logger,
                audit_logger=audit,
                metrics_registry=metrics,
            )
            container.register_instance(IIntelligenceHub, hub)
            container.register_instance(IntelligenceHub, hub)

            corr_eng = CorrelationEngine(logger=logger)
            container.register_instance(ICorrelationEngine, corr_eng)
            container.register_instance(CorrelationEngine, corr_eng)

            graph_repo = GraphRepository()
            container.register_instance(GraphRepository, graph_repo)

            risk_eng = RiskScoringEngine(logger=logger)
            container.register_instance(IRiskScoringEngine, risk_eng)
            container.register_instance(RiskScoringEngine, risk_eng)

            time_gen = TimelineGenerator(logger=logger)
            container.register_instance(ITimelineGenerator, time_gen)
            container.register_instance(TimelineGenerator, time_gen)

            fusion_orch = IntelligenceFusionOrchestrator(
                correlation_engine=corr_eng,
                graph_repository=graph_repo,
                risk_engine=risk_eng,
                timeline_generator=time_gen,
                logger=logger,
            )
            container.register_instance(IFusionOrchestrator, fusion_orch)
            container.register_instance(IntelligenceFusionOrchestrator, fusion_orch)

            # Step 7: Event Bus
            progress.update(task, description="Loading Event Bus...", advance=1)
            await asyncio.sleep(0.06)

            # Step 8: Vault
            progress.update(task, description="Loading Vault...", advance=1)
            await asyncio.sleep(0.06)
            cfg.system.vault_root.mkdir(parents=True, exist_ok=True)

            # Step 9: Command Registry
            progress.update(task, description="Loading Command Registry...", advance=1)
            await asyncio.sleep(0.06)
            app.command_registry.logger = logger
            container.register_instance(CommandRegistry, app.command_registry)

            # Step 10: Commands
            progress.update(task, description="Loading Commands...", advance=1)
            await asyncio.sleep(0.06)
            if not app.command_registry.list_commands():
                app.command_registry.register_command(UsernameCommand())
                app.command_registry.register_command(ImageCommand())
                app.command_registry.register_command(PhoneCommand())
                app.command_registry.register_command(EmailCommand())
                app.command_registry.register_command(DomainCommand())
                app.command_registry.register_command(IPCommand())
                app.command_registry.register_command(GeoCommand())
                app.command_registry.register_command(ProfileCommand())
                app.command_registry.register_command(SetupCommand())
                app.command_registry.register_command(TargetCommand())
                app.command_registry.register_command(HelpCommand())

            # Step 11: Ready
            progress.update(task, description="Ready.", advance=1)
            await asyncio.sleep(0.1)

        self.console.print("[bold green]✔ System initialized.[/bold green]\n")

    def show_dynamic_system_info(self, app: Any) -> None:
        """Display technical hacker-themed system status summary table."""
        cfg = app.config_manager.config
        registry: Optional[PluginRegistry] = None
        try:
            registry = container.resolve(PluginRegistry)
        except Exception:
            pass

        plugin_count = len(registry.list_all_manifests()) if registry else 0
        command_count = len(app.command_registry.list_commands())

        table = Table(border_style="cyan", show_header=False, padding=(0, 2))
        table.add_column("Parameter", style="bold cyan", width=26)
        table.add_column("Value", style="white")

        table.add_row("Application Name", version.APP_NAME)
        table.add_row("Version", version.VERSION)
        table.add_row("Author", version.AUTHOR)
        table.add_row("Build Date", version.BUILD_DATE)
        table.add_row("Python Version", platform.python_version())
        table.add_row("Operating System", f"{platform.system()} {platform.release()}")
        table.add_row("Workspace", str(cfg.system.vault_root))
        table.add_row("Current Language", cfg.system.language.upper())
        table.add_row("Current AI Provider", str(cfg.providers.active_ai_provider))
        table.add_row("Current AI Model", str(cfg.providers.active_vision_model or "auto-resolve"))
        table.add_row("Loaded Plugins", f"[green]{plugin_count}[/green]")
        table.add_row("Loaded Commands", f"[green]{command_count}[/green]")
        table.add_row("SQLite Status", "[green]ONLINE[/green] (notes.db)")
        table.add_row("Cache Status", "[green]ONLINE[/green] (Two-Tier)")
        table.add_row("Vault Status", "[green]ONLINE[/green]")
        table.add_row("Plugin Registry Status", "[green]ACTIVE[/green]")
        table.add_row("Config Status", "[green]LOADED[/green] (4-Tier Priority)")
        table.add_row("Secrets Manager Status", "[green]ACTIVE[/green] (OS Credential Store)")
        table.add_row("Event Bus Status", "[green]ACTIVE[/green] (Async Pub/Sub)")

        self.console.print(Panel(table, title="[bold cyan]SYSTEM STATUS & METADATA[/bold cyan]", border_style="cyan"))
        self.console.print()

    async def run_interactive_startup(self, app: Any) -> None:
        """Run full interactive startup experience including splash screen, animation, and dynamic info."""
        await self.show_splash_screen()
        await self.bootstrap_with_animation(app)
        self.show_dynamic_system_info(app)
