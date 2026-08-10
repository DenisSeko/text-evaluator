"""Pydantic data models shared across the pipeline."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class Article(BaseModel):
    """Cleaned article content extracted from a scraped page."""

    url: str
    title: str | None = None
    author: str | None = None
    published_at: str | None = None
    read_time: str | None = None
    plain_text: str
    char_count: int
    word_count: int
    headings: list[str] = Field(default_factory=list)
    source: str = "trafilatura"


class Criterion(BaseModel):
    """A single scored criterion within an agent's verdict."""

    name: str
    score: float
    note: str = ""


class AgentVerdict(BaseModel):
    """Structured output of one evaluation agent."""

    agent_id: str
    agent_name: str
    perspective: str
    score: float = 0.0
    criteria: list[Criterion] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    verdict: str = ""
    error: str | None = None


class OverallScore(BaseModel):
    """Aggregated final score with a letter grade and label."""

    score: float
    letter_grade: str
    label: str
    weights: dict[str, float]
    agent_scores: dict[str, float]


class EvaluationResult(BaseModel):
    """Complete output of one evaluation run."""

    article: Article
    model: str
    synth_model: str | None = None
    agent_verdicts: list[AgentVerdict] = Field(default_factory=list)
    overall: OverallScore
    synthesis: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))
