"""Asynchronous atomic disk Writer and Reader for Markdown notes.

Performs non-blocking file I/O using aiofiles and publishes NoteCreatedEvent
to the Event Bus whenever a note is created or updated.
"""

import asyncio
from pathlib import Path
from typing import List, Optional
import aiofiles

from ariadne.core.exceptions import StorageException
from ariadne.core.interfaces import IEventBus, ILogger
from ariadne.core.models import IntelligenceResult, NoteEntity, TargetEntity
from ariadne.events.topics import NoteCreatedEvent
from ariadne.markdown.graph_linker import GraphLinker
from ariadne.markdown.metadata_builder import MetadataBuilder
from ariadne.markdown.relationship_builder import RelationshipBuilder
from ariadne.markdown.template_engine import TemplateEngine
from ariadne.markdown.yaml_parser import YamlParser


class MarkdownReader:
    """Reads and parses existing Markdown notes asynchronously."""

    def __init__(self, vault_root: Path, logger: Optional[ILogger] = None) -> None:
        self.vault_root = Path(vault_root)
        self.logger = logger

    async def read_note(self, vault_name: str, relative_path: str) -> Optional[NoteEntity]:
        """Read a note from disk and parse its frontmatter and body."""
        file_path = self.vault_root / vault_name / relative_path
        if not file_path.exists():
            return None

        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()

            fm, body = YamlParser.parse(content)
            links = GraphLinker.extract_links(content)

            return NoteEntity(
                note_id=str(fm.get("id", relative_path)),
                vault_name=vault_name,
                relative_path=relative_path,
                title=str(fm.get("title", relative_path.replace(".md", ""))),
                target_id=str(fm.get("target_id", vault_name)),
                entity_type=str(fm.get("entity_type", "note")),
                source_module=str(fm.get("source_module", "unknown")),
                provider_used=fm.get("provider_used"),
                confidence_score=float(fm.get("confidence_score", 1.0)),
                tags=list(fm.get("tags", [])),
                links=links,
                raw_frontmatter=fm,
                body_content=body,
            )
        except Exception as exc:
            if self.logger:
                self.logger.warning(f"Failed to read markdown note at {file_path}: {exc}")
            return None


class MarkdownWriter:
    """Atomic async disk writer for Markdown notes."""

    def __init__(
        self,
        vault_root: Path,
        event_bus: IEventBus,
        template_engine: Optional[TemplateEngine] = None,
        logger: Optional[ILogger] = None,
    ) -> None:
        self.vault_root = Path(vault_root)
        self.event_bus = event_bus
        self.template_engine = template_engine or TemplateEngine()
        self.logger = logger
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, file_path: Path) -> asyncio.Lock:
        path_str = str(file_path.resolve())
        if path_str not in self._locks:
            self._locks[path_str] = asyncio.Lock()
        return self._locks[path_str]

    def _get_folder_for_entity(self, entity_type: str) -> str:
        """Map entity type to subfolder inside vault."""
        mapping = {
            "social_profile": "Sosyal_Medya",
            "location": "Lokasyonlar",
            "phone": "İletişim",
            "email": "İletişim",
            "ip": "Ağ_ve_IP",
            "domain": "Ağ_ve_IP",
            "data_leak": "Sızıntılar",
            "image_analysis": "Medya_Analiz",
        }
        return mapping.get(entity_type.lower(), "Genel_Notlar")

    async def write_finding(
        self, vault_name: str, target: TargetEntity, result: IntelligenceResult
    ) -> Path:
        """Render and atomically write an intelligence finding note to disk and emit event."""
        subfolder = self._get_folder_for_entity(result.entity_type)
        vault_dir = self.vault_root / vault_name / subfolder
        vault_dir.mkdir(parents=True, exist_ok=True)

        clean_title = (
            result.title.replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
            .replace("+", "plus")
        )
        clean_title = clean_title[:60]
        file_path = vault_dir / f"{clean_title}.md"
        relative_path = f"{subfolder}/{clean_title}.md"

        note_id = f"note-{vault_name}-{result.entity_type}-{clean_title.lower()}"

        # Build cross-links and frontmatter
        rel_links = RelationshipBuilder.infer_relationships(result, target)
        fm = MetadataBuilder.build_frontmatter(result, target, note_id, additional_links=rel_links)

        # Render body template
        context = fm.copy()
        context["content_markdown"] = result.content_markdown
        body = self.template_engine.render("note_template.md", context)

        full_content = YamlParser.dump(fm, body)

        lock = self._get_lock(file_path)
        async with lock:
            try:
                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                    await f.write(full_content)
                if self.logger:
                    self.logger.debug(f"Saved note: {file_path}")
            except Exception as exc:
                raise StorageException(
                    message=f"Failed to write markdown note {file_path}: {exc}",
                    details={"error": str(exc)},
                )

        # Publish NoteCreatedEvent to trigger background SQLite indexer
        await self.event_bus.publish(
            NoteCreatedEvent(
                note_id=note_id,
                target_id=target.target_id,
                relative_path=relative_path,
                vault_name=vault_name,
            )
        )

        return file_path

    async def write_master_report(
        self, vault_name: str, target: TargetEntity, master_report_markdown: str
    ) -> Path:
        """Write the synthesized Master Intelligence Report to the root of the target's vault and emit event."""
        vault_dir = self.vault_root / vault_name
        vault_dir.mkdir(parents=True, exist_ok=True)
        file_path = vault_dir / f"Master_Report_{target.target_id}.md"
        relative_path = f"Master_Report_{target.target_id}.md"
        note_id = f"note-{vault_name}-report-master_{target.target_id.lower()}"

        lock = self._get_lock(file_path)
        async with lock:
            try:
                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                    await f.write(master_report_markdown)
                if self.logger:
                    self.logger.debug(f"Saved master report: {file_path}")
            except Exception as exc:
                raise StorageException(
                    message=f"Failed to write master report {file_path}: {exc}",
                    details={"error": str(exc)},
                )

        await self.event_bus.publish(
            NoteCreatedEvent(
                note_id=note_id,
                target_id=target.target_id,
                relative_path=relative_path,
                vault_name=vault_name,
            )
        )

        return file_path
