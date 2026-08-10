"""Rendering of evaluation results: structured JSON and human-readable Markdown."""

from __future__ import annotations

from datetime import datetime

from .models import EvaluationResult

# Date/time localization: HR long form ("28. siječnja 2026.") vs US ("January 28, 2026").
_HR_MONTHS = {
    1: "siječnja",
    2: "veljače",
    3: "ožujka",
    4: "travnja",
    5: "svibnja",
    6: "lipnja",
    7: "srpnja",
    8: "kolovoza",
    9: "rujna",
    10: "listopada",
    11: "studenoga",
    12: "prosinca",
}
_EN_MONTHS = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}
_DATE_FORMATS = ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d")


def _parse_datetime(value: str) -> datetime | None:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def format_date(value: str, language: str) -> str:
    """Localize a date string: HR \"28. siječnja 2026.\" / US \"January 28, 2026\"."""
    dt = _parse_datetime(value)
    if dt is None:
        return value
    if language == "hr":
        return f"{dt.day}. {_HR_MONTHS[dt.month]} {dt.year}."
    return f"{_EN_MONTHS[dt.month]} {dt.day}, {dt.year}"


def format_datetime(value: str, language: str) -> str:
    """Localize a datetime string: HR \"28. siječnja 2026. u 21:02 (UTC)\" / US \"...\"."""
    dt = _parse_datetime(value)
    if dt is None:
        return value
    time_part = dt.strftime("%H:%M")
    date_part = format_date(value, language)
    if language == "hr":
        return f"{date_part} u {time_part} (UTC)"
    return f"{date_part}, {time_part} (UTC)"


def to_json(result: EvaluationResult) -> dict:
    return result.model_dump(mode="json")


def render_markdown(result: EvaluationResult) -> str:
    """Render a Markdown report that makes the reasoning behind every score visible."""
    article = result.article
    overall = result.overall
    lines: list[str] = []

    lines.append(f"# Lexi tekst evaluacija: {article.title or article.url}")
    lines.append("")
    lines.append(f"- **URL:** {article.url}")
    if article.author:
        lines.append(f"- **Autor:** {article.author}")
    if article.published_at:
        lines.append(f"- **Objavljeno:** {format_date(article.published_at, article.language)}")
    lines.append(f"- **Duljina:** {article.word_count} riječi · {article.read_time}")
    lines.append(
        f"- **Model (agenti):** {result.model} · **Model (sintetizator):** {result.synth_model or '—'}"
    )
    lines.append(f"- **Vrijeme izrade:** {format_datetime(result.created_at, article.language)}")
    lines.append("")

    lines.append(
        f"## Ukupna ocjena: **{overall.score:.1f} / 10 — {overall.letter_grade} ({overall.label})**"
    )
    lines.append("")
    lines.append("| Agent | Ocjena | Težina |")
    lines.append("|---|---|---|")
    for verdict in result.agent_verdicts:
        weight = overall.weights.get(verdict.agent_id, 0.0)
        status = "❌ neuspjeh" if verdict.error else f"{verdict.score:.1f}"
        lines.append(f"| {verdict.agent_name} | {status} | {weight:.0%} |")
    lines.append("")

    if result.synthesis:
        lines.append("## Finalni sud (sintetizator)")
        lines.append("")
        lines.append(result.synthesis.strip())
        lines.append("")

    for verdict in result.agent_verdicts:
        lines.append(f"## {verdict.agent_name} — {verdict.score:.1f} / 10")
        lines.append("")
        lines.append(f"*{verdict.perspective}*")
        lines.append("")
        if verdict.error:
            lines.append(f"> Agent nije uspio: `{verdict.error}`")
            lines.append("")
            continue

        if verdict.criteria:
            lines.append("| Kriterij | Ocjena | Obrazloženje |")
            lines.append("|---|---|---|")
            for criterion in verdict.criteria:
                lines.append(f"| {criterion.name} | {criterion.score:.1f} | {criterion.note} |")
            lines.append("")

        if verdict.strengths:
            lines.append("**Snage:**")
            lines.extend(f"- {s}" for s in verdict.strengths)
            lines.append("")

        if verdict.weaknesses:
            lines.append("**Slabosti:**")
            lines.extend(f"- {w}" for w in verdict.weaknesses)
            lines.append("")

        lines.append(verdict.verdict)
        lines.append("")

    return "\n".join(lines)
