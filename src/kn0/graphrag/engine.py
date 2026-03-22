"""GraphRAG engine scaffold — Graph Retrieval-Augmented Generation for kn0.

This module establishes the async interface for graph-grounded LLM queries.
The public methods raise NotImplementedError until implemented in a future phase.

Planned architecture:
    1. Subgraph retrieval  — fetch N-hop entity neighbourhood from SQLite
    2. Context serialisation — convert subgraph to structured natural-language text
    3. Grounded Q&A  — answer questions using graph context as RAG input
    4. Summarisation — summarise entity connections, timeline, and relationships
"""

from __future__ import annotations

from sqlalchemy.engine import Connection

from kn0.llm.client import LLMClient


class GraphRAGEngine:
    """Graph Retrieval-Augmented Generation engine.

    Uses the kn0 knowledge graph as a structured retrieval context for LLM
    queries.  All methods are async so they compose naturally with the Phase-2
    FastAPI REST API and the LLM client's async interface.

    Example future usage::

        async with engine_context() as engine:
            answer = await engine.query("Who founded Apple Inc.?")
            summary = await engine.summarise_entity(entity_id)
    """

    def __init__(self, conn: Connection, llm_client: LLMClient) -> None:
        self._conn = conn
        self._client = llm_client

    async def query(
        self,
        question: str,
        *,
        entity_ids: list[str] | None = None,
        max_hops: int = 2,
    ) -> str:
        """Answer a natural-language question grounded in the knowledge graph.

        Args:
            question: The question to answer.
            entity_ids: Optional seed entities to focus the subgraph retrieval.
                        If None, the engine attempts to identify relevant
                        entities via full-text search.
            max_hops: How many relationship hops to traverse from seed entities.

        Returns:
            A natural-language answer with provenance references.

        Raises:
            NotImplementedError: Until GraphRAG is fully implemented.
        """
        raise NotImplementedError(
            "GraphRAG query is not yet implemented. "
            "Use `kn0 entities --search` or `kn0 relationships` for now."
        )

    async def summarise_entity(self, entity_id: str) -> str:
        """Generate a natural-language summary of an entity and its connections.

        Args:
            entity_id: The UUID of the entity to summarise.

        Returns:
            A paragraph summarising the entity, its key relationships,
            associated events, and timeline.

        Raises:
            NotImplementedError: Until summarisation is fully implemented.
        """
        raise NotImplementedError(
            "Entity summarisation is not yet implemented."
        )

    async def _retrieve_subgraph(
        self,
        entity_ids: list[str],
        max_hops: int = 2,
    ) -> dict:
        """Retrieve the N-hop subgraph around a set of seed entities.

        Returns a dict with keys:
            - "entities": list of entity rows
            - "relationships": list of relationship rows
            - "events": list of event rows involving these entities
        """
        raise NotImplementedError

    async def _serialise_subgraph(self, subgraph: dict) -> str:
        """Convert a subgraph dict to a structured text block for LLM context.

        Output format (example)::

            ENTITIES:
            - Apple Inc. [ORGANIZATION] — mention_count: 12
            - Steve Jobs [PERSON] — mention_count: 8

            RELATIONSHIPS:
            - Steve Jobs WORKS_FOR Apple Inc. (confidence: 0.91)

            EVENTS:
            - 1976-04-01: FOUNDING — "Apple Computer Company founded"
              Participants: Steve Jobs (FOUNDER), Steve Wozniak (FOUNDER)
        """
        raise NotImplementedError
