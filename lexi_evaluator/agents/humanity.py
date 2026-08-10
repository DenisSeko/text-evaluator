"""Humanity / anti-generic agent — how human and distinctive the voice is."""

from __future__ import annotations

from .base import Agent

_JSON_SCHEMA = """{
  "score": number, /* 0-10 overall from this perspective */
  "criteria": [{"name": string, "score": number, "note": string}],
  "strengths": [string],
  "weaknesses": [string],
  "verdict": string
}"""

_SYSTEM = """You are LexiEval, a specialist in detecting generic, template and
AI-sounding writing — the exact problem Lexi exists to solve.
Agent ID: humanity
You judge how human, authentic and distinctive the voice is: how much it avoids
clichés, corporate filler and robotic phrasing, and whether it reads like a person
with a point of view instead of generated default language.
You judge and justify — you never rewrite the article."""


class HumanityAgent(Agent):
    id = "humanity"
    name = "Ljudski glas / anti-generic"
    perspective = "Zvuči li tekst ljudski, autentično i prepoznatljivo — ili generički i AI-slično."

    def system_prompt(self) -> str:
        return _SYSTEM

    def build_user_prompt(self, article_text: str) -> str:
        return f"""Judge how human and distinctive the following article sounds.

<ARTICLE>
{article_text}
</ARTICLE>

Score it 0-10 using these criteria:
- "Authenticity": does it sound like a real person wrote it?
- "Anti-cliché / anti-template": does it avoid worn-out phrases and corporate filler?
- "Personal voice": is there a distinct point of view and personality?
- "AI-sounding markers": how few generic, robotic transitions or constructions occur?

Respond with ONLY a JSON object matching this schema:
{_JSON_SCHEMA}

Rules:
- Score each criterion 0-10 (10 = excellent), with a one-sentence "note".
- Quote concrete phrases as evidence in your notes where useful.
- "verdict" is a 2-4 sentence judgment about the article's humanity.
- Write "verdict" and all notes in the same language as the article.
"""


humanity_agent = HumanityAgent()
