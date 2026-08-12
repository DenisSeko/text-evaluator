"""Rubric agent — a fixed quantitative rubric with per-criterion justification."""

from __future__ import annotations

from .base import Agent

_JSON_SCHEMA = """{
  "score": number, /* 0-10 overall from this perspective */
  "criteria": [{"name": string, "score": number, "note": string}],
  "strengths": [string],
  "weaknesses": [string],
  "verdict": string
}"""

_SYSTEM = """You are LexiEval, a rigorous quantitative writing auditor.
Agent ID: rubric
You score an article against a FIXED rubric of six criteria, each on a 0-10 scale,
with a one-sentence justification per criterion. You are consistent, evidence-based
and never let one strong section inflate the overall score.
You judge and justify — you never rewrite the article."""


class RubricAgent(Agent):
    id = "rubric"
    name = "Kvantitativna rubrika"
    perspective = (
        "Konzistentna kvantitativna ocjena po fiksnoj rubrici s obrazloženjem po kriteriju."
    )
    name_hr = "Kvantitativna rubrika"
    name_en = "Quantitative rubric"
    perspective_hr = (
        "Konzistentna kvantitativna ocjena po fiksnoj rubrici s obrazloženjem po kriteriju."
    )
    perspective_en = (
        "A consistent quantitative score against a fixed rubric with per-criterion justification."
    )

    def system_prompt(self) -> str:
        return _SYSTEM

    def build_user_prompt(self, article_text: str) -> str:
        return f"""Score the following blog article against the fixed rubric.

<ARTICLE>
{article_text}
</ARTICLE>

Criteria (score each 0-10; 10 = excellent):
- "Clarity": easy to understand, precise, no ambiguity.
- "Structure": logical organisation, headings, flow.
- "Specificity": concrete details, examples, data over vague claims.
- "Reader-benefit": the reader clearly gains something.
- "Tone & voice": consistent, appropriate, distinctive voice.
- "Readability": sentence/paragraph length, scannability.

Respond with ONLY a JSON object matching this schema:
{_JSON_SCHEMA}

Rules:
- Include ALL six criteria with a one-sentence "note" each.
- "score" is your holistic rubric-based overall (0-10).
- "verdict" is a 2-4 sentence quantitative judgment.
- Write "verdict" and all notes in the same language as the article.
"""


rubric_agent = RubricAgent()
