"""Report tests: date/time localization for HR and US formats."""

from __future__ import annotations

from lexi_evaluator.models import AgentVerdict, Article, EvaluationResult, OverallScore
from lexi_evaluator.report import format_date, format_datetime, render_markdown


def test_format_date_croatian() -> None:
    assert format_date("2026-01-28", "hr") == "28. siječnja 2026."


def test_format_date_american() -> None:
    assert format_date("2026-01-28", "en") == "January 28, 2026"


def test_format_datetime_croatian() -> None:
    assert format_datetime("2026-08-10T21:02:16+00:00", "hr") == "10. kolovoza 2026. u 21:02 (UTC)"


def test_format_datetime_american() -> None:
    assert format_datetime("2026-08-10T21:02:16+00:00", "en") == "August 10, 2026, 21:02 (UTC)"


def test_format_date_unknown_value_passthrough() -> None:
    assert format_date("n/a", "hr") == "n/a"
    assert format_datetime("unknown", "en") == "unknown"


def _result(language: str) -> EvaluationResult:
    article = Article(
        url="https://lexi.hr/example/",
        title="Example",
        author="Author",
        published_at="2026-01-28",
        read_time="2 min",
        plain_text="Text.",
        char_count=5,
        word_count=1,
        language=language,
    )
    verdict = AgentVerdict(
        agent_id="structure",
        agent_name="Struktura i tok" if language == "hr" else "Structure and flow",
        perspective=(
            "Vodi li tekst čitatelja logično."
            if language == "hr"
            else "Does the text guide the reader logically."
        ),
        score=8.0,
        criteria=[{"name": "Clarity", "score": 8.0, "note": "Clear."}],
        strengths=["Good hook."],
        weaknesses=["Dense paragraph."],
        verdict="Well structured.",
    )
    return EvaluationResult(
        article=article,
        model="mock",
        synth_model="mock",
        agent_verdicts=[verdict],
        overall=OverallScore(
            score=8.0,
            letter_grade="B",
            label="Very good",
            weights={"structure": 1.0},
            agent_scores={"structure": 8.0},
        ),
        synthesis="Final assessment.",
        created_at="2026-08-10T21:02:16+00:00",
    )


def test_report_chrome_localized_croatian() -> None:
    md = render_markdown(_result("hr"))
    assert "Lexi tekst evaluacija:" in md
    assert "**Autor:**" in md
    assert "**Objavljeno:** 28. siječnja 2026." in md
    assert "**Duljina:** 1 riječi · 2 min" in md
    assert "Ukupna ocjena: **8.0 / 10 — B (Vrlo dobar)**" in md
    assert "Struktura i tok" in md
    assert "Lexi text evaluation" not in md  # no English chrome leaked
    assert "| Kriterij | Ocjena | Obrazloženje |" in md
    assert "**Snage:**" in md
    assert "**Slabosti:**" in md
    assert "Vodi li tekst čitatelja logično." in md


def test_report_chrome_localized_english() -> None:
    md = render_markdown(_result("en"))
    assert "Lexi text evaluation:" in md
    assert "**Author:**" in md
    assert "**Published:** January 28, 2026" in md
    assert "**Length:** 1 words · 2 min" in md
    assert "Overall score: **8.0 / 10 — B (Very good)**" in md
    assert "Structure and flow" in md
    assert "Lexi tekst evaluacija" not in md  # no Croatian chrome leaked
    assert "| Criterion | Score | Rationale |" in md
    assert "**Strengths:**" in md
    assert "**Weaknesses:**" in md
    assert "Does the text guide the reader logically." in md
