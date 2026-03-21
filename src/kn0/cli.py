"""kn0 CLI — command-line interface for document ingestion and knowledge graph queries."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="kn0",
    help="Entity & Relationship Extraction Engine — Knowledge Graph Builder",
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True, style="bold red")


def _get_conn():
    """Get a database connection, initializing DB if needed."""
    from kn0.persistence.database import get_connection
    return get_connection()


# ---------------------------------------------------------------------------
# kn0 ingest <file>
# ---------------------------------------------------------------------------


@app.command()
def ingest(
    file: Path = typer.Argument(..., help="Path to the document to ingest"),
    source_reliability: float = typer.Option(
        0.5, "--reliability", "-r", help="Source reliability weight [0–1]"
    ),
    backend: str = typer.Option(
        "spacy", "--backend", "-b", help="Extraction backend: spacy | llm"
    ),
) -> None:
    """Parse a document and extract entities and relationships into the knowledge graph."""
    if not file.exists():
        err_console.print(f"File not found: {file}")
        raise typer.Exit(1)

    if backend not in ("spacy", "llm"):
        err_console.print(f"Unknown backend {backend!r}. Choose: spacy, llm")
        raise typer.Exit(1)

    from kn0.pipeline import ingest_document

    extraction_backend = None
    if backend == "llm":
        from kn0.llm import get_llm_backend
        extraction_backend = get_llm_backend()
        console.print(f"[cyan]Ingesting[/cyan] {file.name} [dim](backend: llm)[/dim] ...")
    else:
        console.print(f"[cyan]Ingesting[/cyan] {file.name} ...")

    with _get_conn() as conn:
        result = ingest_document(
            file, conn,
            backend=extraction_backend,
            source_reliability=source_reliability,
        )

    if result.was_duplicate:
        console.print(f"[yellow]Already ingested[/yellow] (document id: {result.document_id})")
        return

    if result.error:
        err_console.print(f"Ingestion failed: {result.error}")
        raise typer.Exit(1)

    console.print(f"[green]Done![/green] Document id: {result.document_id}")
    console.print(f"  Pages processed : {result.pages_processed}")
    console.print(f"  Entities created: {result.entities_created}")
    console.print(f"  Entities merged : {result.entities_merged}")
    console.print(f"  Relationships   : {result.relationships_created} new, {result.relationships_updated} updated")


# ---------------------------------------------------------------------------
# kn0 entities
# ---------------------------------------------------------------------------


@app.command()
def entities(
    entity_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by entity type (PERSON, ORGANIZATION, …)"
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of results"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search by name"),
) -> None:
    """List entities stored in the knowledge graph."""
    from kn0.persistence.store import EntityStore

    with _get_conn() as conn:
        store = EntityStore(conn)
        if search:
            rows = store.search_fts(search, limit=limit)
        else:
            rows = store.list_all(entity_type=entity_type, limit=limit)

    if not rows:
        console.print("[yellow]No entities found.[/yellow]")
        return

    table = Table(title=f"Entities ({len(rows)} shown)")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Mentions", justify="right")
    table.add_column("Aliases", style="dim")

    for row in rows:
        aliases = json.loads(row.get("aliases") or "[]")
        table.add_row(
            row["id"][:8],
            row["entity_type"],
            row["canonical_name"],
            str(row.get("mention_count", 0)),
            ", ".join(aliases[:3]) + ("…" if len(aliases) > 3 else ""),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# kn0 relationships
# ---------------------------------------------------------------------------


@app.command()
def relationships(
    rel_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by relationship type"),
    min_confidence: float = typer.Option(0.0, "--min-confidence", "-c", help="Minimum confidence"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of results"),
) -> None:
    """List relationships stored in the knowledge graph."""
    from kn0.persistence.store import RelationshipStore

    with _get_conn() as conn:
        store = RelationshipStore(conn)
        rows = store.list_all(
            relationship_type=rel_type,
            min_confidence=min_confidence if min_confidence > 0 else None,
            limit=limit,
        )

    if not rows:
        console.print("[yellow]No relationships found.[/yellow]")
        return

    table = Table(title=f"Relationships ({len(rows)} shown)")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Type", style="cyan")
    table.add_column("Source", max_width=20)
    table.add_column("Target", max_width=20)
    table.add_column("Confidence", justify="right")
    table.add_column("Status")

    for row in rows:
        conf = row.get("confidence_score", 0.0)
        conf_style = "green" if conf >= 0.7 else ("yellow" if conf >= 0.4 else "red")
        table.add_row(
            row["id"][:8],
            row["relationship_type"],
            row["source_entity_id"][:8],
            row["target_entity_id"][:8],
            f"[{conf_style}]{conf:.2f}[/{conf_style}]",
            row.get("status", ""),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# kn0 status
# ---------------------------------------------------------------------------


@app.command()
def status() -> None:
    """Show knowledge graph statistics."""
    from sqlalchemy import func, select
    from kn0.persistence.models import documents, entities, events, relationships

    with _get_conn() as conn:
        doc_count = conn.execute(select(func.count()).select_from(documents)).scalar()
        entity_count = conn.execute(select(func.count()).select_from(entities)).scalar()
        rel_count = conn.execute(select(func.count()).select_from(relationships)).scalar()
        event_count = conn.execute(select(func.count()).select_from(events)).scalar()

    table = Table(title="kn0 Knowledge Graph Status")
    table.add_column("Metric")
    table.add_column("Count", justify="right", style="bold")

    table.add_row("Documents ingested", str(doc_count))
    table.add_row("Entities", str(entity_count))
    table.add_row("Relationships", str(rel_count))
    table.add_row("Events", str(event_count))

    console.print(table)


# ---------------------------------------------------------------------------
# kn0 documents
# ---------------------------------------------------------------------------


@app.command()
def documents() -> None:
    """List all ingested documents."""
    from kn0.persistence.store import DocumentStore

    with _get_conn() as conn:
        store = DocumentStore(conn)
        rows = store.list_all()

    if not rows:
        console.print("[yellow]No documents ingested yet.[/yellow]")
        return

    table = Table(title=f"Documents ({len(rows)})")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Filename")
    table.add_column("Status", style="cyan")
    table.add_column("Pages", justify="right")
    table.add_column("Ingested at", style="dim")

    for row in rows:
        table.add_row(
            row["id"][:8],
            row["filename"],
            row["status"],
            str(row.get("page_count") or "—"),
            (row.get("created_at") or "")[:19],
        )

    console.print(table)


# ---------------------------------------------------------------------------
# kn0 events
# ---------------------------------------------------------------------------


@app.command()
def events(
    event_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by event type (MEETING, CONFLICT, …)"
    ),
    entity: Optional[str] = typer.Option(
        None, "--entity", "-e", help="Filter by entity ID (shows events they participated in)"
    ),
    after: Optional[str] = typer.Option(None, "--after", help="Show events starting on/after ISO date"),
    before: Optional[str] = typer.Option(None, "--before", help="Show events starting on/before ISO date"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of results"),
) -> None:
    """List events in the knowledge graph."""
    from kn0.persistence.store import EventStore

    with _get_conn() as conn:
        store = EventStore(conn)
        rows = store.list_all(
            event_type=event_type,
            entity_id=entity,
            start_date_gte=after,
            start_date_lte=before,
            limit=limit,
        )
        # Fetch participant counts separately
        from sqlalchemy import func, select
        from kn0.persistence.models import event_participants as ep_table
        counts: dict[str, int] = {}
        if rows:
            event_ids = [r["id"] for r in rows]
            count_rows = conn.execute(
                select(ep_table.c.event_id, func.count().label("cnt"))
                .where(ep_table.c.event_id.in_(event_ids))
                .group_by(ep_table.c.event_id)
            ).mappings().all()
            counts = {r["event_id"]: r["cnt"] for r in count_rows}

    if not rows:
        console.print("[yellow]No events found.[/yellow]")
        return

    table = Table(title=f"Events ({len(rows)} shown)")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Type", style="cyan")
    table.add_column("Title", style="bold")
    table.add_column("Start Date")
    table.add_column("End Date", style="dim")
    table.add_column("Participants", justify="right")

    for row in rows:
        table.add_row(
            row["id"][:8],
            row["event_type"],
            row["title"],
            row.get("start_date") or "—",
            row.get("end_date") or "—",
            str(counts.get(row["id"], 0)),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# kn0 timeline
# ---------------------------------------------------------------------------


@app.command()
def timeline(
    entity: Optional[str] = typer.Option(
        None, "--entity", "-e", help="Filter by entity ID (shows events they participated in)"
    ),
    event_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by event type"),
    after: Optional[str] = typer.Option(None, "--after", help="Show events starting on/after ISO date"),
    before: Optional[str] = typer.Option(None, "--before", help="Show events starting on/before ISO date"),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum number of results"),
) -> None:
    """Display a chronological timeline of events."""
    from kn0.persistence.store import EventStore

    with _get_conn() as conn:
        store = EventStore(conn)
        rows = store.get_timeline(
            entity_id=entity,
            event_type=event_type,
            start_date_gte=after,
            start_date_lte=before,
            limit=limit,
        )

    if not rows:
        console.print("[yellow]No events found.[/yellow]")
        return

    dated = [r for r in rows if r.get("start_date")]
    undated = [r for r in rows if not r.get("start_date")]

    def _render_section(section_rows: list[dict], title: str) -> None:
        tbl = Table(title=title)
        tbl.add_column("Start", style="cyan", min_width=10)
        tbl.add_column("End", style="dim", min_width=10)
        tbl.add_column("Type")
        tbl.add_column("Title", style="bold")
        tbl.add_column("Participants", justify="right")
        for row in section_rows:
            tbl.add_row(
                row.get("start_date") or "—",
                row.get("end_date") or "—",
                row["event_type"],
                row["title"],
                str(row.get("participant_count", 0)),
            )
        console.print(tbl)

    if dated:
        _render_section(dated, f"Timeline ({len(dated)} dated event{'s' if len(dated) != 1 else ''})")
    if undated:
        _render_section(undated, f"Undated Events ({len(undated)})")


# ---------------------------------------------------------------------------
# kn0 ask  (GraphRAG stub — will be fully implemented in Phase 2)
# ---------------------------------------------------------------------------


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to answer using the knowledge graph"),
) -> None:
    """Ask a question answered by the knowledge graph (GraphRAG — coming soon)."""
    console.print(
        "[yellow]GraphRAG query is not yet fully implemented.[/yellow]\n"
        "In the meantime, try:\n"
        "  [cyan]kn0 entities --search[/cyan] <term>\n"
        "  [cyan]kn0 relationships[/cyan]\n"
        "  [cyan]kn0 timeline[/cyan]"
    )


# ---------------------------------------------------------------------------
# kn0 serve  — start the web dashboard
# ---------------------------------------------------------------------------


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (dev mode)"),
) -> None:
    """Start the kn0 web dashboard."""
    import uvicorn
    console.print(f"[cyan]Starting kn0 web dashboard[/cyan] → http://{host}:{port}")
    uvicorn.run(
        "kn0.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
