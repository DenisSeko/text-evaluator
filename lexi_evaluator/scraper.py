"""Fetching raw HTML for an article URL, with an optional on-disk cache."""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx

DEFAULT_USER_AGENT = "lexi-evaluator/0.1 (job-task demo)"


async def fetch_html(
    url: str,
    *,
    cache_dir: str | Path = ".cache",
    use_cache: bool = True,
    user_agent: str | None = None,
    timeout: float = 30.0,
) -> tuple[str, str]:
    """Fetch a URL and return ``(html, final_url)``.

    The raw HTML is cached on disk (keyed by URL hash) so repeated runs during
    development don't re-download the page. Pass ``use_cache=False`` to bypass.
    """
    cache_dir = Path(cache_dir)
    cache_key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    cache_file = cache_dir / f"lexi-{cache_key}.html"

    if use_cache and cache_file.exists():
        return cache_file.read_text(encoding="utf-8"), url

    headers = {
        "User-Agent": user_agent or DEFAULT_USER_AGENT,
        "Accept-Language": "hr,en;q=0.8,hr;q=0.6",
        "Accept": "text/html,application/xhtml+xml",
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text
        final_url = str(response.url)

    if use_cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(html, encoding="utf-8")

    return html, final_url
