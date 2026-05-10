"""Deterministic calendar duration from gap size, staffing, and catalog maturity.

``duration_score`` follows IVI *duree* semantics: **5 = fast / low calendar time**,
**1 = long / multi-quarter**. It is derived from ``duration_months`` so the two stay aligned.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.services.maturity_scoring import maturity_score_or_neutral


@dataclass(frozen=True)
class DurationEstimate:
    """Formula output — months on the wall calendar plus the 1–5 speed score."""

    duration_months: int
    duration_score: int


def _months_to_duration_score(months: int) -> int:
    """Map integer months to IVI-style duree (5 = fastest)."""
    if months <= 2:
        return 5
    if months <= 4:
        return 4
    if months <= 7:
        return 3
    if months <= 12:
        return 2
    return 1


def compute_duration(
    *,
    features_missing_count: int,
    team_size: int,
    maturity: object,
) -> DurationEstimate:
    """Compute ``duration_months`` and ``duration_score`` from the three drivers.

    - More missing capabilities → longer delivery.
    - Larger team → sub-linear compression (square-root parallelism, capped).
    - Higher catalog maturity → less foundational work per gap (shorter elapsed time).
    """
    n = max(0, int(features_missing_count))
    team = max(1, min(int(team_size), 24))
    m = maturity_score_or_neutral(maturity, neutral=3)

    # Base effort grows with each missing capability (month-scale).
    effort_months = 2.0 + 1.35 * n

    # Catalogue maturity PoC→Multi-ref scores 2..5 shorten calendar vs immature tiers.
    maturity_mult = 1.12 - 0.095 * (m - 2)
    maturity_mult = max(0.72, min(1.18, maturity_mult))

    adjusted = effort_months * maturity_mult

    # Sub-linear staff scaling (Brooks-bound).
    parallel = math.sqrt(float(team))
    calendar = adjusted / max(parallel, 0.45)

    months_f = float(max(1.0, min(round(calendar, 6), 36.0)))
    duration_months = int(round(months_f))
    duration_months = max(1, min(duration_months, 36))

    duration_score = _months_to_duration_score(duration_months)
    duration_score = max(1, min(5, duration_score))

    return DurationEstimate(duration_months=duration_months, duration_score=duration_score)
