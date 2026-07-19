"""Profile command handler placeholder."""

import argparse
from rich.console import Console
from ariadne.commands.base import BaseCommand
from ariadne.core.interfaces import CommandContext, CommandManualInfo


class ProfileCommand(BaseCommand):
    """Placeholder handler for multi-network digital footprint aggregation (`profile <target>`)."""

    @property
    def command_name(self) -> str:
        return "profile"

    @property
    def description(self) -> str:
        return "Bir hedef hakkında daha önce export edilen bütün bilgileri tek ekranda toplar."

    @property
    def manual_info(self) -> CommandManualInfo:
        return CommandManualInfo(
            name="PROFILE",
            purpose=self.description,
            short_usage="profile <target>",
            usage_pattern="profile <hedef_adi>",
            required_params=["<hedef_adi> : Toplu profil analizi yapılacak hedef adı (örn: endann, torvalds)"],
            optional_params=[],
            examples=[
                "profile endann",
                "profile torvalds",
            ],
            workflow=[
                "Hedefe ait Obsidian kasasındaki tüm notlar (`[[Username_<target>]]`, `[[IP_<id>]]`) birleştirilir",
                "Çapraz istihbarat ilişkileri graf üzerinde filtrelenir",
                "Kullanıcıya bütünleşik dijital kimlik paneli sunulur",
            ],
            notes=[
                "Bu komut mevcut kasa verilerini okuyarak birleştirilmiş istihbarat profili hazırlar.",
            ],
            error_missing_arg="profile komutu bir hedef profil kimliği bekliyor.\nDoğru kullanım: profile endann\nDetaylı yardım: help profile",
        )

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("target", help="Hedef profil kimliği")

    async def execute(self, args: argparse.Namespace, context: CommandContext) -> None:
        console = Console()
        from ariadne.core.models import IntelligenceResult, TargetEntity, TargetType
        from ariadne.core.interfaces import IFusionOrchestrator, INoteRepository
        from ariadne.export.pipeline import ExportPipeline
        from rich.table import Table

        target = TargetEntity(
            target_id=args.target,
            display_name=args.target,
            target_type=TargetType.USERNAME,
        )

        console.print(
            f"\n[bold cyan]⚡ Initializing Intelligence Fusion for target:[/bold cyan] [bold yellow]'{target.display_name}'[/bold yellow]"
        )

        repository = context.container.resolve(INoteRepository) if hasattr(context, "container") and context.container else None
        orchestrator = context.container.resolve(IFusionOrchestrator) if hasattr(context, "container") and context.container else None

        results = []
        if repository and hasattr(repository, "list_notes_by_target"):
            try:
                notes = await repository.list_notes_by_target(context.vault_name, target.target_id)
                for note in notes:
                    if "report-master" in note.note_id or "Master_Report_" in note.relative_path:
                        continue
                    results.append(
                        IntelligenceResult(
                            title=note.title,
                            entity_type=note.entity_type,
                            source_plugin=note.source_module or "vault_note",
                            content_markdown=note.body_content,
                            confidence_score=note.confidence_score or 0.8,
                            tags=note.tags,
                            metadata=note.raw_frontmatter,
                        )
                    )
            except Exception as e:
                if context.logger:
                    context.logger.warning(f"Failed loading notes for {target.target_id}: {e}")

        # If no notes exist, check if we can scan or run hub across active plugins
        if not results:
            if hasattr(context, "container") and context.container and hasattr(context.container, "resolve"):
                try:
                    from ariadne.core.interfaces import IIntelligenceHub
                    from ariadne.plugins.registry import PluginRegistry
                    hub = context.container.resolve(IIntelligenceHub)
                    registry = context.container.resolve(PluginRegistry)
                    active_plugins = registry.list_active_plugins_for_command("profile", target)
                    if active_plugins:
                        console.print(
                            f"[cyan]No existing vault notes found. Running live scan across {len(active_plugins)} active plugin(s)...[/cyan]"
                        )
                        results = await hub.execute_pipeline(target, [], active_plugins)
                except Exception:
                    pass

        if not results:
            console.print(
                f"[yellow]No intelligence findings discovered in vault '{context.vault_name}' for '{target.target_id}'.[/yellow]"
            )
            return

        if not orchestrator:
            from ariadne.fusion.orchestrator import IntelligenceFusionOrchestrator
            orchestrator = IntelligenceFusionOrchestrator(logger=context.logger)

        master_report = await orchestrator.fuse(target, results)

        # Display Rich UI dashboard
        table = Table(title="🔍 Intelligence Fusion Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="bold white")
        table.add_column("Value", style="bold yellow")

        pct = int(master_report.fusion_score * 100)
        table.add_row("Identity Convergence Probability", f"{pct}% ({master_report.fusion_score:.2f})")
        if master_report.risk_assessment:
            lvl = (
                master_report.risk_assessment.overall_level.value
                if hasattr(master_report.risk_assessment.overall_level, "value")
                else str(master_report.risk_assessment.overall_level)
            )
            table.add_row("Threat Exposure Score", f"{master_report.risk_assessment.overall_score}/100 ({lvl})")
        if master_report.graph_snapshot:
            table.add_row(
                "Entity Graph Topology",
                f"{len(master_report.graph_snapshot.nodes)} Nodes / {len(master_report.graph_snapshot.edges)} Edges",
            )
        if master_report.timeline:
            table.add_row("Chronological Timeline Events", str(len(master_report.timeline.events)))
        table.add_row("Total Verified Discoveries", str(len(results)))

        console.print("\n")
        console.print(table)

        # Export master report
        export_pipe = ExportPipeline(
            repository=repository,
            vault_root=getattr(context, "vault_root", None),
            event_bus=context.event_bus,
            vault_name=context.vault_name,
            logger=context.logger,
            orchestrator=orchestrator,
        )
        saved_paths = await export_pipe.export(target, results, master_report=master_report)
        console.print(
            f"[bold green]✔ Master Intelligence Report exported successfully! ({len(saved_paths)} file(s) updated in vault).[/bold green]\n"
        )
