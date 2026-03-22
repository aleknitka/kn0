"""Base classes and data structures for document parsing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PageContent:
    page_number: int      # 1-based
    text: str
    char_offset: int = 0  # character offset of this page within the full document text


@dataclass
class ParsedDocument:
    """Result of parsing a document file."""
    text: str                              # Full concatenated text
    pages: list[PageContent]              # Per-page breakdown
    metadata: dict[str, Any] = field(default_factory=dict)
    language: str = "en"
    page_count: int = 0

    def __post_init__(self) -> None:
        if not self.page_count:
            self.page_count = len(self.pages)


class DocumentParser(ABC):
    """Abstract base class for format-specific document parsers."""

    @abstractmethod
    def can_parse(self, mime_type: str) -> bool:
        """Return True if this parser handles the given MIME type."""

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse the file and return structured content with page breakdown."""
