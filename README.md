# kn0

**Entity & Relationship Extraction Engine — Knowledge Graph Builder**

kn0 transforms unstructured documents into a structured, queryable knowledge graph. Upload PDFs and text files, and the system automatically identifies entities (people, organizations, locations, dates, concepts) and the relationships between them — all stored locally with full source provenance.

## Features

- **Document ingestion** — PDF (via PyMuPDF + optional OCR) and plain text/Markdown
- **Named entity recognition** — powered by spaCy, mapping to 7 core entity types
- **Relationship extraction** — co-occurrence-based with typed relationship labels
- **Confidence scoring** — composite score from extraction confidence, cross-document corroboration, and source reliability
- **Entity resolution** — deduplication via exact/alias/similarity matching with configurable thresholds
- **Full provenance** — every entity and relationship traces back to document, page, and passage
- **Local SQLite storage** — zero infrastructure, single-file database
- **CLI interface** — ingest documents and query the knowledge graph from the terminal

## Quickstart

```bash
# Install
pip install -e ".[dev]"

# Download spaCy model
python -m spacy download en_core_web_sm

# Ingest a document (DB is auto-created on first use)
kn0 ingest path/to/document.pdf

# List extracted entities
kn0 entities
kn0 entities --type PERSON
kn0 entities --search "Apple"

# List relationships
kn0 relationships --min-confidence 0.5

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
├── ingestion/          Document parsers (PDF, text, registry)
├── extraction/         NER, relationship extraction, entity resolution, confidence scoring
├── persistence/        SQLAlchemy Core models, database setup, data stores
├── api/                FastAPI REST API and visualization server (Phase 2+)
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
| 1 — Foundation | ✅ | Scaffold, DB schema, PDF/text ingestion, NER, CLI |
| 2 — Relationships | Planned | Full RE pipeline, FastAPI REST API |
| 3 — Visualization | Planned | Interactive network graph (Pyvis/D3.js) |
| 4 — Polish | Planned | DOCX/HTML/CSV parsers, pluggable NLP backends, Docker |

## License

MIT — see [LICENSE](LICENSE)
