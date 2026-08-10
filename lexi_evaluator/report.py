"""Rendering of evaluation results: structured JSON and human-readable Markdown."""

from __future__ import annotations

from .models import EvaluationResult


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
        lines.append(f"- **Objavljeno:** {article.published_at}")
    lines.append(f"- **Duljina:** {article.word_count} riječi · {article.read_time}")
    lines.append(
        f"- **Model (agenti):** {result.model} · **Model (sintetizator):** {result.synth_model or '—'}"
    )
    lines.append(f"- **Vrijeme izrade:** {result.created_at}")
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
