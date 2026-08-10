"""Orchestration: run agents in parallel, then (optionally) synthesize a final verdict."""

from __future__ import annotations

import asyncio
import json

from .agents.base import Agent
from .models import AgentVerdict, Article, EvaluationResult
from .providers.base import LLMClient, LLMError, LLMParseError
from .scoring import compute_overall

_SYNTH_SYSTEM = """You are the LexiEval chair. You receive the independent verdicts of
several specialist writing-quality agents and produce ONE final, balanced,
human-readable assessment.
Agent ID: synthesizer
Be concrete: name the article's biggest strengths and weaknesses, and give 3
prioritised, actionable recommendations. Do not just repeat the agents — synthesise.
"""

_SYNTH_USER = """Article: {title}
URL: {url}

Independent agent verdicts (JSON):
{verdicts}

Write your final assessment as plain prose (3-6 sentences). Use the language of the
article. Structure:
1. Final verdict (how well written the article is).
2. Biggest strengths (2).
3. Biggest weaknesses (2).
4. Top 3 actionable recommendations (prioritised).
"""


async def _run_agent(
    agent: Agent,
    article: Article,
    client: LLMClient,
    max_chars: int,
    temperature: float,
) -> AgentVerdict:
    try:
        messages = agent.build_messages(article, max_chars)
        raw = await client.complete(messages, json_mode=True, temperature=temperature)
        return agent.parse_verdict(raw)
    except (LLMError, LLMParseError, ValueError) as exc:
        return AgentVerdict(
            agent_id=agent.id,
            agent_name=agent.name,
            perspective=agent.perspective,
            score=0.0,
            verdict="",
            error=str(exc),
        )


async def _synthesize(
    synth_client: LLMClient,
    article: Article,
    verdicts: list[AgentVerdict],
    temperature: float,
) -> str:
    payload = [v.model_dump(mode="json", exclude={"error"}) for v in verdicts]
    user = _SYNTH_USER.format(
        title=article.title or article.url,
        url=article.url,
        verdicts=json.dumps(payload, ensure_ascii=False, indent=2),
    )
    messages = [
        {"role": "system", "content": _SYNTH_SYSTEM},
        {"role": "user", "content": user},
    ]
    raw = await synth_client.complete(messages, json_mode=False, temperature=temperature)
    return raw.strip()


async def evaluate(
    article: Article,
    client: LLMClient,
    *,
    agents: list[Agent],
    weights: dict[str, float],
    synth_client: LLMClient | None = None,
    model: str,
    synth_model: str | None = None,
    max_chars: int,
    temperature: float,
) -> EvaluationResult:
    """Run all agents concurrently, aggregate, and synthesise the final verdict."""
    verdicts = await asyncio.gather(
        *(_run_agent(a, article, client, max_chars, temperature) for a in agents)
    )
    overall = compute_overall(verdicts, weights)

    synthesis: str | None = None
    if synth_client is not None:
        try:
            synthesis = await _synthesize(synth_client, article, verdicts, temperature)
        except (LLMError, LLMParseError, ValueError):
            synthesis = None

    return EvaluationResult(
        article=article,
        model=model,
        synth_model=synth_model,
        agent_verdicts=list(verdicts),
        overall=overall,
        synthesis=synthesis,
    )
