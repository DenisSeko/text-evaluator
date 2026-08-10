"""Aggregation of per-agent scores into a single overall grade."""

from __future__ import annotations

from .models import AgentVerdict, OverallScore

# (letter, minimum score, label)
GRADE_BANDS: list[tuple[str, float, str]] = [
    ("A", 9.0, "Excellent"),
    ("B", 8.0, "Very good"),
    ("C", 7.0, "Good"),
    ("D", 6.0, "Adequate"),
    ("E", 5.0, "Weak"),
    ("F", 0.0, "Poor"),
]


def grade_and_label(score: float) -> tuple[str, str]:
    """Map a 0-10 score to a letter grade + label using fixed thresholds."""
    for grade, threshold, label in GRADE_BANDS:
        if score >= threshold:
            return grade, label
    return "F", "Poor"


def compute_overall(verdicts: list[AgentVerdict], weights: dict[str, float]) -> OverallScore:
    """Weighted mean of valid agent scores.

    Agents that failed (``error`` set) are excluded and the remaining weights are
    re-normalised so a single failure doesn't drag the result to zero.
    """
    valid = [v for v in verdicts if not v.error]
    used_weights = {v.agent_id: weights[v.agent_id] for v in valid if v.agent_id in weights}
    total_weight = sum(used_weights.values())

    if not valid or total_weight <= 0:
        score = 0.0
        normalised: dict[str, float] = {}
    else:
        normalised = {aid: w / total_weight for aid, w in used_weights.items()}
        score = sum(v.score * normalised[v.agent_id] for v in valid)

    grade, label = grade_and_label(score)
    return OverallScore(
        score=round(score, 2),
        letter_grade=grade,
        label=label,
        weights={aid: round(w, 4) for aid, w in normalised.items()},
        agent_scores={v.agent_id: round(v.score, 2) for v in valid},
    )
