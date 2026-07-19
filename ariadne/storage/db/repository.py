"""SQLite Note Repository implementing INoteRepository and dashboard aggregation queries.

Performs asynchronous database operations using asyncio loop delegates to prevent
blocking the main async event loop.
"""

import asyncio
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ariadne.core.exceptions import StorageException
from ariadne.core.interfaces import ILogger, INoteRepository
from ariadne.core.models import NoteEntity
from ariadne.storage.db.schema import SCHEMA_DDL


class SQLiteNoteRepository(INoteRepository):
    """Repository managing SQLite notes.db index and dashboard queries."""

    def __init__(self, db_path: Optional[Path] = None, logger: Optional[ILogger] = None) -> None:
        """Initialize SQLite note repository."""
        self.db_path = Path(db_path) if db_path is not None else Path("Ariadne_Workspace") / "notes.db"
        self.logger = logger
        self._lock = asyncio.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """Ensure database and tables are created."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.executescript(SCHEMA_DDL)

    def set_target_db(self, db_path: Path) -> None:
        """Dynamically scope database operations to the specified target notes.db."""
        db_path = Path(db_path)
        if self.db_path != db_path:
            self.db_path = db_path
            self._init_db()

    def _execute_sync(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn.execute(query, params)

    async def save_note(self, note: NoteEntity) -> str:
        """Save or update a note entity inside SQLite index."""
        async with self._lock:
            def _sync_save():
                file_mtime = datetime.now(timezone.utc).timestamp()
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("PRAGMA foreign_keys = ON;")
                    # Insert or replace note record
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO notes (
                            note_id, vault_name, relative_path, title, target_id,
                            entity_type, source_module, provider_used, confidence_score,
                            discovered_at, file_mtime
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            note.note_id,
                            note.vault_name,
                            note.relative_path,
                            note.title,
                            note.target_id,
                            note.entity_type,
                            note.source_module,
                            note.provider_used,
                            note.confidence_score,
                            note.discovered_at.isoformat(),
                            file_mtime,
                        ),
                    )

                    # Replace tags
                    conn.execute("DELETE FROM note_tags WHERE note_id = ?", (note.note_id,))
                    for tag in set(note.tags):
                        conn.execute("INSERT INTO note_tags (note_id, tag) VALUES (?, ?)", (note.note_id, tag))

                    # Replace links
                    conn.execute("DELETE FROM note_links WHERE source_note_id = ?", (note.note_id,))
                    for link in set(note.links):
                        conn.execute("INSERT INTO note_links (source_note_id, target_link) VALUES (?, ?)", (note.note_id, link))

            try:
                await asyncio.get_running_loop().run_in_executor(None, _sync_save)
                return str(self.db_path)
            except Exception as exc:
                raise StorageException(
                    message=f"Failed to save note to SQLite index: {exc}", details={"error": str(exc)}
                )

    async def get_note_by_id(self, note_id: str) -> Optional[NoteEntity]:
        """Retrieve note entity from SQLite index."""
        def _sync_get():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM notes WHERE note_id = ?", (note_id,))
                row = cursor.fetchone()
                if not row:
                    return None

                tags = [r[0] for r in conn.execute("SELECT tag FROM note_tags WHERE note_id = ?", (note_id,))]
                links = [r[0] for r in conn.execute("SELECT target_link FROM note_links WHERE source_note_id = ?", (note_id,))]

                return NoteEntity(
                    note_id=row["note_id"],
                    vault_name=row["vault_name"],
                    relative_path=row["relative_path"],
                    title=row["title"],
                    target_id=row["target_id"],
                    entity_type=row["entity_type"],
                    source_module=row["source_module"],
                    provider_used=row["provider_used"],
                    confidence_score=row["confidence_score"],
                    discovered_at=datetime.fromisoformat(row["discovered_at"]),
                    tags=tags,
                    links=links,
                )

        return await asyncio.get_running_loop().run_in_executor(None, _sync_get)

    async def list_notes_by_target(self, vault_name: str, target_id: str) -> List[NoteEntity]:
        """List all indexed notes for a specific target inside a vault."""
        def _sync_list():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT note_id FROM notes WHERE vault_name = ? AND target_id = ? ORDER BY discovered_at DESC",
                    (vault_name, target_id),
                )
                note_ids = [row["note_id"] for row in cursor.fetchall()]
            return note_ids

        ids = await asyncio.get_running_loop().run_in_executor(None, _sync_list)
        results: List[NoteEntity] = []
        for nid in ids:
            note = await self.get_note_by_id(nid)
            if note:
                results.append(note)
        return results

    async def delete_note(self, note_id: str) -> bool:
        """Remove note record from index."""
        def _sync_del():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM notes WHERE note_id = ?", (note_id,))
                return cursor.rowcount > 0

        return await asyncio.get_running_loop().run_in_executor(None, _sync_del)

    async def get_target_summary_stats(self, vault_name: str, target_id: str) -> Dict[str, Any]:
        """High-speed aggregation query returning comprehensive dashboard stats and top findings."""
        def _sync_stats():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Check if exact matches exist for target_id
                exact_count = conn.execute(
                    "SELECT count(*) as c FROM notes WHERE target_id = ?",
                    (target_id,),
                ).fetchone()["c"]

                if exact_count > 0:
                    where_sql = "WHERE target_id = ?"
                    params = (target_id,)
                else:
                    # Target workspace scope: query all notes in this workspace DB
                    where_sql = "WHERE 1=1"
                    params = ()

                total_notes = conn.execute(
                    f"SELECT count(*) as c FROM notes {where_sql}",
                    params,
                ).fetchone()["c"]

                avg_conf = conn.execute(
                    f"SELECT avg(confidence_score) as a FROM notes {where_sql}",
                    params,
                ).fetchone()["a"] or 0.0

                by_entity = {}
                cursor = conn.execute(
                    f"SELECT entity_type, count(*) as count FROM notes {where_sql} GROUP BY entity_type ORDER BY count DESC",
                    params,
                )
                for row in cursor.fetchall():
                    by_entity[row["entity_type"]] = row["count"]

                # Distinct investigated targets/scans
                investigated_targets = {}
                t_cursor = conn.execute(
                    f"SELECT target_id, count(*) as count FROM notes {where_sql} AND target_id != 'Vault' GROUP BY target_id ORDER BY count DESC",
                    params,
                )
                for row in t_cursor.fetchall():
                    investigated_targets[row["target_id"]] = row["count"]

                # Top tags
                top_tags = {}
                try:
                    tag_cursor = conn.execute(
                        "SELECT tag, count(*) as count FROM note_tags GROUP BY tag ORDER BY count DESC LIMIT 12"
                    )
                    for row in tag_cursor.fetchall():
                        top_tags[row["tag"]] = row["count"]
                except Exception:
                    pass

                # Top findings (excluding master report notes)
                top_findings = []
                f_cursor = conn.execute(
                    f"SELECT title, entity_type, provider_used, confidence_score, relative_path, target_id FROM notes {where_sql} AND entity_type != 'note' AND title NOT LIKE 'Master_Report_%' ORDER BY confidence_score DESC, discovered_at DESC LIMIT 20",
                    params,
                )
                for row in f_cursor.fetchall():
                    top_findings.append({
                        "title": row["title"],
                        "entity_type": row["entity_type"],
                        "provider_used": row["provider_used"] or "unknown",
                        "confidence_score": row["confidence_score"] or 0.0,
                        "relative_path": row["relative_path"],
                        "target_id": row["target_id"],
                    })

                # Master reports
                master_reports = []
                m_cursor = conn.execute(
                    f"SELECT title, relative_path, discovered_at FROM notes {where_sql} AND (entity_type = 'note' OR title LIKE 'Master_Report_%') ORDER BY discovered_at DESC LIMIT 10",
                    params,
                )
                for row in m_cursor.fetchall():
                    master_reports.append({
                        "title": row["title"],
                        "relative_path": row["relative_path"],
                        "discovered_at": row["discovered_at"],
                    })

                return {
                    "total_notes": total_notes,
                    "average_confidence": round(avg_conf, 3),
                    "entity_counts": by_entity,
                    "investigated_targets": investigated_targets,
                    "top_tags": top_tags,
                    "top_findings": top_findings,
                    "master_reports": master_reports,
                }

        return await asyncio.get_running_loop().run_in_executor(None, _sync_stats)
