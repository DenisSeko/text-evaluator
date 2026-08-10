"""Extractor tests: clean article content in, boilerplate out."""

from __future__ import annotations

from lexi_evaluator.extractor import detect_language, extract_article

SAMPLE_URL = "https://lexi.hr/why-writing-sounds-generic/"


def test_article_extracted(sample_html: str) -> None:
    article = extract_article(sample_html, SAMPLE_URL)
    assert article.plain_text
    assert article.word_count > 50
    assert article.char_count == len(article.plain_text)


def test_title_detected(sample_html: str) -> None:
    article = extract_article(sample_html, SAMPLE_URL)
    assert article.title
    assert "generic" in article.title.lower()


def test_contains_article_body(sample_html: str) -> None:
    article = extract_article(sample_html, SAMPLE_URL)
    body = article.plain_text.lower()
    # A real sentence from the article body must survive extraction.
    assert "nobody wakes up" in body or "generic" in body


def test_boilerplate_removed(sample_html: str) -> None:
    article = extract_article(sample_html, SAMPLE_URL)
    body = article.plain_text.lower()
    for marker in ("kolačići", "pročitaj još", "all rights reserved", "© 2026"):
        assert marker not in body, f"boilerplate marker leaked into article: {marker!r}"


def test_headings_detected(sample_html: str) -> None:
    article = extract_article(sample_html, SAMPLE_URL)
    assert article.headings, "expected at least one heading"
    assert any("generic" in h.lower() for h in article.headings)


def test_source_is_set(sample_html: str) -> None:
    article = extract_article(sample_html, SAMPLE_URL)
    assert article.source in ("trafilatura", "beautifulsoup")


def test_article_language(sample_html: str) -> None:
    article = extract_article(sample_html, SAMPLE_URL)
    assert article.language in ("hr", "en")
    # The fixture article is English (no Croatian diacritics in the body).
    assert article.language == "en"


def test_detect_language_english() -> None:
    assert detect_language("This is a plain English sentence with no diacritics.") == "en"


def test_detect_language_croatian() -> None:
    assert detect_language("Ovo je hrvatski tekst koji sadrži č, ć, š, ž i đ.") == "hr"


def test_detect_language_empty() -> None:
    assert detect_language("") == "en"
