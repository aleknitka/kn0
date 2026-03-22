# CLAUDE.md — AI Assistant Guide for kn0

This document provides guidance for AI assistants (Claude and others) working on this repository.

## Repository Overview

**kn0** is a Python-based open-source structured intelligence knowledge graph. It transforms unstructured documents into a structured, queryable knowledge graph — extracting entities, relationships, and events — with LLM-powered analysis, GraphRAG querying, and interactive network visualization.

- **Language**: Python 3.10+
- **License**: MIT
- **Owner**: aleknitka
- **Package manager**: pip / uv (uses `pyproject.toml`)

## Repository Structure

```
kn0/
├── pyproject.toml                 # Package config, all deps, ruff/mypy config
├── .env.example                   # Template for environment variables
├── alembic.ini                    # Alembic migration tool config
├── alembic/
│   ├── env.py                     # Migration environment (reads kn0 settings)
│   └── versions/
│       ├── 001_initial_schema.py  # Initial DB schema migration
│       └── 002_add_events.py      # Events, event_participants, event_source_documents
├── src/
│   └── kn0/
│       ├── __init__.py
│       ├── config.py              # pydantic-settings: reads from .env
│       ├── cli.py                 # Typer CLI (kn0 ingest, kn0 entities, kn0 events, …)
│       ├── pipeline.py            # End-to-end ingestion pipeline
│       ├── schemas/               # Pydantic v2 validation & serialization schemas
│       │   ├── __init__.py        # Re-exports all public schemas
│       │   ├── common.py          # KnOBaseModel shared base
│       │   ├── entity.py          # EntityCreate, EntityRead, EntitySummary
│       │   ├── relationship.py    # RelationshipCreate, RelationshipRead
│       │   ├── event.py           # EventCreate, EventRead, EventSummary, ParticipantRead
│       │   └── document.py        # DocumentRead
│       ├── ingestion/
│       │   ├── base.py            # DocumentParser ABC, ParsedDocument, PageContent
│       │   ├── registry.py        # ParserRegistry (MIME → parser)
│       │   ├── pdf_parser.py      # PyMuPDF extraction + OCR stub
│       │   └── text_parser.py     # Plain text / Markdown pseudo-paging
│       ├── extraction/
│       │   ├── base.py            # ExtractionBackend Protocol, dataclasses
│       │   ├── entity_types.py    # EntityType enum + spaCy label map
│       │   ├── type_registry.py   # TypeRegistry class + entity/relationship/event singletons
│       │   ├── spacy_backend.py   # spaCy NER + co-occurrence RE
│       │   ├── resolver.py        # Entity resolution (exact/alias/similarity)
│       │   └── confidence.py      # Confidence scoring formula
│       ├── llm/                   # LLM integration (extraction + future GraphRAG)
│       │   ├── __init__.py        # Re-exports LLMClient, LLMExtractionBackend
│       │   ├── client.py          # Async LLMClient (OpenAI-compatible + Anthropic)
│       │   ├── prompts.py         # Entity + relationship extraction prompt templates
│       │   └── extraction_backend.py  # LLMExtractionBackend (ExtractionBackend Protocol)
│       ├── graphrag/              # GraphRAG engine (Phase 2+)
│       │   ├── __init__.py
│       │   └── engine.py          # GraphRAGEngine scaffold (async interface)
│       ├── persistence/
│       │   ├── models.py          # SQLAlchemy Core table definitions (8 tables)
│       │   ├── database.py        # Engine factory, init_db, get_connection()
│       │   └── store.py           # DocumentStore, EntityStore, RelationshipStore, EventStore
│       ├── api/                   # FastAPI (Phase 2 — not yet implemented)
│       └── visualization/         # Pyvis/NetworkX (Phase 3 — not yet implemented)
└── tests/
    ├── conftest.py                # In-memory DB fixtures
    ├── fixtures/
    │   └── sample.txt             # Sample document for integration tests
    ├── ingestion/
    ├── extraction/
    └── persistence/
```

## Git Workflow

### Branches

- `main` / `master` — stable, production-ready code
- `claude/<description>-<id>` — AI-generated feature branches

### Commit Messages

Write clear, imperative commit messages:
```
Add user authentication module
Fix pagination bug in search results
```

### Push Commands

```bash
git push -u origin <branch-name>
```

## Development Setup

```bash
# Install package + dev dependencies
pip install -e ".[dev]"
# or
uv sync

# Download spaCy model (required for extraction)
python -m spacy download en_core_web_sm

# Initialize/migrate database
alembic upgrade head

# Run tests
pytest

# Lint and format
ruff check .
ruff format .

# Type check
mypy src/
```

## Architecture Notes

### Pipeline Flow

```
File → ParserRegistry → DocumentParser → ParsedDocument
     → SpacyBackend (NER per page)     → ExtractedEntity[]
     → SpacyBackend (RE per sentence)  → ExtractedRelationship[]
     → EntityResolver                  → entity_id (merge or create)
     → EntityStore / RelationshipStore → SQLite
```

### Database Schema (8 tables)

| Table | Purpose |
|---|---|
| `documents` | File metadata, hash (idempotency), processing status |
| `entities` | Canonical entities with JSON aliases and attributes |
| `relationships` | Directed edges (source → target) with confidence score |
| `entity_mentions` | Provenance: entity ↔ document/page/passage |
| `relationship_evidence` | Provenance: relationship ↔ document/page/passage |
| `events` | First-class event objects with date range and location anchor |
| `event_participants` | Many-to-many: entity participates in event with a role |
| `event_source_documents` | Provenance: event ↔ document with per-source confidence |

