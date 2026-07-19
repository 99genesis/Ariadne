"""Isolated Export Pipeline responsible for saving verified intelligence findings to Obsidian & SQLite."""

from typing import Any, List, Optional
from pathlib import Path
import asyncio
from ariadne.core.interfaces import IEventBus, IFusionOrchestrator, ILogger, INoteRepository
from ariadne.core.models import IntelligenceResult, TargetEntity
from ariadne.events.event_bus import AsyncEventBus
from ariadne.markdown.obsidian_exporter import ObsidianExporter
from ariadne.markdown.writer import MarkdownWriter
from ariadne.storage.db.indexer import BackgroundIndexer
from ariadne.fusion.report_builder import MasterReportBuilder


class ExportPipeline:
    """Exports user-reviewed intelligence results to Markdown vault and SQLite metadata store."""

    def __init__(
        self,
        repository: INoteRepository,
        vault_root: Optional[Path] = None,
        event_bus: Optional[IEventBus] = None,
        vault_name: str = "Ariadne_Workspace",
        logger: Optional[ILogger] = None,
        orchestrator: Optional[IFusionOrchestrator] = None,
    ) -> None:
        self.repository = repository
        self.vault_root = vault_root or Path("Ariadne_Workspace")
        self.event_bus = event_bus or AsyncEventBus(logger=logger)
        self.vault_name = vault_name
        self.logger = logger
        self.orchestrator = orchestrator
        self.obsidian_exporter = ObsidianExporter(logger=logger)
        self.markdown_writer = MarkdownWriter(
            vault_root=self.vault_root, event_bus=self.event_bus, logger=logger
        )

    async def export(
        self,
        target: TargetEntity,
        results: List[IntelligenceResult],
        master_report: Optional[Any] = None,
    ) -> List[str]:
        """Export intelligence findings and synthesized Master Report to Obsidian vault notes and SQLite index.

        Args:
            target: Target entity under investigation.
            results: List of user-approved IntelligenceResult objects to export.
            master_report: Optional pre-compiled MasterIntelligenceReport.

        Returns:
            List of generated/updated note file paths including Master Report.
        """
        if not results:
            if self.logger:
                self.logger.info(f"No results selected for export on target '{target.target_id}'.")
            return []

        if self.logger:
            self.logger.info(
                f"Starting Export Pipeline for '{target.target_id}' with {len(results)} finding(s)..."
            )

        vault_dir = self.vault_root / self.vault_name if self.vault_name != self.vault_root.name else self.vault_root
        await self.obsidian_exporter.initialize_vault(vault_dir, self.vault_name)

        indexer = BackgroundIndexer(
            vault_root=self.vault_root, repository=self.repository, event_bus=self.event_bus, logger=self.logger
        )
        await indexer.start()

        saved_paths: List[str] = []
        for result in results:
            try:
                note_path = await self.markdown_writer.write_finding(self.vault_name, target, result)
                saved_paths.append(str(note_path))
            except Exception as exc:
                if self.logger:
                    self.logger.error(
                        f"Failed exporting finding '{getattr(result, 'title', 'unknown')}' to Obsidian/SQLite: {exc}",
                        exc_info=exc,
                    )

        # Generate / write Master Intelligence Report
        try:
            if master_report is None:
                if self.orchestrator and hasattr(self.orchestrator, "fuse"):
                    master_report = await self.orchestrator.fuse(target, results)
                else:
                    master_report = MasterReportBuilder.build_master_report(
                        target=target,
                        results=results,
                        fusion_score=0.75,
                        correlation_details={"explanation_markdown": f"Synthesized report for {len(results)} items."},
                    )
            master_path = await self.markdown_writer.write_master_report(
                self.vault_name, target, getattr(master_report, "master_markdown", str(master_report))
            )
            saved_paths.append(str(master_path))
        except Exception as exc:
            if self.logger:
                self.logger.warning(f"Failed exporting Master Intelligence Report for '{target.target_id}': {exc}")

        await asyncio.sleep(0.3)
        await indexer.stop()

        if self.logger:
            self.logger.info(
                f"Export Pipeline completed successfully. Exported {len(saved_paths)} note(s)."
            )

        return saved_paths

    async def export_master_report(self, target: TargetEntity, master_report: Any) -> str:
        """Export a single master report directly and trigger indexing."""
        vault_dir = self.vault_root / self.vault_name if self.vault_name != self.vault_root.name else self.vault_root
        await self.obsidian_exporter.initialize_vault(vault_dir, self.vault_name)

        indexer = BackgroundIndexer(
            vault_root=self.vault_root, repository=self.repository, event_bus=self.event_bus, logger=self.logger
        )
        await indexer.start()

        path = await self.markdown_writer.write_master_report(
            self.vault_name, target, getattr(master_report, "master_markdown", str(master_report))
        )
        await asyncio.sleep(0.3)
        await indexer.stop()
        return str(path)
