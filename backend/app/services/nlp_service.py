"""NLP service — pitch analysis, tag generation, and suggestions via LLM."""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from sqlalchemy import delete, select

from app.core import llm_client
from app.core.langfuse_tracking import (
    merge_trace_rule_pipeline,
    new_langfuse_client,
    safe_flush,
)
from app.core.database import async_session_factory
from app.models.business_need import NlpCache
from app.schemas.business_need import Suggestion, Tags

from app.services.rules_engine import RuleHints, apply_rules
from app.services.validation_guards import sanitize_pitch_tag_dict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache configuration
# ---------------------------------------------------------------------------

_L1_TTL = 300          # in-memory L1: 5 minutes
_L2_TTL_HOURS = 24     # Postgres L2: 24 hours

# ---------------------------------------------------------------------------
# L1 — in-memory cache (fast, no DB round-trip)
# ---------------------------------------------------------------------------

class _CacheEntry(NamedTuple):
    tags: Tags
    suggestions: list[Suggestion]
    timestamp: float

_l1: dict[str, _CacheEntry] = {}


def _make_key(pitch: str, horizon: str | None) -> str:
    """SHA-256 of normalised pitch + horizon — used for both L1 and L2."""
    raw = f"{pitch.strip().lower()}|{horizon or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _l1_get(key: str) -> tuple[Tags, list[Suggestion]] | None:
    entry = _l1.get(key)
    if entry and (time.monotonic() - entry.timestamp) < _L1_TTL:
        return entry.tags, entry.suggestions
    return None


def _l1_set(key: str, tags: Tags, suggestions: list[Suggestion]) -> None:
    _l1[key] = _CacheEntry(tags=tags, suggestions=suggestions, timestamp=time.monotonic())


# ---------------------------------------------------------------------------
# L2 — Postgres persistent cache (survives container restarts)
# ---------------------------------------------------------------------------

