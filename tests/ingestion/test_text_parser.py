"""Tests for the plain text document parser."""

from pathlib import Path

import pytest

from kn0.ingestion.text_parser import TextParser, _CHARS_PER_PAGE


@pytest.fixture
def parser():
    return TextParser()


def test_can_parse_text_plain(parser):
    assert parser.can_parse("text/plain") is True


def test_can_parse_markdown(parser):
    assert parser.can_parse("text/markdown") is True


def test_cannot_parse_pdf(parser):
    assert parser.can_parse("application/pdf") is False


def test_parse_short_text(parser, tmp_path):
    f = tmp_path / "short.txt"
    f.write_text("Hello world. This is a test.", encoding="utf-8")
    doc = parser.parse(f)

    assert doc.text == "Hello world. This is a test."
    assert len(doc.pages) == 1
    assert doc.pages[0].page_number == 1
    assert doc.pages[0].text == "Hello world. This is a test."
    assert doc.page_count == 1


def test_parse_multipage_text(parser, tmp_path):
    # Create text longer than _CHARS_PER_PAGE
    long_text = ("A" * 100 + "\n\n") * 50   # ~5200 chars
    f = tmp_path / "long.txt"
    f.write_text(long_text, encoding="utf-8")
    doc = parser.parse(f)

    assert len(doc.pages) > 1
    for i, page in enumerate(doc.pages, 1):
        assert page.page_number == i


def test_parse_empty_file(parser, tmp_path):
    f = tmp_path / "empty.txt"
    f.write_text("", encoding="utf-8")
    doc = parser.parse(f)

    assert doc.page_count >= 1
    assert doc.text == ""


def test_page_char_offsets_are_consistent(parser, tmp_path):
    text = "First paragraph.\n\n" + "Second paragraph.\n\n" + "X" * 4000
    f = tmp_path / "offsets.txt"
    f.write_text(text, encoding="utf-8")
    doc = parser.parse(f)

    # Verify char_offset of each page points into the original text
    for page in doc.pages:
        assert doc.text[page.char_offset : page.char_offset + 5] == page.text[:5]
