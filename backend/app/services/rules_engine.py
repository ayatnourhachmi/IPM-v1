"""Deterministic rule engine — runs before the LLM tagging call.

Rules produce hard overrides for specific tag fields. The LLM still generates
the full response, but these overrides are injected into the prompt as
explicit constraints and applied post-parse to guarantee correctness.

Rule priority (highest → lowest):
  1. Client reference detected  → origine = demande_client
  2. Measurable KPI detected    → origine = probleme_operationnel
  3. Data keywords w/o inference verbs → IA excluded from domaine
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pattern libraries
# ---------------------------------------------------------------------------

# Measurable KPI signals — numeric targets, percentages, time reductions, etc.
_KPI_PATTERNS: list[str] = [
    r"\d+\s*%",                           # "20%", "50 %"
    r"\d+\s*x\b",                         # "3x faster"
    r"\bfrom\s+\d+",                      # "from 5 days"
    r"\bto\s+\d+\s*(?:day|hour|min|week)",# "to 1 day"
    r"\breduc\w*\s+by\b",                 # "reduce by", "reducing by"
    r"\bincrease\w*\s+by\b",             # "increase by"
    r"\bsav(?:e|ing)\w*\s+\d+",          # "saving 4 hours"
    r"\b(?:kpi|roi|sla)\b",              # "KPI", "ROI", "SLA"
    r"\bcost\s+(?:reduction|saving)",    # "cost reduction"
    r"\bproductivity\s+gain",            # "productivity gain"
    r"\btime[\s-]+to[\s-]+(?:market|value|close)", # "time-to-market"
    r"\bbaseline\b",                     # "baseline measurement"
    r"\btarget\s+of\s+\d+",             # "target of 95"
]

# Client / customer reference signals
_CLIENT_PATTERNS: list[str] = [
    r"\b(?:our\s+)?client(?:s|'s)?\b",              # "client", "our clients", "client's"
    r"\bcustomer(?:s|'s)?\s+(?:request|ask|need|want|requir|feedback|demand)",
    r"\b(?:request|demand|feedback|requirement)\s+(?:from|by)\s+(?:our\s+)?(?:client|customer)",
    r"\bcontract\s+(?:requirement|obligation|deliverable)",  # "contract requirement"
    r"\bclient[\s-]facing\b",                        # "client-facing"
    r"\bvoice\s+of\s+(?:the\s+)?customer\b",        # "voice of the customer"
    r"\bticket(?:s)?\s+(?:from|raised\s+by)\b",     # "tickets from clients"
    r"\bservice\s+level\s+agreement\b",              # full SLA phrase
]

# Strong inference / AI verbs — required to classify as IA domain
_INFERENCE_PATTERNS: list[str] = [
    r"\bpredict\w*\b",        # predict, prediction, predictive
    r"\bclassif\w*\b",        # classify, classifier, classification
    r"\bdetect\w*\b",         # detect, detection
    r"\brecogniz\w*\b",       # recognize, recognition
    r"\brecommend\w*\b",      # recommend, recommendation
    r"\bforecast\w*\b",       # forecast
    r"\binfer\w*\b",          # infer, inference
    r"\bgener(?:ate|ative)\w*\b", # generate, generative
    r"\btrain(?:ing)?\s+(?:a\s+)?model\b",  # "train a model"
    r"\bmachine\s+learning\b",
    r"\bdeep\s+learning\b",
    r"\bneural\s+(?:net|network)\b",
    r"\b(?:llm|gpt|bert|nlp)\b",
    r"\bembedding\w*\b",
    r"\bvector\s+(?:search|store|database)\b",
    r"\banomaly\s+detection\b",
    r"\bsentiment\s+analysis\b",
    r"\bchatbot\b",
    r"\bconversational\s+ai\b",
    r"\bcomputer\s+vision\b",
    r"\bobject\s+detection\b",
    r"\bgenai\b",
]

# Data engineering keywords — without inference verbs → exclude IA
_DATA_PATTERNS: list[str] = [
    r"\bdashboard\w*\b",
    r"\breport(?:ing)?\b",
    r"\bdata\s+(?:pipeline|lake|warehouse|mart|quality|governance|catalog|lineage)\b",
    r"\betl\b",
    r"\belt\b",
    r"\bingestion\b",
    r"\b(?:business\s+)?intelligence\b",
    r"\banalytics?\b",
    r"\bdata\s+integration\b",
    r"\bmaster\s+data\b",
    r"\bdata\s+(?:platform|architecture|strategy)\b",
]


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class RuleHints:
    """Overrides produced by the deterministic rule engine."""

    origine: Optional[str] = None
    exclude_domaine: list[str] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)  # rule_id → human reason

    @property
    def has_overrides(self) -> bool:
        return bool(self.origine or self.exclude_domaine)

    def to_prompt_context(self) -> str:
        """Render override instructions for injection into the LLM prompt."""
        if not self.has_overrides:
            return "None — classify freely."
        lines = []
        if self.origine:
            reason = next(iter(self.reasons.values()), "rule match")
            lines.append(
                f'- origine MUST be exactly "{self.origine}" '
                f"({reason}). Do not override this."
            )
        for dom in self.exclude_domaine:
            lines.append(
                f'- "{dom}" MUST NOT appear in domaine '
                f"({self.reasons.get('ia_vs_data', 'rule match')})."
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def apply_rules(pitch: str) -> RuleHints:
    """Apply all deterministic rules to the pitch and return override hints."""
    hints = RuleHints()
    text = pitch.lower()

    # ── Rule 1: measurable KPI → origine = probleme_operationnel ─────────────
    if any(re.search(p, text) for p in _KPI_PATTERNS):
        hints.origine = "probleme_operationnel"
        hints.reasons["kpi_detected"] = (
            "Measurable KPI / numeric target detected → probleme_operationnel"
        )

    # ── Rule 2: client reference → demande_client (overrides Rule 1) ─────────
    if any(re.search(p, text) for p in _CLIENT_PATTERNS):
        hints.origine = "demande_client"
        hints.reasons.pop("kpi_detected", None)
        hints.reasons["client_detected"] = (
            "Client / customer reference detected → demande_client "
            "(overrides KPI rule)"
        )

    # ── Rule 3: Data keywords without inference verbs → exclude IA ───────────
    has_inference = any(re.search(p, text) for p in _INFERENCE_PATTERNS)
    has_data = any(re.search(p, text) for p in _DATA_PATTERNS)

    if has_data and not has_inference:
        hints.exclude_domaine.append("IA")
        hints.reasons["ia_vs_data"] = (
            "Data engineering keywords present but no AI inference verbs → "
            "IA excluded from domaine"
        )

    if hints.has_overrides:
        logger.info(
            "Rule engine fired %d override(s) for pitch (len=%d): %s",
            len(hints.reasons),
            len(pitch),
            list(hints.reasons.keys()),
        )
    else:
        logger.debug("Rule engine: no overrides for pitch (len=%d)", len(pitch))

    return hints
