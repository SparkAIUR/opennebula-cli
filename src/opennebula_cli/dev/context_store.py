"""SQLite-backed internal context store."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import cast

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    scope TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    body TEXT NOT NULL,
    source_path TEXT,
    source_ref TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    importance INTEGER NOT NULL DEFAULT 3,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS entry_tags (
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (entry_id, tag)
);

CREATE TABLE IF NOT EXISTS entry_links (
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    related_entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    relation TEXT NOT NULL,
    PRIMARY KEY (entry_id, related_entry_id, relation)
);

CREATE TABLE IF NOT EXISTS entry_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_entries USING fts5(
    title,
    summary,
    body,
    content='entries',
    content_rowid='id'
);
"""


@dataclass(slots=True)
class ContextEntry:
    """Context entry payload."""

    kind: str
    scope: str
    title: str
    summary: str
    body: str
    source_path: str | None = None
    source_ref: str | None = None
    status: str = "active"
    importance: int = 3

    @property
    def content_hash(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.title.encode("utf-8"))
        digest.update(self.summary.encode("utf-8"))
        digest.update(self.body.encode("utf-8"))
        return digest.hexdigest()


class ContextStore:
    """SQLite context store with FTS search."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """Open a connection to the store."""

        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def init(self) -> None:
        """Initialize the store schema."""

        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def add(self, entry: ContextEntry, *, tags: list[str] | None = None) -> int:
        """Insert a new entry."""

        tags = tags or []
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO entries (
                    kind, scope, title, summary, body,
                    source_path, source_ref, status, importance, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.kind,
                    entry.scope,
                    entry.title,
                    entry.summary,
                    entry.body,
                    entry.source_path,
                    entry.source_ref,
                    entry.status,
                    entry.importance,
                    entry.content_hash,
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("Failed to create context store entry.")
            entry_id = int(cursor.lastrowid)
            for tag in tags:
                connection.execute(
                    "INSERT OR IGNORE INTO entry_tags (entry_id, tag) VALUES (?, ?)",
                    (entry_id, tag),
                )
            connection.execute(
                "INSERT INTO fts_entries (rowid, title, summary, body) VALUES (?, ?, ?, ?)",
                (entry_id, entry.title, entry.summary, entry.body),
            )
            return entry_id

    def update(self, entry_id: int, *, summary: str | None = None, body: str | None = None) -> None:
        """Update an existing entry and record a revision."""

        with self.connect() as connection:
            row = connection.execute(
                "SELECT body, title, summary FROM entries WHERE id = ?",
                (entry_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Entry {entry_id} does not exist.")
            connection.execute(
                "INSERT INTO entry_revisions (entry_id, body) VALUES (?, ?)",
                (entry_id, row["body"]),
            )
            next_summary = summary if summary is not None else str(row["summary"])
            next_body = body if body is not None else str(row["body"])
            content_hash = hashlib.sha256(
                f"{row['title']}{next_summary}{next_body}".encode()
            ).hexdigest()
            connection.execute(
                """
                UPDATE entries
                SET summary = ?, body = ?, content_hash = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (next_summary, next_body, content_hash, entry_id),
            )
            connection.execute("DELETE FROM fts_entries WHERE rowid = ?", (entry_id,))
            connection.execute(
                "INSERT INTO fts_entries (rowid, title, summary, body) VALUES (?, ?, ?, ?)",
                (entry_id, row["title"], next_summary, next_body),
            )

    def get(self, entry_id: int) -> sqlite3.Row | None:
        """Get a single entry."""

        with self.connect() as connection:
            row = connection.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
            return cast(sqlite3.Row | None, row)

    def search(self, query: str, *, limit: int = 10) -> list[sqlite3.Row]:
        """Search FTS entries."""

        with self.connect() as connection:
            return list(
                connection.execute(
                    """
                    SELECT entries.*
                    FROM fts_entries
                    JOIN entries ON entries.id = fts_entries.rowid
                    WHERE fts_entries MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (query, limit),
                )
            )

    def list_entries(self, *, limit: int = 20) -> list[sqlite3.Row]:
        """Return the newest entries."""

        with self.connect() as connection:
            return list(
                connection.execute(
                    "SELECT * FROM entries ORDER BY updated_at DESC, id DESC LIMIT ?",
                    (limit,),
                )
            )

    def export_markdown(self) -> str:
        """Export the current entries to a simple Markdown digest."""

        lines = ["# Project Knowledge Base", ""]
        for row in self.list_entries(limit=100):
            lines.extend(
                [
                    f"## [{row['id']}] {row['title']}",
                    f"- Kind: {row['kind']}",
                    f"- Scope: {row['scope']}",
                    f"- Status: {row['status']}",
                    f"- Importance: {row['importance']}",
                    "",
                    row["summary"],
                    "",
                    row["body"],
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"
