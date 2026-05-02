"""SQLite-backed CLI state store for locks and contexts."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path

LOCK_ACTION_CHOICES = ("create", "delete", "update", "list", "show", "all")


@dataclass(slots=True, frozen=True)
class LockState:
    """Current command-lock state."""

    enabled: bool
    actions: frozenset[str]
    commands: frozenset[str]
    password_set: bool


@dataclass(slots=True, frozen=True)
class StoredContext:
    """Stored OpenNebula context credentials."""

    name: str
    endpoint: str
    username: str
    password: str
    version: str | None = None


def default_state_db_path() -> Path:
    """Resolve state DB location from environment and defaults."""

    state_db = os.getenv("OPENNEBULA_CLI_STATE_DB")
    if state_db:
        return Path(state_db).expanduser()

    state_dir_or_db = os.getenv("OPENNEBULA_CLI_STATE_DIR")
    if state_dir_or_db:
        candidate = Path(state_dir_or_db).expanduser()
        if candidate.suffix == ".db":
            return candidate
        return candidate / "state.db"

    xdg_home = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")).expanduser()
    return xdg_home / "opennebula-cli" / "state.db"


class StateStore:
    """SQLite state backend for lock and context management."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_state_db_path()

    def connect(self) -> sqlite3.Connection:
        """Open DB connection and ensure parent directory exists."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def init(self) -> None:
        """Initialize required schema."""

        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS lock_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    enabled INTEGER NOT NULL DEFAULT 0,
                    password_salt TEXT,
                    password_hash TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS lock_actions (
                    action TEXT PRIMARY KEY
                );

                CREATE TABLE IF NOT EXISTS lock_commands (
                    command TEXT PRIMARY KEY
                );

                CREATE TABLE IF NOT EXISTS contexts (
                    name TEXT PRIMARY KEY,
                    endpoint TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    version TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                INSERT OR IGNORE INTO lock_state (id, enabled) VALUES (1, 0);
                """
            )

    def lock_state(self) -> LockState:
        """Return current lock state."""

        self.init()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT enabled, password_salt, password_hash FROM lock_state WHERE id = 1"
            ).fetchone()
            enabled = bool(int(row["enabled"])) if row else False
            password_set = bool(
                (row["password_salt"] if row else None)
                and (row["password_hash"] if row else None)
            )
            actions = frozenset(
                item["action"]
                for item in connection.execute(
                    "SELECT action FROM lock_actions ORDER BY action"
                ).fetchall()
            )
            commands = frozenset(
                item["command"]
                for item in connection.execute(
                    "SELECT command FROM lock_commands ORDER BY command"
                ).fetchall()
            )
            return LockState(
                enabled=enabled,
                actions=actions,
                commands=commands,
                password_set=password_set,
            )

    def set_lock(self, *, actions: set[str], commands: set[str], password: str | None) -> None:
        """Enable lock with selected actions/commands and optional password."""

        self.init()
        password_salt: str | None = None
        password_hash: str | None = None
        if password:
            password_salt = secrets.token_hex(16)
            password_hash = self._hash_password(password_salt, password)

        with self.connect() as connection:
            connection.execute(
                """
                UPDATE lock_state
                   SET enabled = 1,
                       password_salt = ?,
                       password_hash = ?,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = 1
                """,
                (password_salt, password_hash),
            )
            connection.execute("DELETE FROM lock_actions")
            connection.execute("DELETE FROM lock_commands")
            connection.executemany(
                "INSERT INTO lock_actions(action) VALUES (?)",
                [(action,) for action in sorted(actions)],
            )
            connection.executemany(
                "INSERT INTO lock_commands(command) VALUES (?)",
                [(command,) for command in sorted(commands)],
            )

    def disable_lock(self) -> None:
        """Disable lock and clear lock selections/password."""

        self.init()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE lock_state
                   SET enabled = 0,
                       password_salt = NULL,
                       password_hash = NULL,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = 1
                """
            )
            connection.execute("DELETE FROM lock_actions")
            connection.execute("DELETE FROM lock_commands")

    def verify_lock_password(self, password: str) -> bool:
        """Validate supplied unlock password against stored digest."""

        self.init()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT password_salt, password_hash FROM lock_state WHERE id = 1"
            ).fetchone()
            if row is None:
                return False
            salt = row["password_salt"]
            digest = row["password_hash"]
            if not salt or not digest:
                return False
            candidate = self._hash_password(salt, password)
            return hmac.compare_digest(candidate, digest)

    def upsert_context(self, context: StoredContext) -> None:
        """Create or update a named runtime context and mark it active."""

        self.init()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO contexts(name, endpoint, username, password, version, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    endpoint = excluded.endpoint,
                    username = excluded.username,
                    password = excluded.password,
                    version = excluded.version,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    context.name,
                    context.endpoint,
                    context.username,
                    context.password,
                    context.version,
                ),
            )
            connection.execute(
                """
                INSERT INTO meta(key, value) VALUES ('current_context', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (context.name,),
            )

    def use_context(self, name: str) -> bool:
        """Switch active context to an existing context."""

        self.init()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT name FROM contexts WHERE name = ?",
                (name,),
            ).fetchone()
            if row is None:
                return False
            connection.execute(
                """
                INSERT INTO meta(key, value) VALUES ('current_context', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (name,),
            )
            return True

    def get_active_context(self) -> StoredContext | None:
        """Return currently selected context from state DB."""

        self.init()
        with self.connect() as connection:
            meta = connection.execute(
                "SELECT value FROM meta WHERE key = 'current_context'"
            ).fetchone()
            if meta is None:
                return None
            row = connection.execute(
                """
                SELECT name, endpoint, username, password, version
                  FROM contexts
                 WHERE name = ?
                """,
                (meta["value"],),
            ).fetchone()
            if row is None:
                return None
            return StoredContext(
                name=str(row["name"]),
                endpoint=str(row["endpoint"]),
                username=str(row["username"]),
                password=str(row["password"]),
                version=str(row["version"]) if row["version"] else None,
            )

    @staticmethod
    def _hash_password(salt: str, password: str) -> str:
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            200_000,
        )
        return digest.hex()
