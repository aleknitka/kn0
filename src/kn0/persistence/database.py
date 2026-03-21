"""Database engine and session management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, Engine

from kn0.config import settings
from kn0.persistence.models import metadata


def _enable_wal_and_fk(dbapi_connection, connection_record):  # noqa: ARG001
    """Enable WAL mode and foreign key enforcement for SQLite connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_engine(url: str | None = None) -> Engine:
    """Create a configured SQLAlchemy engine."""
    db_url = url or settings.database_url
    engine = create_engine(db_url, echo=False)
    if db_url.startswith("sqlite"):
        event.listen(engine, "connect", _enable_wal_and_fk)
    return engine


def init_db(engine: Engine) -> None:
    """Create all tables and the FTS5 virtual table."""
    metadata.create_all(engine)
    with engine.connect() as conn:
        _create_fts5_table(conn)
        conn.commit()


def _create_fts5_table(conn: Connection) -> None:
    """Create FTS5 virtual table for full-text search over entities."""
    conn.execute(
        text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts
            USING fts5(
                entity_id UNINDEXED,
                canonical_name,
                aliases,
                content='entities',
                content_rowid='rowid'
            )
            """
        )
    )
    # Triggers to keep FTS index in sync
    conn.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS entities_ai AFTER INSERT ON entities BEGIN
                INSERT INTO entities_fts(rowid, entity_id, canonical_name, aliases)
                VALUES (new.rowid, new.id, new.canonical_name, new.aliases);
            END
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS entities_ad AFTER DELETE ON entities BEGIN
                INSERT INTO entities_fts(entities_fts, rowid, entity_id, canonical_name, aliases)
                VALUES ('delete', old.rowid, old.id, old.canonical_name, old.aliases);
            END
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS entities_au AFTER UPDATE ON entities BEGIN
                INSERT INTO entities_fts(entities_fts, rowid, entity_id, canonical_name, aliases)
                VALUES ('delete', old.rowid, old.id, old.canonical_name, old.aliases);
                INSERT INTO entities_fts(rowid, entity_id, canonical_name, aliases)
                VALUES (new.rowid, new.id, new.canonical_name, new.aliases);
            END
            """
        )
    )


# Module-level default engine (lazy-initialized)
_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_db_engine()
        init_db(_engine)
    return _engine


@contextmanager
def get_connection() -> Generator[Connection, None, None]:
    """Context manager providing a database connection with auto-commit/rollback."""
    engine = get_engine()
    with engine.begin() as conn:
        yield conn
