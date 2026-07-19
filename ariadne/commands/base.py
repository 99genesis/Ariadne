"""Base class and common execution routines for all Ariadne CLI commands."""

import argparse
import sys
from abc import ABC, abstractmethod
from typing import List, Optional
from rich.console import Console
from rich.prompt import Prompt

from ariadne.core.interfaces import CommandContext, CommandManualInfo, ICommand, IEventBus, INoteRepository
from ariadne.core.models import IntelligenceResult, TargetEntity
from ariadne.export.pipeline import ExportPipeline
from ariadne.plugins.pipeline import ExecutionPipeline
from ariadne.plugins.registry import PluginRegistry
from ariadne.providers.provider_manager import ProviderManager


class BaseCommand(ICommand, ABC):
    """Abstract base implementation providing shared review and intelligence pipeline execution."""

    @property
    @abstractmethod
    def command_name(self) -> str:
        """Name of the command triggered from CLI e.g. 'username', 'image'."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of the command."""
        pass

    @property
    def manual_info(self) -> CommandManualInfo:
        """Default manual info fallback."""
        return CommandManualInfo(
            name=self.command_name,
            purpose=self.description,
            short_usage=f"{self.command_name} <hedef>",
            usage_pattern=f"{self.command_name} <hedef> [seçenekler]",
            required_params=["hedef"],
            optional_params=["-m, --metadata"],
            examples=[f"{self.command_name} target_example"],
            workflow=["Tarama başlatılır", "Bulgular derlenir", "Obsidian kasasına aktarılır"],
            notes=["Daha fazla parametre için help kullanabilirsiniz."],
            error_missing_arg=f"{self.command_name} komutu için hedef belirtilmedi.",
        )

    @abstractmethod
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure command specific CLI arguments and flags."""
        pass

    @abstractmethod
    async def execute(self, args: argparse.Namespace, context: CommandContext) -> None:
        """Execute the command asynchronously within the provided context."""
        pass

    def run_interactive_review(
        self, results: List[IntelligenceResult], context: CommandContext
    ) -> List[IntelligenceResult]:
        """Present findings in terminal and ask user which items to export."""
        if not context.is_interactive or not sys.stdin.isatty():
            return results

        console = Console()
        console.print("\n[bold cyan]─── Scan Finished: Interactive Review ───[/bold cyan]")
        console.print(f"[bold yellow]{len(results)} finding(s) detected. Select findings to export:[/bold yellow]\n")

        for idx, res in enumerate(results, 1):
            conf_val = getattr(res, "confidence_score", getattr(res, "confidence", 1.0))
            conf_str = f"{conf_val * 100:.0f}%"
            console.print(f"  [bold cyan]\\[{idx}][/bold cyan] [bold white]{res.title}[/bold white]")
            console.print(f"      Confidence: [green]{conf_str}[/green] | Source: [dim]{res.source_plugin}[/dim]")
            meta_dict = getattr(res, "metadata", getattr(res, "data", {}))
            url = meta_dict.get("url", getattr(res, "url", None))
            if url:
                console.print(f"      URL: [blue underline]{url}[/blue underline]")
            if meta_dict:
                preview = ", ".join(f"{k}: {v}" for k, v in list(meta_dict.items())[:4])
                if preview:
                    console.print(f"      Data: [dim]{preview}[/dim]")
            console.print("  ──────────────────────────────────────────────────────")

        while True:
            try:
                choice = Prompt.ask(
                    "\n[bold yellow]Select findings[/bold yellow] ([green]1[/green], [green]1 2[/green], [green]all[/green], [red]cancel[/red])",
                    default="all",
                ).strip().lower()
            except (KeyboardInterrupt, EOFError):
                choice = "cancel"

            if choice in ("cancel", "c", "exit", "q"):
                console.print("[yellow]Export cancelled by user. No records written.[/yellow]")
                return []
            elif choice in ("all", "a", "*"):
                return results
            else:
                try:
                    indices = [int(token) for token in choice.replace(",", " ").split()]
                    selected = []
                    for idx in indices:
                        if 1 <= idx <= len(results):
                            selected.append(results[idx - 1])
                        else:
                            console.print(f"[red]Index {idx} out of range (1-{len(results)})[/red]")
                            break
                    else:
                        if selected:
                            return selected
                        console.print("[red]Please select valid numbers e.g. '1' or '1 2'[/red]")
                except ValueError:
                    console.print("[red]Invalid choice. Enter item numbers, 'all', or 'cancel'.[/red]")

    async def run_intelligence_command(
        self, target: TargetEntity, context: CommandContext, command_override: Optional[str] = None
    ) -> List[str]:
        """Execute intelligence pipeline, prompt for review, and export approved notes."""
        registry = context.container.resolve(PluginRegistry)
        provider_manager = context.container.resolve(ProviderManager)
        event_bus = context.container.resolve(IEventBus)
        repository = context.container.resolve(INoteRepository)

        pipeline = ExecutionPipeline(registry, provider_manager, event_bus, context.logger)
        cmd_name = command_override or self.command_name
        results = await pipeline.run(target, command_name=cmd_name)

        if not results:
            console = Console()
            console.print(f"[yellow]No intelligence findings discovered for target '{target.target_id}'.[/yellow]")
            return []

        selected_results = self.run_interactive_review(results, context)
        if not selected_results:
            return []

        orchestrator = None
        if hasattr(context, "container") and context.container and hasattr(context.container, "resolve"):
            try:
                from ariadne.core.interfaces import IFusionOrchestrator
                orchestrator = context.container.resolve(IFusionOrchestrator)
            except Exception:
                pass

        export_pipe = ExportPipeline(
            repository=repository,
            vault_root=getattr(context, "vault_root", None),
            event_bus=event_bus,
            vault_name=context.vault_name,
            logger=context.logger,
            orchestrator=orchestrator,
        )
        saved_paths = await export_pipe.export(target, selected_results)

        console = Console()
        console.print(
            f"\n[bold green]✔ Export complete! Saved {len(saved_paths)} note(s) to vault '{context.vault_name}/{target.target_id}'.[/bold green]"
        )
        return saved_paths
