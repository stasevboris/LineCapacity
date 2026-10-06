from __future__ import annotations

import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

CREDENTIALS = """
CREATE TABLE IF NOT EXISTS credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    salt TEXT NOT NULL,
    hash TEXT NOT NULL
);
"""

WORK = """
CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    tier TEXT NOT NULL DEFAULT 'demo',
    tier_until REAL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    language TEXT NOT NULL DEFAULT 'ru',
    stamp TEXT NOT NULL,
    created REAL NOT NULL,
    last_login REAL
);
CREATE TABLE IF NOT EXISTS attempts (
    email TEXT PRIMARY KEY,
    failures INTEGER NOT NULL DEFAULT 0,
    blocked_until REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0,
    settings TEXT NOT NULL DEFAULT '{}',
    created REAL NOT NULL,
    updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    is_main INTEGER NOT NULL DEFAULT 0,
    scheme TEXT NOT NULL,
    created REAL NOT NULL,
    updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    owner_id INTEGER NOT NULL,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS team_members (
    team_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    PRIMARY KEY (team_id, user_id)
);
CREATE TABLE IF NOT EXISTS invitations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user INTEGER NOT NULL,
    to_email TEXT NOT NULL,
    team_id INTEGER,
    role TEXT NOT NULL DEFAULT 'reader',
    status TEXT NOT NULL DEFAULT 'waiting',
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS friends (
    one INTEGER NOT NULL,
    two INTEGER NOT NULL,
    created REAL NOT NULL,
    PRIMARY KEY (one, two)
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user INTEGER NOT NULL,
    to_user INTEGER,
    team_id INTEGER,
    body TEXT NOT NULL,
    file_name TEXT,
    file_path TEXT,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS project_shares (
    project_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    PRIMARY KEY (project_id, team_id)
);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    link TEXT NOT NULL DEFAULT '',
    seen INTEGER NOT NULL DEFAULT 0,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS reference_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    settings TEXT NOT NULL DEFAULT '{}',
    period INTEGER NOT NULL DEFAULT 2,
    min_load INTEGER NOT NULL DEFAULT 1,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS consultant_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    chars INTEGER NOT NULL,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS site_options (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    tier TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    pan_masked TEXT NOT NULL DEFAULT '',
    brand TEXT NOT NULL DEFAULT '',
    ext_ref TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT '',
    created REAL NOT NULL,
    finished REAL
);
CREATE TABLE IF NOT EXISTS own_marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    data TEXT NOT NULL,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS revoked_sessions (
    signature TEXT PRIMARY KEY,
    until REAL NOT NULL
);
"""


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


class Store:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.files = self.data_dir / "files"
        self.files.mkdir(exist_ok=True)
        self.credentials = connect(self.data_dir / "credentials.db")
        self.work = connect(self.data_dir / "voltplan.db")
        self.lock = threading.RLock()
        self.credentials.executescript(CREDENTIALS)
        self.work.executescript(WORK)

    @contextmanager
    def writing(self, connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
        with self.lock:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.execute("ROLLBACK")
                raise
            connection.execute("COMMIT")

    def audit(self, user_id: int | None, action: str, details: str = "") -> None:
        with self.writing(self.work) as db:
            db.execute("INSERT INTO audit (user_id, action, details, created) VALUES (?, ?, ?, ?)",
                       (user_id, action, details, time.time()))

    def close(self) -> None:
        self.credentials.close()
        self.work.close()