Plus FTS5 virtual table `entities_fts` for full-text entity search.

### Type Registry

`TypeRegistry` in `src/kn0/extraction/type_registry.py` provides extensible, case-insensitive type validation without modifying the `EntityType` enum:

```python
from kn0.extraction.type_registry import entity_type_registry
entity_type_registry.register("VEHICLE")
```

Three module-level singletons are pre-seeded: `entity_type_registry` (from `EntityType` enum), `relationship_type_registry` (11 default types), `event_type_registry` (15 default types). Pydantic schemas validate against these registries at model construction time.

### Confidence Scoring

```
final = 0.40 × extraction_confidence
      + 0.35 × corroboration_score        (log-scale, # confirming docs)
      + 0.25 × source_reliability          (user-configurable per document)
```

### Entity Resolution

1. Exact canonical name match → merge (score 1.0)
2. Alias match → merge (score 0.95)
3. `difflib.SequenceMatcher` similarity ≥ `merge_threshold` (default 0.85) → merge
4. Similarity ≥ `review_threshold` (default 0.65) → flag UNDER_REVIEW
5. Below → create new entity

### Pluggable NLP Backend

`ExtractionBackend` is defined as a `Protocol` in `src/kn0/extraction/base.py`. Two backends are included:
- **`SpacyBackend`** (default) — fast, offline NER via spaCy
- **`LLMExtractionBackend`** — LLM-powered extraction via `kn0 ingest --backend llm`

To use a custom backend, implement `extract_entities()` and `extract_relationships()` and pass it to `ingest_document(..., backend=your_backend)`.

### LLM Client (`src/kn0/llm/client.py`)

`LLMClient` is an **async** wrapper supporting:
- `lm_studio` — `http://localhost:1234/v1` (default, OpenAI-compatible)
- `ollama` — `http://localhost:11434/v1` (OpenAI-compatible)
- `openai` — `https://api.openai.com/v1`
- `anthropic` — requires `pip install 'kn0[anthropic]'`

All methods are `async def`. The sync `ExtractionBackend` Protocol is satisfied by thin `asyncio.run()` wrappers, making the backend directly usable from async callers (Phase 2 API) without change.

### GraphRAG (`src/kn0/graphrag/engine.py`)

`GraphRAGEngine` is scaffolded with an async interface for graph-grounded LLM Q&A and entity summarisation. Not yet implemented — placeholder `NotImplementedError` methods are in place for Phase 2.

## Configuration (`config.py`)

All settings read from environment / `.env` via `pydantic-settings`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./kn0.db` | SQLAlchemy DB URL |
| `UPLOAD_DIR` | `./uploads` | Local file storage |
| `SPACY_MODEL` | `en_core_web_sm` | spaCy model name |
| `MERGE_THRESHOLD` | `0.85` | Auto-merge similarity threshold |
| `REVIEW_THRESHOLD` | `0.65` | Ambiguous match threshold |
| `MIN_CONFIDENCE_DISPLAY` | `0.3` | Hide relationships below this score |
| `SOURCE_RELIABILITY_DEFAULT` | `0.5` | Default source weight |
| `LLM_PROVIDER` | `lm_studio` | LLM provider: `lm_studio`, `ollama`, `openai`, `anthropic` |
| `LLM_MODEL` | `local-model` | Model name (e.g. `llama3.2`, `gpt-4o-mini`) |
| `LLM_BASE_URL` | `http://localhost:1234/v1` | LM Studio default endpoint |
| `LLM_API_KEY` | `lm-studio` | Dummy key for local providers; real key for OpenAI/Anthropic |
| `LLM_TEMPERATURE` | `0.0` | Sampling temperature (0.0 for deterministic extraction) |
| `LLM_TIMEOUT` | `60.0` | Request timeout in seconds |

## AI Assistant Instructions

When working on this repository:

1. **Explore before editing** — read relevant files before making changes
2. **Minimal changes** — only modify what is necessary; avoid scope creep
3. **Preserve conventions** — SQLAlchemy Core (not ORM), no raw SQL outside `store.py`
4. **No secret leakage** — never hardcode credentials, tokens, or keys
5. **Test awareness** — run `pytest` after changes; maintain 100% pass rate
6. **Update documentation** — keep README and this file current when making structural changes
7. **Branch hygiene** — always develop on the designated feature branch
8. **Type hints** — all new functions must have type annotations
9. **Idempotency** — document ingestion is hash-based idempotent; preserve this property

## Development Milestones

| Phase | Status | Description |
|---|---|---|
| 1 — Foundation | ✅ Complete | Scaffold, DB schema, PDF/text ingestion, NER, entity resolution, confidence scoring, CLI |
| 1.5 — Schemas & Events | ✅ Complete | Pydantic v2 schemas, extensible type registry, events/timeline subsystem (`events`, `event_participants`, `event_source_documents`), `kn0 events` + `kn0 timeline` CLI |
| 1.7 — LLM Backend | ✅ Complete | Async `LLMClient` (LM Studio/Ollama/OpenAI/Anthropic), `LLMExtractionBackend`, `kn0 ingest --backend llm`, GraphRAG scaffold |
| 2 — REST API & GraphRAG | Planned | FastAPI REST API (`src/kn0/api/`), full GraphRAG Q&A, entity summarisation |
| 3 — Visualization | Planned | Interactive network graph via Pyvis/D3.js (`src/kn0/visualization/`) |
| 4 — Polish | Planned | DOCX/HTML/CSV parsers, Docker image, Hugging Face backend option |
