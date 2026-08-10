"""Agent registry."""

from __future__ import annotations

from .base import Agent
from .humanity import humanity_agent
from .psychology import psychology_agent
from .rubric import rubric_agent
from .structure import structure_agent

AGENTS: dict[str, Agent] = {
    agent.id: agent for agent in (structure_agent, psychology_agent, rubric_agent, humanity_agent)
}


def get_agents(ids: list[str] | None = None) -> list[Agent]:
    """Return agents by id (default: all). Validates unknown ids."""
    if not ids:
        return list(AGENTS.values())
    missing = [i for i in ids if i not in AGENTS]
    if missing:
        raise ValueError(f"Unknown agent ids: {missing}. Available: {sorted(AGENTS)}")
    return [AGENTS[i] for i in ids]


__all__ = ["Agent", "AGENTS", "get_agents"]
