"""End-to-end pipeline test with the mock LLM (no API key, no network)."""

from __future__ import annotations

from lexi_evaluator.agents import get_agents
from lexi_evaluator.orchestrator import evaluate
from lexi_evaluator.providers.mock_provider import MockProvider

WEIGHTS = {"structure": 0.3, "rubric": 0.3, "psychology": 0.25, "humanity": 0.15}


async def test_dry_run_pipeline(sample_article, mock_client: MockProvider) -> None:
    synth_client = MockProvider()
    result = await evaluate(
        sample_article,
        mock_client,
        agents=get_agents(),
        weights=WEIGHTS,
        synth_client=synth_client,
        model="mock-model",
        synth_model="mock-synth",
        max_chars=100_000,
        temperature=0.0,
    )

    assert len(result.agent_verdicts) == 4
    for verdict in result.agent_verdicts:
        assert verdict.error is None, verdict.error
        assert 0.0 <= verdict.score <= 10.0
        assert verdict.criteria, "agent should return criteria"
        assert verdict.verdict

    assert result.overall.score > 0
    assert result.overall.letter_grade in {"A", "B", "C", "D", "E", "F"}
    assert result.overall.agent_scores

    assert result.synthesis, "synthesizer should produce a final assessment"
    # 4 agent calls + 1 synthesizer call.
    assert len(mock_client.calls) == 4
    assert len(synth_client.calls) == 1


async def test_dry_run_without_synthesizer(sample_article, mock_client: MockProvider) -> None:
    result = await evaluate(
        sample_article,
        mock_client,
        agents=get_agents(["structure", "rubric"]),
        weights=WEIGHTS,
        synth_client=None,
        model="mock-model",
        synth_model=None,
        max_chars=100_000,
        temperature=0.0,
    )
    assert len(result.agent_verdicts) == 2
    assert result.synthesis is None
    assert result.synth_model is None
