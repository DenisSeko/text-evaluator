"""Structure & flow agent — judges clarity, logical organisation and reader guidance."""

from __future__ import annotations

from .base import Agent

_JSON_SCHEMA = """{
  "score": number, /* 0-10 overall from this perspective */
  "criteria": [{"name": string, "score": number, "note": string}],
  "strengths": [string],
  "weaknesses": [string],
  "verdict": string
}"""

_SYSTEM = """You are LexiEval, an expert structural editor for marketing and blog copy.
Agent ID: structure
You evaluate how well a text is STRUCTURED and how clearly it guides a reader from
the first sentence to the final takeaway. You care about information architecture,
logical flow, heading quality, paragraph rhythm and whether the reader is ever lost.
You judge and justify — you never rewrite the article."""


class StructureAgent(Agent):
    id = "structure"
    name = "Struktura i tok"
    perspective = "Vodi li tekst čitatelja logično kroz sadržaj — jasnoća, organizacija i ritam."

    def system_prompt(self) -> str:
        return _SYSTEM

    def build_user_prompt(self, article_text: str) -> str:
        return f"""Analyse the following blog article as a structural editor.

<ARTICLE>
{article_text}
</ARTICLE>

Score it 0-10 on how well it guides the reader, using these criteria:
- "Hook (uvod)": does the opening pull the reader in and set expectations?
- "Logical flow": does each section build on the previous one without jumps?
- "Heading structure": are headings informative, parallel and well organised?
- "Clarity": is the language precise and easy to follow?
- "Pacing & transitions": are paragraphs digestible and transitions smooth?

Respond with ONLY a JSON object matching this schema:
{_JSON_SCHEMA}

Rules:
- Score each criterion 0-10 (10 = excellent), with a one-sentence "note".
- "verdict" is a 2-4 sentence judgment from the structural perspective.
- Write "verdict" and all notes in the same language as the article.
"""


structure_agent = StructureAgent()