async def _l2_get(key: str) -> tuple[Tags, list[Suggestion]] | None:
    """Read from Postgres cache. Returns None on any error (non-fatal)."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=_L2_TTL_HOURS)
        async with async_session_factory() as session:
            row = await session.scalar(
                select(NlpCache).where(
                    NlpCache.cache_key == key,
                    NlpCache.created_at >= cutoff,
                )
            )
        if row is None:
            return None
        tags = Tags.model_validate(row.tags_json)
        suggestions = [Suggestion(**s) for s in (row.suggestions_json or [])]
        logger.info("L2 cache hit (Postgres) for key=%s", key[:12])
        return tags, suggestions
    except Exception as exc:
        logger.debug("L2 cache read failed (non-fatal): %s", exc)
        return None


async def _l2_set(key: str, pitch: str, horizon: str | None,
                  tags: Tags, suggestions: list[Suggestion]) -> None:
    """Write to Postgres cache. Non-fatal on error."""
    try:
        async with async_session_factory() as session:
            # Upsert — ON CONFLICT DO UPDATE via delete+insert (portable)
            await session.execute(
                delete(NlpCache).where(NlpCache.cache_key == key)
            )
            session.add(NlpCache(
                cache_key=key,
                pitch=pitch,
                horizon=horizon,
                tags_json=json.loads(tags.model_dump_json()),
                suggestions_json=[s.model_dump() for s in suggestions],
            ))
            await session.commit()
        logger.debug("L2 cache written (Postgres) for key=%s", key[:12])
    except Exception as exc:
        logger.debug("L2 cache write failed (non-fatal): %s", exc)


def _apply_rule_overrides(tag_dict: dict, hints: RuleHints) -> dict:
    """Apply deterministic rule overrides to the parsed LLM tag dict.

    Overrides happen AFTER the LLM responds so they are guaranteed regardless
    of whether the LLM followed the prompt constraints.
    """
    if hints.origine:
        tag_dict["origine"] = {"value": hints.origine, "confidence": "high"}
        logger.info(
            "Rule override applied: origine → %s (rules: %s)",
            hints.origine,
            list(hints.reasons.keys()),
        )

    if hints.exclude_domaine:
        original = tag_dict.get("domaine", [])
        filtered = [
            item for item in original
            if (item.get("value") if isinstance(item, dict) else item)
            not in hints.exclude_domaine
        ]
        # Never leave domaine empty — fall back to Autre
        tag_dict["domaine"] = filtered or [{"value": "Autre", "confidence": "low"}]
        removed = len(original) - len(filtered)
        if removed:
            logger.info(
                "Rule override applied: removed %d domain(s) %s from domaine",
                removed,
                hints.exclude_domaine,
            )

    return tag_dict


# Objectif values that contradict each horizon, and the preferred replacement.
_HORIZON_CONTRADICTS: dict[str, set[str]] = {
    "court_terme": {"market_opportunity"},
    "moyen_terme": set(),  # mid-term never forces an override
    "long_terme":  {"cost_reduction", "cx_improvement"},
}
_HORIZON_PREFERRED: dict[str, str] = {
    "court_terme": "cost_reduction",
    "long_terme":  "market_opportunity",
}


def _apply_horizon_override(tag_dict: dict, horizon: str | None, hints: RuleHints) -> dict:
    """Override objectif when it contradicts the horizon.

    The only time we respect the LLM's contradictory objectif is when the
    deterministic rule engine already fired (i.e. the pitch contained measurable
    KPIs or explicit client signals — truly explicit content).

    A generic LLM 'high' confidence is NOT sufficient to resist the horizon,
    because the LLM over-assigns high confidence to clear operational wording
    even when no hard numeric/client signals exist.
    """
    if not horizon:
        return tag_dict

    objectif = tag_dict.get("objectif", {})
    current_value = objectif.get("value", "") if isinstance(objectif, dict) else str(objectif)
    current_confidence = objectif.get("confidence", "low") if isinstance(objectif, dict) else "low"

    contradictory = _HORIZON_CONTRADICTS.get(horizon, set())
    if current_value not in contradictory:
        return tag_dict

    # Only resist the override when the rule engine also fired — that means
    # the pitch had hard, measurable signals (KPIs / client reference) that
    # genuinely justify keeping the LLM's classification.
    if hints.has_overrides:
        logger.debug(
            "Horizon override skipped: rule engine already fired for this pitch "
            "(objectif=%s, horizon=%s)",
            current_value,
            horizon,
        )
        return tag_dict

    new_value = _HORIZON_PREFERRED.get(horizon, current_value)
    tag_dict["objectif"] = {"value": new_value, "confidence": "medium"}
    logger.info(
        "Horizon override applied: objectif %s → %s "
        "(horizon=%s, LLM confidence was %s, no rule-engine signals)",
        current_value,
        new_value,
        horizon,
        current_confidence,
    )

    return tag_dict


# ---------------------------------------------------------------------------
# Horizon context builder
# ---------------------------------------------------------------------------

_HORIZON_CONTEXT: dict[str, str] = {
    "court_terme": (
        "Planning horizon: SHORT-TERM (court_terme — delivery expected within ~6 months).\n"
        "Rule for objectif: when the pitch is ambiguous or could fit multiple objectif values, "
        "you MUST default to 'cost_reduction' or 'cx_improvement'.\n"
        "You MUST NOT select 'market_opportunity' unless the pitch explicitly and "
        "unambiguously describes launching a new product or capturing a new market — "
        "vague growth language does NOT qualify.\n"
        "Select 'risk_mitigation' only if the pitch explicitly mentions a compliance "
        "deadline, audit, security breach, or regulatory obligation."
    ),
    "moyen_terme": (
        "Planning horizon: MID-TERM (moyen_terme — delivery expected within 6–18 months).\n"
        "Rule for objectif: all values are valid. When ambiguous, slightly prefer "
        "'cost_reduction', 'cx_improvement', or 'risk_mitigation' over "
        "'market_opportunity' — choose 'market_opportunity' only when the pitch "
        "clearly signals expansion, new revenue, or competitive positioning."
    ),
    "long_terme": (
        "Planning horizon: LONG-TERM (long_terme — delivery expected beyond 18 months).\n"
        "Rule for objectif: when the pitch is ambiguous or could fit multiple objectif values, "
        "you MUST default to 'market_opportunity' or 'risk_mitigation'.\n"
        "You MUST NOT select 'cost_reduction' or 'cx_improvement' unless the pitch "
        "describes a foundational, multi-year transformation — a simple efficiency "
        "improvement does NOT qualify for long-term horizon."
    ),
}

_HORIZON_NO_CONTEXT = (
    "Planning horizon: not specified — classify objectif solely based on the pitch content."
)


def _build_horizon_context(horizon: str | None) -> str:
    """Return the horizon constraint block for injection into the LLM prompt."""
    ctx = _HORIZON_CONTEXT.get(horizon or "", _HORIZON_NO_CONTEXT)
    logger.info("Horizon context applied: %s", horizon or "none")
    return ctx


def _domain_from_pitch(pitch: str) -> str:
    text = pitch.lower()
    if any(k in text for k in ("ai", "ml", "machine learning", "predict", "model", "llm", "chatbot", "nlp")):
        return "IA"
    if any(k in text for k in ("cloud", "aws", "azure", "saas", "kubernetes", "serverless", "migration")):
        return "Cloud"
    if any(k in text for k in ("security", "cyber", "compliance", "identity", "soc", "siem", "risk")):
        return "Cybersecurite"
    if any(k in text for k in ("data", "dashboard", "report", "analytics", "warehouse", "etl", "bi")):
        return "Data"
    if any(k in text for k in ("hr", "recruit", "talent", "employee", "workforce")):
        return "RH"
    if any(k in text for k in ("finance", "invoice", "payment", "budget", "account")):
        return "Finance"
    if any(k in text for k in ("process", "operations", "workflow", "automation", "rpa", "supply", "logistics")):
        return "Operations"
    return "Autre"


def _objective_from_pitch(pitch: str, horizon: str | None, hints: RuleHints) -> str:
    text = pitch.lower()
    if hints.origine == "demande_client":
        return "cx_improvement"
    if any(k in text for k in ("security", "compliance", "audit", "breach", "fraud", "risk", "regulat")):
        return "risk_mitigation"
    if any(k in text for k in ("growth", "new market", "launch", "revenue", "expand", "customer")):
        return "market_opportunity"
    if horizon == "long_terme":
        return "market_opportunity"
    if any(k in text for k in ("customer", "user", "experience", "satisfaction", "service")):
        return "cx_improvement"
    return "cost_reduction"


def _fallback_analyze_result(pitch: str, horizon: str | None, hints: RuleHints) -> tuple[Tags, list[Suggestion]]:
    objective = _objective_from_pitch(pitch, horizon, hints)
    domain = _domain_from_pitch(pitch)
    impact = "Risk" if objective == "risk_mitigation" else ("CustomerExperience" if objective == "cx_improvement" else "Cost")
    origem = hints.origine or ("probleme_operationnel" if objective != "market_opportunity" else "enjeu_marche")

    tags = Tags(
        objectif={"value": objective, "confidence": "medium"},
        domaine=[{"value": domain, "confidence": "medium"}],
        impact=[{"value": impact, "confidence": "medium"}],
        origine={"value": origem, "confidence": "medium"},
    )

    pitch_summary = " ".join(pitch.strip().split())[:120]
    if len(pitch_summary) > 110:
        pitch_summary = pitch_summary[:110].rstrip() + "..."

    suggestions = [
        Suggestion(
            label="Reformulation",
            text=f"Clarify the need as: {pitch_summary}",
        ),
        Suggestion(
            label="Business Precision",
            text="Add a measurable target, owner, and deadline so the initiative can be evaluated.",
        ),
        Suggestion(
            label="Value Angle",
            text="State the expected business value in cost, risk, revenue, or customer experience terms.",
        ),
    ]
    return tags, suggestions


async def analyze_pitch(
    pitch: str,
    horizon: str | None = None,
) -> tuple[Tags, list[Suggestion]]:
    """Analyze a business need pitch and return structured tags and suggestions.

    Pipeline:
      1. L1 cache (in-memory, 5 min TTL)
      2. L2 cache (Postgres, 24 h TTL — survives restarts)
      3. Deterministic rule engine (pre-LLM)
      4. Horizon context (pre-LLM)
      5. Optional Langfuse trace + LLM (prompt includes rule + horizon hints)
      6. Deterministic overrides + horizon objectif correction (+ Langfuse pipeline metadata)
      7. Populate both cache layers
    """
    key = _make_key(pitch, horizon)

    # 1. L1 — in-memory (fastest)
    hit = _l1_get(key)
    if hit:
        logger.debug("L1 cache hit (horizon=%s)", horizon)
        return hit

    # 2. L2 — Postgres (survives restarts)
    hit = await _l2_get(key)
    if hit:
        _l1_set(key, *hit)   # warm L1 so subsequent requests skip DB
        return hit

    # 2. Deterministic rule engine — runs before the LLM call
    hints: RuleHints = apply_rules(pitch)
    rules_context = hints.to_prompt_context()

    # 3. Horizon context
    horizon_context = _build_horizon_context(horizon)

    # 4. Langfuse parent trace — same trace holds generation + post-LLM pipeline metadata
    trace_meta = {"cache_key_sha256_prefix": key[:16]}
    lf = new_langfuse_client()
    lf_trace = None
    if lf is not None:
        try:
            lf_trace = lf.trace(
                name="nlp_pitch_tagging",
                input={"pitch_preview": pitch[:280], "horizon": horizon},
                metadata=trace_meta,
            )
        except Exception as exc:
            logger.debug("Langfuse NLP trace init skipped (non-fatal): %s", exc)
            lf_trace = None

    # 5. LLM — inject rules_context + horizon_context
    try:
        response = await llm_client.complete(
            prompt_name="nlp_tagging",
            variables={
                "pitch": pitch,
                "rules_context": rules_context,
                "horizon_context": horizon_context,
                "explicit": "Classify the business need pitch into structured tags and suggest improvements.",
                "implicit": "Provide actionable, business-relevant suggestions for clarity and value.",
                "strategic": "Frame DXC as a trusted delivery partner in all suggestions.",
            },
            response_format="json",
            lf_parent_trace=lf_trace,
        )
        parsed = llm_client.parse_json_response(response)
        logger.info("LLM response keys: %s", list(parsed.keys()))
    except TimeoutError as exc:
        logger.warning("LLM analysis timed out; using deterministic fallback for analyze_pitch: %s", exc)
        tags, suggestions = _fallback_analyze_result(pitch, horizon, hints)
        _l1_set(key, tags, suggestions)
        await _l2_set(key, pitch, horizon, tags, suggestions)
        return tags, suggestions

    raw_tags = parsed.get("tags", parsed)  # support both nested and flat responses

    def _scalar(field: str, fallback_value: str) -> dict:
        raw = raw_tags.get(field)
        if isinstance(raw, dict):
            return {"value": raw.get("value", fallback_value), "confidence": raw.get("confidence", "low")}
        if isinstance(raw, str):
            return {"value": raw, "confidence": "low"}
        return {"value": fallback_value, "confidence": "low"}

    def _items(field: str) -> list[dict]:
        raw = raw_tags.get(field, [])
        result: list[dict] = []
        for item in raw:
            if isinstance(item, dict):
                result.append({"value": item.get("value", ""), "confidence": item.get("confidence", "low")})
            elif isinstance(item, str):
                result.append({"value": item, "confidence": "low"})
        return result or [{"value": "Autre", "confidence": "low"}]

    # Build mutable tag dict and apply rule overrides before Pydantic validation
    tag_dict: dict = {
        "objectif": _scalar("objectif", "cost_reduction"),
        "domaine":  _items("domaine"),
        "impact":   _items("impact"),
        "origine":  _scalar("origine", "probleme_operationnel"),
    }

    tags_pre_override = copy.deepcopy(tag_dict)

    tag_dict = _apply_rule_overrides(tag_dict, hints)
    after_rules = copy.deepcopy(tag_dict)

    tag_dict = _apply_horizon_override(tag_dict, horizon, hints)

    tag_dict = sanitize_pitch_tag_dict(tag_dict)

    def _objectif_blob(d: dict) -> str:
        return json.dumps(d.get("objectif"), sort_keys=True, default=str)

    horizon_override_fired = _objectif_blob(after_rules) != _objectif_blob(tag_dict)

    merge_trace_rule_pipeline(
        lf_trace,
        base_metadata=trace_meta,
        pitch_preview=pitch[:200],
        horizon=horizon,
        hints_payload={
            "origine_hint": hints.origine,
            "exclude_domaine": list(hints.exclude_domaine),
            "reasons": dict(hints.reasons),
            "has_overrides": hints.has_overrides,
        },
        tags_pre_override=tags_pre_override,
        tags_post_pipeline=tag_dict,
        horizon_override_fired=horizon_override_fired,
    )
    safe_flush(lf)

    tags = Tags(**tag_dict)

    # Parse suggestions
    suggestions: list[Suggestion] = []
    raw_suggestions = parsed.get("suggestions", [])
    logger.info("Raw suggestions count: %d", len(raw_suggestions))
    for s in raw_suggestions:
        if isinstance(s, dict) and "label" in s and "text" in s:
            suggestions.append(Suggestion(label=s["label"], text=s["text"]))

    logger.info("Parsed %d suggestions for pitch (len=%d)", len(suggestions), len(pitch))

    # 8. Populate both cache layers
    _l1_set(key, tags, suggestions)
    await _l2_set(key, pitch, horizon, tags, suggestions)

    return tags, suggestions
