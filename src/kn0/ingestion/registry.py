"""Parser registry: maps MIME types to DocumentParser implementations."""

from __future__ import annotations

from pathlib import Path

from kn0.ingestion.base import DocumentParser, ParsedDocument
from kn0.ingestion.pdf_parser import PdfParser
from kn0.ingestion.text_parser import TextParser

# Extension to MIME type fallback mapping (when python-magic is unavailable)
_EXT_TO_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/plain",
    ".markdown": "text/plain",
}


def _detect_mime(file_path: Path) -> str:
    """Detect MIME type via python-magic, falling back to extension lookup."""
    try:
        import magic
        return magic.from_file(str(file_path), mime=True)
    except (ImportError, Exception):
        ext = file_path.suffix.lower()
        return _EXT_TO_MIME.get(ext, "application/octet-stream")


class ParserRegistry:
    """Registry that selects the appropriate parser for a given file."""

    def __init__(self) -> None:
        self._parsers: list[DocumentParser] = []
        # Register built-in parsers
        self.register(TextParser())
        self.register(PdfParser())

    def register(self, parser: DocumentParser) -> None:
        """Add a parser to the registry."""
        self._parsers.append(parser)

    def get_parser(self, mime_type: str) -> DocumentParser:
        """Return the first parser that handles this MIME type."""
        for parser in self._parsers:
            if parser.can_parse(mime_type):
                return parser
        raise ValueError(f"No parser available for MIME type: {mime_type!r}")

    def parse(self, file_path: Path) -> tuple[ParsedDocument, str]:
        """Detect MIME type, select parser, and return (ParsedDocument, mime_type)."""
        mime_type = _detect_mime(file_path)
        parser = self.get_parser(mime_type)
        return parser.parse(file_path), mime_type


# Module-level default registry instance
default_registry = ParserRegistry()
