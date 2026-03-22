"""Plain text and Markdown document parser."""

from __future__ import annotations

from pathlib import Path

from kn0.ingestion.base import DocumentParser, PageContent, ParsedDocument

# Approximate characters per pseudo-page for plain text
_CHARS_PER_PAGE = 3000


class TextParser(DocumentParser):
    """Handles .txt and .md files by splitting into pseudo-pages."""

    SUPPORTED_MIMES = {
        "text/plain",
        "text/markdown",
        "text/x-markdown",
    }

    def can_parse(self, mime_type: str) -> bool:
        return mime_type in self.SUPPORTED_MIMES

    def parse(self, file_path: Path) -> ParsedDocument:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        pages = self._split_pages(text)
        return ParsedDocument(
            text=text,
            pages=pages,
            metadata={"source_path": str(file_path)},
            language="en",
            page_count=len(pages),
        )

    def _split_pages(self, text: str) -> list[PageContent]:
        """Split text into pseudo-pages at paragraph boundaries."""
        if not text.strip():
            return [PageContent(page_number=1, text="", char_offset=0)]

        pages: list[PageContent] = []
        page_num = 1
        start = 0

        while start < len(text):
            end = start + _CHARS_PER_PAGE
            if end >= len(text):
                pages.append(PageContent(page_number=page_num, text=text[start:], char_offset=start))
                break

            # Try to break at a paragraph boundary (double newline)
            split_pos = text.rfind("\n\n", start, end)
            if split_pos == -1 or split_pos <= start:
                # Fall back to single newline
                split_pos = text.rfind("\n", start, end)
            if split_pos == -1 or split_pos <= start:
                split_pos = end

            chunk = text[start : split_pos + 1]
            pages.append(PageContent(page_number=page_num, text=chunk, char_offset=start))
            page_num += 1
            start = split_pos + 1

        return pages
