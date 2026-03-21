"""Shared pytest fixtures for kn0 tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.engine import Connection

from kn0.persistence.database import create_db_engine, init_db
from kn0.persistence.store import DocumentStore, EntityStore, RelationshipStore


@pytest.fixture
def db_engine():
    """In-memory SQLite engine for each test."""
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_conn(db_engine) -> Connection:
    """Database connection within a transaction that is always rolled back."""
    with db_engine.begin() as conn:
        yield conn


@pytest.fixture
def doc_store(db_conn) -> DocumentStore:
    return DocumentStore(db_conn)


@pytest.fixture
def entity_store(db_conn) -> EntityStore:
    return EntityStore(db_conn)


@pytest.fixture
def rel_store(db_conn) -> RelationshipStore:
    return RelationshipStore(db_conn)


@pytest.fixture
def sample_text_file(tmp_path: Path) -> Path:
    """A simple plain-text file for ingestion tests."""
    content = (
        "Apple Inc. was founded by Steve Jobs and Steve Wozniak in Cupertino, California in 1976. "
        "The company launched the Macintosh computer in 1984. "
        "Tim Cook became CEO of Apple Inc. in August 2011 after Jobs resigned. "
        "Microsoft Corporation, led by Satya Nadella, is based in Redmond, Washington."
    )
    f = tmp_path / "sample.txt"
    f.write_text(content, encoding="utf-8")
    return f
