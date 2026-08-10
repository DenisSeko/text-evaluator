"""Base class and shared parsing/validation helpers for evaluation agents."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, ValidationError

from ..models import AgentVerdict, Article, Criterion
from ..providers.base import LLMParseError


class AgentOutput(BaseModel):
    """Schema every agent's JSON response must satisfy."""

    score: float = Field(ge=0.0, le=10.0)
    criteria: list[dict[str, object]] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    verdict: str = ""


def extract_json(text: str) -> dict[str, object]:
    """Locate the JSON object inside a model response (handles code fences)."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMParseError("No JSON object found in model response")
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMParseError(f"Model returned invalid JSON: {exc}") from exc


def _clamp(value: object, low: float = 0.0, high: float = 10.0) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return low


class Agent(ABC):
    """One evaluation perspective. Subclasses supply prompts and are invoked
    independently (in parallel) by the orchestrator."""

    id: str
    name: str
    perspective: str
    model: str | None = None  # optional per-agent model override

    @abstractmethod
    def system_prompt(self) -> str:
        """The agent's role/perspective prompt (system message)."""

    @abstractmethod
    def build_user_prompt(self, article_text: str) -> str:
        """The task prompt that embeds the article and the required JSON schema."""

    def build_messages(self, article: Article, max_chars: int) -> list[dict[str, str]]:
        text = article.plain_text[:max_chars]
        language_name = "Croatian" if article.language == "hr" else "English"
        user_prompt = self.build_user_prompt(text)
        # Auto-detected article language drives the language of the whole review:
        # verdict, strengths, weaknesses, per-criterion notes AND criterion names.
        user_prompt += (
            f"\n\nLanguage: the article is written in {language_name}. Write ALL text "
            'output in that language — "verdict", "strengths", "weaknesses", every '
            f'"note" and every criterion "name". Use ONLY {language_name}: translate '
            "every English criterion name and never add English glosses in parentheses."
        )
        return [
            {"role": "system", "content": self.system_prompt()},
            {"role": "user", "content": user_prompt},
        ]

    def parse_verdict(self, raw: str) -> AgentVerdict:
        data = extract_json(raw)
        try:
            output = AgentOutput.model_validate(data)
        except ValidationError as exc:
            raise LLMParseError(f"Agent '{self.id}' output failed validation: {exc}") from exc

        criteria = [
            Criterion(
                name=str(c.get("name", "?")),
                score=_clamp(c.get("score", 0.0)),
                note=str(c.get("note", "")),
            )
            for c in output.criteria
        ]
        return AgentVerdict(
            agent_id=self.id,
            agent_name=self.name,
            perspective=self.perspective,
            score=_clamp(output.score),
            criteria=criteria,
            strengths=list(output.strengths),
            weaknesses=list(output.weaknesses),
            verdict=output.verdict,
        )
