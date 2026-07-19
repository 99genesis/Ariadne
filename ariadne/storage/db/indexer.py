"""Background metadata indexer and sync service.

Listens to real-time NoteCreatedEvent pub/sub messages AND provides periodic/on-demand
directory scanning to synchronize external Obsidian modifications into SQLite.
"""

import asyncio
from pathlib import Path
from typing import Optional

from ariadne.core.interfaces import IEventBus, ILogger, INoteRepository
from ariadne.events.topics import NoteCreatedEvent
from ariadne.markdown.writer import MarkdownReader


class BackgroundIndexer:
    """Synchronizes disk markdown notes to SQLite index via Event Bus and background scanning."""

    def __init__(
        self,
        vault_root: Path,
        repository: INoteRepository,
        event_bus: IEventBus,
        logger: Optional[ILogger] = None,
    ) -> None:
        self.vault_root = Path(vault_root)
        self.repository = repository
        self.event_bus = event_bus
        self.logger = logger
        self.reader = MarkdownReader(vault_root=self.vault_root, logger=logger)
        self._is_running = False

    async def start(self) -> None:
        """Register event listeners and start indexing."""
        if self._is_running:
            return
        self.event_bus.subscribe(NoteCreatedEvent, self._on_note_created)
        self._is_running = True
        if self.logger:
            self.logger.info("Background SQLite Indexer started and subscribed to NoteCreatedEvent.")

    async def stop(self) -> None:
        """Unsubscribe and stop background worker."""
        self.event_bus.unsubscribe(NoteCreatedEvent, self._on_note_created)
        self._is_running = False
        if self.logger:
            self.logger.info("Background SQLite Indexer stopped.")

    async def _on_note_created(self, event: NoteCreatedEvent) -> None:
        """Event listener invoked instantly whenever a note is written by MarkdownWriter."""
        try:
            note = await self.reader.read_note(event.vault_name, event.relative_path)
            if note:
                await self.repository.save_note(note)
                if self.logger:
                    self.logger.debug(f"Instant Event-driven index sync for note '{event.note_id}'")
        except Exception as exc:
            if self.logger:
                self.logger.error(f"Error handling NoteCreatedEvent in indexer: {exc}", exc_info=exc)

    async def scan_and_reindex_vault(self, vault_name: str) -> int:
        """Perform a full directory scan of a vault and re-index all .md files."""
        vault_dir = self.vault_root / vault_name
        if not vault_dir.exists():
            if self.logger:
                self.logger.warning(f"Cannot scan vault '{vault_name}': Folder missing.")
            return 0

        indexed_count = 0
        for md_file in vault_dir.rglob("*.md"):
            if ".obsidian" in md_file.parts:
                continue

            rel_path = md_file.relative_to(vault_dir).as_posix()
            try:
                note = await self.reader.read_note(vault_name, rel_path)
                if note:
                    await self.repository.save_note(note)
                    indexed_count += 1
            except Exception as exc:
                if self.logger:
                    self.logger.warning(f"Failed to reindex file {md_file}: {exc}")

        if self.logger:
            self.logger.info(
                f"Full re-index complete for vault '{vault_name}'. Synchronized {indexed_count} note(s)."
            )
        return indexed_count
