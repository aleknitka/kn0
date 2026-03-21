# kn0

**Structured intelligence knowledge graph for documents — Entity, Relationship & Event Extraction Engine**

kn0 turns unstructured documents into a structured, queryable knowledge graph. Feed it PDFs and text files; it extracts entities (people, organizations, locations, events), maps the relationships between them, and builds a navigable intelligence picture — all stored locally with full source provenance and zero external dependencies.

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

## How It Works

```
Documents → Entities → Relationships → Events → Knowledge Graph
```

- **Documents** are ingested and hashed — re-ingesting the same file is a no-op.
- **Entities** are the nodes: people, organizations, locations, dates, concepts. Duplicates are automatically merged using name similarity.
- **Relationships** are the directed edges between entities, extracted from co-occurring sentences and weighted by a confidence score.
- **Events** are first-class timeline objects: dated occurrences with typed participants (entity + role) and provenance back to the source document.
- **Confidence scores** combine extraction certainty, cross-document corroboration, and configurable per-source reliability.

## Usage

### Step 1 — Install and set up

```bash
pip install -e ".[dev]"
python -m spacy download en_core_web_sm
cp .env.example .env       # edit DATABASE_URL if needed
alembic upgrade head        # creates kn0.db
```

### Step 2 — Ingest documents

```bash
kn0 ingest report.pdf
kn0 ingest memo.txt --reliability 0.9   # higher weight for trusted sources
```

Re-ingesting the same file is safe — kn0 detects the duplicate by file hash and skips it.

### Step 3 — Explore entities

```bash
kn0 entities                      # all entities (default: 20 shown)
kn0 entities --type PERSON        # filter by type
kn0 entities --type ORGANIZATION
kn0 entities --search "Apple"     # full-text search
kn0 entities --limit 50
```

Available types: `PERSON`, `ORGANIZATION`, `LOCATION`, `DATE`, `EVENT`, `CONCEPT`, `MONETARY`, `OTHER`

### Step 4 — Explore relationships

```bash
kn0 relationships                        # all relationships
kn0 relationships --type WORKS_FOR
kn0 relationships --min-confidence 0.6   # only high-confidence edges
```

### Step 5 — Explore events & timeline

```bash
kn0 events                                  # all events
kn0 events --type MEETING
kn0 events --after 2023-01-01 --before 2024-12-31
kn0 events --entity <entity-id>             # events an entity participated in

kn0 timeline                                # chronological view, undated events last
kn0 timeline --type CONFLICT
kn0 timeline --entity <entity-id>
```

### Step 6 — Check the graph at a glance

```bash
kn0 status      # document, entity, relationship, and event counts
kn0 documents   # list all ingested files with processing status
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

## Docker

### Build and run

```bash
docker build -t kn0 .
docker run --rm -v kn0_data:/data kn0 kn0 status
```

The entrypoint automatically runs `alembic upgrade head` on every start, so the database is always up to date.

### Ingest a document

Mount your documents directory alongside the data volume:

```bash
docker run --rm \
  -v kn0_data:/data \
  -v /path/to/your/docs:/docs \
  kn0 kn0 ingest /docs/report.pdf
```

### Query the graph

```bash
docker run --rm -v kn0_data:/data kn0 kn0 entities --type PERSON
docker run --rm -v kn0_data:/data kn0 kn0 timeline
```

### Using Docker Compose

```bash
# Build once
docker compose build

# Run any kn0 command
docker compose run --rm kn0 kn0 status
docker compose run --rm kn0 kn0 entities --type PERSON
docker compose run --rm -v /path/to/docs:/docs kn0 kn0 ingest /docs/report.pdf
```

The `kn0_data` named volume persists the SQLite database and uploads across runs.

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
