"""AuditLogger implementing IAuditLogger for enterprise compliance and traceability.

Records immutable audit events into SQLite table (`audit_logs`) and JSONL file (`audit.log`).
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ariadne.core.interfaces import IAuditLogger, ILogger


class AuditLogger(IAuditLogger):
    """Enterprise audit logger recording structured events to SQLite and JSONL."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        log_file: Optional[Path] = None,
        logger: Optional[ILogger] = None,
    ) -> None:
        """Initialize AuditLogger with database and log file targets."""
        self.db_path = Path(db_path) if db_path is not None else Path("Ariadne_Workspace") / "audit.db"
        self.log_file = Path(log_file) if log_file is not None else Path("Ariadne_Workspace") / "audit.jsonl"
        self.logger = logger
        self._lock = asyncio.Lock()
        self._init_storage()

    def _init_storage(self) -> None:
        """Ensure parent directories exist and SQLite schema is initialized."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_logs(session_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_logs(event_type);")

    def set_target_paths(self, db_path: Path, log_file: Optional[Path] = None) -> None:
        """Dynamically switch audit storage targets upon workspace changes."""
        db_path = Path(db_path)
        if self.db_path != db_path:
            self.db_path = db_path
            if log_file:
                self.log_file = Path(log_file)
            self._init_storage()

    async def log_event(self, event_type: str, session_id: str, details: Dict[str, Any]) -> None:
        """Asynchronously log an audit event to SQLite and JSONL."""
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        details_json = json.dumps(details, default=str, ensure_ascii=False)

        async with self._lock:
            def _sync_log() -> None:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT INTO audit_logs (event_type, session_id, timestamp, details_json)
                        VALUES (?, ?, ?, ?)
                        """,
                        (event_type, session_id, timestamp_iso, details_json),
                    )

                if self.log_file:
                    entry = {
                        "event_type": event_type,
                        "session_id": session_id,
                        "timestamp": timestamp_iso,
                        "details": details,
                    }
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(entry, default=str, ensure_ascii=False) + "\n")

            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, _sync_log)
            except Exception as exc:
                if self.logger:
                    self.logger.error(f"Failed writing audit log event '{event_type}': {exc}", exc_info=exc)

    async def get_events(
        self,
        session_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve historical audit events from SQLite database."""
        def _sync_query() -> List[Dict[str, Any]]:
            query = "SELECT event_type, session_id, timestamp, details_json FROM audit_logs WHERE 1=1"
            params: List[Any] = []
            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            results = []
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, tuple(params))
                for row in cursor.fetchall():
                    results.append(
                        {
                            "event_type": row[0],
                            "session_id": row[1],
                            "timestamp": row[2],
                            "details": json.loads(row[3]),
                        }
                    )
            return results

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync_query)
