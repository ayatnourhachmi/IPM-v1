"""Langfuse instrumentation helpers — prompt intent layers, rule overrides, score calibration."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from app.core.config import settings

logger = logging.getLogger(__name__)


def langfuse_credentials_configured() -> bool:
    return bool(
        (settings.langfuse_public_key or "").strip()
        and (settings.langfuse_secret_key or "").strip()
    )


def new_langfuse_client():
    """Return a Langfuse client or None if SDK missing / credentials unset."""
    if not langfuse_credentials_configured():
        return None
    try:
        from langfuse import Langfuse

        return Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception as exc:
        logger.warning("Langfuse client init failed (non-fatal): %s", exc)
        return None


def safe_flush(client: Any) -> None:
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        pass


def truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def filter_variables_for_metadata(variables: Mapping[str, str]) -> dict[str, str]:
    """Drop intent triple from duplicate storage (they appear on prompt_intent layered fields)."""
    skip = frozenset({"explicit", "implicit", "strategic"})
    out: dict[str, str] = {}
    for k, v in variables.items():
        if k in skip:
            continue
        vs = str(v)
        out[k] = truncate(vs, 4000)
    return dict(sorted(out.items()))


def attach_llm_generation(
    lf_trace: Any | None,
    *,
    prompt_name: str,
    model_label: str,
    system_prompt: str,
    user_prompt: str,
    intent_explicit: str,
    intent_implicit: str,
    intent_strategic: str,
    context_before_intent: str,
    variable_snapshot: Mapping[str, str],
    completion_text: str,
    usage: Mapping[str, int] | None = None,
) -> None:
    """Record model I/O plus intent-layer breakdown on an existing Langfuse trace."""
    if lf_trace is None:
        return
    try:
        meta = {
            "prompt_name": prompt_name,
            "llm_provider": settings.llm_provider,
            "prompt_intent": {
                "explicit": truncate(intent_explicit, 6000),
                "implicit": truncate(intent_implicit, 6000),
                "strategic": truncate(intent_strategic, 6000),
            },
            "prompt_template_filled_before_intent_wrap": truncate(context_before_intent, 14000),
            "prompt_substituted_variables": filter_variables_for_metadata(variable_snapshot),
            "usage_prompt_tokens": (usage or {}).get("prompt_tokens", 0),
            "usage_completion_tokens": (usage or {}).get("completion_tokens", 0),
        }
        lf_trace.generation(
            name=f"{prompt_name}_generation",
            model=model_label,
            input=[
                {"role": "system", "content": truncate(system_prompt, 32000)},
                {"role": "user", "content": truncate(user_prompt, 32000)},
            ],
            output=truncate(completion_text, 48000),
            metadata=meta,
        )
    except Exception as exc:
        logger.warning("Langfuse generation attach skipped (non-fatal): %s", exc)


def merge_trace_rule_pipeline(
    lf_trace: Any | None,
    *,
    base_metadata: Mapping[str, Any] | None = None,
    pitch_preview: str,
    horizon: str | None,
    hints_payload: Mapping[str, Any],
    tags_pre_override: Mapping[str, Any],
    tags_post_pipeline: Mapping[str, Any],
    horizon_override_fired: bool,
) -> None:
    """Log deterministic NLP rule overrides (post-LLM) on the tagging trace."""
    if lf_trace is None:
        return
    meta = dict(base_metadata or {})
    meta["nlp_rule_override_pipeline"] = {
        "pitch_preview": truncate(pitch_preview, 500),
        "horizon": horizon or "",
        "rule_engine_signals": dict(hints_payload),
        "tags_after_llm_pre_rule_override": dict(tags_pre_override),
        "tags_after_rule_pipeline": dict(tags_post_pipeline),
        "horizon_based_objectif_correction": horizon_override_fired,
    }
    try:
        lf_trace.update(metadata=meta)
    except Exception as exc:
        logger.warning("Langfuse rule_pipeline metadata skipped (non-fatal): %s", exc)
