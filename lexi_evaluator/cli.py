"""Command-line interface: `python -m lexi_evaluator <url>`."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .agents import get_agents
from .config import get_settings
from .extractor import extract_article
from .orchestrator import evaluate
from .providers import build_client
from .report import render_markdown, to_json
from .scraper import fetch_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lexi_evaluator",
        description=(
            "Evaluate the writing quality of a Lexi blog post using multiple AI agents. "
            "Run from the project root, e.g.: python -m lexi_evaluator <URL>"
        ),
    )
    parser.add_argument(
        "url", nargs="?", help="URL of a Lexi blog post (or fixture name with --fixture)"
    )
    parser.add_argument(
        "--output", choices=["md", "json"], default="md", help="Output format (default: md)"
    )
    parser.add_argument(
        "--out-file", type=Path, default=None, help="Write output to a file instead of stdout"
    )
    parser.add_argument("--model", default=None, help="Override the agent model (LEXI_MODEL)")
    parser.add_argument(
        "--synth-model", default=None, help="Override the synthesizer model (LEXI_MODEL_SYNTH)"
    )
    parser.add_argument("--agents", default=None, help="Comma-separated agent ids (default: all)")
    parser.add_argument("--no-synth", action="store_true", help="Skip the final synthesizer call")
    parser.add_argument("--no-cache", action="store_true", help="Bypass the on-disk HTML cache")
    parser.add_argument(
        "--dry-run", action="store_true", help="Use a mock LLM — no API key, no network"
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="Load article HTML from a local file instead of scraping (offline runs)",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="Truncate article text to N chars (default: LEXI_MAX_CHARS)",
    )
    return parser


def _log(message: str) -> None:
    print(message, file=sys.stderr)


async def _run(args: argparse.Namespace) -> None:
    settings = get_settings()
    model = args.model or settings.model
    synth_model = args.synth_model or settings.model_synth
    max_chars = args.max_chars or settings.max_chars

    # 1) Get raw HTML (scrape or fixture).
    if args.fixture:
        html = args.fixture.read_text(encoding="utf-8")
        url = args.url or f"fixture:{args.fixture.name}"
        _log(f"[lexi] loaded fixture {args.fixture.name}")
    else:
        if not args.url:
            raise SystemExit("error: a URL is required (or use --fixture for offline runs)")
        _log(f"[lexi] fetching {args.url} ...")
        html, url = await fetch_html(
            args.url,
            cache_dir=settings.cache_dir,
            use_cache=not args.no_cache,
            user_agent=settings.user_agent,
            timeout=settings.request_timeout,
        )

    # 2) Extract clean article content.
    article = extract_article(html, url)
    _log(f"[lexi] article: {article.title!r} ({article.word_count} words, {article.source})")

    # 3) Agents.
    agent_ids = args.agents.split(",") if args.agents else None
    agents = get_agents(agent_ids)
    _log(f"[lexi] agents: {', '.join(a.id for a in agents)}")

    # 4) LLM clients.
    client = build_client(settings, dry_run=args.dry_run, model=model)
    synth_client = (
        None if args.no_synth else build_client(settings, dry_run=args.dry_run, model=synth_model)
    )

    # 5) Evaluate.
    result = await evaluate(
        article,
        client,
        agents=agents,
        weights=settings.agent_weights(),
        synth_client=synth_client,
        model=model,
        synth_model=synth_model if synth_client is not None else None,
        max_chars=max_chars,
        temperature=settings.temperature,
    )

    # 6) Render.
    if args.output == "json":
        text = json.dumps(to_json(result), ensure_ascii=False, indent=2)
    else:
        text = render_markdown(result)

    if args.out_file:
        args.out_file.parent.mkdir(parents=True, exist_ok=True)
        args.out_file.write_text(text, encoding="utf-8")
        _log(f"[lexi] wrote {args.output.upper()} to {args.out_file}")
    else:
        print(text)


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
