"""PDF document parser using PyMuPDF with optional OCR fallback."""

from __future__ import annotations

import warnings
from pathlib import Path

from kn0.ingestion.base import DocumentParser, PageContent, ParsedDocument

# Minimum character count to consider a page "text-bearing" (not scanned)
_MIN_CHARS_FOR_TEXT = 20


class PdfParser(DocumentParser):
    """Extracts text from PDF files page-by-page using PyMuPDF."""

    SUPPORTED_MIMES = {"application/pdf"}

    def can_parse(self, mime_type: str) -> bool:
        return mime_type in self.SUPPORTED_MIMES

    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise RuntimeError("PyMuPDF (fitz) is required for PDF parsing. Run: pip install pymupdf") from e

        doc = fitz.open(str(file_path))
        pages: list[PageContent] = []
        full_text_parts: list[str] = []
        char_offset = 0

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_text = page.get_text("text")

            if len(page_text.strip()) < _MIN_CHARS_FOR_TEXT:
                page_text = self._ocr_fallback(page, page_idx + 1)

            pages.append(
                PageContent(
                    page_number=page_idx + 1,
                    text=page_text,
                    char_offset=char_offset,
                )
            )
            full_text_parts.append(page_text)
            char_offset += len(page_text)

        doc.close()
        full_text = "\n".join(full_text_parts)

        return ParsedDocument(
            text=full_text,
            pages=pages,
            metadata={"source_path": str(file_path)},
            language="en",
            page_count=len(pages),
        )

    def _ocr_fallback(self, page: object, page_num: int) -> str:
        """Attempt OCR via Tesseract if available, otherwise return empty string."""
        try:
            import fitz

            # PyMuPDF ≥ 1.21 supports get_textpage_ocr for Tesseract-backed OCR
            if hasattr(page, "get_textpage_ocr"):
                tp = page.get_textpage_ocr(flags=3, language="eng", dpi=150)
                return page.get_text(textpage=tp)  # type: ignore[arg-type]
        except Exception:
            pass

        warnings.warn(
            f"Page {page_num} appears to be scanned and OCR is not available. "
            "Install Tesseract and PyMuPDF ≥ 1.21 for OCR support.",
            stacklevel=2,
        )
        return ""
