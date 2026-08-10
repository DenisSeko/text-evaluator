"""Extract clean article content from raw HTML.

Primary path uses `trafilatura` (robust for WordPress pages, removes navigation,
footer and boilerplate). If that yields nothing we fall back to a targeted
BeautifulSoup extraction that keeps only the article container.
"""

from __future__ import annotations

import re

import trafilatura
from bs4 import BeautifulSoup

from .models import Article

# Substrings that mark boilerplate blocks we never want inside the article.
_BOILERPLATE_MARKERS = (
    "kolačići",
    "cookie",
    "pročitaj još",
    "read more",
    "all rights reserved",
    "dogovorimo demo",
    "postani partner",
    "©",
)


def _clean_text(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # drop markdown links
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _estimate_read_time(word_count: int) -> str:
    minutes = max(1, round(word_count / 200))
    return f"{minutes} min"


def _headings_from_html(html: str) -> list[str]:
    """Collect H1/H2/H3 text used to verify/annotate structure."""
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return []
    headings: list[str] = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = _clean_text(tag.get_text(" ", strip=True))
        if text and text not in headings:
            headings.append(text)
    return headings


def _build_article(
    url: str,
    text: str,
    *,
    source: str,
    headings: list[str] | None = None,
    meta: dict[str, str] | None = None,
) -> Article:
    meta = meta or {}
    words = len(text.split())
    return Article(
        url=url,
        title=meta.get("title") or (headings[0] if headings else None),
        author=meta.get("author"),
        published_at=meta.get("date"),
        read_time=_estimate_read_time(words),
        plain_text=text,
        char_count=len(text),
        word_count=words,
        headings=headings or [],
        source=source,
    )


def _extract_bs4(html: str, url: str) -> Article:
    """Fallback extractor: keep only the article container and semantic blocks."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "aside", "form", "iframe"]):
        tag.decompose()

    container = soup.find("article") or soup.find("main") or soup.body
    if container is None:
        raise ValueError("No article content found in the page")

    # Drop boilerplate containers (cookie banners, related-posts blocks, ...).
    for el in list(container.find_all(["div", "section", "aside"])):
        text = el.get_text(" ", strip=True)
        if 0 < len(text) < 400 and any(m in text.lower() for m in _BOILERPLATE_MARKERS):
            el.decompose()

    headings: list[str] = []
    parts: list[str] = []
    for el in container.find_all(["h1", "h2", "h3", "p", "blockquote", "li"]):
        text = _clean_text(el.get_text(" ", strip=True))
        if not text:
            continue
        if el.name in ("h1", "h2", "h3"):
            if text not in headings:
                headings.append(text)
            parts.append(text)
        else:
            parts.append(text)

    body_text = "\n\n".join(parts)
    if not body_text:
        raise ValueError("No article text found in the page")
    return _build_article(url, body_text, source="beautifulsoup", headings=headings)


def extract_article(html: str, url: str) -> Article:
    """Extract a clean `Article` from raw HTML."""
    meta: dict[str, str] = {}
    text: str | None = None
    try:
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            include_links=False,
            favor_recall=False,
        )
        metadata = trafilatura.metadata.extract_metadata(html)
        if metadata:
            meta = {
                "title": metadata.title or "",
                "author": metadata.author or "",
                "date": metadata.date or "",
            }
    except Exception:
        text = None

    if text and text.strip():
        return _build_article(
            url,
            _clean_text(text),
            source="trafilatura",
            headings=_headings_from_html(html),
            meta=meta,
        )
    return _extract_bs4(html, url)
