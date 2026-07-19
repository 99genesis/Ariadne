"""SQLite DDL Schema definitions for Ariadne Metadata Indexer.

Ensures high-speed terminal dashboard queries across thousands of markdown notes
without parsing files on every read request.
"""

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS notes (
    note_id TEXT PRIMARY KEY,
    vault_name TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    title TEXT NOT NULL,
    target_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    source_module TEXT NOT NULL,
    provider_used TEXT,
    confidence_score REAL DEFAULT 1.0,
    discovered_at TEXT NOT NULL,
    file_mtime REAL NOT NULL,
    UNIQUE(vault_name, relative_path)
);

CREATE TABLE IF NOT EXISTS note_tags (
    note_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (note_id, tag),
    FOREIGN KEY (note_id) REFERENCES notes(note_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS note_links (
    source_note_id TEXT NOT NULL,
    target_link TEXT NOT NULL,
    PRIMARY KEY (source_note_id, target_link),
    FOREIGN KEY (source_note_id) REFERENCES notes(note_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS indexer_state (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_notes_vault_target ON notes(vault_name, target_id);
CREATE INDEX IF NOT EXISTS idx_notes_entity_type ON notes(entity_type);
CREATE INDEX IF NOT EXISTS idx_notes_discovered ON notes(discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON note_tags(tag);
CREATE INDEX IF NOT EXISTS idx_links_target ON note_links(target_link);
"""
