"""Deterministic mock LLM client — powers ``--dry-run`` and offline tests.

Returns canned, schema-valid responses per agent id (read from the system
prompt) so the whole pipeline can be exercised without an API key or network.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .base import LLMClient

_CANNED_VERDICTS: dict[str, dict[str, Any]] = {
    "structure": {
        "score": 8.5,
        "criteria": [
            {
                "name": "Hook (uvod)",
                "score": 8.0,
                "note": "Opens with a relatable, concrete scenario.",
            },
            {
                "name": "Logical flow",
                "score": 9.0,
                "note": "Each section builds on the previous one.",
            },
            {
                "name": "Heading structure",
                "score": 9.0,
                "note": "Headings are informative and well ordered.",
            },
            {"name": "Clarity", "score": 8.5, "note": "Sentences are easy to follow."},
            {"name": "Pacing & transitions", "score": 8.0, "note": "Paragraphs are digestible."},
        ],
        "strengths": ["Clear narrative arc from hook to takeaway.", "Headings guide the reader."],
        "weaknesses": ["Some paragraphs could be shorter."],
        "verdict": "The text is very well structured and guides the reader logically from the opening hook to a concrete takeaway.",
    },
    "psychology": {
        "score": 8.0,
        "criteria": [
            {"name": "Concreteness", "score": 8.5, "note": "Uses specific examples and metaphors."},
            {
                "name": "Reader benefit",
                "score": 8.0,
                "note": "Explains why it matters to the reader.",
            },
            {
                "name": "Tone & emotional resonance",
                "score": 8.0,
                "note": "Human, conversational tone.",
            },
            {
                "name": "Avoiding generic filler",
                "score": 7.5,
                "note": "Mostly specific, a few generic transitions.",
            },
        ],
        "strengths": ["Strong reader-benefit framing.", "Concrete psychological explanations."],
        "weaknesses": ["A couple of sections rely on abstract phrasing."],
        "verdict": "Psychologically grounded writing that keeps the reader's benefit central.",
    },
    "rubric": {
        "score": 8.2,
        "criteria": [
            {"name": "Clarity", "score": 8.5, "note": "Precise and unambiguous."},
            {"name": "Structure", "score": 9.0, "note": "Well organized."},
            {"name": "Specificity", "score": 8.5, "note": "Concrete examples throughout."},
            {"name": "Reader-benefit", "score": 8.0, "note": "Clear value proposition."},
            {"name": "Tone & voice", "score": 8.0, "note": "Consistent, human voice."},
            {"name": "Readability", "score": 7.5, "note": "Good but some long sentences."},
        ],
        "strengths": ["High specificity.", "Consistent voice."],
        "weaknesses": ["Readability dips in a few passages."],
        "verdict": "Above-average copy that scores consistently across the rubric.",
    },
    "humanity": {
        "score": 8.7,
        "criteria": [
            {
                "name": "Authenticity",
                "score": 9.0,
                "note": "Sounds like a real person with a point of view.",
            },
            {
                "name": "Anti-cliché / anti-template",
                "score": 8.5,
                "note": "Avoids corporate filler.",
            },
            {"name": "Personal voice", "score": 8.5, "note": "Distinctive phrasing."},
            {
                "name": "AI-sounding markers",
                "score": 8.8,
                "note": "Few generic AI transitions detected.",
            },
        ],
        "strengths": ["Genuine, opinionated voice.", "Minimal template language."],
        "weaknesses": ["One or two transitions still feel formulaic."],
        "verdict": "Reads human and distinctive rather than generic or AI-generated.",
    },
}

_CANNED_SYNTHESIS_HR = (
    "Svi agenti su suglasni da je tekst iznad prosjeka: odlično strukturiran, "
    "psihološki utemeljen i ljudski u tonu. Najveće snage su konkretni primjeri i "
    "logičan tok; najslabija točka je čitljivost u par dužih odlomaka. Preporuka: "
    "skratiti najdulje rečenice i ukloniti preostale generičke prijelaze."
)

_CANNED_SYNTHESIS_EN = (
    "All agents agree the article is above average: well structured, psychologically "
    "grounded and human in tone. Its biggest strengths are concrete examples and a "
    "logical flow; the weakest point is readability in a couple of longer paragraphs. "
    "Recommendation: shorten the longest sentences and drop the remaining generic "
    "transitions."
)


class MockProvider(LLMClient):
    name = "mock"

    def __init__(self) -> None:
        self.calls: list[list[dict[str, Any]]] = []

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        json_mode: bool = False,
        temperature: float | None = None,
    ) -> str:
        self.calls.append(messages)
        system = messages[0]["content"] if messages else ""
        match = re.search(r"Agent ID: (\w+)", system)
        agent_id = match.group(1) if match else "structure"

        if agent_id == "synthesizer":
            user = messages[-1]["content"] if messages else ""
            is_croatian = "Croatian" in user
            return _CANNED_SYNTHESIS_HR if is_croatian else _CANNED_SYNTHESIS_EN

        payload = _CANNED_VERDICTS.get(agent_id, _CANNED_VERDICTS["structure"])
        return json.dumps(payload, ensure_ascii=False)
