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

# Grade label localization (canonical label -> HR / EN display).
_GRADE_LABELS = {
    "Excellent": ("Odličan", "Excellent"),
    "Very good": ("Vrlo dobar", "Very good"),
    "Good": ("Dobar", "Good"),
    "Adequate": ("Dovoljan", "Adequate"),
    "Weak": ("Slab", "Weak"),
    "Poor": ("Loš", "Poor"),
}

# Report chrome localization: {key: (hr, en)}. The whole report follows the
# article's language so an EN article never sees Croatian chrome (and vice versa).
_L = {
    "title_prefix": ("Lexi tekst evaluacija", "Lexi text evaluation"),
    "url": ("URL", "URL"),
    "author": ("Autor", "Author"),
    "published": ("Objavljeno", "Published"),
    "length": ("Duljina", "Length"),
    "words": ("riječi", "words"),
    "model_agents": ("Model (agenti)", "Model (agents)"),
    "model_synth": ("Model (sintetizator)", "Model (synthesizer)"),
    "created": ("Vrijeme izrade", "Created"),
    "overall": ("Ukupna ocjena", "Overall score"),
    "agent": ("Agent", "Agent"),
    "score": ("Ocjena", "Score"),
    "weight": ("Težina", "Weight"),
    "failed": ("neuspjeh", "failed"),
    "final_synthesis": ("Finalni sud (sintetizator)", "Final assessment (synthesizer)"),
    "criterion": ("Kriterij", "Criterion"),
    "rationale": ("Obrazloženje", "Rationale"),
    "strengths": ("Snage", "Strengths"),
    "weaknesses": ("Slabosti", "Weaknesses"),
    "agent_failed": ("Agent nije uspio", "Agent failed"),
}


def _t(language: str, key: str) -> str:
    hr, en = _L[key]
    return hr if language == "hr" else en


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
    lang = article.language if article.language in ("hr", "en") else "en"
    gr_label_hr, gr_label_en = _GRADE_LABELS.get(overall.label, (overall.label, overall.label))
    grade_label = gr_label_hr if lang == "hr" else gr_label_en
    lines: list[str] = []

    lines.append(f"# {_t(lang, 'title_prefix')}: {article.title or article.url}")
    lines.append("")
    lines.append(f"- **{_t(lang, 'url')}:** {article.url}")
    if article.author:
        lines.append(f"- **{_t(lang, 'author')}:** {article.author}")
    if article.published_at:
        lines.append(f"- **{_t(lang, 'published')}:** {format_date(article.published_at, lang)}")
    lines.append(
        f"- **{_t(lang, 'length')}:** {article.word_count} {_t(lang, 'words')} · {article.read_time}"
    )
    lines.append(
        f"- **{_t(lang, 'model_agents')}:** {result.model} · "
        f"**{_t(lang, 'model_synth')}:** {result.synth_model or '—'}"
    )
    lines.append(f"- **{_t(lang, 'created')}:** {format_datetime(result.created_at, lang)}")
    lines.append("")

    lines.append(
        f"## {_t(lang, 'overall')}: **{overall.score:.1f} / 10 — "
        f"{overall.letter_grade} ({grade_label})**"
    )
    lines.append("")
    lines.append(f"| {_t(lang, 'agent')} | {_t(lang, 'score')} | {_t(lang, 'weight')} |")
    lines.append("|---|---|---|")
    for verdict in result.agent_verdicts:
        weight = overall.weights.get(verdict.agent_id, 0.0)
        status = f"❌ {_t(lang, 'failed')}" if verdict.error else f"{verdict.score:.1f}"
        lines.append(f"| {verdict.agent_name} | {status} | {weight:.0%} |")
    lines.append("")

    if result.synthesis:
        lines.append(f"## {_t(lang, 'final_synthesis')}")
        lines.append("")
        lines.append(result.synthesis.strip())
        lines.append("")

    for verdict in result.agent_verdicts:
        lines.append(f"## {verdict.agent_name} — {verdict.score:.1f} / 10")
        lines.append("")
        lines.append(f"*{verdict.perspective}*")
        lines.append("")
        if verdict.error:
            lines.append(f"> {_t(lang, 'agent_failed')}: `{verdict.error}`")
            lines.append("")
            continue

        if verdict.criteria:
            lines.append(
                f"| {_t(lang, 'criterion')} | {_t(lang, 'score')} | {_t(lang, 'rationale')} |"
            )
            lines.append("|---|---|---|")
            for criterion in verdict.criteria:
                lines.append(f"| {criterion.name} | {criterion.score:.1f} | {criterion.note} |")
            lines.append("")

        if verdict.strengths:
            lines.append(f"**{_t(lang, 'strengths')}:**")
            lines.extend(f"- {s}" for s in verdict.strengths)
            lines.append("")

        if verdict.weaknesses:
            lines.append(f"**{_t(lang, 'weaknesses')}:**")
            lines.extend(f"- {w}" for w in verdict.weaknesses)
            lines.append("")

        lines.append(verdict.verdict)
        lines.append("")

    return "\n".join(lines)
