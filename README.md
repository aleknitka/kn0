# kn0

**Open-source knowledge graph inspired by Palantir Gotham — Entity, Relationship & Event Extraction Engine**

kn0 transforms unstructured documents into a structured, queryable knowledge graph. Upload PDFs and text files, and the system automatically identifies entities (people, organizations, locations, dates, concepts), the relationships between them, and the events that connect them — all stored locally with full source provenance.

## Features

- **Document ingestion** — PDF (via PyMuPDF + optional OCR) and plain text/Markdown
- **Named entity recognition** — powered by spaCy, mapping to 7 core entity types
- **Relationship extraction** — co-occurrence-based with typed relationship labels
- **Events & timeline** — first-class event objects with date ranges, participant roles, and source provenance
- **Extensible type system** — register custom entity, relationship, and event types at runtime
- **Pydantic schemas** — validated input/output models for all core objects
- **Confidence scoring** — composite score from extraction confidence, cross-document corroboration, and source reliability
- **Entity resolution** — deduplication via exact/alias/similarity matching with configurable thresholds
- **Full provenance** — every entity, relationship, and event traces back to document, page, and passage
- **Local SQLite storage** — zero infrastructure, single-file database
- **CLI interface** — ingest documents and query the knowledge graph from the terminal

## Quickstart

```bash
# Install
pip install -e ".[dev]"

# Download spaCy model
python -m spacy download en_core_web_sm

# Initialize / migrate the database
alembic upgrade head

# Ingest a document
kn0 ingest path/to/document.pdf

# List extracted entities
kn0 entities
kn0 entities --type PERSON
kn0 entities --search "Apple"

# List relationships
kn0 relationships --min-confidence 0.5

# List events
kn0 events
kn0 events --type MEETING --after 2024-01-01

# View chronological timeline
kn0 timeline
kn0 timeline --entity <entity-id> --after 2020-01-01

# Show statistics
kn0 status

# List all ingested documents
kn0 documents
```

## Project Structure

```
src/kn0/
├── config.py           Settings via pydantic-settings / .env
├── cli.py              Typer CLI entry point
├── pipeline.py         End-to-end ingestion pipeline
├── schemas/            Pydantic v2 validation & serialization schemas
├── ingestion/          Document parsers (PDF, text, registry)
├── extraction/         NER, RE, entity resolution, confidence scoring, type registry
├── persistence/        SQLAlchemy Core models (8 tables), database setup, data stores
├── api/                FastAPI REST API (Phase 2+)
└── visualization/      NetworkX + Pyvis graph rendering (Phase 3+)
```

## Configuration

Copy `.env.example` to `.env` and adjust:

```env
DATABASE_URL=sqlite:///./kn0.db
UPLOAD_DIR=./uploads
SPACY_MODEL=en_core_web_sm
MERGE_THRESHOLD=0.85
REVIEW_THRESHOLD=0.65
MIN_CONFIDENCE_DISPLAY=0.3
SOURCE_RELIABILITY_DEFAULT=0.5
```

## Extending Types

Register custom types at application startup:

```python
from kn0.extraction.type_registry import (
    entity_type_registry,
    event_type_registry,
    relationship_type_registry,
)

entity_type_registry.register("VEHICLE")
relationship_type_registry.register("TRANSFERRED_TO")
event_type_registry.register("DETONATION")
```

## Development

```bash
# Run tests
pytest

# Lint
ruff check .

# Format
ruff format .

# Type check
mypy src/
```

## Roadmap

| Phase | Status | Description |
|---|---|---|
| 1 — Foundation | ✅ | Scaffold, DB schema, PDF/text ingestion, NER, entity resolution, CLI |
| 1.5 — Schemas & Events | ✅ | Pydantic schemas, extensible type registry, events/timeline subsystem |
| 2 — REST API | Planned | Full RE pipeline, FastAPI REST API (`src/kn0/api/`) |
| 3 — Visualization | Planned | Interactive network graph (Pyvis/D3.js) (`src/kn0/visualization/`) |
| 4 — Polish | Planned | DOCX/HTML/CSV parsers, pluggable NLP backends, Docker |

## License

MIT — see [LICENSE](LICENSE)
