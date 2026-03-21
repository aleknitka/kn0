"""Extensible type registry for entity, relationship, and event types.

Wraps the existing EntityType enum without modifying it. Custom types can be
registered at runtime via ``registry.register("MY_TYPE")``.
"""

from __future__ import annotations


class TypeRegistry:
    """A case-insensitive set of valid type strings, extensible at runtime."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._types: dict[str, str] = {}  # upper → original

    def seed_from_enum(self, enum_class: type) -> None:
        """Seed the registry from an enum whose values are strings."""
        for member in enum_class:
            self._types[member.value.upper()] = member.value

    def register(self, type_string: str) -> None:
        """Add a custom type string to the registry."""
        self._types[type_string.upper()] = type_string

    def is_valid(self, type_string: str) -> bool:
        """Return True if the type string is registered (case-insensitive)."""
        return type_string.upper() in self._types

    def all_types(self) -> list[str]:
        """Return all registered type strings, sorted."""
        return sorted(self._types.values())


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

from kn0.extraction.entity_types import EntityType  # noqa: E402

entity_type_registry = TypeRegistry("entity")
entity_type_registry.seed_from_enum(EntityType)

relationship_type_registry = TypeRegistry("relationship")
for _rt in [
    "WORKS_FOR",
    "AFFILIATED_WITH",
    "LOCATED_IN",
    "PART_OF",
    "LEADS",
    "KNOWS",
    "PARTICIPATED_IN",
    "CAUSED",
    "PRECEDED",
    "OWNS",
    "RELATED_TO",
]:
    relationship_type_registry.register(_rt)

event_type_registry = TypeRegistry("event")
for _et in [
    "MEETING",
    "CONFLICT",
    "ELECTION",
    "ACQUISITION",
    "FOUNDING",
    "DEATH",
    "BIRTH",
    "TRIAL",
    "TREATY",
    "ANNOUNCEMENT",
    "APPOINTMENT",
    "RESIGNATION",
    "MERGER",
    "ATTACK",
    "OTHER",
]:
    event_type_registry.register(_et)
