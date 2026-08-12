"""Psychology agent — judges persuasive-writing psychology (concreteness, benefit, tone)."""

from __future__ import annotations

from .base import Agent

_JSON_SCHEMA = """{
  "score": number, /* 0-10 overall from this perspective */
  "criteria": [{"name": string, "score": number, "note": string}],
  "strengths": [string],
  "weaknesses": [string],
  "verdict": string
}"""

_SYSTEM = """You are LexiEval, an expert in the psychology of persuasive, human writing.
Agent ID: psychology
You evaluate whether a text applies proven principles of good writing: concreteness
over abstraction, a clear benefit for the reader, a genuine human tone, emotional
engagement, specific examples and stories, and the absence of generic filler.
You judge and justify — you never rewrite the article."""


class PsychologyAgent(Agent):
    id = "psychology"
    name = "Psihologija pisanja"
    perspective = (
        "Koristi li tekst psihološke principe dobrog pisanja — konkretnost, benefit "
        "za čitatelja i ton."
    )
    name_hr = "Psihologija pisanja"
    name_en = "Psychology of writing"
    perspective_hr = (
        "Koristi li tekst psihološke principe dobrog pisanja — konkretnost, benefit "
        "za čitatelja i ton."
    )
    perspective_en = (
        "Does the text apply psychological principles of good writing — concreteness, "
        "reader benefit and tone."
    )

    def system_prompt(self) -> str:
        return _SYSTEM

    def build_user_prompt(self, article_text: str) -> str:
        return f"""Analyse the following blog article as a psychology-of-writing expert.

<ARTICLE>
{article_text}
</ARTICLE>

Score it 0-10 using these criteria:
- "Concreteness": are ideas concrete and vivid instead of abstract?
- "Reader benefit": does the reader clearly see what's in it for them?
- "Tone & emotional resonance": is the tone human, warm and emotionally engaging?
- "Avoiding generic filler": does it dodge clichés, buzzwords and empty phrases?
- "Examples & storytelling": does it use stories, examples, metaphors?
- "Trust & authority": does it support claims and build credibility?

Respond with ONLY a JSON object matching this schema:
{_JSON_SCHEMA}

Rules:
- Score each criterion 0-10 (10 = excellent), with a one-sentence "note".
- "verdict" is a 2-4 sentence judgment from the psychology perspective.
- Write "verdict" and all notes in the same language as the article.
"""


psychology_agent = PsychologyAgent()
