"""Scoring/aggregation tests."""

from __future__ import annotations

from lexi_evaluator.models import AgentVerdict
from lexi_evaluator.scoring import compute_overall, grade_and_label

WEIGHTS = {"structure": 0.3, "rubric": 0.3, "psychology": 0.25, "humanity": 0.15}


def _verdict(agent_id: str, score: float, *, error: str | None = None) -> AgentVerdict:
    return AgentVerdict(
        agent_id=agent_id,
        agent_name=agent_id,
        perspective="",
        score=score,
        error=error,
    )


def test_weighted_mean() -> None:
    verdicts = [
        _verdict("structure", 8.0),
        _verdict("rubric", 9.0),
        _verdict("psychology", 7.0),
        _verdict("humanity", 6.0),
    ]
    expected = 8.0 * 0.3 + 9.0 * 0.3 + 7.0 * 0.25 + 6.0 * 0.15
    overall = compute_overall(verdicts, WEIGHTS)
    assert overall.score == round(expected, 2)
    assert overall.agent_scores == {
        "structure": 8.0,
        "rubric": 9.0,
        "psychology": 7.0,
        "humanity": 6.0,
    }


def test_failed_agent_renormalises_weights() -> None:
    verdicts = [
        _verdict("structure", 10.0),
        _verdict("rubric", 8.0),
        _verdict("psychology", 7.0, error="boom"),
        _verdict("humanity", 6.0, error="boom"),
    ]
    overall = compute_overall(verdicts, WEIGHTS)
    # Only structure (0.3) + rubric (0.3) count; weights re-normalised 50/50.
    assert overall.score == 9.0
    assert overall.weights == {"structure": 0.5, "rubric": 0.5}


def test_all_failed_gives_zero() -> None:
    verdicts = [_verdict(a, 9.0, error="boom") for a in WEIGHTS]
    overall = compute_overall(verdicts, WEIGHTS)
    assert overall.score == 0.0
    assert overall.letter_grade == "F"


def test_grade_bands() -> None:
    assert grade_and_label(9.5) == ("A", "Excellent")
    assert grade_and_label(8.4) == ("B", "Very good")
    assert grade_and_label(7.2) == ("C", "Good")
    assert grade_and_label(6.1) == ("D", "Adequate")
    assert grade_and_label(5.3) == ("E", "Weak")
    assert grade_and_label(2.0) == ("F", "Poor")
    assert grade_and_label(10.0) == ("A", "Excellent")
