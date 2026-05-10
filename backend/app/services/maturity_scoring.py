"""Catalog maturity → IVI maturité score (1–5). Deterministic parsing of catalog/Excel labels only.

Scores are fixed lookup — no model inference. Unknown labels yield ``None`` so callers avoid
inventing a tier.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Canonical tokens after normalizing catalog free text
CANONICAL_TO_SCORE: dict[str, int] = {
    "poc": 2,
    "pilot": 3,
    "production": 4,
    "multi_ref": 5,
}


def normalize_maturity(raw: object) -> Optional[str]:
    """Map a catalog maturity cell to a canonical slug, or ``None`` if not recognized."""
    if raw is None:
        return None
    v = str(raw).strip().lower()
    if not v or v in ("nan", "none", "-", "n/a", "na"):
        return None

    compact = v.replace("-", "").replace(" ", "").replace("_", "")

    # Multi-ref / multi-reference (catalog-only label; never inferred from other signals)
    if "multi" in v:
        if "ref" in v or compact.startswith("multiref") or "reference" in v:
            return "multi_ref"

    if v.startswith("poc") or compact == "poc":
        return "poc"
    if v.startswith("pilot"):
        return "pilot"
    if v.startswith("prod") or compact in ("prod", "ga", "live", "released"):
        return "production"

    return None


def maturity_score(raw: object) -> Optional[int]:
    """Return maturité score from catalog maturity text, or ``None`` if unknown."""
    key = normalize_maturity(raw)
    if key is None:
        logger.debug("Maturity scoring: unrecognized catalog maturity label %r", raw)
        return None
    return CANONICAL_TO_SCORE.get(key)


def maturity_score_or_neutral(raw: object, neutral: int = 3) -> int:
    """Like ``maturity_score`` but return *neutral* when the label cannot be mapped (logged)."""
    s = maturity_score(raw)
    if s is None:
        logger.info("Maturity scoring: unknown label %r — using neutral %s", raw, neutral)
        return max(1, min(5, neutral))
    return s
